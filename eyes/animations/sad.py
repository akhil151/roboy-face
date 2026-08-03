"""
Sad animation - low-energy, downcast emotional state.

Eyes lowered slightly, upper lids drooping, lower lids flat,
inner corners slightly raised (tear-like shape), slow heavy breathing.
Communicates sadness, disappointment, low mood.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class SadAnimation(AnimationState):
    name = "sad"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 600.0
        self._exit_duration_ms = 450.0
        layout = config.layout
        self._base_radius = layout.eye_radius
        self._left_cx = config.display.width * 0.5 - layout.eye_spacing * 0.5
        self._right_cx = config.display.width * 0.5 + layout.eye_spacing * 0.5
        self._cy = layout.center_y

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 0.97
        for eye, cx, tilt in [(pose.left, self._left_cx, 1.0), (pose.right, self._right_cx, -1.0)]:
            eye.pos_x = eye.pos_x + (cx + tilt * 2.0 - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy + 5.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (0.91 - eye.scale_y) * t
            eye.lid_openness = eye.lid_openness + (0.75 - eye.lid_openness) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.14 - eye.upper_lid_curvature) * t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (0.10 - eye.lower_lid_curvature) * t
            eye.iris_scale = eye.iris_scale + (0.96 - eye.iris_scale) * t
            eye.look_offset_y += 6.0 * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        slow = math.sin(t_s * 2.0 * math.pi / 6.5) * 0.01
        droop = abs(math.sin(t_s * 2.0 * math.pi / 6.5)) * 0.01
        for eye in [pose.left, pose.right]:
            eye.scale_y += slow
            eye.upper_lid_curvature += droop

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
