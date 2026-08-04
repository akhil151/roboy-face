"""
Reusable Animation Direction Framework for ELO Educational Robot.

Provides Disney/Pixar-style animation direction and choreography tools,
composing existing Motion Primitives, Animation Clips, Motion Curves,
Personality Profiles, and Emotion Blending without modifying engine architecture.

Key Components:
  - StageConfig / StageType: Explicit ENTER, LOOP, EXIT stage parameters.
  - AnimationDirection: State-agnostic parameter configuration container.
  - Choreography Helpers: 16 reusable motion helpers (Attention Gain/Release,
    Emotional Settle, Eye Compression/Expansion, Curious Tilt, Double Blink, etc.).
  - Sequencing Helpers: ChoreographyStep & ChoreographySequence builder.
  - Timing Helpers: Principles of animation timing (anticipation, overshoot,
    follow_through, hold, settle).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from .eye_pair import EyePair
from .easing import (
    EasingFunction,
    ease_in_out_cubic,
    ease_out_cubic,
    ease_in_cubic,
    ease_out_back,
    clamp01,
    lerp,
)
from .motion_curves import PROPERTY_CURVES, cinematic_delta
from .personality import PersonalityProfile, PersonalityBundle, PersonalityAdaptor
from .motion_primitives import (
    BreathingConfig,
    BounceConfig,
    OvershootConfig,
    SettleConfig,
    DriftConfig,
    PulseConfig,
    SquashConfig,
    StretchConfig,
    LookScanConfig,
    BlinkMotionConfig,
    AttentionShiftConfig,
    SettledPair,
    LookScanPrimitive,
    AttentionShiftPrimitive,
    apply_breathing_pair,
    apply_bounce_pair,
    apply_drift_pair,
    apply_pulse_pair,
    apply_squash_pair,
    apply_stretch_pair,
    apply_blink_compression_pair,
    overshoot_envelope,
)


# ---------------------------------------------------------------------------
# Stage Definitions (ENTER, LOOP, EXIT)
# ---------------------------------------------------------------------------

class StageType(Enum):
    ENTER = "enter"
    LOOP = "loop"
    EXIT = "exit"


@dataclass
class StageConfig:
    """Configuration for a single stage (ENTER, LOOP, EXIT) of an animation."""
    stage_type: StageType = StageType.LOOP
    duration_ms: float = 300.0
    motion_intensity: float = 1.0
    emotion_intensity: float = 1.0
    primary_motion: str = "breathing"      # "bounce", "pulse", "stretch", "scan", "breathing", "none"
    secondary_motion: str = "drift"        # "drift", "micro", "none"
    blink_behaviour: str = "normal"        # "soft", "fast", "double", "normal", "suppressed"
    breathing_behaviour: str = "normal"    # "normal", "deep", "rapid", "disabled"
    look_behaviour: str = "centered"       # "centered", "scan", "shift", "lock"
    pause_timing_ms: float = 0.0
    overshoot_amount: float = 0.10
    settle_speed: float = 1.0


# ---------------------------------------------------------------------------
# AnimationDirection Data Structure
# ---------------------------------------------------------------------------

@dataclass
class AnimationDirection:
    """Reusable Animation Direction profile.

    States configure this data structure rather than hardcoding state logic.
    Provides timing, intensity, motion curve, and emotional axes.
    """
    enter_duration: float = 350.0
    exit_duration: float = 280.0
    hold_duration: float = 0.0
    breathing_strength: float = 1.0
    bounce_strength: float = 0.0
    blink_style: str = "normal"            # "soft", "fast", "double", "normal"
    look_style: str = "centered"           # "centered", "scan", "shift", "lock"
    attention_speed: float = 1.0
    settle_speed: float = 1.0
    overshoot_amount: float = 0.10
    motion_curve: str = "cinematic"
    energy: float = 0.5
    warmth: float = 0.5
    confidence: float = 0.5
    curiosity: float = 0.5
    calmness: float = 0.5
    enter_stage: Optional[StageConfig] = field(default=None)
    loop_stage: Optional[StageConfig] = field(default=None)
    exit_stage: Optional[StageConfig] = field(default=None)
    # Structured metadata for future AI behavior integration
    emotion_goal: str = ""
    viewer_response: str = ""
    attention_style: str = ""
    interaction_style: str = ""
    signature_motion: str = ""

    def __post_init__(self) -> None:
        if self.enter_stage is None:
            self.enter_stage = StageConfig(
                stage_type=StageType.ENTER,
                duration_ms=self.enter_duration,
                overshoot_amount=self.overshoot_amount,
                settle_speed=self.settle_speed,
            )
        if self.loop_stage is None:
            self.loop_stage = StageConfig(
                stage_type=StageType.LOOP,
                duration_ms=0.0,  # Infinite loop
                motion_intensity=1.0,
                blink_behaviour=self.blink_style,
                look_behaviour=self.look_style,
            )
        if self.exit_stage is None:
            self.exit_stage = StageConfig(
                stage_type=StageType.EXIT,
                duration_ms=self.exit_duration,
                settle_speed=self.settle_speed,
            )

    @classmethod
    def from_personality(
        cls,
        profile: PersonalityProfile,
        blink_style: str = "normal",
        look_style: str = "centered",
    ) -> AnimationDirection:
        """Construct AnimationDirection configured from a PersonalityProfile."""
        p = profile.clamped()
        bundle = PersonalityAdaptor.adapt(p)
        dur_scale = bundle.timing.duration_scale

        return cls(
            enter_duration=350.0 * dur_scale,
            exit_duration=280.0 * dur_scale,
            hold_duration=0.0,
            breathing_strength=bundle.amplitudes.breathing,
            bounce_strength=bundle.amplitudes.bounce,
            blink_style=blink_style,
            look_style=look_style,
            attention_speed=bundle.amplitudes.scan,
            settle_speed=1.0 / max(0.1, dur_scale),
            overshoot_amount=0.10 * bundle.amplitudes.overshoot,
            energy=p.energy,
            warmth=p.warmth,
            confidence=p.amplitude,
            curiosity=p.attention,
            calmness=p.calmness,
        )

    def to_personality_profile(self) -> PersonalityProfile:
        """Extract matching PersonalityProfile from direction fields."""
        return PersonalityProfile(
            energy=self.energy,
            warmth=self.warmth,
            attention=self.curiosity,
            calmness=self.calmness,
            amplitude=self.confidence,
            blink_tendency=0.5,
        ).clamped()

    def get_stage(self, stage_type: StageType) -> StageConfig:
        if stage_type == StageType.ENTER:
            return self.enter_stage or StageConfig(StageType.ENTER, self.enter_duration)
        elif stage_type == StageType.LOOP:
            return self.loop_stage or StageConfig(StageType.LOOP, 0.0)
        else:
            return self.exit_stage or StageConfig(StageType.EXIT, self.exit_duration)


# ---------------------------------------------------------------------------
# Timing Helpers (Animation Principles)
# ---------------------------------------------------------------------------

def anticipation(t: float, amount: float = 0.1, curve_name: str = "pos_y") -> float:
    """Calculate pre-motion anticipation offset (dip before movement).

    t in [0, 1]. Returns an offset value (negative peak during anticipation phase).
    """
    t = clamp01(t)
    if t < 0.25:
        # Pre-movement dip down to -amount
        phase = t / 0.25
        return -amount * math.sin(phase * math.pi)
    else:
        # Recover smoothly
        phase = (t - 0.25) / 0.75
        return lerp(-amount * 0.2, 0.0, ease_out_cubic(phase))


def overshoot(t: float, amount: float = 0.12, peak: float = 0.55) -> float:
    """Calculate overshoot progress envelope for crisp, weighted motion."""
    cfg = OvershootConfig(overshoot_amount=amount, overshoot_peak=peak)
    return overshoot_envelope(clamp01(t), cfg)


def follow_through(t: float, delay: float = 0.1, dampening: float = 0.8) -> float:
    """Calculate secondary delayed movement curve (for lids/iris trailing eyes)."""
    t_delayed = clamp01((t - delay) / max(0.001, (1.0 - delay)))
    return ease_out_cubic(t_delayed) * dampening


def hold(t: float, hold_start: float = 0.4, hold_duration: float = 0.2) -> float:
    """Flatten velocity during hold interval within progress [0,1]."""
    t = clamp01(t)
    hold_end = min(1.0, hold_start + hold_duration)
    if t < hold_start:
        return t / hold_start * hold_start
    elif t <= hold_end:
        return hold_start
    else:
        remaining = 1.0 - hold_end
        if remaining <= 0:
            return 1.0
        return hold_start + (t - hold_end) / remaining * (1.0 - hold_start)


def settle(t: float, dampening: float = 1.0) -> float:
    """Spring-damped convergence return curve toward rest target (1.0)."""
    t = clamp01(t)
    envelope = math.exp(-dampening * 4.0 * t)
    oscillation = math.cos(t * math.pi * 3.0)
    return 1.0 - envelope * oscillation


# ---------------------------------------------------------------------------
# Reusable Choreography Helpers
# ---------------------------------------------------------------------------

def attention_gain_helper(
    pose: EyePair,
    progress: float,
    intensity: float = 1.0,
    config: Optional[AttentionShiftConfig] = None,
    target_dx: float = 12.0,
    target_dy: float = -6.0,
) -> None:
    """Rapid focal shift/scale with overshoot toward an attention target."""
    if config is None:
        config = AttentionShiftConfig()
    progress = clamp01(progress)
    ov = overshoot(progress, amount=0.15 * intensity)
    dx = (target_dx + config.overshoot_forward_px) * ov * intensity
    dy = target_dy * ov * intensity

    for eye in (pose.left, pose.right):
        eye.look_offset_x += dx
        eye.look_offset_y += dy
        eye.iris_scale *= (1.0 + 0.08 * ov * intensity)


def attention_release_helper(pose: EyePair, progress: float, intensity: float = 1.0) -> None:
    """Smooth decay/settle back to neutral focal state."""
    progress = clamp01(progress)
    decay = (1.0 - ease_out_cubic(progress)) * intensity
    for eye in (pose.left, pose.right):
        eye.look_offset_x *= decay
        eye.look_offset_y *= decay
        eye.iris_scale = lerp(eye.iris_scale, 1.0, progress)


def emotional_settle_helper(
    pose: EyePair,
    progress: float,
    config: Optional[SettleConfig] = None,
) -> None:
    """Exponential/spring damped envelope return on pose parameters."""
    progress = clamp01(progress)
    s_val = settle(progress, dampening=1.2)

    for eye in (pose.left, pose.right):
        eye.squash *= (1.0 - progress)
        eye.stretch *= (1.0 - progress)
        eye.bounce_offset_y *= (1.0 - progress)


def natural_pause_helper(pose: EyePair, progress: float, intensity: float = 1.0) -> None:
    """Hold macro motion constant while maintaining subtle organic drift."""
    t_hold = hold(progress, hold_start=0.2, hold_duration=0.6)
    drift_amt = 0.5 * intensity * math.sin(t_hold * math.pi * 2.0)
    for eye in (pose.left, pose.right):
        eye.look_offset_x += drift_amt * 0.3
        eye.look_offset_y += drift_amt * 0.15


def eye_compression_helper(
    pose: EyePair,
    amount: float = 1.0,
    config: Optional[SquashConfig] = None,
    progress: float = 0.5,
) -> None:
    """Squash/scale narrowing of eyes via existing squash primitive."""
    if config is None:
        config = SquashConfig(amount=0.15)
    apply_squash_pair(pose, clamp01(progress), config, amount=amount)


def eye_expansion_helper(
    pose: EyePair,
    amount: float = 1.0,
    config: Optional[StretchConfig] = None,
    progress: float = 0.5,
) -> None:
    """Stretch/dilation expansion of eyes via existing stretch primitive."""
    if config is None:
        config = StretchConfig(amount=0.15)
    apply_stretch_pair(pose, clamp01(progress), config, amount=amount)


def look_scan_helper(
    pose: EyePair,
    dt_s: float,
    elapsed_s: float,
    scan_primitive: LookScanPrimitive,
    amount: float = 1.0,
) -> None:
    """Multi-target look sweep using LookScanPrimitive."""
    scan_primitive.apply_to_pair(pose, dt_s, elapsed_s, amount=amount)


def look_return_helper(pose: EyePair, settle_pair: SettledPair, dt_s: float) -> None:
    """Spring-settle look offsets smoothly back to center (0, 0)."""
    settle_pair.set_target(0.0, 0.0)
    vx, vy = settle_pair.update(dt_s)
    for eye in (pose.left, pose.right):
        eye.look_offset_x = vx
        eye.look_offset_y = vy


def soft_blink_helper(
    pose: EyePair,
    progress: float,
    config: Optional[BlinkMotionConfig] = None,
) -> None:
    """Gentle eyelid dip and compression with soft timing curve."""
    if config is None:
        config = BlinkMotionConfig(compression_amount=0.04, expansion_amount=0.02)
    progress = clamp01(progress)
    # Bell curve for blink weight
    weight = math.sin(progress * math.pi)
    apply_blink_compression_pair(pose, weight, weight, cfg=config, amount=0.7)


def fast_blink_helper(
    pose: EyePair,
    progress: float,
    config: Optional[BlinkMotionConfig] = None,
) -> None:
    """Crisp, rapid eyelid compression."""
    if config is None:
        config = BlinkMotionConfig(compression_amount=0.06, expansion_amount=0.03)
    progress = clamp01(progress)
    weight = math.sin(progress * math.pi) ** 2  # Sharper peak
    apply_blink_compression_pair(pose, weight, weight, cfg=config, amount=1.2)


def double_blink_helper(
    pose: EyePair,
    progress: float,
    config: Optional[BlinkMotionConfig] = None,
) -> None:
    """Dual-peak compression sequence (two quick blinks)."""
    if config is None:
        config = BlinkMotionConfig(compression_amount=0.05, expansion_amount=0.025)
    progress = clamp01(progress)
    if progress < 0.45:
        # First blink
        w = math.sin((progress / 0.45) * math.pi)
    elif progress < 0.55:
        # Inter-blink gap
        w = 0.0
    else:
        # Second blink
        w = math.sin(((progress - 0.55) / 0.45) * math.pi)

    apply_blink_compression_pair(pose, w, w, cfg=config, amount=1.0)


def curious_tilt_helper(
    pose: EyePair,
    tilt_angle_deg: float = 5.0,
    progress: float = 1.0,
) -> None:
    """Asymmetric height/scale offset to simulate curious head tilt."""
    progress = clamp01(progress)
    rad = math.radians(tilt_angle_deg) * progress
    y_shift = math.sin(rad) * 8.0

    # Left eye tilts up, right eye tilts down
    pose.left.pos_y -= y_shift
    pose.right.pos_y += y_shift
    pose.left.scale_y *= (1.0 + 0.04 * progress)
    pose.right.scale_y *= (1.0 - 0.04 * progress)


def breathing_pulse_helper(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    breathing_cfg: Optional[BreathingConfig] = None,
    pulse_cfg: Optional[PulseConfig] = None,
    amount: float = 1.0,
) -> None:
    """Rhythmic respiration coupled with subtle iris/radius pulse."""
    if breathing_cfg is None:
        breathing_cfg = BreathingConfig()
    if pulse_cfg is None:
        pulse_cfg = PulseConfig(amplitude_scale=0.02, frequency_hz=0.25)

    apply_breathing_pair(pose, dt_ms, elapsed_ms, breathing_cfg, amount)
    apply_pulse_pair(pose, dt_ms, elapsed_ms, pulse_cfg, amount)


def bounce_accent_helper(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    bounce_cfg: Optional[BounceConfig] = None,
    amount: float = 1.0,
) -> None:
    """Vertical bounce impulse with landing squash and rise stretch."""
    if bounce_cfg is None:
        bounce_cfg = BounceConfig(amplitude_px=4.0, frequency_hz=1.2)
    apply_bounce_pair(pose, dt_ms, elapsed_ms, bounce_cfg, amount)


def focus_lock_helper(pose: EyePair, focus_amount: float = 1.0) -> None:
    """Tight pupil/iris scale reduction, slight lid narrowing, locked drift."""
    amt = clamp01(focus_amount)
    for eye in (pose.left, pose.right):
        eye.iris_scale = lerp(eye.iris_scale, 0.88, amt)
        eye.lid_openness = lerp(eye.lid_openness, 0.78, amt)
        eye.scale_x = lerp(eye.scale_x, 0.95, amt)
        eye.scale_y = lerp(eye.scale_y, 0.95, amt)


def focus_release_helper(pose: EyePair, progress: float) -> None:
    """Dilation and lid relaxation returning focus state to baseline."""
    progress = clamp01(progress)
    for eye in (pose.left, pose.right):
        eye.iris_scale = lerp(eye.iris_scale, 1.0, progress)
        eye.lid_openness = lerp(eye.lid_openness, 1.0, progress)
        eye.scale_x = lerp(eye.scale_x, 1.0, progress)
        eye.scale_y = lerp(eye.scale_y, 1.0, progress)


# ---------------------------------------------------------------------------
# Choreography Sequence Runner
# ---------------------------------------------------------------------------

@dataclass
class ChoreographyStep:
    """A single step within a choreography sequence."""
    name: str
    duration_ms: float
    action: Callable[[EyePair, float, float], None]  # (pose, dt_ms, progress) -> None
    ease: EasingFunction = ease_in_out_cubic


class ChoreographySequence:
    """Configurable sequence of choreography steps.

    Example chain: Expand -> Overshoot -> Pause -> Blink -> Breathing -> Idle
    Executes steps deterministically with zero runtime allocations.
    """

    def __init__(self, name: str = "sequence") -> None:
        self.name = name
        self._steps: List[ChoreographyStep] = []
        self._current_step_idx: int = 0
        self._step_elapsed_ms: float = 0.0
        self._total_elapsed_ms: float = 0.0
        self._completed: bool = False

    @property
    def steps(self) -> List[ChoreographyStep]:
        return self._steps

    @property
    def is_finished(self) -> bool:
        return self._completed

    @property
    def current_step_index(self) -> int:
        return self._current_step_idx

    @property
    def current_step_name(self) -> str:
        if 0 <= self._current_step_idx < len(self._steps):
            return self._steps[self._current_step_idx].name
        return "completed" if self._completed else "idle"

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self._steps)

    @property
    def progress(self) -> float:
        tot = self.total_duration_ms
        if tot <= 0:
            return 1.0 if self._completed else 0.0
        return clamp01(self._total_elapsed_ms / tot)

    def add_step(
        self,
        name: str,
        duration_ms: float,
        action: Callable[[EyePair, float, float], None],
        ease: EasingFunction = ease_in_out_cubic,
    ) -> ChoreographySequence:
        """Add a step to the sequence. Returns self for chaining."""
        self._steps.append(ChoreographyStep(name, max(0.0, duration_ms), action, ease))
        return self

    def reset(self) -> None:
        self._current_step_idx = 0
        self._step_elapsed_ms = 0.0
        self._total_elapsed_ms = 0.0
        self._completed = False

    def update(self, dt_ms: float, pose: EyePair) -> None:
        """Advance the sequence by dt_ms and execute the active step action in-place."""
        if self._completed or not self._steps:
            return

        self._step_elapsed_ms += dt_ms
        self._total_elapsed_ms += dt_ms

        while self._current_step_idx < len(self._steps):
            step = self._steps[self._current_step_idx]
            if step.duration_ms <= 0:
                # Instant step
                step.action(pose, dt_ms, 1.0)
                self._current_step_idx += 1
                self._step_elapsed_ms = 0.0
                continue

            if self._step_elapsed_ms >= step.duration_ms:
                # Step complete, run final progress=1.0 then advance
                progress = 1.0
                eased_p = step.ease(progress)
                step.action(pose, dt_ms, eased_p)
                overflow_ms = self._step_elapsed_ms - step.duration_ms
                self._current_step_idx += 1
                self._step_elapsed_ms = overflow_ms
            else:
                # Step in progress
                progress = clamp01(self._step_elapsed_ms / step.duration_ms)
                eased_p = step.ease(progress)
                step.action(pose, dt_ms, eased_p)
                break

        if self._current_step_idx >= len(self._steps):
            self._completed = True


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Stage & Direction
    "StageType",
    "StageConfig",
    "AnimationDirection",
    # Timing Helpers
    "anticipation",
    "overshoot",
    "follow_through",
    "hold",
    "settle",
    # Choreography Helpers
    "attention_gain_helper",
    "attention_release_helper",
    "emotional_settle_helper",
    "natural_pause_helper",
    "eye_compression_helper",
    "eye_expansion_helper",
    "look_scan_helper",
    "look_return_helper",
    "soft_blink_helper",
    "fast_blink_helper",
    "double_blink_helper",
    "curious_tilt_helper",
    "breathing_pulse_helper",
    "bounce_accent_helper",
    "focus_lock_helper",
    "focus_release_helper",
    # Sequence Helpers
    "ChoreographyStep",
    "ChoreographySequence",
]
