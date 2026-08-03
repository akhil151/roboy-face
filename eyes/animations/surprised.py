"""
Surprised animation - high-arousal, startled state.

Eyes wide open, lids fully retracted, iris dilated fully,
slight forward bounce and stretch, lids pulled fully back.
Communicates surprise, shock, realization, excitement.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .base import AnimationState

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class SurprisedAnimation(AnimationState):
    name = "surprised"

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)
        self._entry_duration_ms = 280.0
        self._exit_duration_ms = 320.0
        layout = config.layout
        self._base_radius = layout.eye_radius
        self._left_cx = config.display.width * 0.5 - layout.eye_spacing * 0.5
        self._right_cx = config.display.width * 0.5 + layout.eye_spacing * 0.5
        self._cy = layout.center_y

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        target_radius = self._base_radius * 1.10
        stretch_t = 1.0 - (1.0 - t) * (1.0 - t)
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = eye.pos_x + (cx - eye.pos_x) * t
            eye.pos_y = eye.pos_y + (self._cy - 5.0 - eye.pos_y) * stretch_t
            eye.radius = eye.radius + (target_radius - eye.radius) * stretch_t
            eye.scale_y = eye.scale_y + (1.12 - eye.scale_y) * stretch_t
            eye.scale_x = eye.scale_x + (1.04 - eye.scale_x) * t
            eye.stretch = eye.stretch + (0.08 - eye.stretch) * stretch_t
            eye.lid_openness = eye.lid_openness + (1.10 - eye.lid_openness) * stretch_t
            eye.upper_lid_curvature = eye.upper_lid_curvature + (-0.18 - eye.upper_lid_curvature) * stretch_t
            eye.lower_lid_curvature = eye.lower_lid_curvature + (0.12 - eye.lower_lid_curvature) * stretch_t
            eye.iris_scale = eye.iris_scale + (1.08 - eye.iris_scale) * stretch_t

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        t_s = elapsed_ms / 1000.0
        decay = math.exp(-t_s * 1.5)
        bounce = -abs(math.sin(t_s * 2.0 * math.pi * 2.2)) * 4.0 * decay
        wide = math.sin(t_s * 2.0 * math.pi * 2.5) * 0.015 * decay
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y = bounce
            eye.scale_y += wide
            eye.stretch += wide * 0.5

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        inv = 1.0 - t
        for eye in [pose.left, pose.right]:
            eye.bounce_offset_y *= inv
            eye.stretch *= inv
