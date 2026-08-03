"""
Focus animation - intense concentration mode.

Eyes narrowed, lids tensed, iris slightly constricted,
very still (reduced micro motion), sharp tight geometry.
Communicates reading, analysis, sharp focus.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class FocusAnimation(AnimationState):
    name = "focus"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 320.0
        self._exit_duration_ms = 280.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 0.95
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy - 1.5 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (0.85 - eye.scale_y) * t
            eye.scale_x = eye.scale_x + (1.03 - eye.scale_x) * t
            eye.squash = eye.squash + (0.07 - eye.squash) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.05 - eye.upper_lid_curvature) * t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (0.09 - eye.lower_lid_curvature) * t
            eye.lid_openness = eye.lid_openness + (0.68 - eye.lid_openness) * t
            eye.iris_scale = eye.iris_scale + (1.06 - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        tiny = math.sin(t_s * 2.0 * math.pi / 8.0) * 0.004
        focus_twitch = math.sin(t_s * 2.0 * math.pi * 1.3) * math.exp(-2.0 * (t_s % 2.0)) * 0.5
        for eye in [pose.left, pose.right]:
            eye.scale_y += tiny
            eye.look_offset_y -= focus_twitch

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        pass
