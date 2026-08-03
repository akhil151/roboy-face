"""
Animation clip system - cinematic Enter / Loop / Exit for every emotional state.

Instead of a single continuous update, each state exposes three clips:
  * EnterClip  - runs ONCE on state entry, with anticipation + settle
  * LoopClip   - runs EVERY FRAME while the state is active
  * ExitClip   - runs ONCE on state exit, with overshoot + decay

Each clip is a reusable, declarative description of motion using the motion
primitives library.  States in Phase 2B will simply compose these clips
rather than hardcode procedural motion directly into entry_pose/loop_pose/
exit_pose callbacks.

Design:
  * Clip instances are DATA - they hold configuration, not mutable state.
    The ClipPlayer owns the per-frame state (elapsed timers, internal
    primitive instances).
  * Every clip writes additively into a target EyePair, so multiple clips
    can be cross-faded during transitions.
  * Clip durations are explicit; Enter/Exit have finite duration, Loop is
    infinite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .eye_pair import EyePair
from .easing import EasingFunction, ease_in_out_cubic, ease_out_cubic, ease_in_cubic, clamp01, lerp
from .motion_primitives import (
    BreathingConfig,
    BounceConfig,
    DriftConfig,
    PulseConfig,
    SquashConfig,
    StretchConfig,
    OvershootConfig,
    apply_breathing_pair,
    apply_bounce_pair,
    apply_drift_pair,
    apply_pulse_pair,
    apply_squash_pair,
    apply_stretch_pair,
    overshoot_envelope,
)


# ---------------------------------------------------------------------------
# Clip descriptor types
# ---------------------------------------------------------------------------


@dataclass
class PrimitiveInvocation:
    """A single call to a motion primitive, configured with amount + cfg."""
    # Callable that writes additively into an EyePair.
    fn: Callable[[EyePair, float, float, object, float], None]
    config: object = None
    amount: float = 1.0
    # Optional per-invocation amplitude envelope [0..1] as a function of clip-local t.
    envelope_fn: Optional[Callable[[float], float]] = None


@dataclass
class AnimationClip:
    """Declarative description of a reusable animation segment.

    The clip itself is PURE DATA.  Playback is handled by ClipPlayer,
    which instantiates any stateful primitives and advances per-frame
    timing.
    """
    # Name for debugging / audit trails.
    name: str = "clip"
    # Length in milliseconds; for LoopClip use 0 (infinite).
    duration_ms: float = 0.0
    # Global easing applied to the overall blend weight of this clip.
    weight_ease: EasingFunction = ease_in_out_cubic
    # Ordered list of primitive invocations.  Each is applied additively.
    primitives: List[PrimitiveInvocation] = field(default_factory=list)
    # Optional static target-pose setter, called at t=0 with blend weight.
    # Signature: (pose: EyePair, t: float, eased_t: float) -> None, writes IN-PLACE into pose.
    pose_fn: Optional[Callable[[EyePair, float, float], None]] = None
    # Optional squash/stretch envelope at the entry/exit edges.
    edge_squash: Optional[SquashConfig] = None
    edge_stretch: Optional[StretchConfig] = None
    # For clips with overshoot-style envelopes (Enter clips).
    overshoot_cfg: Optional[OvershootConfig] = None


# ---------------------------------------------------------------------------
# Clip player - owns runtime timing + stateful primitive instances.
# ---------------------------------------------------------------------------


class ClipPlayer:
    """Plays an AnimationClip into a target EyePair.

    Handles timing, overall weight-curve application, and edge effects
    (squash/stretch at clip boundaries).  One player per clip-lifecycle
    (each Enter/Exit transition gets a fresh player; Loop has one that
    runs continuously).
    """

    def __init__(self, clip: AnimationClip) -> None:
        self._clip = clip
        self._elapsed_ms: float = 0.0
        self._completed: bool = False

    # ------------------------------------------------------------------
    @property
    def name(self) -> str:
        return self._clip.name

    @property
    def duration_ms(self) -> float:
        return self._clip.duration_ms

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed_ms

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def progress(self) -> float:
        """0..1 linear progress through the clip; 1.0 if infinite loop."""
        if self._clip.duration_ms <= 0:
            return 1.0
        return clamp01(self._elapsed_ms / self._clip.duration_ms)

    def reset(self) -> None:
        self._elapsed_ms = 0.0
        self._completed = False

    # ------------------------------------------------------------------
    def apply(self, dt_ms: float, pose: EyePair, global_weight: float = 1.0) -> float:
        """Advance the clip by ``dt_ms`` and write additively into ``pose``.

        Returns the effective global-weight used this frame so callers can
        cross-fade between players.
        """
        if self._completed:
            return 0.0
        self._elapsed_ms += dt_ms
        t = self.progress
        infinite = self._clip.duration_ms <= 0
        if not infinite and self._elapsed_ms >= self._clip.duration_ms:
            self._completed = True
            t = 1.0

        eased_t = self._clip.weight_ease(t)
        # For overshoot-style entry clips, replace eased_t with the full
        # anticipation/overshoot/settle envelope.
        if self._clip.overshoot_cfg is not None:
            env_t = overshoot_envelope(t, self._clip.overshoot_cfg)
            # env_t may be slightly negative (anticipation) or > 1 (overshoot).
            global_weight *= 1.0
            # We capture this override later via overshoot_t.
            overshoot_t = env_t
        else:
            overshoot_t = eased_t

        weight = eased_t * global_weight
        if weight <= 0.0 and infinite:
            return 0.0

        # 1. Static pose function (for parameter targets).
        if self._clip.pose_fn is not None:
            self._clip.pose_fn(pose, t, overshoot_t if self._clip.overshoot_cfg else eased_t)

        # 2. Edge effects: optional squash at start, stretch at end.
        if self._clip.edge_stretch is not None and t < 0.45:
            local_t = t / 0.45
            apply_stretch_pair(pose, local_t, self._clip.edge_stretch, weight)
        if self._clip.edge_squash is not None and t > 0.55:
            local_t = 1.0 - (t - 0.55) / 0.45
            apply_squash_pair(pose, clamp01(local_t), self._clip.edge_squash, weight)

        # 3. Primitive invocations.
        for inv in self._clip.primitives:
            inv_amount = inv.amount * weight
            if inv.envelope_fn is not None:
                inv_amount *= clamp01(inv.envelope_fn(t))
            if inv_amount <= 0.0:
                continue
            inv.fn(pose, dt_ms, self._elapsed_ms, inv.config, inv_amount)

        return weight


# ---------------------------------------------------------------------------
# Composed state-level clip container
# ---------------------------------------------------------------------------


@dataclass
class StateClips:
    """The three clips that make up a full animation state.

    Phase 2B will construct one StateClips per emotional state, then the
    ExpressiveAnimation base class (below) wires them into the existing
    AnimationState entry_pose / loop_pose / exit_pose callbacks so that
    the existing AnimationMixer / StateMachine architecture drives the
    playback seamlessly.
    """
    enter: AnimationClip = field(default_factory=lambda: AnimationClip(name="enter", duration_ms=350.0))
    loop: AnimationClip = field(default_factory=lambda: AnimationClip(name="loop", duration_ms=0.0))
    exit: AnimationClip = field(default_factory=lambda: AnimationClip(name="exit", duration_ms=300.0))


class StateClipPlayer:
    """Orchestrates the three clips for a single AnimationState.

    Responsibilities:
      * Instantiates ClipPlayer instances on demand for Enter / Exit / Loop.
      * Handles the entry -> loop handoff (crossfade as Enter finishes).
      * Plays Loop continuously while the state is active.
      * Plays Exit on state leave (triggered by exit_pose callback).
    """

    def __init__(self, clips: StateClips) -> None:
        self._clips = clips
        self._enter_player: Optional[ClipPlayer] = None
        self._loop_player: Optional[ClipPlayer] = None
        self._exit_player: Optional[ClipPlayer] = None

    # ------------------------------------------------------------------
    def on_enter(self) -> None:
        """Called by the state's on_enter() hook."""
        self._enter_player = ClipPlayer(self._clips.enter)
        self._loop_player = ClipPlayer(self._clips.loop)
        self._exit_player = None  # Fresh exit on the way out.

    def on_exit(self) -> None:
        """Called by the state's on_exit() hook."""
        self._exit_player = ClipPlayer(self._clips.exit)
        # Enter / loop are still alive briefly until exit takes over.

    # ------------------------------------------------------------------
    def play_entry(
        self,
        dt_ms: float,
        entry_t: float,
        pose: EyePair,
    ) -> None:
        """Called each frame during entry_pose() by the animation state.

        ``entry_t`` in [0,1] is the overall transition blend-progress from
        the AnimationMixer; it controls the global weight of the Enter
        clip and also controls the internal Enter-clip timer.
        """
        if self._enter_player is None:
            self._enter_player = ClipPlayer(self._clips.enter)
        # Map entry_t [0..1] to the Enter clip's elapsed_ms time so we
        # stay in sync with the mixer-level blend even under variable dt.
        target_elapsed = entry_t * self._clips.enter.duration_ms
        synthetic_dt = target_elapsed - self._enter_player.elapsed_ms
        if synthetic_dt < 0:
            synthetic_dt = 0.0
        # Loop also begins immediately with a fade-in.
        loop_t = clamp01(entry_t * 1.4)  # loop is 40% faded in by entry end.
        loop_weight = ease_out_cubic(loop_t)
        # Apply enter (full weight from entry_t), then loop (fading in).
        self._enter_player.apply(synthetic_dt, pose, global_weight=1.0)
        if self._loop_player is None:
            self._loop_player = ClipPlayer(self._clips.loop)
        self._loop_player.apply(max(dt_ms, synthetic_dt), pose, global_weight=loop_weight)

    def play_loop(
        self,
        dt_ms: float,
        elapsed_ms: float,
        pose: EyePair,
    ) -> None:
        """Called each frame during loop_pose() by the animation state."""
        if self._loop_player is None:
            self._loop_player = ClipPlayer(self._clips.loop)
        # Loop runs forever at full weight.
        self._loop_player.apply(dt_ms, pose, global_weight=1.0)

    def play_exit(
        self,
        exit_t: float,
        pose: EyePair,
    ) -> None:
        """Called each frame during exit_pose() by the animation state.

        ``exit_t`` in [0,1] is the mixer-level transition progress; the
        Exit clip fades from 0 -> 1 as the state is blended away.
        """
        if self._exit_player is None:
            self._exit_player = ClipPlayer(self._clips.exit)
        target_elapsed = exit_t * self._clips.exit.duration_ms
        synthetic_dt = target_elapsed - self._exit_player.elapsed_ms
        if synthetic_dt < 0:
            synthetic_dt = 0.0
        # Exit clip contribution ramps with exit_t.
        self._exit_player.apply(synthetic_dt, pose, global_weight=1.0)


