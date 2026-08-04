"""
Focus animation - intense concentration mode.

Feeling: Locked attention
Signature Motion: Attention Lock
Director Note: The child should feel the robot is looking directly at them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, focus_lock_helper, emotional_settle_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class FocusAnimation(ExpressiveAnimation):
    name = "focus"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=220.0,
            exit_duration=250.0,
            hold_duration=150.0,
            breathing_strength=0.5,
            bounce_strength=0.0,
            blink_style="fast",
            look_style="lock",
            emotion_goal="Establish locked direct eye contact",
            viewer_response="Child feels the robot is looking directly at them",
            attention_style="predictive_tracking",
            interaction_style="concentrated",
            signature_motion="attention_lock",
            energy=0.55,
            warmth=0.32,
            curiosity=0.98,
            calmness=0.78,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.48,
            blink_tendency=0.22,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.94
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 1.0
            eye.radius = target_radius
            eye.scale_y = 0.62
            eye.scale_x = 1.08
            eye.squash = 0.10
            eye.upper_lid_curvature = -0.22
            eye.lower_lid_curvature = 0.08
            eye.lid_openness = 0.55
            eye.iris_scale = 1.02

    def entry_pose(self, t: float, pose: EyePair) -> None:
        super().entry_pose(t, pose)
        # Apply focus lock and spring settle helper on enter
        focus_lock_helper(pose, focus_amount=t)
        emotional_settle_helper(pose, t)

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        for eye in (pose.left, pose.right):
            eye.scale_y = 0.62
            eye.squash = 0.10
            eye.lid_openness = 0.55
            eye.upper_lid_curvature = -0.22
