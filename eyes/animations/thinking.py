"""
Thinking animation - active cognitive processing mode.

Eyes slightly squinted, slow lateral micro-saccades, gentle rotation.
Communicates reasoning, deliberation, or processing of complex input.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class ThinkingAnimation(ExpressiveAnimation):
    name = "thinking"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.thinking()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.97
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 2.0
            eye.radius = target_radius
            eye.scale_y = 0.94
            eye.scale_x = 1.02
            eye.squash = 0.04
            eye.upper_lid_curvature = 0.08
            eye.lower_lid_curvature = 0.06
            eye.iris_scale = 1.03

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.6,
            "blink_motion": 0.8,
        }
