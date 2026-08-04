"""
Calm animation - the default relaxed state.

Feeling: Peaceful, Safe, Comfortable
Signature Motion: Gentle Breathing
Director Note: The child should feel relaxed around the robot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class CalmAnimation(ExpressiveAnimation):
    name = "calm"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=350.0,
            exit_duration=280.0,
            hold_duration=100.0,
            breathing_strength=1.0,
            bounce_strength=0.0,
            blink_style="soft",
            look_style="centered",
            emotion_goal="Peaceful safety and comfort",
            viewer_response="Child feels relaxed and safe around the robot",
            attention_style="imperceptible_drift",
            interaction_style="passive_receptive",
            signature_motion="gentle_breathing",
            energy=0.22,
            warmth=0.65,
            calmness=0.90,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=0.18,
            calmness=self.direction.calmness,
            amplitude=0.14,
            blink_tendency=0.50,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy
            eye.radius = self._base_radius
            eye.scale_x = 1.0
            eye.scale_y = 1.0
            eye.upper_lid_curvature = 0.0
            eye.lower_lid_curvature = 0.0
            eye.lid_openness = 1.0
            eye.iris_scale = 1.0
            eye.opacity = 1.0

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.02,
            "blink_motion": 1.0,
        }
