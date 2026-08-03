"""
Calm animation - the default relaxed state.

Eyes are centered, eyelids relaxed, gentle breathing baseline.
Serves as the identity pose that other states blend to/from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class CalmAnimation(ExpressiveAnimation):
    name = "calm"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.relaxed()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy
            eye.radius = self._base_radius
            eye.scale_x = 1.0
            eye.scale_y = 1.0
            eye.upper_lid_curvature = 0.0
            eye.lower_lid_curvature = 0.0
            eye.iris_scale = 1.0
            eye.opacity = 1.0
