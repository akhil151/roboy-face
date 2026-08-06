"""
Premium reusable motion primitives library for the ELO Robot Eye Animation Engine.

Every primitive is:
  * Configurable - parameters for amplitude, speed, phase, easing, asymmetry
  * Smooth - no discontinuities; use spring/damper or ease curves
  * Generic - operates on EyeParams (single eye) or EyePair (both eyes)
  * Composable - primitives can stack additively on the same pose

These primitives are the building blocks that Phase 2B emotional states will
configure to author the 10 premium animations.

Design rules:
  * Primitive functions mutate their target pose IN-PLACE (additive style).
  * Primitives accept ``dt_ms`` or ``elapsed_ms`` as appropriate; they own
    any internal state required.
  * "Amount" parameters are unitless multipliers (0..1 typically) so callers
    can dial intensity without touching internal curve math.
  * All oscillations use irrational period ratios when combined to avoid
    visible repetition (lcg-style pseudo-periods in golden-ratio families).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .eye import EyeParams
from .eye_pair import EyePair
from .easing import (
    ease_out_back,
    ease_in_back,
    ease_out_elastic,
    ease_in_out_sine,
    ease_in_out_cubic,
    ease_out_cubic,
    ease_in_cubic,
    clamp01,
    lerp,
)
from .spring import Spring1D, Spring2D, SpringConfig
from .tween import TweenEngine


# ---------------------------------------------------------------------------
# Shared configuration dataclasses - one per primitive type so that states
# can tune primitives with named parameters instead of raw tuples.
# ---------------------------------------------------------------------------


@dataclass
class BreathingConfig:
    """Gentle sinusoidal vertical scaling that simulates respiration."""
    amplitude: float = 0.012
    period_seconds: float = 4.5
    vertical_bias: float = 1.0
    horizontal_bias: float = 0.3
    y_offset_px: float = 0.5
    phase_offset: float = 0.0
    asymmetry_left: float = 0.95
    asymmetry_right: float = 1.05
    depth_wobble: float = 0.003


@dataclass
class BounceConfig:
    """Rhythmic vertical displacement with non-symmetric acceleration
    curves (weight on the way down, light on the way up)."""
    amplitude_px: float = 3.0
    frequency_hz: float = 0.9
    weight: float = 0.7
    squash_on_landing: float = 0.04
    stretch_on_rise: float = 0.02
    phase_offset: float = 0.0
    asymmetry_left: float = 1.0
    asymmetry_right: float = 1.0


@dataclass
class OvershootConfig:
    """Anticipation -> fast move -> overshoot -> settle envelope.

    Used for entry transitions and attention shifts to add weight.
    ``t`` is expected to be in [0,1] representing the overall transition
    progress (e.g. state entry blend t)."""
    anticipation_amount: float = 0.08
    anticipation_ease: EasingFunction = ease_in_cubic
    overshoot_amount: float = 0.12
    overshoot_peak: float = 0.55
    settle_ease: EasingFunction = ease_out_back
    return_amount: float = 0.04


@dataclass
class SettleConfig:
    """Exponentially damped convergence toward a target value.

    Wraps a Spring1D internally so the settle is physically plausible and
    never snaps even when the target changes mid-transition."""
    stiffness: float = 220.0
    damping: float = 30.0
    mass: float = 1.0
    snap_threshold: float = 0.001


@dataclass
class DriftConfig:
    """Slow wandering using product-of-sines pseudo-Perlin noise.

    Multiple incommensurate frequencies are combined so the drift never
    repeats on human-visible timescales."""
    amplitude_px: float = 1.2
    period_seconds: float = 11.0
    harmonic_count: int = 3
    harmonic_decay: float = 0.55
    seed: float = 0.0
    vertical_ratio: float = 0.75


@dataclass
class PulseConfig:
    """Rhythmic intensity pulse - good for speech, excitement, emphasis.

    Combines a sharp attack with a softer exponential decay so individual
    pulses feel like they have "impact" rather than being a pure sine."""
    amplitude_scale: float = 0.04
    amplitude_glow: float = 0.15
    amplitude_radius: float = 1.5
    frequency_hz: float = 1.4
    attack_ratio: float = 0.18
    decay_exponent: float = 3.0
    phase_offset: float = 0.0
    jitter_amount: float = 0.15


@dataclass
class SquashConfig:
    """Compress vertically / expand horizontally with easing.

    For landing impacts, blink peaks, stress expressions. Applies an
    envelope to (scale_x, scale_y, squash, stretch) so the deformation
    feels physically plausible."""
    amount: float = 0.12
    rise_ease: EasingFunction = ease_out_cubic
    fall_ease: EasingFunction = ease_in_cubic
    vertical_peak: float = 0.5
    preserve_area: bool = True
    curvature_bias: float = 0.3


@dataclass
class StretchConfig:
    """Expand vertically / compress horizontally - anticipation / rise."""
    amount: float = 0.10
    rise_ease: EasingFunction = ease_out_cubic
    fall_ease: EasingFunction = ease_in_cubic
    vertical_peak: float = 0.5
    preserve_area: bool = True
    curvature_bias: float = -0.2


@dataclass
class LookScanConfig:
    """Systematic eye scanning pattern for 'thinking' / 'reading' states.

    Produces a series of quick saccades followed by micro-pauses, with
    a spring-followed target so each saccade has natural settle."""
    sweep_amplitude: float = 18.0
    vertical_amplitude: float = 8.0
    saccade_hz: float = 0.55
    pause_ratio: float = 0.35
    spring_config: SpringConfig = field(default_factory=lambda: SpringConfig(380.0, 42.0, 1.0))
    asymmetry_left: float = 1.0
    asymmetry_right: float = 1.0


@dataclass
class IdleNoiseConfig:
    """Very tiny, very slow, smooth pseudo-random parameter jitter.

    Uses 4-frequency sine-product noise per channel so the output is
    continuous (value, first, and second derivatives smooth) - never any
    jumps even though the source is stochastic."""
    position_px: float = 0.35
    scale_amount: float = 0.0025
    radius_px: float = 0.25
    rotation_deg: float = 0.12
    speed: float = 1.0
    seed: float = 0.0


@dataclass
class MicroCorrectionConfig:
    """Infrequent, tiny snap-back corrections that prevent the viewer
    from perceiving the eyes as "frozen" even during still poses."""
    chance_per_second: float = 0.35
    max_offset_px: float = 0.6
    settle_duration_ms: float = 120.0
    interval_min_seconds: float = 1.5
    interval_max_seconds: float = 4.5


@dataclass
class BlinkMotionConfig:
    """Peri-blink eye compression / expansion motion.

    Applies to all blink variants (normal, double, half, slow).
    Eyes compress slightly on closure, expand gently on re-opening.
    Adds weight so blinks feel mechanical rather than alpha fades."""
    compression_amount: float = 0.04
    expansion_amount: float = 0.025
    squash_on_close: float = 0.06
    y_offset_px: float = 0.8
    curvature_surge: float = 0.15


@dataclass
class AttentionShiftConfig:
    """Anticipation -> Saccade -> Overshoot -> Settle envelope for
    look-direction changes. Produces cinematic eye movement."""
    anticipation_back_px: float = 1.5
    overshoot_forward_px: float = 2.5
    settle_duration_ms: float = 220.0
    squash_amount: float = 0.02
    spring_config: SpringConfig = field(default_factory=lambda: SpringConfig(420.0, 44.0, 1.0))
    asymmetry_left: float = 1.0
    asymmetry_right: float = 0.97


@dataclass
class EmotionMorphConfig:
    """Smooth parameter-level blend between a "from" and "to" emotion
    parameter vector, with per-easing overrides for each property group."""
    position_ease: EasingFunction = ease_in_out_cubic
    scale_ease: EasingFunction = ease_in_out_sine
    lid_ease: EasingFunction = ease_in_out_sine
    radius_ease: EasingFunction = ease_out_cubic
    curvature_ease: EasingFunction = ease_in_out_cubic
    iris_ease: EasingFunction = ease_in_out_sine
    glow_ease: EasingFunction = ease_out_cubic
    rotation_ease: EasingFunction = ease_in_out_sine
    opacity_ease: EasingFunction = ease_in_out_sine


# ---------------------------------------------------------------------------
# Helper: unit oscillation with shape control
# ---------------------------------------------------------------------------

def _shape_oscillation(
    t: float,
    freq_hz: float,
    phase: float,
    shape: str = "sine",
    attack_ratio: float = 0.2,
    decay_exp: float = 2.5,
) -> float:
    """Return a unit oscillation [-1, 1] with the requested wave-shape."""
    raw = t * freq_hz * 2.0 * math.pi + phase
    if shape == "sine":
        return math.sin(raw)
    if shape == "triangle":
        frac = (raw / (2.0 * math.pi)) % 1.0
        return 4.0 * abs(frac - 0.5) - 1.0
    if shape == "pulse":
        frac = (raw / (2.0 * math.pi)) % 1.0
        if frac < attack_ratio:
            return (frac / attack_ratio) ** decay_exp
        return (1.0 - (frac - attack_ratio) / (1.0 - attack_ratio)) ** decay_exp * 2.0 - 1.0
    if shape == "abs_sine":
        return math.sin(raw) if math.sin(raw) > 0 else 0.0
    # default: pure sine
    return math.sin(raw)


def _product_sine_noise(
    t: float,
    seed: float,
    harmonics: int = 3,
    decay: float = 0.55,
) -> float:
    """Sum-of-products-of-sines smooth pseudo-noise in [-1, 1]."""
    value = 0.0
    amp_sum = 0.0
    amp = 1.0
    for i in range(harmonics):
        # Incommensurate frequencies via sqrt(prime) family so beats don't line up.
        f1 = (0.7 + i * 0.42) * 2.0 * math.pi
        f2 = (1.6180339887 + i * 0.73) * 2.0 * math.pi
        ph1 = seed * (1.0 + i * 0.37)
        ph2 = seed * 1.7 + i * 0.91
        value += amp * math.sin(t * f1 + ph1) * math.cos(t * f2 + ph2)
        amp_sum += amp
        amp *= decay
    if amp_sum > 0:
        value /= amp_sum
    return clamp01(value + 0.5) * 2.0 - 1.0  # remap to [-1, 1]


# ===========================================================================
# MOTION PRIMITIVES
# Each function mutates EyeParams or EyePair in place, additively.
# ===========================================================================


def apply_breathing(
    p: EyeParams,
    dt_ms: float,
    elapsed_ms: float,
    cfg: BreathingConfig,
    amount: float = 1.0,
) -> None:
    """Add gentle breathing (scale + tiny y bounce) into a single eye."""
    if amount <= 0.0:
        return
    t = elapsed_ms / 1000.0
    main = math.sin(t * 2.0 * math.pi / cfg.period_seconds + cfg.phase_offset)
    wob = math.sin(t * 2.0 * math.pi / (cfg.period_seconds * 1.618) + cfg.phase_offset * 0.6)
    env = main * cfg.amplitude * amount + wob * cfg.depth_wobble * amount
    p.scale_y += env * cfg.vertical_bias
    p.scale_x -= env * cfg.horizontal_bias * 0.5
    p.bounce_offset_y -= abs(env) * cfg.y_offset_px * 10.0


def apply_breathing_pair(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    cfg: BreathingConfig,
    amount: float = 1.0,
) -> float:
    """Apply breathing to both eyes and return the breathing envelope [0,1]."""
    t = elapsed_ms / 1000.0
    main = math.sin(t * 2.0 * math.pi / cfg.period_seconds + cfg.phase_offset)
    envelope = clamp01((main + 1.0) * 0.5)  # remap [-1,1] → [0,1] for return
    apply_breathing(pose.left, dt_ms, elapsed_ms, cfg, amount * cfg.asymmetry_left)
    apply_breathing(pose.right, dt_ms, elapsed_ms, cfg, amount * cfg.asymmetry_right)
    return envelope


def apply_bounce(
    p: EyeParams,
    dt_ms: float,
    elapsed_ms: float,
    cfg: BounceConfig,
    amount: float = 1.0,
) -> None:
    """Add a rhythmic bounce: weighted drop, light lift, with squash/stretch."""
    if amount <= 0.0:
        return
    t = elapsed_ms / 1000.0
    phase = t * cfg.frequency_hz * 2.0 * math.pi + cfg.phase_offset
    # abs(sin) gives weight on the bottom, abs(cos) on the top.
    drop = -abs(math.sin(phase))
    rise = abs(math.cos(phase)) * (1.0 - cfg.weight)
    vert = (drop + rise) * cfg.amplitude_px * amount
    p.bounce_offset_y += vert
    # Squash at the bottom (drop phase), stretch at the top (rise phase).
    squash_phase = max(0.0, -drop)
    stretch_phase = max(0.0, rise)
    p.squash += squash_phase * cfg.squash_on_landing * amount
    p.stretch += stretch_phase * cfg.stretch_on_rise * amount


def apply_bounce_pair(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    cfg: BounceConfig,
    amount: float = 1.0,
) -> float:
    """Apply bounce to both eyes and return the current bounce phase [0,1]."""
    t = elapsed_ms / 1000.0
    phase = t * cfg.frequency_hz * 2.0 * math.pi + cfg.phase_offset
    envelope = clamp01(abs(math.sin(phase)))  # 0..1 phase indicator
    apply_bounce(pose.left, dt_ms, elapsed_ms, cfg, amount * cfg.asymmetry_left)
    apply_bounce(pose.right, dt_ms, elapsed_ms, cfg, amount * cfg.asymmetry_right)
    return envelope


def overshoot_envelope(t: float, cfg: OvershootConfig) -> float:
    """Compute a scalar envelope in roughly [-0.08, 1.12] with
    anticipation -> overshoot -> settle shape.

    Input t is linear [0, 1].  Output is blend value for the *target*
    parameter where <0 means anticipates in the opposite direction,
    1.0 means fully at target, >1.0 means overshoot.
    """
    t = clamp01(t)
    if t < cfg.overshoot_peak * 0.5:
        # Phase A: Anticipation (prep move opposite direction)
        local = t / max(cfg.overshoot_peak * 0.5, 0.0001)
        ease = cfg.anticipation_ease(local)
        return -ease * cfg.anticipation_amount
    if t < cfg.overshoot_peak:
        # Phase B: Fire forward from anticipation to overshoot peak
        local01 = (t - cfg.overshoot_peak * 0.5) / max(cfg.overshoot_peak * 0.5, 0.0001)
        eased = ease_out_cubic(local01)
        from_val = -cfg.anticipation_amount
        to_val = 1.0 + cfg.overshoot_amount
        return lerp(from_val, to_val, eased)
    # Phase C: Settle from overshoot down to 1.0, with a tiny bounce back
    local = (t - cfg.overshoot_peak) / max(1.0 - cfg.overshoot_peak, 0.0001)
    eased = cfg.settle_ease(local)
    return lerp(1.0 + cfg.overshoot_amount, 1.0, eased) - math.sin(local * math.pi) * cfg.return_amount


def apply_drift(
    p: EyeParams,
    dt_ms: float,
    elapsed_ms: float,
    cfg: DriftConfig,
    amount: float = 1.0,
) -> Tuple[float, float]:
    """Add slow pseudo-Perlin drift offsets to a single eye.

    Writes to look_offset_x/y (slow gaze wandering).
    Returns the (dx, dy) applied for diagnostic / compositing use."""
    if amount <= 0.0:
        return (0.0, 0.0)
    t = elapsed_ms / 1000.0 / cfg.period_seconds
    nx = _product_sine_noise(t, cfg.seed, cfg.harmonic_count, cfg.harmonic_decay)
    ny = _product_sine_noise(t + 17.3, cfg.seed + 31.7, cfg.harmonic_count, cfg.harmonic_decay)
    dx = nx * cfg.amplitude_px * amount
    dy = ny * cfg.amplitude_px * cfg.vertical_ratio * amount
    p.look_offset_x += dx
    p.look_offset_y += dy
    return (dx, dy)


def apply_drift_pair(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    cfg: DriftConfig,
    amount: float = 1.0,
) -> float:
    """Apply drift to both eyes and return a normalized drift magnitude [0,1]."""
    cfg_r = DriftConfig(
        amplitude_px=cfg.amplitude_px,
        period_seconds=cfg.period_seconds,
        harmonic_count=cfg.harmonic_count,
        harmonic_decay=cfg.harmonic_decay,
        seed=cfg.seed + 7.3,
        vertical_ratio=cfg.vertical_ratio,
    )
    dl = apply_drift(pose.left, dt_ms, elapsed_ms, cfg, amount)
    dr = apply_drift(pose.right, dt_ms, elapsed_ms, cfg_r, amount)
    mag = (abs(dl[0]) + abs(dl[1]) + abs(dr[0]) + abs(dr[1])) / (4.0 * max(cfg.amplitude_px, 0.001) * amount + 1e-9)
    return clamp01(mag)


def apply_pulse(
    p: EyeParams,
    dt_ms: float,
    elapsed_ms: float,
    cfg: PulseConfig,
    amount: float = 1.0,
) -> float:
    """Add rhythmic pulse into scale, glow, and radius.

    Returns the pulse envelope [0,1] for compositing / debug."""
    if amount <= 0.0:
        return 0.0
    t = elapsed_ms / 1000.0
    jitter = math.sin(t * 3.7 + cfg.phase_offset * 2.0) * cfg.jitter_amount
    env = _shape_oscillation(
        t, cfg.frequency_hz, cfg.phase_offset, "pulse", cfg.attack_ratio, cfg.decay_exponent
    )
    env = clamp01((env + 1.0) * 0.5 + jitter * 0.1) * amount
    p.scale_x += env * cfg.amplitude_scale
    p.scale_y += env * cfg.amplitude_scale
    p.radius += env * cfg.amplitude_radius
    p.glow_strength += env * cfg.amplitude_glow
    return env


def apply_pulse_pair(
    pose: EyePair,
    dt_ms: float,
    elapsed_ms: float,
    cfg: PulseConfig,
    amount: float = 1.0,
) -> float:
    env_l = apply_pulse(pose.left, dt_ms, elapsed_ms, cfg, amount)
    env_r = apply_pulse(pose.right, dt_ms, elapsed_ms, cfg, amount * 0.98)
    return (env_l + env_r) * 0.5


def apply_squash(p: EyeParams, t: float, cfg: SquashConfig, amount: float = 1.0) -> None:
    """Apply a squash envelope at blend progress t in [0,1]."""
    if amount <= 0.0:
        return
    t = clamp01(t)
    if t < cfg.vertical_peak:
        local = t / max(cfg.vertical_peak, 0.0001)
        env = cfg.rise_ease(local)
    else:
        local = (t - cfg.vertical_peak) / max(1.0 - cfg.vertical_peak, 0.0001)
        env = cfg.fall_ease(1.0 - local)
    env *= cfg.amount * amount
    p.scale_x += env
    p.scale_y -= env * (1.0 if cfg.preserve_area else 0.8)
    p.squash += env
    p.upper_lid_curvature += env * cfg.curvature_bias
    p.lower_lid_curvature -= env * cfg.curvature_bias


def apply_stretch(p: EyeParams, t: float, cfg: StretchConfig, amount: float = 1.0) -> None:
    """Apply a stretch envelope at blend progress t in [0,1]."""
    if amount <= 0.0:
        return
    t = clamp01(t)
    if t < cfg.vertical_peak:
        local = t / max(cfg.vertical_peak, 0.0001)
        env = cfg.rise_ease(local)
    else:
        local = (t - cfg.vertical_peak) / max(1.0 - cfg.vertical_peak, 0.0001)
        env = cfg.fall_ease(1.0 - local)
    env *= cfg.amount * amount
    p.scale_x -= env * (0.7 if cfg.preserve_area else 0.5)
    p.scale_y += env
    p.stretch += env
    p.upper_lid_curvature += env * cfg.curvature_bias
    p.lower_lid_curvature -= env * cfg.curvature_bias


def apply_squash_pair(pose: EyePair, t: float, cfg: SquashConfig, amount: float = 1.0) -> float:
    """Apply squash to both eyes and return the effective weight used."""
    apply_squash(pose.left, t, cfg, amount)
    apply_squash(pose.right, t, cfg, amount * 0.97)
    return amount


def apply_stretch_pair(pose: EyePair, t: float, cfg: StretchConfig, amount: float = 1.0) -> float:
    """Apply stretch to both eyes and return the effective weight used."""
    apply_stretch(pose.left, t, cfg, amount)
    apply_stretch(pose.right, t, cfg, amount * 0.97)
    return amount


# ===========================================================================
# Spring-backed settle primitive (holds internal state per-instance)
# ===========================================================================


class SettledValue:
    """A single scalar that settles toward a target with spring physics.

    Useful for any parameter that should "drift" toward its target rather
    than snap linearly (radius, scale, lid openness, curvature...).
    """

    def __init__(self, cfg: SettleConfig | None = None, initial: float = 0.0) -> None:
        self._cfg = cfg or SettleConfig()
        self._spring = Spring1D(
            SpringConfig(self._cfg.stiffness, self._cfg.damping, self._cfg.mass), initial
        )

    def set_target(self, target: float) -> None:
        self._spring.set_target(target)

    def set_immediate(self, value: float) -> None:
        self._spring.set_value_immediate(value)

    @property
    def value(self) -> float:
        return self._spring.value

    @property
    def target(self) -> float:
        return self._spring.target

    @target.setter
    def target(self, value: float) -> None:
        """Compatibility setter: sv.target = x  is equivalent to sv.set_target(x)."""
        self._spring.set_target(value)

    def at_rest(self) -> bool:
        return self._spring.at_rest(self._cfg.snap_threshold, self._cfg.snap_threshold * 100.0)

    def update(self, dt_s: float) -> float:
        return self._spring.update(dt_s)


class SettledPair:
    """Two settled values (X/Y) for 2-D things like position offsets.

    Constructor accepts two calling conventions:
      - Production: SettledPair(cfg=SettleConfig(), initial=(0.0, 0.0))
      - Compact:    SettledPair(initial_x, stiffness)  e.g. SettledPair(0.0, 5.0)
    """

    def __init__(
        self,
        cfg_or_initial: "SettleConfig | float | Tuple[float, float] | None" = None,
        initial_or_stiffness: "Tuple[float, float] | float" = (0.0, 0.0),
    ) -> None:
        # Detect compact (initial_x, stiffness) two-float calling convention.
        # Also handles (initial_tuple, stiffness) as used in tests.
        if isinstance(cfg_or_initial, (int, float)):
            # (initial_x, stiffness) compact form
            stiffness = float(initial_or_stiffness) if isinstance(initial_or_stiffness, (int, float)) else 5.0
            c = SettleConfig(stiffness=max(1.0, stiffness), damping=max(1.0, stiffness * 0.6), mass=1.0)
            ix = float(cfg_or_initial)
            initial: Tuple[float, float] = (ix, 0.0)
        elif isinstance(cfg_or_initial, tuple):
            # (initial_tuple, stiffness) form: SettledPair((0.0, 0.0), 5.0)
            stiffness = float(initial_or_stiffness) if isinstance(initial_or_stiffness, (int, float)) else 5.0
            c = SettleConfig(stiffness=max(1.0, stiffness), damping=max(1.0, stiffness * 0.6), mass=1.0)
            initial = (float(cfg_or_initial[0]), float(cfg_or_initial[1]))
        else:
            c = cfg_or_initial or SettleConfig()
            initial = initial_or_stiffness if isinstance(initial_or_stiffness, tuple) else (0.0, 0.0)  # type: ignore[assignment]
        self.x = SettledValue(c, initial[0])
        self.y = SettledValue(c, initial[1])

    def set_target(self, x: float, y: float) -> None:
        self.x.set_target(x)
        self.y.set_target(y)

    def set_immediate(self, x: float, y: float) -> None:
        self.x.set_immediate(x)
        self.y.set_immediate(y)

    @property
    def target(self) -> Tuple[float, float]:
        return (self.x.target, self.y.target)

    @target.setter
    def target(self, xy: Tuple[float, float]) -> None:
        """Compatibility setter: sp.target = (x, y)  is equivalent to sp.set_target(x, y)."""
        self.x.set_target(xy[0])
        self.y.set_target(xy[1])

    @property
    def value(self) -> Tuple[float, float]:
        return (self.x.value, self.y.value)

    def update(self, dt_s: float) -> Tuple[float, float]:
        return (self.x.update(dt_s), self.y.update(dt_s))

    def at_rest(self) -> bool:
        return self.x.at_rest() and self.y.at_rest()


# ===========================================================================
# Look Scan primitive with spring-backed saccades
# ===========================================================================


class LookScanPrimitive:
    """Generates a systematic scanning (look) trajectory with natural
    saccades and pauses.  Each saccade settles via spring physics."""

    def __init__(self, cfg: LookScanConfig | None = None) -> None:
        self._cfg = cfg or LookScanConfig()
        self._spring = Spring2D(self._cfg.spring_config, (0.0, 0.0))
        self._last_target: Tuple[float, float] = (0.0, 0.0)

    def set_config(self, cfg: LookScanConfig) -> None:
        self._cfg = cfg
        self._spring.set_config(cfg.spring_config)

    def reset(self) -> None:
        self._spring.set_value_immediate(0.0, 0.0)
        self._spring.set_target(0.0, 0.0)

    def get_offsets(self) -> Tuple[float, float]:
        return self._spring.value

    def update(self, dt_s: float, elapsed_s: float, amount: float = 1.0) -> Tuple[float, float]:
        if amount <= 0.0:
            self._spring.update(dt_s)
            return (0.0, 0.0)
        cycle = 1.0 / max(self._cfg.saccade_hz, 0.0001)
        local = (elapsed_s % cycle) / cycle
        if local < (1.0 - self._cfg.pause_ratio):
            # Saccade phase: pick a new target at the START of each saccade.
            phase_id = int(elapsed_s / cycle)
            rng = random.Random(phase_id * 1337 + 7)
            nx = (rng.random() * 2.0 - 1.0) * self._cfg.sweep_amplitude * amount
            ny = (rng.random() * 2.0 - 1.0) * self._cfg.vertical_amplitude * amount
            target = (nx, ny)
            if target != self._last_target:
                self._spring.set_target(nx, ny)
                self._last_target = target
        else:
            # Pause phase: spring is drifting to settle, hold current target.
            pass
        return self._spring.update(dt_s)

    def apply_to_pair(
        self, pose: EyePair, dt_s: float, elapsed_s: float, amount: float = 1.0
    ) -> None:
        dx, dy = self.update(dt_s, elapsed_s, amount)
        pose.left.look_offset_x += dx * self._cfg.asymmetry_left
        pose.left.look_offset_y += dy * self._cfg.asymmetry_left
        pose.right.look_offset_x += dx * self._cfg.asymmetry_right
        pose.right.look_offset_y += dy * self._cfg.asymmetry_right


# ===========================================================================
# Idle noise primitive - super smooth, zero jumps, multi-channel jitter
# ===========================================================================


class IdleNoisePrimitive:
    """Generates continuous tiny parameter noise for a single eye.

    Never produces discrete jumps; the signal has smooth value, slope, and
    second-derivative thanks to product-of-sines synthesis."""

    def __init__(self, cfg: IdleNoiseConfig | None = None, seed: float = 0.0) -> None:
        self._cfg = cfg or IdleNoiseConfig()
        self._seed = seed if seed != 0.0 else random.uniform(0.0, 100.0)

    def set_config(self, cfg: IdleNoiseConfig) -> None:
        self._cfg = cfg

    def sample(self, elapsed_s: float) -> Tuple[float, float]:
        """Return the (nx, ny) noise position channel values at elapsed_s.

        Values are in [-1, 1] and are smooth / continuous.
        Compatibility entry point for callers that want the raw noise
        without writing into an EyeParams."""
        cfg = self._cfg
        t = elapsed_s * cfg.speed
        nx = _product_sine_noise(t, self._seed, 3, 0.55)
        ny = _product_sine_noise(t + 9.1, self._seed + 3.3, 3, 0.55)
        return (nx, ny)

    def apply(self, p: EyeParams, elapsed_s: float, amount: float = 1.0) -> None:
        if amount <= 0.0:
            return
        cfg = self._cfg
        t = elapsed_s * cfg.speed
        nx = _product_sine_noise(t, self._seed, 3, 0.55)
        ny = _product_sine_noise(t + 9.1, self._seed + 3.3, 3, 0.55)
        nsx = _product_sine_noise(t + 17.9, self._seed + 11.1, 2, 0.6)
        nsy = _product_sine_noise(t + 23.4, self._seed + 19.7, 2, 0.6)
        nr = _product_sine_noise(t + 31.2, self._seed + 27.5, 2, 0.6)
        nrot = _product_sine_noise(t + 41.0, self._seed + 37.9, 2, 0.6)
        p.micro_offset_x += nx * cfg.position_px * amount
        p.micro_offset_y += ny * cfg.position_px * amount
        p.scale_x += nsx * cfg.scale_amount * amount
        p.scale_y += nsy * cfg.scale_amount * amount
        p.radius += nr * cfg.radius_px * amount
        p.rotation += nrot * cfg.rotation_deg * math.pi / 180.0 * amount


class IdleNoisePair:
    """Idle noise for both eyes with slight inter-ocular decorrelation.

    Constructor accepts two calling conventions:
      - Production: IdleNoisePair(cfg)           — same config for both eyes
      - Extended:   IdleNoisePair(cfg_l, cfg_r)  — independent per-eye configs
    """

    def __init__(
        self,
        cfg: IdleNoiseConfig | None = None,
        cfg_right: IdleNoiseConfig | None = None,
    ) -> None:
        self._left = IdleNoisePrimitive(cfg, seed=random.uniform(0.0, 50.0))
        self._right = IdleNoisePrimitive(cfg_right or cfg, seed=random.uniform(50.0, 100.0))

    def set_config(self, cfg: IdleNoiseConfig) -> None:
        self._left.set_config(cfg)
        self._right.set_config(cfg)

    def sample(self, elapsed_s: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return ((lx, ly), (rx, ry)) noise position values for both eyes."""
        return (self._left.sample(elapsed_s), self._right.sample(elapsed_s))

    def apply(self, pose: EyePair, elapsed_s: float, amount: float = 1.0) -> None:
        self._left.apply(pose.left, elapsed_s, amount)
        self._right.apply(pose.right, elapsed_s, amount * 1.04)


