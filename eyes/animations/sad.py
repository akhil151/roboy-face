"""
Sad animation - low-energy, downcast emotional state.

Eyes lowered slightly, upper lids drooping, lower lids flat,
inner corners slightly raised (tear-like shape), slow heavy breathing.
Communicates sadness, disappointment, low mood.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SadAnimation(ExpressiveAnimation):
    name = "sad"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.sad()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.97
        for eye, cx, tilt in [(pose.left, self._left_cx, 1.0), (pose.right, self._right_cx, -1.0)]:
            eye.pos_x = cx + tilt * 2.0
            eye.pos_y = self._cy + 5.0
            eye.radius = target_radius
            eye.scale_y = 0.91
            eye.lid_openness = 0.75
            eye.upper_lid_curvature = 0.14
            eye.lower_lid_curvature = 0.10
            eye.iris_scale = 0.96
            eye.look_offset_y = 6.0

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 0.5,
        }