# ---------------------------------------------------------------------------
# Built-in reusable clip factories (for Phase 2B convenience)
# ---------------------------------------------------------------------------


def make_basic_enter_clip(
    duration_ms: float = 350.0,
    *,
    stretch_at_start: float = 0.08,
    squash_at_end: float = 0.06,
    overshoot_amount: float = 0.10,
    anticipation_amount: float = 0.06,
) -> AnimationClip:
    """Factory: a standard Enter clip with anticipation, stretch, settle."""
    return AnimationClip(
        name="standard_enter",
        duration_ms=duration_ms,
        weight_ease=ease_in_out_cubic,
        overshoot_cfg=OvershootConfig(
            anticipation_amount=anticipation_amount,
            overshoot_amount=overshoot_amount,
            overshoot_peak=0.55,
        ),
        edge_stretch=StretchConfig(amount=stretch_at_start, vertical_peak=0.2),
        edge_squash=SquashConfig(amount=squash_at_end, vertical_peak=0.75),
        primitives=[],
    )


def make_basic_exit_clip(
    duration_ms: float = 300.0,
    *,
    squash_at_start: float = 0.05,
    bounce_decay: float = 0.5,
) -> AnimationClip:
    """Factory: standard Exit clip with squash + gentle bounce-off."""
    return AnimationClip(
        name="standard_exit",
        duration_ms=duration_ms,
        weight_ease=ease_in_cubic,
        edge_squash=SquashConfig(amount=squash_at_start, vertical_peak=0.3),
        primitives=[
            PrimitiveInvocation(
                fn=apply_bounce_pair,
                config=BounceConfig(
                    amplitude_px=2.0 * bounce_decay,
                    frequency_hz=1.8,
                    weight=0.5,
                    squash_on_landing=0.03,
                ),
                amount=bounce_decay,
                envelope_fn=lambda t: 1.0 - ease_in_cubic(t),
            ),
        ],
    )


