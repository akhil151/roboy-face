"""
Focus animation - intense concentration mode.

Eyes narrowed, lids tensed, iris slightly constricted,
very still (reduced micro motion), sharp tight geometry.
Communicates reading, analysis, sharp focus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class FocusAnimation(ExpressiveAnimation):
    name = "focus"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.focused()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.95
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 1.5
            eye.radius = target_radius
            eye.scale_y = 0.85
            eye.scale_x = 1.03
            eye.squash = 0.07
            eye.upper_lid_curvature = 0.05
            eye.lower_lid_curvature = 0.09
            eye.lid_openness = 0.68
            eye.iris_scale = 1.06

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.3,
            "blink_motion": 0.6,
        }
