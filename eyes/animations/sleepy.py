"""
Sleepy animation - low-arousal, drowsy state.

Lids heavy, eyes half-closed, slow sinusoidal lid droop,
very slow breathing, slow micro motion.
Communicates tiredness, sleepiness, relaxation.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class SleepyAnimation(AnimationState):
    name = "sleepy"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 700.0
        self._exit_duration_ms = 500.0

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 0.95
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy + 3.0 - eye.pos_y) * t
            eye.radius = eye.radius + (target_radius - eye.radius) * t
            eye.scale_y = eye.scale_y + (0.82 - eye.scale_y) * t
            eye.lid_openness = eye.lid_openness + (0.45 - eye.lid_openness) * t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (0.22 - eye.upper_lid_curvature) * t
            eye.blink_weight = eye.blink_weight + (0.25 - eye.blink_weight) * t
            eye.iris_scale = eye.iris_scale + (0.90 - eye.iris_scale) * t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        droop = math.sin(t_s * 2.0 * math.pi / 4.2) * 0.05 + 0.12
        slow_scale = math.sin(t_s * 2.0 * math.pi / 7.0) * 0.01
        for eye in [pose.left, pose.right]:
            eye.blink_weight = min(0.8, eye.blink_weight + droop)
            eye.lid_openness = max(0.2, eye.lid_openness - droop * 0.3)
            eye.scale_y += slow_scale

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        inv = 1.0 - t
        for eye in [pose.left, pose.right]:
            eye.blink_weight *= inv
            eye.lid_openness = eye.lid_openness * inv + 1.0 * t
