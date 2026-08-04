"""
Single eye rig with all procedural animation parameters.

Every animation is performed by smoothly interpolating these values.
No image assets are used - rendering is entirely procedural from this state.

All interpolation is performed IN-PLACE on preallocated instances to avoid
per-frame allocation pressure. Use ``copy_from``/``blend_from_into``/``lerp_into``
rather than constructing new EyeParams objects each frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


# ---------------------------------------------------------------------------
# Preallocated defaults used to reset() an instance without allocation.
# ---------------------------------------------------------------------------
_DEFAULT_PARAMS = {
    "pos_x": 0.0,
    "pos_y": 0.0,
    "radius": 75.0,
    "scale_x": 1.0,
    "scale_y": 1.0,
    "stretch": 0.0,
    "squash": 0.0,
    "rotation": 0.0,
    "blink_weight": 0.0,
    "lid_openness": 1.0,
    "look_offset_x": 0.0,
    "look_offset_y": 0.0,
    "emotion_blend_weight": 0.0,
    "micro_offset_x": 0.0,
    "micro_offset_y": 0.0,
    "bounce_offset_x": 0.0,
    "bounce_offset_y": 0.0,
    "opacity": 1.0,
    "glow_strength": 0.0,
    "iris_scale": 1.0,
    "upper_lid_curvature": 0.0,
    "lower_lid_curvature": 0.0,
}

_PARAM_NAMES: Tuple[str, ...] = tuple(_DEFAULT_PARAMS.keys())


@dataclass
class EyeParams:
    pos_x: float = 0.0
    pos_y: float = 0.0
    radius: float = 75.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    stretch: float = 0.0
    squash: float = 0.0
    rotation: float = 0.0
    blink_weight: float = 0.0
    lid_openness: float = 1.0
    look_offset_x: float = 0.0
    look_offset_y: float = 0.0
    emotion_blend_weight: float = 0.0
    micro_offset_x: float = 0.0
    micro_offset_y: float = 0.0
    bounce_offset_x: float = 0.0
    bounce_offset_y: float = 0.0
    opacity: float = 1.0
    glow_strength: float = 0.0
    iris_scale: float = 1.0
    upper_lid_curvature: float = 0.0
    lower_lid_curvature: float = 0.0

    def copy(self) -> "EyeParams":
        new = EyeParams()
        for name in _PARAM_NAMES:
            setattr(new, name, getattr(self, name))
        return new

    def copy_from(self, other: "EyeParams") -> None:
        for name in _PARAM_NAMES:
            setattr(self, name, getattr(other, name))

    def reset(self) -> None:
        for name, value in _DEFAULT_PARAMS.items():
            setattr(self, name, value)

    def lerp_into(self, a: "EyeParams", b: "EyeParams", t: float) -> None:
        """Set ``self = a + (b - a) * t``.  Zero allocation.

        This is the hot-path interpolation used by the mixer every frame.
        """
        for name in _PARAM_NAMES:
            av = getattr(a, name)
            bv = getattr(b, name)
            setattr(self, name, av + (bv - av) * t)

    def blend_accumulate(self, other: "EyeParams", weight: float) -> None:
        """Add ``other * weight`` into this instance (for additive layers)."""
        if weight == 0.0:
            return
        for name in _PARAM_NAMES:
            v = getattr(self, name)
            setattr(self, name, v + getattr(other, name) * weight)

    def blend_max(self, other: "EyeParams") -> None:
        """Component-wise max; useful for blink weight, lid closure, etc."""
        for name in _PARAM_NAMES:
            ov = getattr(other, name)
            sv = getattr(self, name)
            if ov > sv:
                setattr(self, name, ov)

    def clamp_safe(self) -> None:
        """Clamp ratios and values to safe physical and rendering boundaries."""
        if self.opacity > 1.0:
            self.opacity = 1.0
        elif self.opacity < 0.0:
            self.opacity = 0.0

        # Physical geometry & transform bounds
        self.radius = max(10.0, min(110.0, self.radius))
        self.scale_x = max(0.10, min(1.35, self.scale_x))
        self.scale_y = max(0.10, min(1.35, self.scale_y))
        self.stretch = max(-0.35, min(0.35, self.stretch))
        self.squash = max(0.0, min(0.40, self.squash))
        self.rotation = max(-0.35, min(0.35, self.rotation))
        self.iris_scale = max(0.10, min(1.50, self.iris_scale))

        # Dynamic offsets bounds
        self.look_offset_x = max(-36.0, min(36.0, self.look_offset_x))
        self.look_offset_y = max(-36.0, min(36.0, self.look_offset_y))
        self.bounce_offset_x = max(-26.0, min(26.0, self.bounce_offset_x))
        self.bounce_offset_y = max(-26.0, min(26.0, self.bounce_offset_y))
        self.micro_offset_x = max(-10.0, min(10.0, self.micro_offset_x))
        self.micro_offset_y = max(-10.0, min(10.0, self.micro_offset_y))


def blend_params(a: EyeParams, b: EyeParams, t: float) -> EyeParams:
    """Linearly interpolate between two EyeParams states.

    Retained for compatibility.  Prefer ``EyeParams.lerp_into`` when the
    destination is already allocated (the common hot-path case).
    """
    result = a.copy()
    for name in _PARAM_NAMES:
        av = getattr(a, name)
        bv = getattr(b, name)
        setattr(result, name, av + (bv - av) * t)
    return result
