"""
Single eye rig with all procedural animation parameters.

Every animation is performed by smoothly interpolating these values.
No image assets are used - rendering is entirely procedural from this state.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EyeParams:
    pos_x: float = 0.0
    pos_y: float = 0.0
    radius: float = 90.0
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
        return EyeParams(
            pos_x=self.pos_x,
            pos_y=self.pos_y,
            radius=self.radius,
            scale_x=self.scale_x,
            scale_y=self.scale_y,
            stretch=self.stretch,
            squash=self.squash,
            rotation=self.rotation,
            blink_weight=self.blink_weight,
            lid_openness=self.lid_openness,
            look_offset_x=self.look_offset_x,
            look_offset_y=self.look_offset_y,
            emotion_blend_weight=self.emotion_blend_weight,
            micro_offset_x=self.micro_offset_x,
            micro_offset_y=self.micro_offset_y,
            bounce_offset_x=self.bounce_offset_x,
            bounce_offset_y=self.bounce_offset_y,
            opacity=self.opacity,
            glow_strength=self.glow_strength,
            iris_scale=self.iris_scale,
            upper_lid_curvature=self.upper_lid_curvature,
            lower_lid_curvature=self.lower_lid_curvature,
        )

    def reset(self) -> None:
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.radius = 90.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.stretch = 0.0
        self.squash = 0.0
        self.rotation = 0.0
        self.blink_weight = 0.0
        self.lid_openness = 1.0
        self.look_offset_x = 0.0
        self.look_offset_y = 0.0
        self.emotion_blend_weight = 0.0
        self.micro_offset_x = 0.0
        self.micro_offset_y = 0.0
        self.bounce_offset_x = 0.0
        self.bounce_offset_y = 0.0
        self.opacity = 1.0
        self.glow_strength = 0.0
        self.iris_scale = 1.0
        self.upper_lid_curvature = 0.0
        self.lower_lid_curvature = 0.0


def blend_params(a: EyeParams, b: EyeParams, t: float) -> EyeParams:
    """Linearly interpolate between two EyeParams states."""
    result = a.copy()
    result.pos_x = a.pos_x + (b.pos_x - a.pos_x) * t
    result.pos_y = a.pos_y + (b.pos_y - a.pos_y) * t
    result.radius = a.radius + (b.radius - a.radius) * t
    result.scale_x = a.scale_x + (b.scale_x - a.scale_x) * t
    result.scale_y = a.scale_y + (b.scale_y - a.scale_y) * t
    result.stretch = a.stretch + (b.stretch - a.stretch) * t
    result.squash = a.squash + (b.squash - a.squash) * t
    result.rotation = a.rotation + (b.rotation - a.rotation) * t
    result.blink_weight = a.blink_weight + (b.blink_weight - a.blink_weight) * t
    result.lid_openness = a.lid_openness + (b.lid_openness - a.lid_openness) * t
    result.look_offset_x = a.look_offset_x + (b.look_offset_x - a.look_offset_x) * t
    result.look_offset_y = a.look_offset_y + (b.look_offset_y - a.look_offset_y) * t
    result.emotion_blend_weight = a.emotion_blend_weight + (b.emotion_blend_weight - a.emotion_blend_weight) * t
    result.micro_offset_x = a.micro_offset_x + (b.micro_offset_x - a.micro_offset_x) * t
    result.micro_offset_y = a.micro_offset_y + (b.micro_offset_y - a.micro_offset_y) * t
    result.bounce_offset_x = a.bounce_offset_x + (b.bounce_offset_x - a.bounce_offset_x) * t
    result.bounce_offset_y = a.bounce_offset_y + (b.bounce_offset_y - a.bounce_offset_y) * t
    result.opacity = a.opacity + (b.opacity - a.opacity) * t
    result.glow_strength = a.glow_strength + (b.glow_strength - a.glow_strength) * t
    result.iris_scale = a.iris_scale + (b.iris_scale - b.iris_scale) * t
    result.upper_lid_curvature = a.upper_lid_curvature + (b.upper_lid_curvature - a.upper_lid_curvature) * t
    result.lower_lid_curvature = a.lower_lid_curvature + (b.lower_lid_curvature - a.lower_lid_curvature) * t
    return result
