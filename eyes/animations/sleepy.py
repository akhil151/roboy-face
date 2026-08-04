"""
Sleepy animation - low-arousal, drowsy state.

Feeling: Relaxed, Sleepy
Signature Motion: Heavy Blink
Director Note: Feels sleepy rather than broken.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .expressive import ExpressiveAnimation
from ..engine.personality import PersonalityProfile, PersonalityBundle
from ..engine.choreography import AnimationDirection, soft_blink_helper

if TYPE_CHECKING:
    from ..engine.eye_pair import EyePair


class SleepyAnimation(ExpressiveAnimation):
    name = "sleepy"

    def __init__(self, config: object) -> None:
        self.direction = AnimationDirection(
            enter_duration=500.0,
            exit_duration=400.0,
            hold_duration=300.0,
            breathing_strength=1.5,
            bounce_strength=0.0,
            blink_style="soft",
            look_style="centered",
            emotion_goal="Drowsy peaceful relaxation",
            viewer_response="Child feels calm and restful",
            attention_style="drowsy_drift",
            interaction_style="resting",
            signature_motion="heavy_blink",
            energy=0.08,
            warmth=0.45,
            curiosity=0.15,
            calmness=0.95,
        )
        super().__init__(config)  # type: ignore[arg-type]

    def configure_personality(self) -> PersonalityProfile:
        return PersonalityProfile(
            energy=self.direction.energy,
            warmth=self.direction.warmth,
            attention=self.direction.curiosity,
            calmness=self.direction.calmness,
            amplitude=0.18,
            blink_tendency=0.80,
        )

    def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
        target_radius = self._base_radius * 0.94
        for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
            eye.pos_x = cx
            eye.pos_y = self._cy + 3.5
            eye.radius = target_radius
            eye.scale_y = 0.80
            eye.lid_openness = 0.35
            eye.upper_lid_curvature = 0.28
            eye.blink_weight = 0.20
            eye.iris_scale = 0.88

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: EyePair) -> None:
        super().loop_pose(dt_ms, elapsed_ms, pose)
        # Slow sinusoidal lid droop and heavy blink signature motion
        droop_sine = 0.06 * math.sin(elapsed_ms * 0.001)
        for eye in (pose.left, pose.right):
            eye.lid_openness = max(0.15, 0.35 + droop_sine)

        cycle_t = (elapsed_ms % 5000.0) / 5000.0
        if 0.60 <= cycle_t <= 0.80:
            soft_blink_helper(pose, (cycle_t - 0.60) / 0.20)

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 0.4,
        }
