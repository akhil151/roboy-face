"""
Listening animation - receptive attention mode.

Feeling: Interested, Paying attention
Signature Motion: Inward Lean
Director Note: The robot should look like it is carefully listening.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, attention_gain_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class ListeningAnimation(ExpressiveAnimation):
    name = "listening"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=280.0,
            exit_duration=250.0,
            hold_duration=150.0,
            breathing_strength=0.8,
            bounce_strength=0.1,
            blink_style="attentive",
            look_style="shift",
            emotion_goal="Interested attention and engagement",
            viewer_response="Child feels heard and carefully listened to",
            attention_style="focused_tracking",
            interaction_style="active_listener",
            signature_motion="inward_lean",
            energy=0.48,
            warmth=0.60,
            curiosity=0.88,
            calmness=0.75,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.24,
            blink_tendency=0.32,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.01
        # Inward lean: left eye moves right (+2px), right eye moves left (-2px)
        pose.left.pos_x = self._left_cx + 2.0
        pose.right.pos_x = self._right_cx - 2.0

        for eye in (pose.left, pose.right):
            eye.pos_y = self._cy - 2.5
            eye.radius = target_radius
            eye.scale_y = 1.01
            eye.scale_x = 0.99
            eye.lid_openness = 1.045
            eye.upper_lid_curvature = -0.08
            eye.lower_lid_curvature = 0.04
            eye.iris_scale = 0.97

    def entry_pose(self, t: float, pose: EyePair) -> None:
        super().entry_pose(t, pose)
        # Apply tiny attention gain helper on enter
        attention_gain_helper(pose, t, intensity=0.6, target_dx=3.0, target_dy=-2.0)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.05,
            "pulse": 0.0,
            "scan": 0.10,
            "blink_motion": 1.0,
        }
