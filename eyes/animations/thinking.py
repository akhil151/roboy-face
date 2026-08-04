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
from ..engine.choreography import AnimationDirection, natural_pause_helper, soft_blink_helper

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
            amplitude=0.20,
            blink_tendency=0.25,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.96
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy
            eye.radius = target_radius
            eye.scale_y = 0.98
            eye.scale_x = 1.00
            eye.rotation = 0.0
            eye.lid_openness = 0.82
            eye.upper_lid_curvature = 0.08
            eye.look_offset_x = 0.0
            eye.look_offset_y = 0.0

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        import math
        super().loop_pose(dt_ms, elapsed_ms, pose)

        # 4.5-second intelligent thinking sequence: slow look scan -> pause -> tiny twitch -> pause -> blink -> return
        cycle_ms = 4500.0
        t_phase = (elapsed_ms % cycle_ms) / cycle_ms

        if t_phase < 0.35:
            # Phase 1: Slow look scan up & right with transient eyelid asymmetry
            scan_t = math.sin((t_phase / 0.35) * math.pi * 0.5)
            look_x = 12.0 * scan_t
            look_y = -10.0 * scan_t
            for eye in (pose.left, pose.right):
                eye.look_offset_x = look_x
                eye.look_offset_y = look_y
            # Transient asymmetry: left eye narrows slightly during inquiry scan
            pose.left.lid_openness = 0.82 - 0.12 * scan_t
            pose.left.upper_lid_curvature = 0.10 + 0.08 * scan_t
            pose.left.rotation = 0.05 * scan_t
        elif t_phase < 0.45:
            # Phase 2: Pause at top-right scan point with holding transient posture
            for eye in (pose.left, pose.right):
                eye.look_offset_x = 12.0
                eye.look_offset_y = -10.0
            pose.left.lid_openness = 0.70
            pose.left.upper_lid_curvature = 0.18
            pose.left.rotation = 0.05
        elif t_phase < 0.55:
            # Phase 3: Tiny intelligent twitch
            twitch_t = (t_phase - 0.45) / 0.10
            twitch_offset = math.sin(twitch_t * math.pi * 2.0) * 1.5
            pose.left.micro_offset_x += twitch_offset
            pose.left.micro_offset_y -= twitch_offset * 0.5
            pose.right.micro_offset_x += twitch_offset
            pose.right.micro_offset_y -= twitch_offset * 0.5
            for eye in (pose.left, pose.right):
                eye.look_offset_x = 12.0
                eye.look_offset_y = -10.0
            pose.left.lid_openness = 0.70
            pose.left.upper_lid_curvature = 0.18
            pose.left.rotation = 0.05
        elif t_phase < 0.68:
            # Phase 4: Contemplative pause
            for eye in (pose.left, pose.right):
                eye.look_offset_x = 12.0
                eye.look_offset_y = -10.0
            pose.left.lid_openness = 0.70
            pose.left.upper_lid_curvature = 0.18
        elif t_phase < 0.80:
            # Phase 5: Soft intelligent blink, resetting transient asymmetry
            blink_t = (t_phase - 0.68) / 0.12
            soft_blink_helper(pose, blink_t)
            ease_ret = 1.0 - blink_t
            for eye in (pose.left, pose.right):
                eye.look_offset_x = 12.0 * ease_ret
                eye.look_offset_y = -10.0 * ease_ret
            pose.left.lid_openness = 0.70 + 0.12 * blink_t
            pose.left.rotation = 0.05 * ease_ret
        else:
            # Phase 6: Smooth return to center gaze and symmetrical posture
            return_t = (t_phase - 0.80) / 0.20
            ease_ret = 1.0 - math.sin(return_t * math.pi * 0.5)
            for eye in (pose.left, pose.right):
                eye.look_offset_x = 4.0 * ease_ret
                eye.look_offset_y = -3.0 * ease_ret
            pose.left.lid_openness = 0.82

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 0.7,
        }
