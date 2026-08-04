"""
Sad animation - low-energy, downcast emotional state.

Feeling: Gentle sadness (NOT depression)
Signature Motion: Posture Droop
Director Note: The child should feel empathy, never discomfort.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, soft_blink_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SadAnimation(ExpressiveAnimation):
    name = "sad"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=400.0,
            exit_duration=350.0,
            hold_duration=200.0,
            breathing_strength=0.7,
            bounce_strength=0.0,
            blink_style="soft",
            look_style="centered",
            emotion_goal="Express gentle vulnerability",
            viewer_response="Child feels empathy without discomfort",
            attention_style="downcast_introspective",
            interaction_style="subdued",
            signature_motion="posture_droop",
            energy=0.18,
            warmth=0.55,
            curiosity=0.25,
            calmness=0.80,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.28,
            blink_tendency=0.60,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.96
        # Slight inner tilt: left eye moves right (+2px), right eye moves left (-2px)
        pose.left.pos_x = self._left_cx + 2.0
        pose.right.pos_x = self._right_cx - 2.0

        for eye in (pose.left, pose.right):
            eye.pos_y = self._cy + 5.5
            eye.radius = target_radius
            eye.scale_y = 0.96
            eye.scale_x = 1.00
            eye.lid_openness = 0.72
            eye.upper_lid_curvature = 0.18
            eye.lower_lid_curvature = 0.12
            eye.iris_scale = 0.98
            eye.look_offset_y = 5.0

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Slow droopy blink cycle
        cycle_t = (elapsed_ms % 6500.0) / 6500.0
        if 0.55 <= cycle_t <= 0.70:
            soft_blink_helper(pose, (cycle_t - 0.55) / 0.15)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 0.5,
        }
