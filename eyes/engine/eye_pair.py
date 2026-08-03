"""
Eye pair system - manages left and right eyes as a cohesive unit.

Provides symmetric control for both eyes while allowing per-eye variation.
Handles spatial layout based on configuration.
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

    def copy(self) -> "EyePair":
        ep = EyePair()
        ep.left = self.left.copy()
        ep.right = self.right.copy()
        ep.left_center_x = self.left_center_x
        ep.right_center_x = self.right_center_x
        ep.center_y = self.center_y
        return ep


def blend_eye_pair(a: EyePair, b: EyePair, t: float) -> EyePair:
    result = a.copy()
    result.left = blend_params(a.left, b.left, t)
    result.right = blend_params(a.right, b.right, t)
    if t > 0.5:
        result.left_center_x = b.left_center_x
        result.right_center_x = b.right_center_x
        result.center_y = b.center_y
    return result
