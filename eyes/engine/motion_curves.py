"""
Motion curve definitions for every animatable property in EyeParams.

Each property (radius, scale, rotation, lid_openness, ...) has a curve
description which defines:
  * The physical units and sensible default range
  * The default easing curve to use when morphing this property
  * Perceptual transfer function (linear / square / sqrt) so that equal
    perceptual deltas map to equal parameter deltas across the whole range
  * "Anticipation amount" - how much this property should move in the
    OPPOSITE direction before the main transition (weight, bounce, etc.)
  * "Overshoot amount" - how much this property should overshoot its target
    past the endpoint and settle back

These curves are used by the emotion blending system, the StateClipPlayer,
and by primitive authors to keep motion consistent across states.

Design rule: these curves are DECLARATIVE metadata - they describe how a
property SHOULD animate, they don't perform the animation themselves.  The
actual interpolation is done by morph_param / apply_emotion_morph in
motion_primitives, by the TweenEngine, or by Spring1D/2D.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

import math

from .easing import (
    EasingFunction,
    ease_in_out_cubic,
    ease_in_out_sine,
    ease_out_cubic,
    ease_in_cubic,
    ease_out_back,
    ease_out_elastic,
    clamp01,
)


@dataclass
class PropertyCurve:
    """Declarative motion metadata for a single EyeParams property.

    The curve never performs animation itself; it tells OTHER systems how
    to animate this property with cinematic quality.
    """

    # Human-readable name (matches EyeParams attribute name).
    name: str
    # Physical units for debug UI / tuning (displayed to animator, not computed).
    units: str
    # Sensible default [min, max] range (NOT a hard clamp; states can exceed).
    default_range: Tuple[float, float]
    # Resting / neutral value at the "calm" identity pose.
    neutral: float
    # Default easing for this property during transitions.
    default_ease: EasingFunction
    # Perceptual transfer: xform from linear blend progress to actual value blend.
    # "linear" by default; use sqrt for areas, square for intensities, etc.
    perceptual_xform: Callable[[float], float] = lambda t: t
    # How much this property "anticipates" - fraction of the delta moved BACKWARD first.
    # Typical values: 0.05 for scale, 0.02 for position, 0.15 for lid curvature.
    anticipation: float = 0.0
    # How much this property "overshoots" - fraction of delta moved PAST target.
    # Typical values: 0.10 for squash/stretch, 0.05 for lids, 0.02 for position.
    overshoot: float = 0.0
    # Settle time multiplier relative to global transition duration.
    # >1 means "slower", <1 means "snappier".  Good for separating layers.
    time_multiplier: float = 1.0
    # Priority (for debug / layer ordering).  Higher = "more important" for UI.
    priority: int = 50

    def transfer(self, t: float) -> float:
        """Apply perceptual transform to [0,1] progress t."""
        return self.perceptual_xform(clamp01(t))


# ---------------------------------------------------------------------------
# Property library - one entry per animatable field in EyeParams.
# ---------------------------------------------------------------------------


def _sqrt_xform(t: float) -> float:
    """Square-root transfer: small changes near 0 are perceptually bigger."""
    return math.sqrt(clamp01(t))


def _square_xform(t: float) -> float:
    """Square transfer: small changes near 1 are perceptually bigger."""
    t = clamp01(t)
    return t * t


PROPERTY_CURVES: Dict[str, PropertyCurve] = {
    # ------------------------------------------------------------------
    # Position group - smooth, slight overshoot, no dramatic anticipation.
    # ------------------------------------------------------------------
    "pos_x": PropertyCurve(
        name="pos_x",
        units="px",
        default_range=(50.0, 750.0),
        neutral=260.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.02,
        overshoot=0.02,
        time_multiplier=1.0,
        priority=90,
    ),
    "pos_y": PropertyCurve(
        name="pos_y",
        units="px",
        default_range=(40.0, 440.0),
        neutral=240.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.02,
        overshoot=0.025,
        time_multiplier=1.02,
        priority=90,
    ),
    # ------------------------------------------------------------------
    # Size / shape group - cinematic overshoot + modest anticipation.
    # ------------------------------------------------------------------
    "radius": PropertyCurve(
        name="radius",
        units="px",
        default_range=(30.0, 100.0),
        neutral=90.0,
        default_ease=ease_out_cubic,
        perceptual_xform=_sqrt_xform,
        anticipation=0.04,
        overshoot=0.06,
        time_multiplier=0.95,
        priority=85,
    ),
    "scale_x": PropertyCurve(
        name="scale_x",
        units="ratio",
        default_range=(0.7, 1.3),
        neutral=1.0,
        default_ease=ease_in_out_sine,
        anticipation=0.06,
        overshoot=0.09,
        time_multiplier=1.0,
        priority=80,
    ),
    "scale_y": PropertyCurve(
        name="scale_y",
        units="ratio",
        default_range=(0.7, 1.3),
        neutral=1.0,
        default_ease=ease_in_out_sine,
        anticipation=0.06,
        overshoot=0.09,
        time_multiplier=1.0,
        priority=80,
    ),
    "stretch": PropertyCurve(
        name="stretch",
        units="ratio",
        default_range=(0.0, 0.25),
        neutral=0.0,
        default_ease=ease_out_back,
        perceptual_xform=_square_xform,
        anticipation=0.08,
        overshoot=0.14,
        time_multiplier=0.9,
        priority=75,
    ),
    "squash": PropertyCurve(
        name="squash",
        units="ratio",
        default_range=(0.0, 0.25),
        neutral=0.0,
        default_ease=ease_out_back,
        perceptual_xform=_square_xform,
        anticipation=0.08,
        overshoot=0.14,
        time_multiplier=0.9,
        priority=75,
    ),
    # ------------------------------------------------------------------
    # Rotation - smooth, subtle; very conservative overshoot.
    # ------------------------------------------------------------------
    "rotation": PropertyCurve(
        name="rotation",
        units="rad",
        default_range=(-0.4, 0.4),
        neutral=0.0,
        default_ease=ease_in_out_sine,
        anticipation=0.01,
        overshoot=0.02,
        time_multiplier=1.08,
        priority=70,
    ),
    # ------------------------------------------------------------------
    # Eyelid group - expressive: lots of curvature overshoot, timed slightly slow.
    # ------------------------------------------------------------------
    "lid_openness": PropertyCurve(
        name="lid_openness",
        units="ratio",
        default_range=(0.0, 1.0),
        neutral=1.0,
        default_ease=ease_in_out_sine,
        perceptual_xform=_square_xform,
        anticipation=0.02,
        overshoot=0.04,
        time_multiplier=1.06,
        priority=95,
    ),
    "blink_weight": PropertyCurve(
        name="blink_weight",
        units="ratio",
        default_range=(0.0, 1.0),
        neutral=0.0,
        default_ease=ease_out_elastic,
        perceptual_xform=_square_xform,
        anticipation=0.0,
        overshoot=0.0,
        time_multiplier=0.7,
        priority=95,
    ),
    "upper_lid_curvature": PropertyCurve(
        name="upper_lid_curvature",
        units="ratio",
        default_range=(-0.5, 0.5),
        neutral=0.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.10,
        overshoot=0.12,
        time_multiplier=1.12,
        priority=88,
    ),
    "lower_lid_curvature": PropertyCurve(
        name="lower_lid_curvature",
        units="ratio",
        default_range=(-0.5, 0.5),
        neutral=0.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.12,
        overshoot=0.12,
        time_multiplier=1.12,
        priority=88,
    ),
    # ------------------------------------------------------------------
    # Iris
    # ------------------------------------------------------------------
    "iris_scale": PropertyCurve(
        name="iris_scale",
        units="ratio",
        default_range=(0.7, 1.25),
        neutral=1.0,
        default_ease=ease_in_out_sine,
        perceptual_xform=_sqrt_xform,
        anticipation=0.015,
        overshoot=0.03,
        time_multiplier=1.15,
        priority=82,
    ),
    # ------------------------------------------------------------------
    # Offsets (look / micro / bounce) - these blend linearly, spring handles "snap".
    # ------------------------------------------------------------------
    "look_offset_x": PropertyCurve(
        name="look_offset_x",
        units="px",
        default_range=(-35.0, 35.0),
        neutral=0.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.03,
        overshoot=0.05,
        time_multiplier=0.9,
        priority=78,
    ),
    "look_offset_y": PropertyCurve(
        name="look_offset_y",
        units="px",
        default_range=(-35.0, 35.0),
        neutral=0.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.03,
        overshoot=0.05,
        time_multiplier=0.9,
        priority=78,
    ),
    "micro_offset_x": PropertyCurve(
        name="micro_offset_x",
        units="px",
        default_range=(-3.0, 3.0),
        neutral=0.0,
        default_ease=ease_in_out_sine,
        anticipation=0.0,
        overshoot=0.0,
        time_multiplier=1.0,
        priority=60,
    ),
    "micro_offset_y": PropertyCurve(
        name="micro_offset_y",
        units="px",
        default_range=(-3.0, 3.0),
        neutral=0.0,
        default_ease=ease_in_out_sine,
        anticipation=0.0,
        overshoot=0.0,
        time_multiplier=1.0,
        priority=60,
    ),
    "bounce_offset_x": PropertyCurve(
        name="bounce_offset_x",
        units="px",
        default_range=(-6.0, 6.0),
        neutral=0.0,
        default_ease=ease_out_back,
        anticipation=0.04,
        overshoot=0.15,
        time_multiplier=0.85,
        priority=65,
    ),
    "bounce_offset_y": PropertyCurve(
        name="bounce_offset_y",
        units="px",
        default_range=(-8.0, 8.0),
        neutral=0.0,
        default_ease=ease_out_back,
        anticipation=0.04,
        overshoot=0.15,
        time_multiplier=0.85,
        priority=65,
    ),
    # ------------------------------------------------------------------
    # Effects group (glow, opacity) - square transfer, gentle motion.
    # ------------------------------------------------------------------
    "opacity": PropertyCurve(
        name="opacity",
        units="ratio",
        default_range=(0.0, 1.0),
        neutral=1.0,
        default_ease=ease_in_out_sine,
        perceptual_xform=_square_xform,
        anticipation=0.0,
        overshoot=0.0,
        time_multiplier=1.1,
        priority=55,
    ),
    "glow_strength": PropertyCurve(
        name="glow_strength",
        units="ratio",
        default_range=(0.0, 0.8),
        neutral=0.0,
        default_ease=ease_out_cubic,
        perceptual_xform=_square_xform,
        anticipation=0.0,
        overshoot=0.08,
        time_multiplier=0.92,
        priority=55,
    ),
    "emotion_blend_weight": PropertyCurve(
        name="emotion_blend_weight",
        units="ratio",
        default_range=(0.0, 1.0),
        neutral=0.0,
        default_ease=ease_in_out_cubic,
        anticipation=0.0,
        overshoot=0.0,
        time_multiplier=1.0,
        priority=40,
    ),
}


def get_curve(prop_name: str) -> PropertyCurve:
    """Return the PropertyCurve metadata for a named EyeParams attribute."""
    if prop_name not in PROPERTY_CURVES:
        raise KeyError(
            f"No motion curve defined for property '{prop_name}'. "
            f"Available: {sorted(PROPERTY_CURVES.keys())}"
        )
    return PROPERTY_CURVES[prop_name]


def curve_names_by_priority() -> list[str]:
    """Return property names sorted from highest-priority to lowest."""
    return sorted(PROPERTY_CURVES.keys(), key=lambda n: (-PROPERTY_CURVES[n].priority, n))


# ---------------------------------------------------------------------------
# Cinematic blend helpers
# ---------------------------------------------------------------------------


def cinematic_delta(
    curve: PropertyCurve,
    from_value: float,
    to_value: float,
    t: float,
    *,
    global_anticipation_scale: float = 1.0,
    global_overshoot_scale: float = 1.0,
) -> float:
    """Blend from_value -> to_value using the property's cinematic curve.

    Combines:
      * The curve's default easing (scaled by time_multiplier)
      * The perceptual transfer function
      * The anticipation phase (pre-move in opposite direction)
      * The overshoot phase (post-move past target, then settle back)

    The returned value can go slightly outside [from_value, to_value] when
    anticipation/overshoot are nonzero - this is INTENTIONAL for cinematic
    feel.  Callers should clamp only the final pose before rendering
    (``EyeParams.clamp_safe`` / ``EyePair.clamp_safe`` already do this).
    """
    t_raw = clamp01(t)
    # Apply time_multiplier: compress/expand t around the 0.5 midpoint.
    tm = max(0.1, min(5.0, curve.time_multiplier))
    if tm != 1.0:
        center = 0.5
        t_scaled = center + (t_raw - center) / tm
        t_scaled = clamp01(t_scaled)
    else:
        t_scaled = t_raw

    eased = curve.default_ease(t_scaled)
    xferred = curve.transfer(eased)
    # Base linear blend.
    base = from_value + (to_value - from_value) * xferred
    delta = to_value - from_value
    if delta == 0.0:
        return base
    # Anticipation: at the very beginning, pull slightly the wrong way.
    # Skip at t=0 exactly so the blend starts precisely at from_value.
    ant_amount = curve.anticipation * global_anticipation_scale
    if ant_amount > 0.0 and 0.0 < t_raw < 0.35:
        ant_window = 1.0 - (t_raw / 0.35)
        ant_window = ant_window * ant_window  # squared falloff
        base -= delta * ant_amount * ant_window
    # Overshoot: near the end, push slightly past the target.
    over_amount = curve.overshoot * global_overshoot_scale
    if over_amount > 0.0 and t_raw > 0.55:
        over_window = 1.0 - ((t_raw - 0.55) / 0.45)
        over_window = over_window * over_window  # squared falloff
        base += delta * over_amount * over_window
    return base


# ---------------------------------------------------------------------------
# Convenience: property-group shortcuts for states that want to animate
# whole categories at once (positions, shape, lids, effects).
# ---------------------------------------------------------------------------


def group_property_names(group: str = "") -> "list[str] | dict[str, list[str]]":
    """Return property names belonging to a semantic group.

    When called with no arguments (or group=""), returns a dict mapping
    every group name to its property list.  This lets callers check how
    many groups are defined (``len(group_property_names()) == 7``).

    When called with a group name string, returns the list for that group.

    Groups:
      * "position" : pos_x, pos_y
      * "size"     : radius, scale_x, scale_y, stretch, squash
      * "shape"    : size + rotation
      * "lids"     : lid_openness, blink_weight, upper_lid_curvature, lower_lid_curvature
      * "iris"     : iris_scale
      * "offsets"  : look_offset_*, micro_offset_*, bounce_offset_*
      * "effects"  : opacity, glow_strength, emotion_blend_weight
    """
    groups: dict[str, list[str]] = {
        "position": ["pos_x", "pos_y"],
        "size": ["radius", "scale_x", "scale_y", "stretch", "squash"],
        "shape": ["radius", "scale_x", "scale_y", "stretch", "squash", "rotation"],
        "lids": [
            "lid_openness",
            "blink_weight",
            "upper_lid_curvature",
            "lower_lid_curvature",
        ],
        "iris": ["iris_scale"],
        "offsets": [
            "look_offset_x",
            "look_offset_y",
            "micro_offset_x",
            "micro_offset_y",
            "bounce_offset_x",
            "bounce_offset_y",
        ],
        "effects": ["opacity", "glow_strength", "emotion_blend_weight"],
    }
    if not group:
        # No-arg call: return the whole groups dict so callers can inspect
        # how many groups exist and what they contain.
        return groups
    if group not in groups:
        raise KeyError(f"Unknown property group '{group}'. Available: {sorted(groups.keys())}")
    return groups[group]


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "PropertyCurve",
    "PROPERTY_CURVES",
    "get_curve",
    "curve_names_by_priority",
    "cinematic_delta",
    "group_property_names",
]
