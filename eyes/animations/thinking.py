"""
Thinking animation - active cognitive processing mode.

Feeling: Processing, Curious
Signature Motion: Tiny Twitch
Director Note: The robot should appear to be searching for an answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, natural_pause_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class ThinkingAnimation(ExpressiveAnimation):
    name = "thinking"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=320.0,
            exit_duration=300.0,
            hold_duration=200.0,
            breathing_strength=0.6,
            bounce_strength=0.0,
            blink_style="rare",
            look_style="scan",
            emotion_goal="Cognitive processing and inquiry",
            viewer_response="Child senses the robot is searching for an answer",
            attention_style="exploratory_scan",
            interaction_style="deliberating",
            signature_motion="tiny_twitch",
            energy=0.38,
            warmth=0.42,
            curiosity=0.85,
            calmness=0.70,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.42,
            blink_tendency=0.25,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.97
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 1.8
            eye.radius = target_radius
            eye.scale_y = 0.94
            eye.scale_x = 1.02
            eye.squash = 0.05
            eye.upper_lid_curvature = 0.10
            eye.lower_lid_curvature = 0.06
            eye.lid_openness = 0.88
            eye.iris_scale = 1.02

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Apply natural pause and micro-twitch helper during loop
        progress = (elapsed_ms % 4000.0) / 4000.0
        natural_pause_helper(pose, progress, intensity=0.7)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.65,
            "blink_motion": 0.7,
        }
