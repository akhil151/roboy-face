"""
Speaking animation - active verbal output mode.

Eyes open, rhythmic jaw/cheek simulation via vertical micro-bounce,
slight horizontal stretch mimicking speech articulation.
Communicates that the robot is actively talking.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class SpeakingAnimation(AnimationState):
    name = "speaking"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 250.0
        self._exit_duration_ms = 250.0
        layout = config.layout
        self._base_radius = layout.eye_radius
        self._left_cx = config.display.width * 0.5 - layout.eye_spacing * 0.5
        self._right_cx = config.display.width * 0.5 + layout.eye_spacing * 0.5
        self._cy = layout.center_y

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 1.02
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy - 2.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (1.03 - eye.scale_y) * t
            eye.lid_openness = eye.lid_openness + (1.05 - eye.lid_openness) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (-0.04 - eye.upper_lid_curvature) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        bounce = -abs(math.sin(t_s * 2.0 * math.pi * 1.8)) * 2.0
        stretch = math.sin(t_s * 2.0 * math.pi * 3.1) * 0.012
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y = bounce
            eye.scale_y += math.sin(t_s * 2.0 * math.pi * 2.1) * 0.02
            eye.stretch += stretch

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y *= (1.0 - t)
            eye.stretch *= (1.0 - t)
