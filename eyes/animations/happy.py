"""
Happy animation - positive, joyful emotional state.

Eyes slightly squinted (smiling via lids), lifted lower lids (cheek raise),
iris slightly dilated, gentle up-and-down bounce rhythm.
Communicates warmth, happiness, friendliness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class HappyAnimation(ExpressiveAnimation):
    name = "happy"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.excited()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.96
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 1.5
            eye.radius = target_radius
            eye.scale_y = 0.88
            eye.scale_x = 1.06
            eye.squash = 0.08
            eye.upper_lid_curvature = 0.18
            eye.lower_lid_curvature = -0.20
            eye.lid_openness = 0.82
            eye.iris_scale = 0.92

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.4,
            "pulse": 0.1,
            "scan": 0.0,
            "blink_motion": 1.0,
        }
