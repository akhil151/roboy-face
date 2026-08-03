"""
Thinking animation - active cognitive processing mode.

Eyes slightly squinted, slow lateral micro-saccades, gentle rotation.
Communicates reasoning, deliberation, or processing of complex input.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class ThinkingAnimation(AnimationState):
    name = "thinking"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 400.0
        self._exit_duration_ms = 300.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 0.97
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy + 2.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (0.94 - eye.scale_y) * t
            eye.scale_x = eye.scale_x + (1.02 - eye.scale_x) * t
            eye.squash = eye.squash + (0.04 - eye.squash) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.08 - eye.upper_lid_curvature) * t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (0.06 - eye.lower_lid_curvature) * t
            eye.iris_scale = eye.iris_scale + (1.03 - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        look_x = math.sin(t_s * 2.0 * math.pi / 3.7) * 0.35
        look_y = math.sin(t_s * 2.0 * math.pi / 2.3 + 0.5) * 0.2
        rot = math.sin(t_s * 2.0 * math.pi / 4.5) * 0.01
        for eye in [pose.left, pose.right]:
            eye.look_offset_x += look_x * 8.0
            eye.look_offset_y += look_y * 6.0
            eye.rotation += rot

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
