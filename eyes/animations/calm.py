"""
Calm animation - the default relaxed state.

Eyes are centered, eyelids relaxed, gentle breathing baseline.
Serves as the identity pose that other states blend to/from.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class CalmAnimation(AnimationState):
    name = "calm"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 300.0
        self._exit_duration_ms = 250.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        t2 = t * t
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy - eye.pos_y) * t
            eye.radius = eye.radius + (self._base_radius - eye.radius) * t
            eye.scale_x = eye.scale_x + (1.0 - eye.scale_x) * t
            eye.scale_y = eye.scale_y + (1.0 - eye.scale_y) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.0 - eye.upper_lid_curvature) * t2
            eye.lower_lid_curvature = eye.lower_lid_curvature + (0.0 - eye.lower_lid_curvature) * t2
            eye.iris_scale = eye.iris_scale + (1.0 - eye.iris_scale) * t
            eye.opacity = eye.opacity + (1.0 - eye.opacity) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t = elapsed_ms / 1000.0
        breathe = math.sin(t * 2.0 * math.pi / 4.5) * 0.012
        for eye in [pose.left, pose.right]:
            eye.scale_y = 1.0 + breathe

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