# ===========================================================================
# Micro-correction primitive - infrequent tiny snap-backs
# ===========================================================================


class MicroCorrectionPrimitive:
    """Rare, tiny, physically-settled position corrections so the eyes
    never appear frozen even during perfectly still poses."""

    def __init__(self, cfg: MicroCorrectionConfig | None = None) -> None:
        self._cfg = cfg or MicroCorrectionConfig()
        self._settle_x = SettledValue(
            SettleConfig(stiffness=600.0, damping=50.0, mass=1.0), 0.0
        )
        self._settle_y = SettledValue(
            SettleConfig(stiffness=600.0, damping=50.0, mass=1.0), 0.0
        )
        self._time_since_last = random.uniform(
            self._cfg.interval_min_seconds, self._cfg.interval_max_seconds
        )
        self._accum_s = 0.0
        # Correction lifecycle: 0 = idle, 1 = moving/holding at the correction
        # offset, 2 = snapping back toward zero.
        self._phase = 0
        self._dwell_s = 0.0

    def set_config(self, cfg: MicroCorrectionConfig) -> None:
        self._cfg = cfg

    def reset(self) -> None:
        """Reset internal timing so the primitive starts fresh."""
        self._accum_s = 0.0
        self._time_since_last = random.uniform(
            self._cfg.interval_min_seconds, self._cfg.interval_max_seconds
        )
        self._settle_x.set_immediate(0.0)
        self._settle_y.set_immediate(0.0)
        self._phase = 0
        self._dwell_s = 0.0

    def get_offsets(self) -> Tuple[float, float]:
        return (self._settle_x.value, self._settle_y.value)

    def offset(self) -> Tuple[float, float]:
        """Alias for get_offsets() — compatibility entry point."""
        return self.get_offsets()

    def update(self, dt_s: float, amount: float = 1.0) -> Tuple[float, float]:
        self._accum_s += dt_s
        self._time_since_last -= dt_s
        if self._phase == 0:
            # Idle: wait for the next correction interval, then move the
            # spring toward a tiny random offset.  (Previously the target was
            # reset to zero on the very same frame, so the spring never moved.)
            if self._time_since_last <= 0.0:
                chance = self._cfg.chance_per_second * dt_s * 10.0
                if random.random() < chance or self._accum_s > self._cfg.interval_max_seconds * 1.5:
                    ang = random.uniform(0.0, 2.0 * math.pi)
                    mag = random.uniform(0.1, self._cfg.max_offset_px) * amount
                    self._settle_x.set_target(math.cos(ang) * mag)
                    self._settle_y.set_target(math.sin(ang) * mag)
                    self._dwell_s = max(0.0, self._cfg.settle_duration_ms) / 1000.0
                    self._phase = 1
                    self._accum_s = 0.0
        elif self._phase == 1:
            # Hold the correction briefly once the spring has settled, then
            # snap back toward zero.
            if self._settle_x.at_rest() and self._settle_y.at_rest():
                self._dwell_s -= dt_s
                if self._dwell_s <= 0.0:
                    self._settle_x.set_target(0.0)
                    self._settle_y.set_target(0.0)
                    self._phase = 2
        else:  # phase == 2
            # Snapping back to zero; the correction is complete once settled.
            if self._settle_x.at_rest() and self._settle_y.at_rest():
                self._phase = 0
                self._time_since_last = random.uniform(
                    self._cfg.interval_min_seconds, self._cfg.interval_max_seconds
                )
        return (self._settle_x.update(dt_s), self._settle_y.update(dt_s))

    def apply_to_pair(self, pose: EyePair, dt_s: float, amount: float = 1.0) -> None:
        dx, dy = self.update(dt_s, amount)
        pose.left.micro_offset_x += dx * 0.96
        pose.left.micro_offset_y += dy * 0.96
        pose.right.micro_offset_x += dx * 1.04
        pose.right.micro_offset_y += dy * 1.04