def make_breathing_loop_clip(
    breathing_cfg: Optional[BreathingConfig] = None,
    drift_cfg: Optional[DriftConfig] = None,
    *,
    breathing_amount: float = 1.0,
    drift_amount: float = 0.8,
) -> AnimationClip:
    """Factory: a Loop clip with breathing + drift baseline."""
    breathing_cfg = breathing_cfg or BreathingConfig()
    drift_cfg = drift_cfg or DriftConfig(period_seconds=9.0, amplitude_px=0.9)
    return AnimationClip(
        name="breathing_loop",
        duration_ms=0.0,
        weight_ease=ease_in_out_cubic,
        primitives=[
            PrimitiveInvocation(
                fn=apply_breathing_pair,
                config=breathing_cfg,
                amount=breathing_amount,
            ),
            PrimitiveInvocation(
                fn=apply_drift_pair,
                config=drift_cfg,
                amount=drift_amount,
            ),
        ],
    )


def make_pulse_loop_clip(
    pulse_cfg: Optional[PulseConfig] = None,
    amount: float = 1.0,
) -> AnimationClip:
    """Factory: Loop clip with rhythmic pulse (for speaking/excited states)."""
    pulse_cfg = pulse_cfg or PulseConfig()
    return AnimationClip(
        name="pulse_loop",
        duration_ms=0.0,
        primitives=[
            PrimitiveInvocation(fn=apply_pulse_pair, config=pulse_cfg, amount=amount),
        ],
    )


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "PrimitiveInvocation",
    "AnimationClip",
    "ClipPlayer",
    "StateClips",
    "StateClipPlayer",
    "make_basic_enter_clip",
    "make_basic_exit_clip",
    "make_breathing_loop_clip",
    "make_pulse_loop_clip",
]
