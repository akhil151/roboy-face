"""
Animation mixer - smoothly blends between animation states.

Never instantly switches. Instead, it:
1. Captures the "from" pose when a transition begins
2. Calls exit_pose on the old state and entry_pose on the new state
3. Linearly interpolates all EyePair parameters over a blend duration

All parameters morph continuously: radius, scale, eye height,
lid curvature, movement, blink frequency targets, etc.
Default blend duration: 350 milliseconds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ..engine.config import EngineConfig
from ..engine.easing import ease_in_out_cubic, get_easing, EasingFunction
from ..engine.eye_pair import EyePair, blend_eye_pair

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


class AnimationMixer:
    def __init__(self, config: EngineConfig, default_pose: EyePair) -> None:
        self._config = config
        self._current_state: Optional["AnimationState"] = None
        self._current_pose: EyePair = default_pose.copy()
        self._transition: Optional[_ActiveTransition] = None
        self._loop_elapsed_ms: float = 0.0

    @property
    def current_state_name(self) -> str:
        if self._current_state is None:
            return "none"
        return self._current_state.state_name

    @property
    def is_blending(self) -> bool:
        return self._transition is not None and not self._transition.complete

    def set_state_immediate(self, state: "AnimationState") -> None:
        if self._current_state is not None:
            self._current_state.on_exit()
        state.on_enter()
        self._current_state = state
        self._loop_elapsed_ms = 0.0
        state.entry_pose(1.0, self._current_pose)
        self._transition = None

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

        from_pose = self._current_pose.copy()
        if self._current_state is not None:
            self._current_state.on_exit()

        state.on_enter()

        self._transition = _ActiveTransition(
            from_pose=from_pose,
            to_state=state,
            from_state=self._current_state,
            duration_ms=duration_ms,
            easing=easing_fn,
        )
        self._current_state = state
        self._loop_elapsed_ms = 0.0

    def get_pose(self) -> EyePair:
        return self._current_pose

    def update(self, dt_ms: float) -> None:
        if self._transition is not None and not self._transition.complete:
            tr = self._transition
            tr.elapsed_ms += dt_ms
            raw_t = tr.elapsed_ms / tr.duration_ms if tr.duration_ms > 0 else 1.0

            t = max(0.0, min(1.0, raw_t))
            eased_t = tr.easing(t)

            from_pose = tr.from_pose.copy()

            if tr.from_state is not None:
                tr.from_state.exit_pose(eased_t, from_pose)

            to_pose = EyePair()
            to_pose.left = from_pose.left.copy()
            to_pose.right = from_pose.right.copy()
            tr.to_state.entry_pose(eased_t, to_pose)

            loop_pose = to_pose.copy()
            self._loop_elapsed_ms += dt_ms
            tr.to_state.loop_pose(dt_ms, self._loop_elapsed_ms, loop_pose)

            entry_t = eased_t
            entry_blended = blend_eye_pair(to_pose, loop_pose, min(1.0, eased_t * 1.4))
            self._current_pose = blend_eye_pair(from_pose, entry_blended, eased_t)

            if raw_t >= 1.0:
                tr.complete = True
                self._transition = None
            return

        if self._current_state is not None:
            self._loop_elapsed_ms += dt_ms
            self._current_state.loop_pose(dt_ms, self._loop_elapsed_ms, self._current_pose)