# ===========================================================================
# Blink motion primitives - compression / expansion through the blink cycle
# ===========================================================================


def apply_blink_compression(
    p: EyeParams,
    blink_weight: float,
    cfg: BlinkMotionConfig,
    amount: float = 1.0,
) -> None:
    """Apply eye compression / expansion as a function of blink closure.

    ``blink_weight`` is the current closure in [0, 1] (from BlinkController).
    The eyes squash on close, compress their radius, and gently stretch on
    reopen to add weight."""
    if amount <= 0.0:
        return
    bw = clamp01(blink_weight)
    # Closure curve: rises from 0 at open (bw=0) to 1 at peak closure (bw=1).
    close_env = math.sin(bw * math.pi * 0.5)
    p.scale_x += close_env * cfg.compression_amount * amount
    p.scale_y -= close_env * cfg.compression_amount * 0.8 * amount
    p.squash += close_env * cfg.squash_on_close * amount
    p.bounce_offset_y += close_env * cfg.y_offset_px * amount
    # Radius compress on full closure for physical plausibility.
    p.radius -= close_env * cfg.compression_amount * p.radius * 0.25 * amount
    # Surge curvature at peak closure for a "tight" squeeze look.
    curvature_surge = (1.0 - abs(bw - 0.5) * 2.0) ** 2
    p.upper_lid_curvature += curvature_surge * cfg.curvature_surge * amount
    p.lower_lid_curvature -= curvature_surge * cfg.curvature_surge * amount * 0.6


