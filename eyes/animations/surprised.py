"""
Surprised animation - high-arousal, startled state.

Eyes wide open, lids fully retracted, iris dilated fully,
slight forward bounce and stretch, lids pulled fully back.
Communicates surprise, shock, realization, excitement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SurprisedAnimation(ExpressiveAnimation):
    name = "surprised"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.surprised()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.10
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 5.0
            eye.radius = target_radius
            eye.scale_y = 1.12
            eye.scale_x = 1.04
            eye.stretch = 0.08
            eye.lid_openness = 1.10
            eye.upper_lid_curvature = -0.18
            eye.lower_lid_curvature = 0.12
            eye.iris_scale = 1.08

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.6,
            "pulse": 0.3,
            "scan": 0.0,
            "blink_motion": 1.2,
        }
