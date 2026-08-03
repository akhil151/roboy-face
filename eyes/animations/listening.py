"""
Listening animation - receptive attention mode.

Eyes slightly wider, iris tracking active, upper lids lifted slightly.
Communicates that the robot is actively listening to the user.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class ListeningAnimation(AnimationState):
    name = "listening"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 350.0
        self._exit_duration_ms = 280.0
        layout = config.layout
        self._base_radius = layout.eye_radius
        self._left_cx = config.display.width * 0.5 - layout.eye_spacing * 0.5
        self._right_cx = config.display.width * 0.5 + layout.eye_spacing * 0.5
        self._cy = layout.center_y

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 1.03
        openness = 1.0 + 0.05 * t
        upper_curve = -0.12 * t
        iris = 1.0 - 0.05 * t
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy - 3.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (1.04 - eye.scale_y) * t
            eye.scale_x = eye.scale_x + (0.98 - eye.scale_x) * t
            eye.lid_openness = eye.lid_openness + (openness - eye.lid_openness) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (upper_curve - eye.upper_lid_curvature) * t
            eye.iris_scale = eye.iris_scale + (iris - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        tiny_y = math.sin(t_s * 2.0 * math.pi / 6.0 + 0.3) * 1.5
        tiny_open = math.sin(t_s * 2.0 * math.pi / 3.0) * 0.012
        for eye in [pose.left, pose.right]:
            eye.pos_y += tiny_y
            eye.scale_y += tiny_open

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