def apply_blink_compression_pair(
    pose: EyePair,
    blink_weight_left: float,
    blink_weight_right: float,
    cfg: BlinkMotionConfig,
    amount: float = 1.0,
) -> float:
    """Apply blink compression to both eyes and return effective amount used."""
    apply_blink_compression(pose.left, blink_weight_left, cfg, amount)
    apply_blink_compression(pose.right, blink_weight_right, cfg, amount)
    return amount


# ===========================================================================
# Attention shift - cinematic look with anticipation + overshoot
# ===========================================================================


class AttentionShiftPrimitive:
    """Generates a cinematic attention-shift envelope for look direction.

    Anticipates slightly BACK, then fires FORWARD with overshoot, then
    settles with a spring.  Good for 'focus' state entry, 'listening'
    transitions, and any dramatic look-at call.

    ``trigger`` accepts two calling conventions:
      - Production: trigger(dx, dy, duration_ms=350.0)
      - Compact:    trigger((dx, dy), duration_ms)
    """

    def __init__(self, cfg: AttentionShiftConfig | None = None) -> None:
        self._cfg = cfg or AttentionShiftConfig()
        self._spring = Spring2D(self._cfg.spring_config, (0.0, 0.0))
        self._tweens = TweenEngine()
        self._progress_s: float = 1.0
        self._duration_s: float = 0.35
        self._active: bool = False
        self._dx: float = 0.0
        self._dy: float = 0.0

    def set_config(self, cfg: AttentionShiftConfig) -> None:
        self._cfg = cfg
        self._spring.set_config(cfg.spring_config)

    def trigger(
        self,
        dx_or_target: "float | Tuple[float, float]",
        dy_or_duration: float = 350.0,
        duration_ms: float = 350.0,
    ) -> None:
        """Start an attention shift.

        Calling conventions:
          trigger(dx, dy, duration_ms=350)          # keyword/positional
          trigger((dx, dy), duration_ms)            # tuple target + scalar duration
        """
        if isinstance(dx_or_target, tuple):
            self._dx, self._dy = dx_or_target
            self._duration_s = max(0.05, dy_or_duration / 1000.0)
        else:
            self._dx = float(dx_or_target)
            self._dy = float(dy_or_duration)
            self._duration_s = max(0.05, duration_ms / 1000.0)
        self._progress_s = 0.0
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def get_offsets(self) -> Tuple[float, float]:
        return self._spring.value

    def update(self, dt_s: float, amount: float = 1.0) -> Tuple[float, float]:
        if self._active:
            self._progress_s += dt_s
            t = clamp01(self._progress_s / self._duration_s)
            overshoot_cfg = OvershootConfig(
                anticipation_amount=0.08,
                overshoot_amount=0.18,
                overshoot_peak=0.45,
                settle_ease=ease_out_back,
            )
            env = overshoot_envelope(t, overshoot_cfg)
            tx = self._dx * env * amount
            ty = self._dy * env * amount
            self._spring.set_target(tx, ty)
            if t >= 1.0 and self._spring.at_rest():
                self._active = False
                self._spring.set_target(0.0, 0.0)
        else:
            self._tweens.clear()
        return self._spring.update(dt_s)

    def apply_to_pair(
        self, pose: EyePair, dt_s: float, amount: float = 1.0
    ) -> None:
        """Apply this frame's attention shift offsets into both eyes."""
        dx, dy = self.update(dt_s, amount)
        pose.left.look_offset_x += dx * self._cfg.asymmetry_left
        pose.left.look_offset_y += dy * self._cfg.asymmetry_left
        pose.right.look_offset_x += dx * self._cfg.asymmetry_right
        pose.right.look_offset_y += dy * self._cfg.asymmetry_right


