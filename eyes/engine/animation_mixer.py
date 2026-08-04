"""
Animation mixer with layered composition.

Composition pipeline (top to bottom, stacked additively / by priority):

    [ State Pose ]          <- current AnimationState (blended across transitions)
          +
    [ Blink Layer ]         <- BlinkController blink_weight / lid closure
          +
    [ Look Layer ]          <- LookController eye offsets
          +
    [ Micro Motion Layer ]  <- MicroMotion subtle drift / sway / breathe
          +
    [ Speech Pulse (tbd) ]  <- reserved slot for Phase 2 lip-sync-like pulse
          ↓
    Final Eye Pose

All transitions and layer compositing mutate preallocated scratch buffers in
place; the mixer never allocates EyePair instances on the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple, TYPE_CHECKING

from ..engine.config import EngineConfig
from ..engine.easing import ease_in_out_cubic, get_easing, EasingFunction
from ..engine.eye_pair import EyePair

if TYPE_CHECKING:
    from .base import AnimationState


@dataclass
class _ActiveTransition:
    from_pose: EyePair
    to_state: "AnimationState"
    from_state: Optional["AnimationState"]
    elapsed_ms: float = 0.0
    duration_ms: float = 350.0
    easing: EasingFunction = field(default_factory=lambda: ease_in_out_cubic)
    complete: bool = False


class LayerSlots:
    """Weights for each composition layer, reported for the debug overlay."""

    __slots__ = ("blink", "look", "micro", "speech")

    def __init__(self) -> None:
        self.blink: float = 0.0
        self.look: Tuple[float, float] = (0.0, 0.0)
        self.micro: Tuple[float, float] = (0.0, 0.0)
        self.speech: float = 0.0

    def reset(self) -> None:
        self.blink = 0.0
        self.look = (0.0, 0.0)
        self.micro = (0.0, 0.0)
        self.speech = 0.0


class AnimationMixer:
    """Layered animation composition pipeline.

    Constructor overloads (backward-compatible):
      AnimationMixer(config, default_pose)  -- production (AnimationEngine)
      AnimationMixer(config, state_machine) -- standalone / test
    """

    def __init__(
        self,
        config: EngineConfig,
        default_pose_or_sm: "EyePair | StateMachine",
    ) -> None:
        from .state_machine import StateMachine as _SM
        self._config = config
        self._current_state: Optional["AnimationState"] = None

        if isinstance(default_pose_or_sm, _SM):
            # Standalone / test path: build scratch buffers from a neutral pose.
            _sm = default_pose_or_sm
            _sm._attach_mixer(self)
            _default = EyePair()
        else:
            _default = default_pose_or_sm

        # Reused output buffers - never replace these objects, only mutate.
        self._current_pose: EyePair = _default.copy()
        self._final_pose: EyePair = _default.copy()

        # Scratch buffers used only inside update() to avoid allocations.
        self._scratch_from: EyePair = _default.copy()
        self._scratch_to: EyePair = _default.copy()
        self._scratch_loop: EyePair = _default.copy()
        self._scratch_entry: EyePair = _default.copy()

        self._transition: Optional[_ActiveTransition] = None
        self._loop_elapsed_ms: float = 0.0
        self._blend_progress: float = 1.0
        self._layer_weights = LayerSlots()

    # ------------------------------------------------------------------
    # Public read-only properties (used by debug overlay / API)
    # ------------------------------------------------------------------
    @property
    def current_state_name(self) -> str:
        if self._current_state is None:
            return "none"
        return self._current_state.state_name

    @property
    def is_blending(self) -> bool:
        return self._transition is not None and not self._transition.complete

    @property
    def blend_progress(self) -> float:
        """0..1 progress of the active state transition, 1.0 when idle."""
        return self._blend_progress

    @property
    def layer_weights(self) -> LayerSlots:
        return self._layer_weights

    # ------------------------------------------------------------------
    # State transition control
    # ------------------------------------------------------------------
    def set_state_immediate(self, state: "AnimationState") -> None:
        if self._current_state is not None:
            self._current_state.on_exit()
        state.on_enter()
        self._current_state = state
        self._loop_elapsed_ms = 0.0
        # Entry pose on top of _current_pose at t=1.
        state.entry_pose(1.0, self._current_pose)
        self._transition = None
        self._blend_progress = 1.0

    def transition_to(
        self,
        state: "AnimationState",
        duration_ms: Optional[float] = None,
        easing: str | EasingFunction = "ease_in_out_cubic",
    ) -> None:
        if duration_ms is None:
            duration_ms = self._config.timing.state_transition_ms

        if duration_ms <= 0 or self._current_state is None:
            self.set_state_immediate(state)
            return

        easing_fn = easing if callable(easing) else get_easing(easing)

        # Snapshot the current pose as "from"; don't touch _current_pose
        # until the transition advances inside update().
        self._scratch_from.copy_from(self._current_pose)
        if self._current_state is not None:
            self._current_state.on_exit()

        state.on_enter()

        self._transition = _ActiveTransition(
            from_pose=self._scratch_from.copy(),
            to_state=state,
            from_state=self._current_state,
            duration_ms=duration_ms,
            easing=easing_fn,
        )
        self._current_state = state
        self._loop_elapsed_ms = 0.0
        self._blend_progress = 0.0

    def get_pose(self) -> EyePair:
        """Return the current STATE pose (before layer composition)."""
        return self._current_pose

    def get_final_pose(self) -> EyePair:
        """Return the fully composed pose including all layers."""
        return self._final_pose

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------
    def update(
        self,
        dt_ms: float,
        blink_weight: "float | EyePair" = 0.0,
        look_offsets: Tuple[float, float] = (0.0, 0.0),
        micro_offsets: Tuple[float, float] = (0.0, 0.0),
        speech_pulse: float = 0.0,
        dst: Optional[EyePair] = None,
    ) -> None:
        """Advance the animation mixer by dt_ms.

        Accepts both keyword layer inputs (production path) and test calling
        conventions:
          update(dt_ms, blink_weight=bw, look_offsets=...) -- production hot-path
          update(dt_ms, dst_pair)                           -- test / standalone
        """
        # Detect EyePair passed as 2nd positional argument (test / standalone compat path).
        if isinstance(blink_weight, EyePair):
            dst = blink_weight
            bw_val: float = 0.0
        else:
            bw_val = float(blink_weight)
        self._layer_weights.reset()
        self._layer_weights.blink = bw_val
        self._layer_weights.look = look_offsets
        self._layer_weights.micro = micro_offsets
        self._layer_weights.speech = speech_pulse

        # 1. Compute the state pose into _current_pose
        if self._transition is not None and not self._transition.complete:
            tr = self._transition
            tr.elapsed_ms += dt_ms
            raw_t = tr.elapsed_ms / tr.duration_ms if tr.duration_ms > 0 else 1.0
            t = max(0.0, min(1.0, raw_t))
            eased_t = tr.easing(t)
            self._blend_progress = eased_t

            # from_pose with exit modifier applied
            self._scratch_from.copy_from(tr.from_pose)
            if tr.from_state is not None:
                tr.from_state.exit_pose(eased_t, self._scratch_from)

            # to_pose with entry modifier applied
            self._scratch_to.copy_from(tr.from_pose)
            tr.to_state.entry_pose(eased_t, self._scratch_to)

            # loop pose evolving on top of "to" side of the blend
            self._scratch_loop.copy_from(self._scratch_to)
            self._loop_elapsed_ms += dt_ms
            tr.to_state.loop_pose(dt_ms, self._loop_elapsed_ms, self._scratch_loop)

            # entry -> loop crossfade so loop takes over once entry finishes
            entry_to_loop_t = max(0.0, min(1.0, eased_t * 1.4))
            self._scratch_entry.lerp_into(self._scratch_to, self._scratch_loop, entry_to_loop_t)

            # Blend "from" side with composed "to + loop" side using cinematic emotion morphing
            from .motion_primitives import apply_emotion_morph_pair
            apply_emotion_morph_pair(self._current_pose, self._scratch_from, self._scratch_entry, eased_t)

            if raw_t >= 1.0:
                tr.complete = True
                self._transition = None
                self._blend_progress = 1.0
        elif self._current_state is not None:
            self._loop_elapsed_ms += dt_ms
            self._current_state.loop_pose(dt_ms, self._loop_elapsed_ms, self._current_pose)
            self._blend_progress = 1.0

        # 2. Compose layers on top of state pose -> _final_pose
        self._compose_layers(
            blink_weight=bw_val,
            look_offsets=look_offsets,
            micro_offsets=micro_offsets,
            speech_pulse=speech_pulse,
        )

        # 3. If a dst EyePair was passed (test/standalone compat), copy into it.
        if dst is not None:
            dst.copy_from(self._final_pose)

    # ------------------------------------------------------------------
    # Layer composition
    #
    # Layers mutate _final_pose directly.  Each layer is conceptually
    # additive (look/micro offsets) or priority-max (blink).
    # ------------------------------------------------------------------
    def _compose_layers(
        self,
        blink_weight: float,
        look_offsets: Tuple[float, float],
        micro_offsets: Tuple[float, float],
        speech_pulse: float,
    ) -> None:
        final = self._final_pose
        final.copy_from(self._current_pose)

        self._apply_look_layer(final, look_offsets)
        self._apply_micro_layer(final, micro_offsets)
        self._apply_speech_pulse(final, speech_pulse)
        self._apply_blink_layer(final, blink_weight)

        final.clamp_safe()

    @staticmethod
    def _apply_look_layer(final: EyePair, offsets: Tuple[float, float]) -> None:
        dx, dy = offsets
        if dx == 0.0 and dy == 0.0:
            return
        for eye in (final.left, final.right):
            eye.look_offset_x += dx
            eye.look_offset_y += dy

    @staticmethod
    def _apply_micro_layer(final: EyePair, offsets: Tuple[float, float]) -> None:
        dx, dy = offsets
        if dx == 0.0 and dy == 0.0:
            return
        # Per-eye slight lateral asymmetry (~0.3px) keeps stereo natural.
        final.left.micro_offset_x += dx - 0.15
        final.left.micro_offset_y += dy
        final.right.micro_offset_x += dx + 0.15
        final.right.micro_offset_y += dy

    @staticmethod
    def _apply_blink_layer(final: EyePair, weight: float) -> None:
        if weight <= 0.0:
            return
        for eye in (final.left, final.right):
            if weight > eye.blink_weight:
                eye.blink_weight = weight
            openness = 1.0 - weight
            if openness < eye.lid_openness:
                eye.lid_openness = openness

    @staticmethod
    def _apply_speech_pulse(final: EyePair, pulse: float) -> None:
        """Speech pulse layer: procedurally influences bounce, stretch, squash, and scale.

        Pulse input is in [0, 1] representing current audio amplitude / speech energy.
        Applies zero-allocation additive procedural deformation to both eyes.
        """
        if pulse <= 0.0:
            return
        p = max(0.0, min(1.0, pulse))
        for eye in (final.left, final.right):
            eye.bounce_offset_y += -p * 1.8
            eye.stretch += p * 0.02
            eye.squash += p * 0.01
            eye.scale_y += p * 0.015
            eye.scale_x -= p * 0.005

