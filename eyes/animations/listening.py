"""
Listening animation - receptive attention mode.

Eyes slightly wider, iris tracking active, upper lids lifted slightly.
Communicates that the robot is actively listening to the user.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class ListeningAnimation(ExpressiveAnimation):
    name = "listening"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.neutral()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.03
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 3.0
            eye.radius = target_radius
            eye.scale_y = 1.04
            eye.scale_x = 0.98
            eye.lid_openness = 1.05
            eye.upper_lid_curvature = -0.12
            eye.iris_scale = 0.95

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.1,
            "pulse": 0.0,
            "scan": 0.4,
            "blink_motion": 1.0,
        }
