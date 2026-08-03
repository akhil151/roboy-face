"""
ExpressiveAnimation - integration base class for Phase 2B premium emotional states.

Every future emotional state (calm, happy, surprised, ...) will inherit from
ExpressiveAnimation instead of the raw AnimationState base class.  This class:

  * Wires PersonalityProfile -> all motion primitives via PersonalityBundle
  * Wires StateClips (Enter/Loop/Exit) -> entry_pose / loop_pose / exit_pose
  * Wires per-frame primitive invocations (breathing, bounce, pulse, drift...)
    into the loop phase so states just declare amounts, not procedural code
  * Handles blink-compression motion during the blink_controller blink_weight
  * Provides convenient hooks: configure_personality(), configure_clips(),
    and configure_target_pose() that subclasses override.

CRITICAL DESIGN RULE: This class DOES NOT modify the AnimationState public API.
It merely fills in entry_pose / loop_pose / exit_pose with defaults that
subclasses can override partially or wholesale when needed.  The existing
StateMachine / AnimationMixer architecture continues to drive playback without
any modification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple

from .base import AnimationState
from ..engine.personality import (
    PersonalityProfile,
    PersonalityBundle,
    PersonalityAdaptor,
)
from ..engine.animation_clips import (
    StateClips,
    StateClipPlayer,
    make_basic_enter_clip,
    make_basic_exit_clip,
    make_breathing_loop_clip,
)
from ..engine.motion_primitives import (
    BlinkMotionConfig,
    LookScanPrimitive,
    AttentionShiftPrimitive,
    apply_bounce_pair,
    apply_pulse_pair,
    apply_blink_compression_pair,
)
from ..engine.easing import clamp01

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


# ---------------------------------------------------------------------------
# Per-loop primitive intensity flags / amounts for a state.
# ---------------------------------------------------------------------------


class ExpressiveAnimation(AnimationState, ABC):
    """Abstract base: declarative emotional states via personality + clips.

    Subclassing recipe for Phase 2B (10 emotional states):

        class HappyAnimation(ExpressiveAnimation):
            name = "happy"

            def configure_personality(self) -> PersonalityProfile:
                return PersonalityProfile.excited()  # or build custom 6-axis

            def configure_clips(self, bundle: PersonalityBundle) -> StateClips:
                return StateClips(
                    enter=make_basic_enter_clip(350.0),
                    loop=make_breathing_loop_clip(
                        breathing_cfg=bundle.breathing,
                        drift_cfg=bundle.drift,
                    ),
                    exit=make_basic_exit_clip(280.0),
                )

            def configure_target_pose(self, bundle: PersonalityBundle, pose: EyePair) -> None:
                # Write this state's neutral target pose into pose.
                for eye, cx in [(pose.left, self._left_cx), (pose.right, self._right_cx)]:
                    eye.pos_x = cx
                    eye.pos_y = self._cy + 1.5
                    eye.radius = self._base_radius * 0.96
                    eye.scale_y = 0.88
                    eye.squash = 0.08
                    eye.upper_lid_curvature = 0.18
                    eye.lower_lid_curvature = -0.20
                    eye.lid_openness = 0.82
                    eye.iris_scale = 0.92

            # Optionally override loop_intensities() for bounce, pulse, scan amounts.
    """

    # ------------------------------------------------------------------
    # Subclass hooks (override these, nothing else)
    # ------------------------------------------------------------------

    @abstractmethod
    def configure_personality(self) -> PersonalityProfile:
        """Return this state's 6-axis personality profile."""
        ...

    def configure_clips(self, bundle: PersonalityBundle) -> StateClips:
        """Return Enter/Loop/Exit clips for this state.

        Default implementation: standard enter + breathing/drift loop + standard exit.
        Subclasses should override to add pulse, bounce, scan etc. via PrimitiveInvocation.
        """
        return StateClips(
            enter=make_basic_enter_clip(
                duration_ms=350.0 * bundle.timing.duration_scale,
                overshoot_amount=0.10 * bundle.amplitudes.overshoot,
                anticipation_amount=0.06 * bundle.amplitudes.overshoot,
            ),
            loop=make_breathing_loop_clip(
                breathing_cfg=bundle.breathing,
                drift_cfg=bundle.drift,
            ),
            exit=make_basic_exit_clip(
                duration_ms=280.0 * bundle.timing.duration_scale,
            ),
        )

    @abstractmethod
    def configure_target_pose(self, bundle: PersonalityBundle, pose: "EyePair") -> None:
        """Write this state's NEUTRAL target pose into ``pose``.

        Called once during construction; the target pose is the endpoint
        that entry_pose() animates TOWARD and exit_pose() animates AWAY FROM.
        """
        ...

    def loop_intensities(self, bundle: PersonalityBundle) -> dict[str, float]:
        """Return per-primitive intensity multipliers for the loop phase.

        Keys: bounce, pulse, scan, blink_motion.  All default to 0 or 1.
        """
        return {
            "bounce": 0.0,
            "pulse": 0.0,
            "scan": 0.0,
            "blink_motion": 1.0,
        }

    # ------------------------------------------------------------------
    # Constructor / lifecycle
    # ------------------------------------------------------------------

    def __init__(self, config: "EngineConfig") -> None:
        super().__init__(config)

        # 1. Build personality -> primitive configs.
        self._profile: PersonalityProfile = self.configure_personality().clamped()
        self._bundle: PersonalityBundle = PersonalityAdaptor.adapt(self._profile)

        # 2. Override entry/exit durations to match personality timing.
        dur = self._bundle.timing.duration_scale
        self._entry_duration_ms = 200.0 * dur
        self._exit_duration_ms = 200.0 * dur
        if self._bundle.timing.transition_override_ms is not None:
            # Entry = ~75% of the mixer-level transition window.
            self._entry_duration_ms = self._bundle.timing.transition_override_ms * 0.75
            self._exit_duration_ms = self._bundle.timing.transition_override_ms * 0.7

        # 3. Allocate target pose buffer and populate it via subclass hook.
        from ..engine.eye_pair import EyePair
        self._target_pose: EyePair = EyePair()
        self._target_pose.configure(config)
        self.configure_target_pose(self._bundle, self._target_pose)

        # 4. Build Enter/Loop/Exit clips + player.
        self._clips: StateClips = self.configure_clips(self._bundle)
        self._clip_player: StateClipPlayer = StateClipPlayer(self._clips)

        # 5. Optional per-loop primitive intensities.
        self._intensities: dict[str, float] = self.loop_intensities(self._bundle)

        # 6. Stateful primitives for per-loop use (scan, attention shift).
        self._look_scan: LookScanPrimitive = LookScanPrimitive(self._bundle.scan)
        self._attention_shift: AttentionShiftPrimitive = AttentionShiftPrimitive()

        # 7. Cached blink-motion config.
        self._blink_cfg: BlinkMotionConfig = self._bundle.blink_motion

    # ------------------------------------------------------------------
    # Read-only accessors for Phase 2B state authors
    # ------------------------------------------------------------------

    @property
    def personality_profile(self) -> PersonalityProfile:
        return self._profile

    @property
    def personality_bundle(self) -> PersonalityBundle:
        return self._bundle

    @property
    def target_pose(self) -> "EyePair":
        return self._target_pose

    @property
    def clips(self) -> StateClips:
        return self._clips

    # ------------------------------------------------------------------
    # AnimationState lifecycle hooks - forward to clip player.
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        super().on_enter()
        self._clip_player.on_enter()
        self._look_scan.reset()

    def on_exit(self) -> None:
        super().on_exit()
        self._clip_player.on_exit()

    # ------------------------------------------------------------------
    # Pose computation - blends target_pose with personality/clips.
    # ------------------------------------------------------------------

    def entry_pose(self, t: float, pose: "EyePair") -> None:
        """Blend from incoming pose toward target_pose, overlaid with Enter clip + overshoot."""
        t = clamp01(t)
        from ..engine.emotion_blending import CinematicBlender
        # Use cinematic per-property blend from the incoming pose -> target pose.
        # First: copy target_pose into a scratch via lerp with cinematic delta.
        # For simplicity and to preserve per-frame zero-allocation semantics,
        # we lerp pose (from) -> target_pose with cinematic curves applied on top.
        # Apply cinematic blend for every non-offset property into pose.
        self._cinematic_lerp(pose, self._target_pose, t)
        # Then apply the Enter clip additively on top.
        self._clip_player.play_entry(16.0, t, pose)

    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        """Run the Loop clip, then add per-loop primitive contributions."""
        # Lerp pose toward target_pose at t=1 (since loop runs after entry).
        # But pose already carries the loop state; use clips to add baseline motion.
        self._clip_player.play_loop(dt_ms, elapsed_ms, pose)

        amps = self._bundle.amplitudes
        # Bounce
        bounce_w = self._intensities.get("bounce", 0.0)
        if bounce_w > 0.0:
            apply_bounce_pair(pose, dt_ms, elapsed_ms, self._bundle.bounce, bounce_w * amps.bounce)

        # Pulse
        pulse_w = self._intensities.get("pulse", 0.0)
        if pulse_w > 0.0:
            apply_pulse_pair(pose, dt_ms, elapsed_ms, self._bundle.pulse, pulse_w * amps.pulse)

        # Look scan
        scan_w = self._intensities.get("scan", 0.0)
        if scan_w > 0.0:
            self._look_scan.apply_to_pair(pose, dt_ms / 1000.0, elapsed_ms / 1000.0, scan_w * amps.scan)

        # Blink motion is applied externally via apply_blink_motion() each frame
        # by the engine-level blender, so we don't duplicate it here.

    def exit_pose(self, t: float, pose: "EyePair") -> None:
        """Fade out target pose with Exit clip overlay."""
        t = clamp01(t)
        # Exit clip fades the pose back toward neutral.
        self._clip_player.play_exit(t, pose)

    # ------------------------------------------------------------------
    # External: blink-motion integration (called by the mixer-level hot path).
    # ------------------------------------------------------------------

    def apply_blink_motion(self, pose: "EyePair", blink_weight: float) -> None:
        """Apply peri-blink compression/expansion for a given blink_weight in [0,1].

        Called each frame by the engine hot path after BlinkController has
        produced its blink_weight output.  Intensity scales with the state's
        blink_motion amplitude and personality.
        """
        w = self._intensities.get("blink_motion", 1.0)
        if w <= 0.0 or blink_weight <= 0.0:
            return
        apply_blink_compression_pair(
            pose,
            blink_weight_left=blink_weight,
            blink_weight_right=blink_weight,
            cfg=self._blink_cfg,
            amount=w * self._bundle.amplitudes.blink_motion,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cinematic_lerp(pose: "EyePair", target_pose: "EyePair", t: float) -> None:
        """Cinematic per-property lerp from pose -> target_pose.

        Uses motion_curves cinematic_delta for every property group to add
        anticipation + overshoot into the blend.  Mutates pose in place."""
        from ..engine.motion_curves import cinematic_delta, PROPERTY_CURVES
        from ..engine.easing import ease_in_out_cubic, clamp01

        t = clamp01(t)
        for side in ("left", "right"):
            src = getattr(pose, side)
            tgt = getattr(target_pose, side)
            for prop_name, curve in PROPERTY_CURVES.items():
                fv = getattr(src, prop_name)
                tv = getattr(tgt, prop_name)
                if fv == tv:
                    continue
                nv = cinematic_delta(curve, fv, tv, t)
                setattr(src, prop_name, nv)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ExpressiveAnimation",
]
