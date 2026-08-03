"""
Animation state machine.

Manages the 10 official states:
calm, listening, thinking, speaking, happy, caring, sad, sleepy, surprised, focus.

Holds a registry of AnimationState instances and delegates transitions
through the AnimationMixer for smooth blending.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..animations.base import AnimationState
    from .animation_mixer import AnimationMixer

VALID_STATES: frozenset[str] = frozenset(
    [
        "calm",
        "listening",
        "thinking",
        "speaking",
        "happy",
        "caring",
        "sad",
        "sleepy",
        "surprised",
        "focus",
    ]
)


@dataclass
class StateMachine:
    _mixer: "AnimationMixer"
    _states: dict[str, "AnimationState"] = field(default_factory=dict)
    _requested_state: Optional[str] = None
    _transition_duration_ms: Optional[float] = None

    def register(self, name: str, state: "AnimationState") -> None:
        if name not in VALID_STATES:
            raise ValueError(
                f"Invalid state name '{name}'. Valid states: {sorted(VALID_STATES)}"
            )
        self._states[name] = state

    def get_state(self, name: str) -> Optional["AnimationState"]:
        return self._states.get(name)

    def set_state(
        self,
        name: str,
        transition_duration_ms: Optional[float] = None,
    ) -> None:
        if name not in self._states:
            raise ValueError(
                f"State '{name}' is not registered. Registered: {sorted(self._states.keys())}"
            )
        self._requested_state = name
        self._transition_duration_ms = transition_duration_ms

    @property
    def current_state_name(self) -> str:
        return self._mixer.current_state_name

    @property
    def is_idle(self) -> bool:
        return not self._mixer.is_blending and self._requested_state is None

    def initialize(self, initial_state: str = "calm") -> None:
        if initial_state not in self._states:
            raise ValueError(
                f"Initial state '{initial_state}' not registered. "
                f"Available: {sorted(self._states.keys())}"
            )
        self._mixer.set_state_immediate(self._states[initial_state])

    def update(self, dt_ms: float) -> None:
        if self._requested_state is not None:
            state = self._states[self._requested_state]
            self._mixer.transition_to(state, self._transition_duration_ms)
            self._requested_state = None
            self._transition_duration_ms = None
