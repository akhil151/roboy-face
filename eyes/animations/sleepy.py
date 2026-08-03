"""
Sleepy animation - low-arousal, drowsy state.

Lids heavy, eyes half-closed, slow sinusoidal lid droop,
very slow breathing, slow micro motion.
Communicates tiredness, sleepiness, relaxation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SleepyAnimation(ExpressiveAnimation):
    name = "sleepy"

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile.sleepy()

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.95
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 3.0
            eye.radius = target_radius
            eye.scale_y = 0.82
            eye.lid_openness = 0.45
            eye.upper_lid_curvature = 0.22
            eye.blink_weight = 0.25
            eye.iris_scale = 0.90

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 0.4,
        }
