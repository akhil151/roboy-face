"""
Eye pair system - manages left and right eyes as a cohesive unit.

Provides symmetric control for both eyes while allowing per-eye variation.
Handles spatial layout based on configuration.

All hot-path operations mutate preallocated instances in place to avoid
per-frame garbage collection pressure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .config import EngineConfig
from .eye import EyeParams, blend_params


@dataclass
class EyePair:
    left: EyeParams = field(default_factory=EyeParams)
    right: EyeParams = field(default_factory=EyeParams)
    left_center_x: float = 0.0
    right_center_x: float = 0.0
    center_y: float = 0.0

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def configure(self, config: EngineConfig) -> None:
        layout = config.layout
        display_w = config.display.width
        center_x = display_w * 0.5
        self.left_center_x = center_x - layout.eye_spacing * 0.5
        self.right_center_x = center_x + layout.eye_spacing * 0.5
        self.center_y = layout.center_y

        self.left.pos_x = self.left_center_x
        self.left.pos_y = self.center_y
        self.left.radius = layout.eye_radius

        self.right.pos_x = self.right_center_x
        self.right.pos_y = self.center_y
        self.right.radius = layout.eye_radius

    def reset(self) -> None:
        self.left.reset()
        self.right.reset()
        self.left.pos_x = self.left_center_x
        self.left.pos_y = self.center_y
        self.right.pos_x = self.right_center_x
        self.right.pos_y = self.center_y

    # ------------------------------------------------------------------
    # Zero-allocation transforms
    # ------------------------------------------------------------------
    def copy(self) -> "EyePair":
        ep = EyePair()
        ep.left.copy_from(self.left)
        ep.right.copy_from(self.right)
        ep.left_center_x = self.left_center_x
        ep.right_center_x = self.right_center_x
        ep.center_y = self.center_y
        return ep

    def copy_from(self, other: "EyePair") -> None:
        self.left.copy_from(other.left)
        self.right.copy_from(other.right)
        self.left_center_x = other.left_center_x
        self.right_center_x = other.right_center_x
        self.center_y = other.center_y

    def lerp_into(self, a: "EyePair", b: "EyePair", t: float) -> None:
        self.left.lerp_into(a.left, b.left, t)
        self.right.lerp_into(a.right, b.right, t)
        if t >= 0.5:
            self.left_center_x = b.left_center_x
            self.right_center_x = b.right_center_x
            self.center_y = b.center_y
        else:
            self.left_center_x = a.left_center_x
            self.right_center_x = a.right_center_x
            self.center_y = a.center_y

    def blend_accumulate(self, other: "EyePair", weight: float) -> None:
        self.left.blend_accumulate(other.left, weight)
        self.right.blend_accumulate(other.right, weight)

    def blend_max(self, other: "EyePair") -> None:
        self.left.blend_max(other.left)
        self.right.blend_max(other.right)

    def clamp_safe(self, display_width: float = 800.0, display_height: float = 480.0) -> None:
        import math
        self.left.clamp_safe()
        self.right.clamp_safe()

        # Resolution-independent safe region bounds
        margin = min(display_width, display_height) * 0.025
        min_spacing = display_width * 0.22
        max_spacing = display_width * 0.48

        # 1. Soft spacing constraint
        current_spacing = self.right_center_x - self.left_center_x
        if current_spacing < min_spacing:
            mid_x = (self.left_center_x + self.right_center_x) * 0.5
            target_left = mid_x - min_spacing * 0.5
            target_right = mid_x + min_spacing * 0.5
            self.left_center_x += (target_left - self.left_center_x) * 0.25
            self.right_center_x += (target_right - self.right_center_x) * 0.25
        elif current_spacing > max_spacing:
            mid_x = (self.left_center_x + self.right_center_x) * 0.5
            target_left = mid_x - max_spacing * 0.5
            target_right = mid_x + max_spacing * 0.5
            self.left_center_x += (target_left - self.left_center_x) * 0.25
            self.right_center_x += (target_right - self.right_center_x) * 0.25

        # 2. Resolution-independent canvas boundary constraint with soft spring/damping restoration
        damping = 0.85
        for eye in (self.left, self.right):
            sx = eye.scale_x + eye.stretch - eye.squash * 0.5
            sy = eye.scale_y + eye.squash - eye.stretch * 0.5
            eff_rx = eye.radius * max(0.01, sx)
            eff_ry = eye.radius * max(0.01, sy)

            cos_r = abs(math.cos(eye.rotation))
            sin_r = abs(math.sin(eye.rotation))
            extent_x = eff_rx * cos_r + eff_ry * sin_r
            extent_y = eff_rx * sin_r + eff_ry * cos_r

            total_cx = eye.pos_x + eye.look_offset_x + eye.micro_offset_x + eye.bounce_offset_x
            total_cy = eye.pos_y + eye.look_offset_y + eye.micro_offset_y + eye.bounce_offset_y

            min_x = margin + extent_x
            max_x = display_width - margin - extent_x
            min_y = margin + extent_y
            max_y = display_height - margin - extent_y

            if total_cx < min_x:
                overflow = min_x - total_cx
                eye.look_offset_x += overflow * damping
            elif total_cx > max_x:
                overflow = max_x - total_cx
                eye.look_offset_x += overflow * damping

            if total_cy < min_y:
                overflow = min_y - total_cy
                eye.look_offset_y += overflow * damping
            elif total_cy > max_y:
                overflow = max_y - total_cy
                eye.look_offset_y += overflow * damping

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def centers(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return (
            (self.left_center_x, self.center_y),
            (self.right_center_x, self.center_y),
        )


def blend_eye_pair(a: EyePair, b: EyePair, t: float) -> EyePair:
    """Linearly interpolate between two EyePair states (compatibility API).

    Prefer ``EyePair.lerp_into`` when the destination exists.
    """
    result = a.copy()
    result.lerp_into(a, b, t)
    return result
