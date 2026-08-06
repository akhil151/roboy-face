"""
Transition Director contracts.

The Transition Director owns HOW the robot changes expressive state:
which target state to enter, how long the blend takes, and which easing
to use. It translates those decisions into engine ``set_state()`` calls
via the ``EngineDriver`` protocol.

This module must NOT reimplement blending - the engine already owns smooth
state blending (see ``eyes.engine.state_machine`` + ``eyes.engine.animation_mixer``).
LES only DECIDES and REQUESTS; the engine EXECUTES.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..timeline.scheduler import EngineDriver


@dataclass(frozen=True)
class TransitionSpec:
    """A planned emotional state transition."""

    from_state: str
    to_state: str
    blend_ms: float                      # passed through to engine set_state()
    easing: str = "smooth"
    # TODO(LES-Phase-1): enumerate the easing keys the engine accepts and
    # document them here.


class TransitionDirector(ABC):
    """Interface for planning and requesting state transitions.

    Future responsibilities (Phase 1):
        * decide blend duration from intent urgency / personality
        * avoid pointless re-transitions to the already-active state
        * priority handling: dramatic vs. subtle changes
    """

    @abstractmethod
    def request_transition(self, to_state: str, blend_ms: Optional[float] = None) -> None:
        """Queue a transition request toward ``to_state``."""
        ...

    @abstractmethod
    def current_spec(self) -> Optional[TransitionSpec]:
        """Return the active transition, or None once settled."""
        ...

    @abstractmethod
    def apply(self, engine: EngineDriver) -> None:
        """Execute the current transition on the engine (a set_state call)."""
        ...

    @abstractmethod
    def update(self, dt_ms: float) -> None:
        """Advance transition bookkeeping. Called once per tick."""
        ...


__all__ = ["TransitionSpec", "TransitionDirector"]
