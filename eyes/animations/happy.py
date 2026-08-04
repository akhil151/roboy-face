"""
Happy animation - positive, joyful emotional state.

Feeling: Joy
Signature Motion: Double Blink
Director Note: The child should instinctively smile back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, bounce_accent_helper, double_blink_helper
from ..engine.animation_clips import StateClips, make_basic_enter_clip, make_basic_exit_clip, make_breathing_loop_clip

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class HappyAnimation(ExpressiveAnimation):
    name = "happy"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=350.0,
            exit_duration=300.0,
            hold_duration=100.0,
            breathing_strength=1.1,
            bounce_strength=0.50,
            blink_style="double",
            look_style="centered",
            emotion_goal="Express joyful warmth and friendship",
            viewer_response="Child instinctively smiles back",
            attention_style="playful_sparkle",
            interaction_style="welcoming",
            signature_motion="double_blink",
            energy=0.88,
            warmth=0.90,
            curiosity=0.75,
            calmness=0.48,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.85,
            blink_tendency=0.75,
        )

    def configure_clips(self, bundle: PersonalityBundle) -> StateClips:
        return StateClips(
            enter=make_basic_enter_clip(
                duration_ms=350.0,
                stretch_at_start=0.05,
                squash_at_end=0.04,
                overshoot_amount=0.10,
                anticipation_amount=0.05,
            ),
            loop=make_breathing_loop_clip(
                breathing_cfg=bundle.breathing,
                drift_cfg=bundle.drift,
            ),
            exit=make_basic_exit_clip(duration_ms=300.0),
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.98
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 1.5
            eye.radius = target_radius
            eye.scale_y = 0.88
            eye.scale_x = 1.05
            eye.squash = 0.02
            eye.upper_lid_curvature = 0.20
            eye.lower_lid_curvature = -0.38
            eye.lid_openness = 0.76
            eye.iris_scale = 0.94

    def entry_pose(self, t: float, pose: EyePair) -> None:
        super().entry_pose(t, pose)
        # Apply gentle bounce impulse accent during enter
        bounce_accent_helper(pose, 8.0, t * 350.0, amount=0.35)

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Periodic double blink accent signature motion
        cycle_t = (elapsed_ms % 6000.0) / 6000.0
        if 0.40 <= cycle_t <= 0.50:
            double_blink_helper(pose, (cycle_t - 0.40) / 0.10)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.20,
            "pulse": 0.15,
            "scan": 0.0,
            "blink_motion": 1.0,
        }
