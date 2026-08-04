"""
Speaking animation - active verbal output mode.

Feeling: Communicating
Signature Motion: Speech Pulse
Director Note: Speech should feel alive without distracting the child.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, breathing_pulse_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SpeakingAnimation(ExpressiveAnimation):
    name = "speaking"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=250.0,
            exit_duration=250.0,
            hold_duration=50.0,
            breathing_strength=1.2,
            bounce_strength=0.45,
            blink_style="normal",
            look_style="centered",
            emotion_goal="Active verbal communication",
            viewer_response="Child engages with spoken guidance without distraction",
            attention_style="expressive_articulation",
            interaction_style="communicating",
            signature_motion="speech_pulse",
            energy=0.78,
            warmth=0.70,
            curiosity=0.65,
            calmness=0.55,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.22,
            blink_tendency=0.50,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.00
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 1.5
            eye.radius = target_radius
            eye.scale_y = 1.00
            eye.scale_x = 1.00
            eye.lid_openness = 1.028
            eye.upper_lid_curvature = -0.04
            eye.lower_lid_curvature = 0.02
            eye.iris_scale = 1.0

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Apply very subtle speech-synchronized breathing pulse (eyes barely react)
        breathing_pulse_helper(pose, dt_ms, elapsed_ms, amount=0.18)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.06,
            "pulse": 0.08,
            "scan": 0.01,
            "blink_motion": 1.0,
        }
