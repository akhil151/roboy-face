"""
Personality model - expressive characteristics that influence every motion primitive.

Every emotional state defines a PersonalityProfile which encodes six
high-level expressive axes:

    Energy      - overall movement intensity / speed
    Warmth      - approachability / friendliness (curvature, softness)
    Attention   - look engagement / scan frequency
    Calmness    - inverse of jitter / shake / abruptness
    Amplitude   - gross movement size multiplier
    Blink Tendency - how often / how expressively the eyes blink

Instead of every state hardcoding its own breathing amplitude, bounce
frequency, drift speed, etc., states simply declare their personality and
the personality_adapter() derives concrete motion-primitive configuration
from those six numbers.

This keeps Phase 2B animation authoring declarative: "I want this state to
be HIGH energy, MEDIUM warmth, HIGH calmness" is all you write; the math
for what that means for each primitive's cfg is computed here.

The mapping is invertible and deterministic: the same personality profile
always produces the same derived primitive configs (no randomness here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import math

from .easing import clamp01, lerp
from .motion_primitives import (
    BreathingConfig,
    BounceConfig,
    DriftConfig,
    PulseConfig,
    SquashConfig,
    StretchConfig,
    LookScanConfig,
    IdleNoiseConfig,
    MicroCorrectionConfig,
    BlinkMotionConfig,
    OvershootConfig,
    SettleConfig,
)
from .spring import SpringConfig


# ---------------------------------------------------------------------------
# Core profile
# ---------------------------------------------------------------------------


@dataclass
class PersonalityProfile:
    """Six expressive axes that define a state's motion personality.

    All axes are unitless ratios in [0, 1].  0.5 is the "neutral baseline"
    inherited from the calm/default state.  Values outside [0,1] are
    clamped by the adaptor.
    """

    # High energy = faster, bigger, snappier motion.
    energy: float = 0.5
    # High warmth = more curvature, softer lids, more up-curve smiles.
    warmth: float = 0.5
    # High attention = more look scanning, faster look response.
    attention: float = 0.5
    # High calmness = low jitter, slow transitions, fewer micro-corrections.
    calmness: float = 0.5
    # High amplitude = bigger gross movements (multiplied across all primitives).
    amplitude: float = 0.5
    # High blink_tendency = more frequent, more expressive blinks.
    blink_tendency: float = 0.5

    def clamped(self) -> "PersonalityProfile":
        return PersonalityProfile(
            energy=clamp01(self.energy),
            warmth=clamp01(self.warmth),
            attention=clamp01(self.attention),
            calmness=clamp01(self.calmness),
            amplitude=clamp01(self.amplitude),
            blink_tendency=clamp01(self.blink_tendency),
        )

    # ------------------------------------------------------------------
    # Built-in profiles for convenience.
    # ------------------------------------------------------------------
    @classmethod
    def neutral(cls) -> "PersonalityProfile":
        return cls(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)

    @classmethod
    def excited(cls) -> "PersonalityProfile":
        return cls(0.92, 0.85, 0.78, 0.42, 0.88, 0.72)

    @classmethod
    def relaxed(cls) -> "PersonalityProfile":
        return cls(0.22, 0.62, 0.30, 0.88, 0.32, 0.52)

    @classmethod
    def focused(cls) -> "PersonalityProfile":
        return cls(0.55, 0.35, 0.95, 0.72, 0.48, 0.28)

    @classmethod
    def sleepy(cls) -> "PersonalityProfile":
        return cls(0.10, 0.42, 0.18, 0.92, 0.20, 0.78)

    @classmethod
    def surprised(cls) -> "PersonalityProfile":
        return cls(0.95, 0.60, 0.88, 0.20, 0.92, 0.85)

    @classmethod
    def sad(cls) -> "PersonalityProfile":
        return cls(0.20, 0.55, 0.28, 0.78, 0.30, 0.58)

    @classmethod
    def caring(cls) -> "PersonalityProfile":
        return cls(0.45, 0.92, 0.72, 0.76, 0.50, 0.62)

    @classmethod
    def speaking(cls) -> "PersonalityProfile":
        return cls(0.80, 0.68, 0.60, 0.50, 0.70, 0.50)

    @classmethod
    def thinking(cls) -> "PersonalityProfile":
        return cls(0.40, 0.40, 0.82, 0.68, 0.40, 0.42)


# ---------------------------------------------------------------------------
# Derived motion timing - derived from personality once per state.
# ---------------------------------------------------------------------------


@dataclass
class DerivedTiming:
    """Temporal characteristics derived from the personality profile."""
    # Global multiplier for all durations.  >1 = slower.  <1 = snappier.
    duration_scale: float = 1.0
    # Spring characteristic frequency multiplier for all springs.
    spring_freq_scale: float = 1.0
    # Blink interval multiplier: >1 = less frequent, <1 = more frequent.
    blink_interval_scale: float = 1.0
    # Blink amplitude multiplier (for expressive blinks).
    blink_amplitude_scale: float = 1.0
    # Micro-motion speed multiplier.
    micro_speed_scale: float = 1.0
    # Entry/exit transition duration override (ms, or None = use engine default).
    transition_override_ms: Optional[float] = None


@dataclass
class DerivedAmplitudes:
    """Amplitude multipliers for each motion primitive category."""
    breathing: float = 1.0
    bounce: float = 1.0
    drift: float = 1.0
    pulse: float = 1.0
    squash: float = 1.0
    stretch: float = 1.0
    scan: float = 1.0
    idle_noise: float = 1.0
    micro_correction: float = 1.0
    blink_motion: float = 1.0
    overshoot: float = 1.0
    settle: float = 1.0


# ---------------------------------------------------------------------------
# Adaptor: pure function to derive primitive configs from a personality.
# ---------------------------------------------------------------------------


def _signed_bias(axis_01: float, baseline: float, range_lo: float, range_hi: float) -> float:
    """Map axis_01 in [0,1] -> [baseline-range_lo, baseline+range_hi] centered at 0.5."""
    signed = clamp01(axis_01) - 0.5  # in [-0.5, 0.5]
    if signed >= 0:
        return baseline + signed * 2.0 * range_hi
    return baseline + signed * 2.0 * range_lo


class PersonalityAdaptor:
    """Derives concrete motion-primitive configurations from a PersonalityProfile.

    The adaptor is STATeless - call ``adapt(profile)`` to produce a bundle
    of configured primitive configs and timing characteristics.  The same
    profile always produces the same bundle (deterministic, no RNG).
    """

    # Baseline neutral-values at personality=0.5 across every axis.
    BASE_DURATION_SCALE = 1.0
    BASE_SPRING_FREQ = 1.0
    BASE_BLINK_INTERVAL = 1.0
    BASE_BLINK_AMP = 1.0
    BASE_MICRO_SPEED = 1.0

    @staticmethod
    def derive_timing(p: PersonalityProfile) -> DerivedTiming:
        p = p.clamped()
        # Duration: high energy = snappier (duration_scale < 1).
        duration_scale = _signed_bias(p.energy, 1.0, 0.45, -0.40)
        duration_scale *= _signed_bias(p.calmness, 1.0, -0.10, 0.35)
        # Spring frequency: high energy = stiffer springs.
        spring_freq = _signed_bias(p.energy, 1.0, -0.30, 0.55)
        spring_freq *= _signed_bias(p.attention, 1.0, -0.15, 0.35)
        # Blink interval: high blink_tendency = MORE frequent (scale < 1).
        blink_interval = _signed_bias(p.blink_tendency, 1.0, 0.55, -0.38)
        blink_interval *= _signed_bias(p.calmness, 1.0, -0.10, 0.25)
        # Blink amplitude: high energy + high blink_tendency = expressive blinks.
        blink_amp = _signed_bias(p.blink_tendency, 1.0, -0.30, 0.60)
        blink_amp *= _signed_bias(p.energy, 1.0, -0.20, 0.45)
        # Micro speed: energy drives it up, calmness drives it down.
        micro_speed = _signed_bias(p.energy, 1.0, -0.40, 0.50)
        micro_speed *= _signed_bias(p.calmness, 1.0, 0.25, -0.25)
        # Transition override for extreme personalities.
        transition_ms: Optional[float] = None
        if p.calmness > 0.85:
            transition_ms = 500.0
        elif p.energy > 0.88:
            transition_ms = 280.0
        return DerivedTiming(
            duration_scale=max(0.45, min(2.2, duration_scale)),
            spring_freq_scale=max(0.4, min(2.5, spring_freq)),
            blink_interval_scale=max(0.40, min(2.5, blink_interval)),
            blink_amplitude_scale=max(0.5, min(2.0, blink_amp)),
            micro_speed_scale=max(0.35, min(2.2, micro_speed)),
            transition_override_ms=transition_ms,
        )

    @staticmethod
    def derive_amplitudes(p: PersonalityProfile) -> DerivedAmplitudes:
        p = p.clamped()
        amp_core = _signed_bias(p.amplitude, 1.0, -0.55, 0.80)
        energy = p.energy
        calm = p.calmness
        attn = p.attention
        warm = p.warmth
        blink = p.blink_tendency

        breathing = amp_core * _signed_bias(calm, 1.0, 0.30, -0.20)
        bounce = amp_core * _signed_bias(energy, 1.0, -0.60, 0.90) * _signed_bias(amp_core, 1.0, -0.20, 0.20)
        drift = amp_core * _signed_bias(calm, 1.0, 0.40, -0.35) * _signed_bias(1.0 - attn, 1.0, 0.0, 0.35)
        pulse = amp_core * _signed_bias(energy, 1.0, -0.70, 0.95) * _signed_bias(1.0 - calm, 1.0, 0.0, 0.30)
        squash = amp_core * _signed_bias(energy, 1.0, -0.50, 0.80) * _signed_bias(warm, 1.0, -0.10, 0.25)
        stretch = amp_core * _signed_bias(energy, 1.0, -0.50, 0.80) * _signed_bias(attn, 1.0, -0.10, 0.30)
        scan = amp_core * _signed_bias(attn, 1.0, -0.75, 0.85) * _signed_bias(energy, 1.0, -0.20, 0.30)
        idle_noise = amp_core * _signed_bias(1.0 - calm, 1.0, -0.60, 0.90) * _signed_bias(energy, 1.0, -0.20, 0.20)
        micro_correction = amp_core * _signed_bias(1.0 - calm, 1.0, -0.55, 0.85)
        blink_motion = amp_core * _signed_bias(blink, 1.0, -0.55, 0.85) * _signed_bias(energy, 1.0, -0.20, 0.40)
        overshoot = _signed_bias(energy, 1.0, -0.35, 0.45) * _signed_bias(1.0 - calm, 1.0, -0.15, 0.35)
        settle = _signed_bias(calm, 1.0, -0.30, 0.40)

        return DerivedAmplitudes(
            breathing=max(0.1, min(3.0, breathing)),
            bounce=max(0.0, min(3.5, bounce)),
            drift=max(0.05, min(3.0, drift)),
            pulse=max(0.0, min(3.5, pulse)),
            squash=max(0.0, min(3.0, squash)),
            stretch=max(0.0, min(3.0, stretch)),
            scan=max(0.0, min(3.0, scan)),
            idle_noise=max(0.0, min(3.0, idle_noise)),
            micro_correction=max(0.0, min(3.0, micro_correction)),
            blink_motion=max(0.1, min(2.5, blink_motion)),
            overshoot=max(0.2, min(2.0, overshoot)),
            settle=max(0.5, min(2.0, settle)),
        )

    # ------------------------------------------------------------------
    # Full bundle: concrete primitive configs ready to use.
    # ------------------------------------------------------------------

    @classmethod
    def adapt(cls, p: PersonalityProfile) -> "PersonalityBundle":
        timing = cls.derive_timing(p)
        amps = cls.derive_amplitudes(p)
        freq = timing.spring_freq_scale
        micro_s = timing.micro_speed_scale

        # Baseline primitive configs, scaled by personality.
        breathing_cfg = BreathingConfig(
            amplitude=0.012 * amps.breathing,
            period_seconds=4.5 / max(0.5, micro_s * 0.8 + 0.2),
            y_offset_px=0.5 * amps.breathing,
            depth_wobble=0.003 * amps.breathing,
        )
        bounce_cfg = BounceConfig(
            amplitude_px=3.0 * amps.bounce,
            frequency_hz=0.9 * micro_s,
            weight=lerp(0.5, 0.85, p.energy),
            squash_on_landing=0.04 * amps.squash,
            stretch_on_rise=0.02 * amps.stretch,
        )
        drift_cfg = DriftConfig(
            amplitude_px=1.2 * amps.drift,
            period_seconds=11.0 / max(0.4, micro_s * 0.7 + 0.3),
            harmonic_count=3,
            harmonic_decay=0.55,
            vertical_ratio=0.75,
        )
        pulse_cfg = PulseConfig(
            amplitude_scale=0.04 * amps.pulse,
            amplitude_glow=0.15 * amps.pulse,
            amplitude_radius=1.5 * amps.pulse,
            frequency_hz=1.4 * micro_s,
            attack_ratio=lerp(0.28, 0.14, p.energy),
            decay_exponent=lerp(2.2, 3.6, p.calmness),
            jitter_amount=lerp(0.05, 0.22, 1.0 - p.calmness),
        )
        squash_cfg = SquashConfig(
            amount=0.12 * amps.squash,
            vertical_peak=0.5,
            preserve_area=True,
            curvature_bias=lerp(0.05, 0.45, p.warmth),
        )
        stretch_cfg = StretchConfig(
            amount=0.10 * amps.stretch,
            vertical_peak=0.5,
            preserve_area=True,
            curvature_bias=lerp(-0.05, -0.35, p.attention),
        )
        scan_cfg = LookScanConfig(
            sweep_amplitude=18.0 * amps.scan,
            vertical_amplitude=8.0 * amps.scan,
            saccade_hz=0.55 * freq,
            pause_ratio=lerp(0.50, 0.25, p.attention),
            spring_config=SpringConfig(
                stiffness=lerp(260.0, 520.0, p.energy),
                damping=lerp(48.0, 36.0, p.attention),
                mass=1.0,
            ),
        )
        idle_noise_cfg = IdleNoiseConfig(
            position_px=0.35 * amps.idle_noise,
            scale_amount=0.0025 * amps.idle_noise,
            radius_px=0.25 * amps.idle_noise,
            rotation_deg=0.12 * amps.idle_noise,
            speed=0.8 * micro_s,
        )
        micro_corr_cfg = MicroCorrectionConfig(
            chance_per_second=lerp(0.10, 0.65, 1.0 - p.calmness),
            max_offset_px=0.6 * amps.micro_correction,
            settle_duration_ms=lerp(180.0, 90.0, p.energy),
            interval_min_seconds=lerp(0.8, 2.2, p.calmness),
            interval_max_seconds=lerp(3.0, 6.0, p.calmness),
        )
        blink_motion_cfg = BlinkMotionConfig(
            compression_amount=0.04 * amps.blink_motion,
            expansion_amount=0.025 * amps.blink_motion,
            squash_on_close=0.06 * amps.blink_motion,
            y_offset_px=0.8 * amps.blink_motion,
            curvature_surge=0.15 * amps.blink_motion * (0.6 + p.warmth * 0.8),
        )
        overshoot_cfg = OvershootConfig(
            anticipation_amount=0.08 * amps.overshoot,
            overshoot_amount=0.12 * amps.overshoot,
            overshoot_peak=lerp(0.65, 0.45, p.energy),
        )
        settle_cfg = SettleConfig(
            stiffness=lerp(140.0, 360.0, p.energy) * freq,
            damping=lerp(38.0, 22.0, 1.0 - p.calmness),
            mass=1.0,
            snap_threshold=lerp(0.003, 0.0005, p.calmness),
        )
        return PersonalityBundle(
            profile=p.clamped(),
            timing=timing,
            amplitudes=amps,
            breathing=breathing_cfg,
            bounce=bounce_cfg,
            drift=drift_cfg,
            pulse=pulse_cfg,
            squash=squash_cfg,
            stretch=stretch_cfg,
            scan=scan_cfg,
            idle_noise=idle_noise_cfg,
            micro_correction=micro_corr_cfg,
            blink_motion=blink_motion_cfg,
            overshoot=overshoot_cfg,
            settle=settle_cfg,
        )


@dataclass
class PersonalityBundle:
    """Complete set of configured motion primitives for a personality.

    Phase 2B states will instantiate one bundle via PersonalityAdaptor.adapt()
    and use its ``breathing``, ``bounce``, ... config objects directly as
    arguments to the motion primitive apply_* functions.
    """
    profile: PersonalityProfile
    timing: DerivedTiming
    amplitudes: DerivedAmplitudes
    breathing: BreathingConfig
    bounce: BounceConfig
    drift: DriftConfig
    pulse: PulseConfig
    squash: SquashConfig
    stretch: StretchConfig
    scan: LookScanConfig
    idle_noise: IdleNoiseConfig
    micro_correction: MicroCorrectionConfig
    blink_motion: BlinkMotionConfig
    overshoot: OvershootConfig
    settle: SettleConfig

    # ------------------------------------------------------------------
    # Convenience: factory from a profile.
    # ------------------------------------------------------------------
    @classmethod
    def from_profile(cls, profile: PersonalityProfile) -> "PersonalityBundle":
        return PersonalityAdaptor.adapt(profile)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "PersonalityProfile",
    "DerivedTiming",
    "DerivedAmplitudes",
    "PersonalityAdaptor",
    "PersonalityBundle",
]
