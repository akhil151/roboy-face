"""
Caring animation - nurturing, empathetic mode.

Eyes slightly softer, wider vertically, lids gentle, subtle warmth via
lower lid curve and slightly dilated iris. Slow gentle motion.
Communicates empathy, caring, concern, support.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class CaringAnimation(AnimationState):
    name = "caring"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 500.0
        self._exit_duration_ms = 380.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 1.01
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy + 1.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (1.02 - eye.scale_y) * t
            eye.scale_x = eye.scale_x + (0.99 - eye.scale_x) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (-0.03 - eye.upper_lid_curvature) * t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (-0.08 - eye.lower_lid_curvature) * t
            eye.lid_openness = eye.lid_openness + (0.96 - eye.lid_openness) * t
            eye.iris_scale = eye.iris_scale + (0.94 - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        warm = math.sin(t_s * 2.0 * math.pi / 5.5 + 0.2) * 0.008
        for eye in [pose.left, pose.right]:
            eye.scale_y += warm
            eye.lower_lid_curvature += math.sin(t_s * 2.0 * math.pi / 5.5 + 0.2) * 0.01

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
