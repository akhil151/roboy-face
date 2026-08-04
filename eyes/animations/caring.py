"""
Caring animation - nurturing, empathetic mode.

Feeling: Warm, Comforting
Signature Motion: Long Slow Blink
Director Note: The robot should feel emotionally supportive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, soft_blink_helper, emotional_settle_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class CaringAnimation(ExpressiveAnimation):
    name = "caring"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=450.0,
            exit_duration=350.0,
            hold_duration=250.0,
            breathing_strength=1.3,
            bounce_strength=0.0,
            blink_style="soft",
            look_style="centered",
            emotion_goal="Provide warm emotional support",
            viewer_response="Child feels comforted and emotionally supported",
            attention_style="gentle_nurturing",
            interaction_style="empathetic",
            signature_motion="long_slow_blink",
            energy=0.35,
            warmth=0.95,
            curiosity=0.68,
            calmness=0.85,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.45,
            blink_tendency=0.65,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.01
        # Eyes move slightly closer together
        pose.left.pos_x = self._left_cx + 3.0
        pose.right.pos_x = self._right_cx - 3.0

        for eye in (pose.left, pose.right):
            eye.pos_y = self._cy + 1.2
            eye.radius = target_radius
            eye.scale_y = 1.02
            eye.scale_x = 0.99
            eye.upper_lid_curvature = -0.05
            eye.lower_lid_curvature = -0.10
            eye.lid_openness = 0.95
            eye.iris_scale = 0.93

    def entry_pose(self, t: float, pose: EyePair) -> None:
        super().entry_pose(t, pose)
        # Soft emotional settle helper during entry
        emotional_settle_helper(pose, t)

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Long slow blink signature motion
        cycle_t = (elapsed_ms % 7000.0) / 7000.0
        if 0.50 <= cycle_t <= 0.65:
            soft_blink_helper(pose, (cycle_t - 0.50) / 0.15)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.05,
            "scan": 0.0,
            "blink_motion": 0.9,
        }