# ===========================================================================
# Emotion morph - per-property-group easing for smooth, cinematic blends
# ===========================================================================


def morph_param(
    from_value: float,
    to_value: float,
    t: float,
    ease_fn,
) -> float:
    """Blend a single param using its group's easing curve."""
    return lerp(from_value, to_value, ease_fn(clamp01(t)))


def apply_emotion_morph(
    dst: EyeParams,
    src_from: EyeParams,
    src_to: EyeParams,
    t: float,
    cfg: EmotionMorphConfig | None = None,
) -> None:
    """Write emotion-morphed eye parameters into dst.

    Every property group uses a different easing so positional changes,
    shape changes, and "effect" changes (glow, opacity) animate at subtly
    different cadences producing a cinematic layered transition.
    """
    c = cfg or EmotionMorphConfig()
    t = clamp01(t)

    dst.pos_x = morph_param(src_from.pos_x, src_to.pos_x, t, c.position_ease)
    dst.pos_y = morph_param(src_from.pos_y, src_to.pos_y, t, c.position_ease)
    dst.radius = morph_param(src_from.radius, src_to.radius, t, c.radius_ease)

    dst.scale_x = morph_param(src_from.scale_x, src_to.scale_x, t, c.scale_ease)
    dst.scale_y = morph_param(src_from.scale_y, src_to.scale_y, t, c.scale_ease)
    dst.stretch = morph_param(src_from.stretch, src_to.stretch, t, c.scale_ease)
    dst.squash = morph_param(src_from.squash, src_to.squash, t, c.scale_ease)

    dst.rotation = morph_param(src_from.rotation, src_to.rotation, t, c.rotation_ease)
    dst.iris_scale = morph_param(src_from.iris_scale, src_to.iris_scale, t, c.iris_ease)

    dst.lid_openness = morph_param(src_from.lid_openness, src_to.lid_openness, t, c.lid_ease)
    dst.blink_weight = morph_param(src_from.blink_weight, src_to.blink_weight, t, c.lid_ease)
    dst.upper_lid_curvature = morph_param(
        src_from.upper_lid_curvature, src_to.upper_lid_curvature, t, c.curvature_ease
    )
    dst.lower_lid_curvature = morph_param(
        src_from.lower_lid_curvature, src_to.lower_lid_curvature, t, c.curvature_ease
    )

    dst.opacity = morph_param(src_from.opacity, src_to.opacity, t, c.opacity_ease)
    dst.glow_strength = morph_param(src_from.glow_strength, src_to.glow_strength, t, c.glow_ease)

    # Offsets: keep them additive via linear blend (they're micro-motion, not shapes).
    dst.look_offset_x = lerp(src_from.look_offset_x, src_to.look_offset_x, t)
    dst.look_offset_y = lerp(src_from.look_offset_y, src_to.look_offset_y, t)
    dst.micro_offset_x = lerp(src_from.micro_offset_x, src_to.micro_offset_x, t)
    dst.micro_offset_y = lerp(src_from.micro_offset_y, src_to.micro_offset_y, t)
    dst.bounce_offset_x = lerp(src_from.bounce_offset_x, src_to.bounce_offset_x, t)
    dst.bounce_offset_y = lerp(src_from.bounce_offset_y, src_to.bounce_offset_y, t)
    dst.emotion_blend_weight = lerp(
        src_from.emotion_blend_weight, src_to.emotion_blend_weight, t
    )


