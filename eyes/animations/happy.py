"""
Happy animation - positive, joyful emotional state.

Eyes slightly squinted (smiling via lids), lifted lower lids (cheek raise),
iris slightly dilated, gentle up-and-down bounce rhythm.
Communicates warmth, happiness, friendliness.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class HappyAnimation(AnimationState):
    name = "happy"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 350.0
        self._exit_duration_ms = 300.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 0.96
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy + 1.5 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (0.88 - eye.scale_y) * t
            eye.scale_x = eye.scale_x + (1.06 - eye.scale_x) * t
            eye.squash = eye.squash + (0.08 - eye.squash) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.18 - eye.upper_lid_curvature) * t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (-0.20 - eye.lower_lid_curvature) * t
            eye.lid_openness = eye.lid_openness + (0.82 - eye.lid_openness) * t
            eye.iris_scale = eye.iris_scale + (0.92 - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        bounce = -abs(math.sin(t_s * 2.0 * math.pi * 0.9)) * 3.0
        squint = math.sin(t_s * 2.0 * math.pi * 0.9) * 0.01
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y = bounce
            eye.scale_y += squint
            eye.upper_lid_curvature += abs(math.sin(t_s * 2.0 * math.pi * 0.9)) * 0.02

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y *= (1.0 - t)
