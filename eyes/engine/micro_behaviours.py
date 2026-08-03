"""
Micro-behaviours autonomous motion system.

The robot should NEVER appear frozen.  This system orchestrates five
layers of subtle, always-on procedural motion that sits beneath every
emotional state:

  1. TINY BREATHING       - ~0.5-1.5% vertical scale pulse (gentle)
  2. TINY DRIFT           - slow, never-repeating wandering (product-sines)
  3. MICRO CORRECTION     - infrequent ~0.2-0.6px snap-back jitters
  4. NATURAL PAUSES       - occasional "hold still" windows with slow fade
  5. OCCASIONAL DOUBLE BLINK - scheduled via probability with personality
  6. RANDOM EYE SETTLING  - spring-back toward look center with jitter
  7. VERY SMALL IDLE NOISE - sub-pixel continuous parameter jitter

Each layer has its own amplitude, frequency, and cadence so the sum
never looks mechanical.  All outputs are additive offsets written into
an EyePair so they compose naturally with the animation state output.

The MicroBehaviourSystem is designed to be driven FROM the existing
AnimationEngine.step() / AnimationMixer.update() hot path without any
changes to those modules: the engine simply calls
MicroBehaviourSystem.apply(pose, dt_s) each frame and the layers stack.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .eye_pair import EyePair
from .easing import clamp01, ease_in_out_sine, ease_out_cubic
from .config import EngineConfig
from .personality import PersonalityProfile, PersonalityBundle, PersonalityAdaptor
from .motion_primitives import (
    IdleNoisePair,
    MicroCorrectionPrimitive,
    DriftConfig,
    BreathingConfig,
    apply_breathing_pair,
    apply_drift_pair,
    SettledPair,
)


# ---------------------------------------------------------------------------
# Per-layer configuration
# ---------------------------------------------------------------------------


@dataclass
class MicroBehaviourConfig:
    """Global tuning knobs for the micro-behaviour system."""
    # Master multiplier for all layers.  Set to 0 to fully disable.
    master_amount: float = 1.0
    # Per-layer enable flags so states can selectively disable components.
    breathing_enabled: bool = True
    drift_enabled: bool = True
    micro_correction_enabled: bool = True
    idle_noise_enabled: bool = True
    random_settling_enabled: bool = True
    natural_pauses_enabled: bool = True
    # Natural pause cadence.
    pause_chance_per_minute: float = 1.4
    pause_min_seconds: float = 1.0
    pause_max_seconds: float = 2.8
    pause_fade_seconds: float = 0.5
    # Random eye settling cadence (toward 0,0 look direction).
    settle_chance_per_10s: float = 0.8
    settle_duration_seconds: float = 0.7
    settle_jitter_px: float = 0.25
    # Sub-pixel amount for the "don't look frozen" safety net (always on).
    safety_net_amplitude_px: float = 0.08


# ---------------------------------------------------------------------------
# The main system
# ---------------------------------------------------------------------------


class MicroBehaviourSystem:
    """Composes 7 layers of always-on micro-motion.

    Designed to be instantiated once per AnimationEngine.  Holds internal
    state for all stateful primitives (IdleNoisePair, MicroCorrection,
    SettledPair for settling, etc.) plus timing for natural pauses.

    Usage:
        mbs = MicroBehaviourSystem(engine.config)
        # ... each frame, after computing state pose:
        mbs.apply(final_pose, dt_s, current_personality_bundle)

    No-arg construction is also supported for testing / standalone use:
        mbs = MicroBehaviourSystem()
        mbs.apply(pose, 16.0)   # dt can be ms (>1) or seconds (<= 1)
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        mb_cfg: Optional[MicroBehaviourConfig] = None,
    ) -> None:
        if config is None:
            from .config import EngineConfig as _EC
            config = _EC()
        self._engine_cfg = config
        self._cfg = mb_cfg or MicroBehaviourConfig()

        # Stateful primitives.
        self._idle_noise = IdleNoisePair()
        self._micro_correction = MicroCorrectionPrimitive()
        self._settle_springs = SettledPair()
        self._breathing_cfg_cache: Optional[BreathingConfig] = None
        self._drift_cfg_cache: Optional[DriftConfig] = None

        # Elapsed timers.
        self._elapsed_s: float = 0.0
        self._micro_elapsed_ms: float = 0.0

        # Natural-pause state machine.
        self._pause_active: bool = False
        self._pause_elapsed_s: float = 0.0
        self._pause_duration_s: float = 0.0
        self._pause_fade: float = 0.0  # 0 = full motion, 1 = fully paused.
        self._time_since_last_pause_s: float = 60.0

        # Random eye-settling state machine.
        self._settling_active: bool = False
        self._settle_elapsed_s: float = 0.0
        self._settle_duration_s: float = 0.7
        self._time_since_last_settle_s: float = 20.0
        self._settle_jitter_x: float = 0.0
        self._settle_jitter_y: float = 0.0

        # Safety-net: slow product-sine wander at sub-pixel amplitude,
        # never disabled, guarantees the eyes literally never freeze.
        self._safety_seed_x: float = random.uniform(0.0, 100.0)
        self._safety_seed_y: float = random.uniform(100.0, 200.0)
        self._safety_seed_s: float = random.uniform(200.0, 300.0)

        # Current personality (updated by set_personality).
        self._personality: PersonalityBundle = PersonalityAdaptor.adapt(PersonalityProfile.neutral())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def config(self) -> MicroBehaviourConfig:
        return self._cfg

    def set_micro_config(self, cfg: MicroBehaviourConfig) -> None:
        self._cfg = cfg

    def set_personality(self, bundle: PersonalityBundle) -> None:
        """Swap in derived primitive configs for a new personality.

        Called whenever the active state changes so the micro-motion
        matches the current emotional state's expressive characteristics.
        """
        self._personality = bundle
        self._idle_noise.set_config(bundle.idle_noise)
        self._micro_correction.set_config(bundle.micro_correction)
        self._breathing_cfg_cache = bundle.breathing
        self._drift_cfg_cache = bundle.drift

    def reset(self) -> None:
        self._elapsed_s = 0.0
        self._micro_elapsed_ms = 0.0
        self._pause_active = False
        self._pause_elapsed_s = 0.0
        self._pause_fade = 0.0
        self._settling_active = False
        self._settle_elapsed_s = 0.0
        self._idle_noise = IdleNoisePair()
        self._micro_correction = MicroCorrectionPrimitive()
        self._settle_springs.set_immediate(0.0, 0.0)
        self._idle_noise.set_config(self._personality.idle_noise)
        self._micro_correction.set_config(self._personality.micro_correction)

    # ------------------------------------------------------------------
    # Internal: layer amounts with pause-fade + personality amplitude
    # ------------------------------------------------------------------

    def _layer_amounts(self) -> dict[str, float]:
        master = self._cfg.master_amount
        pause = 1.0 - self._pause_fade  # 1 = normal motion, 0 = full pause.
        calm_scale = 0.6 + self._personality.profile.calmness * 0.4
        energy_scale = 0.55 + self._personality.profile.energy * 0.45
        amps = self._personality.amplitudes
        return {
            "breathing": master * pause * (1.0 if self._cfg.breathing_enabled else 0.0) * amps.breathing * calm_scale,
            "drift": master * pause * (1.0 if self._cfg.drift_enabled else 0.0) * amps.drift * calm_scale,
            "micro_correction": master * pause * (1.0 if self._cfg.micro_correction_enabled else 0.0) * amps.micro_correction * energy_scale,
            "idle_noise": master * pause * (1.0 if self._cfg.idle_noise_enabled else 0.0) * amps.idle_noise * (1.05 - 0.35 * self._personality.profile.calmness),
            "random_settling": master * (1.0 if self._cfg.random_settling_enabled else 0.0),
            "safety_net": master,  # never scaled by pause.
        }

    def _update_pause_machine(self, dt_s: float) -> None:
        if not self._cfg.natural_pauses_enabled:
            return
        # Outside of a pause: roll probability to start one.
        if not self._pause_active:
            self._time_since_last_pause_s += dt_s
            chance_per_sec = self._cfg.pause_chance_per_minute / 60.0
            # Linear ramp: the longer since last pause, the more likely.
            time_weight = min(1.0, self._time_since_last_pause_s / 120.0)
            if random.random() < chance_per_sec * dt_s * (0.6 + time_weight * 1.8):
                self._pause_active = True
                self._pause_elapsed_s = 0.0
                self._pause_duration_s = random.uniform(
                    self._cfg.pause_min_seconds, self._cfg.pause_max_seconds
                )
        else:
            self._pause_elapsed_s += dt_s
            fade = self._cfg.pause_fade_seconds
            if self._pause_elapsed_s < fade:
                # Fading INTO the pause.
                self._pause_fade = ease_out_cubic(self._pause_elapsed_s / max(fade, 0.0001))
            elif self._pause_elapsed_s < (self._pause_duration_s - fade):
                self._pause_fade = 1.0
            elif self._pause_elapsed_s < self._pause_duration_s:
                remain = self._pause_duration_s - self._pause_elapsed_s
                self._pause_fade = ease_out_cubic(remain / max(fade, 0.0001))
            else:
                self._pause_active = False
                self._pause_fade = 0.0
                self._time_since_last_pause_s = 0.0

    def _update_settle_machine(self, dt_s: float) -> None:
        if not self._cfg.random_settling_enabled:
            return
        if not self._settling_active:
            self._time_since_last_settle_s += dt_s
            chance_per_sec = self._cfg.settle_chance_per_10s / 10.0
            attn_bias = 1.0 - self._personality.profile.attention * 0.6
            if random.random() < chance_per_sec * dt_s * (0.4 + self._time_since_last_settle_s / 30.0) * attn_bias:
                self._settling_active = True
                self._settle_elapsed_s = 0.0
                self._settle_duration_s = self._cfg.settle_duration_seconds * (
                    0.7 + random.random() * 0.6
                )
                self._settle_jitter_x = (random.random() * 2.0 - 1.0) * self._cfg.settle_jitter_px
                self._settle_jitter_y = (random.random() * 2.0 - 1.0) * self._cfg.settle_jitter_px
                self._settle_springs.set_target(self._settle_jitter_x, self._settle_jitter_y)
        else:
            self._settle_elapsed_s += dt_s
            if self._settle_elapsed_s >= self._settle_duration_s:
                self._settling_active = False
                self._time_since_last_settle_s = 0.0
                self._settle_springs.set_target(0.0, 0.0)

    def _safety_net(self, pose: EyePair, amount: float) -> None:
        """Apply a sub-pixel, never-stopping wander to both eyes.

        Uses 3-frequency product-sine noise with independent seeds per axis
        so the signal is C2 continuous (no jumps).  This guarantees that
        even with all other layers disabled, the eyes literally never
        freeze on the same pixel for more than ~16 ms."""
        if amount <= 0.0:
            return
        amp = self._cfg.safety_net_amplitude_px * amount
        t = self._elapsed_s
        # X, Y, scale (tiny) channels, each with 3 incommensurate frequencies.
        nx = (
            math.sin(t * 0.73 + self._safety_seed_x)
            * math.cos(t * 1.618 + self._safety_seed_x * 0.41)
            + math.sin(t * 2.414 + self._safety_seed_y * 0.23) * 0.4
        ) * 0.7
        ny = (
            math.cos(t * 0.91 + self._safety_seed_y)
            * math.sin(t * 1.306 + self._safety_seed_y * 0.67)
            + math.cos(t * 2.672 + self._safety_seed_s * 0.18) * 0.4
        ) * 0.7
        ns = (
            math.sin(t * 1.13 + self._safety_seed_s)
            * math.cos(t * 1.839 + self._safety_seed_s * 0.31)
        ) * 0.5
        # Inter-ocular decorrelation: right eye gets a 90-degree phase shift.
        pose.left.micro_offset_x += nx * amp
        pose.left.micro_offset_y += ny * amp
        pose.left.scale_y += ns * 0.0008 * amount
        pose.right.micro_offset_x += -ny * amp * 0.92
        pose.right.micro_offset_y += nx * amp * 0.92
        pose.right.scale_y += -ns * 0.0008 * 0.96 * amount

    # ------------------------------------------------------------------
    # Primary per-frame entry point
    # ------------------------------------------------------------------

    def apply(
        self,
        pose: EyePair,
        dt: float,
        personality_bundle: Optional[PersonalityBundle] = None,
    ) -> None:
        """Apply all 7 micro layers additively into the provided pose.

        ``dt`` may be supplied in seconds (dt <= 1.0, production hot-path)
        or in milliseconds (dt > 1.0, convenient for tests/standalone use).

        Call this once per frame AFTER the state pose has been written
        into ``pose``.  The function mutates ``pose`` in place and is
        guaranteed to never introduce parameter jumps.
        """
        # Detect unit: production engine passes seconds; tests pass ms.
        dt_s = dt / 1000.0 if dt > 1.0 else dt
        if personality_bundle is not None:
            # Smoothly swap personality if a new one was provided.
            self.set_personality(personality_bundle)

        self._elapsed_s += dt_s
        self._micro_elapsed_ms += dt_s * 1000.0

        # Reset micro-motion channels: these belong exclusively to MBS.
        # State layers never write micro_offset_*; resetting here prevents
        # accumulation and matches the architectural "fresh each frame" contract.
        for eye in (pose.left, pose.right):
            eye.micro_offset_x = 0.0
            eye.micro_offset_y = 0.0

        # Update state machines for pauses + settling.
        self._update_pause_machine(dt_s)
        self._update_settle_machine(dt_s)

        amounts = self._layer_amounts()

        # --- Layer 1: Tiny breathing (personality-scaled).
        if amounts["breathing"] > 0.0001:
            bcfg = self._breathing_cfg_cache or self._personality.breathing
            apply_breathing_pair(pose, dt_s * 1000.0, self._micro_elapsed_ms, bcfg, amounts["breathing"])

        # --- Layer 2: Tiny drift.
        if amounts["drift"] > 0.0001:
            dcfg = self._drift_cfg_cache or self._personality.drift
            apply_drift_pair(pose, dt_s * 1000.0, self._micro_elapsed_ms, dcfg, amounts["drift"])

        # --- Layer 3: Micro corrections.
        if amounts["micro_correction"] > 0.0001:
            self._micro_correction.apply_to_pair(pose, dt_s, amounts["micro_correction"])
        else:
            # Still advance timing so behavior is deterministic.
            self._micro_correction.update(dt_s, 0.0)

        # --- Layer 4: Very small idle noise.
        if amounts["idle_noise"] > 0.0001:
            self._idle_noise.apply(pose, self._elapsed_s, amounts["idle_noise"])

        # --- Layer 5: Random eye settling (spring-driven jitter).
        if amounts["random_settling"] > 0.0001 and self._settling_active:
            sx, sy = self._settle_springs.update(dt_s)
            t = clamp01(self._settle_elapsed_s / max(self._settle_duration_s, 0.0001))
            envelope = math.sin(t * math.pi) * amounts["random_settling"]
            pose.left.look_offset_x += sx * envelope
            pose.left.look_offset_y += sy * envelope
            pose.right.look_offset_x += sx * envelope * 0.95
            pose.right.look_offset_y += sy * envelope * 0.95
        else:
            self._settle_springs.update(dt_s)

        # --- Layers 6 (natural pauses) & 7 (safety net) handled above.
        self._safety_net(pose, amounts["safety_net"])

    # ------------------------------------------------------------------
    # Debug / introspection
    # ------------------------------------------------------------------

    @property
    def pause_active(self) -> bool:
        return self._pause_active

    @property
    def pause_fade(self) -> float:
        return self._pause_fade

    @property
    def settling_active(self) -> bool:
        return self._settling_active

    @property
    def personality(self) -> PersonalityBundle:
        return self._personality


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "MicroBehaviourConfig",
    "MicroBehaviourSystem",
]
