"""
Speaking animation - active verbal output mode.

Eyes open, rhythmic jaw/cheek simulation via vertical micro-bounce,
slight horizontal stretch mimicking speech articulation.
Communicates that the robot is actively talking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SpeakingAnimation(ExpressiveAnimation):
    name = "speaking"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.speaking()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.02
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 2.0
            eye.radius = target_radius
            eye.scale_y = 1.03
            eye.lid_openness = 1.05
            eye.upper_lid_curvature = -0.04

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.5,
            "pulse": 0.4,
            "scan": 0.0,
            "blink_motion": 1.0,
        }
