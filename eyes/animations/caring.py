"""
Caring animation - nurturing, empathetic mode.

Eyes slightly softer, wider vertically, lids gentle, subtle warmth via
lower lid curve and slightly dilated iris. Slow gentle motion.
Communicates empathy, caring, concern, support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class CaringAnimation(ExpressiveAnimation):
    name = "caring"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.caring()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.01
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 1.0
            eye.radius = target_radius
            eye.scale_y = 1.02
            eye.scale_x = 0.99
            eye.upper_lid_curvature = -0.03
            eye.lower_lid_curvature = -0.08
            eye.lid_openness = 0.96
            eye.iris_scale = 0.94

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.05,
            "scan": 0.0,
            "blink_motion": 0.9,
        }
