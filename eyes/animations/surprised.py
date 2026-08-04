"""
Surprised animation - high-arousal, startled state.

Feeling: Playful surprise
Signature Motion: Expansion Freeze
Director Note: The surprise should be delightful, not frightening.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, eye_expansion_helper
from ..engine.animation_clips import StateClips, make_basic_enter_clip, make_basic_exit_clip

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SurprisedAnimation(ExpressiveAnimation):
    name = "surprised"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=180.0,
            exit_duration=300.0,
            hold_duration=400.0,
            breathing_strength=0.2,
            bounce_strength=0.60,
            blink_style="fast",
            look_style="centered",
            emotion_goal="Express playful delight and wonder",
            viewer_response="Child experiences delightful surprise without fear",
            attention_style="startled_focus",
            interaction_style="playful_reaction",
            signature_motion="expansion_freeze",
            energy=0.96,
            warmth=0.65,
            curiosity=0.92,
            calmness=0.18,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.95,
            blink_tendency=0.85,
        )

    def configure_clips(self, bundle: PersonalityBundle) -> StateClips:
        return StateClips(
            enter=make_basic_enter_clip(
                duration_ms=180.0,
                stretch_at_start=0.06,
                squash_at_end=0.03,
                overshoot_amount=0.10,
                anticipation_amount=0.03,
            ),
            loop=super().configure_clips(bundle).loop,
            exit=make_basic_exit_clip(duration_ms=300.0),
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 1.04
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy - 3.0
            eye.radius = target_radius
            eye.scale_y = 1.05
            eye.scale_x = 1.04
            eye.stretch = 0.08
            eye.lid_openness = 1.15
            eye.upper_lid_curvature = -0.25
            eye.lower_lid_curvature = 0.18
            eye.iris_scale = 1.05

    def entry_pose(self, t: float, pose: EyePair) -> None:
        super().entry_pose(t, pose)
        # Apply gentle expansion helper on enter
        eye_expansion_helper(pose, amount=0.15, progress=t)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        # Minimal loop movement (held wide open freeze)
        return {
            "bounce": 0.05,
            "pulse": 0.02,
            "scan": 0.0,
            "blink_motion": 1.0,
        }
