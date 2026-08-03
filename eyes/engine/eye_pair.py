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

    def clamp_safe(self) -> None:
        self.left.clamp_safe()
        self.right.clamp_safe()

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