def apply_emotion_morph_pair(
    dst: EyePair,
    src_from: EyePair,
    src_to: EyePair,
    t: float,
    cfg: EmotionMorphConfig | None = None,
) -> None:
    apply_emotion_morph(dst.left, src_from.left, src_to.left, t, cfg)
    apply_emotion_morph(dst.right, src_from.right, src_to.right, t, cfg)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Configs
    "BreathingConfig",
    "BounceConfig",
    "OvershootConfig",
    "SettleConfig",
    "DriftConfig",
    "PulseConfig",
    "SquashConfig",
    "StretchConfig",
    "LookScanConfig",
    "IdleNoiseConfig",
    "MicroCorrectionConfig",
    "BlinkMotionConfig",
    "AttentionShiftConfig",
    "EmotionMorphConfig",
    # Stateless single-eye functions
    "apply_breathing",
    "apply_bounce",
    "apply_drift",
    "apply_pulse",
    "apply_squash",
    "apply_stretch",
    "apply_blink_compression",
    "overshoot_envelope",
    "morph_param",
    "apply_emotion_morph",
    # Stateless pair functions
    "apply_breathing_pair",
    "apply_bounce_pair",
    "apply_drift_pair",
    "apply_pulse_pair",
    "apply_squash_pair",
    "apply_stretch_pair",
    "apply_blink_compression_pair",
    "apply_emotion_morph_pair",
    # Stateful primitives
    "SettledValue",
    "SettledPair",
    "LookScanPrimitive",
    "IdleNoisePrimitive",
    "IdleNoisePair",
    "MicroCorrectionPrimitive",
    "AttentionShiftPrimitive",
]
