"""
Behavior scheduler contracts.

The Scheduler is the BOUNDARY between LES and the animation engine. It
consumes ``BehaviorRequest`` objects, plans ``TimelineEvent`` objects, and
emits ``EngineCommand`` objects that drive the engine's stable public API.

The engine (``eyes/``, v1.0 STABLE) is referenced ONLY through the
``EngineDriver`` protocol - LES never imports or modifies the engine at
runtime. The type-only import below documents the exact engine types used.

Engine API surface LES relies on (stable since v1.0):
    * set_state(state, transition_ms)
    * blink()
    * trigger_blink_type(blink_type)
    * look_at(x, y)
    * step(dt_ms, speech_pulse)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional, Protocol, Tuple, TYPE_CHECKING

from ..director.behavior_director import BehaviorRequest

if TYPE_CHECKING:
    from eyes.engine.blink_controller import BlinkType


EngineCommandName = Literal[
    "set_state",
    "blink",
    "trigger_blink_type",
    "look_at",
    "step",
]


@dataclass(frozen=True)
class EngineCommand:
    """One imperative call into the animation engine."""

    command: EngineCommandName
    args: Tuple[object, ...] = ()
    delay_ms: float = 0.0
    # TODO(LES-Phase-1): support relative scheduling (execute N ms from now).


class EngineDriver(Protocol):
    """The minimal engine surface LES is allowed to call.

    Implemented by ``eyes.engine.AnimationEngine`` / ``eyes.EyeEngine``
    (both unchanged - the protocol only describes what LES needs).
    """

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        ...

    def blink(self) -> None:
        ...

    def trigger_blink_type(self, blink_type: "BlinkType") -> None:
        ...

    def look_at(self, x: float, y: float) -> None:
        ...

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> object:
        ...


class Scheduler(ABC):
    """Interface for translating behavior requests into engine commands.

    Future responsibilities (Phase 1):
        * attach to an EngineDriver at startup
        * plan one or more TimelineEvents per BehaviorRequest
        * each tick: advance the timeline and emit EngineCommands for
          events that come due
        * own the mapping behavior -> engine state / blink / look commands
    """

    @abstractmethod
    def attach(self, engine: EngineDriver) -> None:
        """Bind the scheduler to a running engine instance."""
        ...

    @abstractmethod
    def schedule(self, request: BehaviorRequest) -> None:
        """Accept a behavior request and plan its timeline events."""
        ...

    @abstractmethod
    def advance(self, dt_ms: float) -> list[EngineCommand]:
        """Advance scheduling state and return any due engine commands."""
        ...

    @abstractmethod
    def drain_commands(self) -> list[EngineCommand]:
        """Return and clear all pending engine commands."""
        ...


__all__ = ["EngineCommand", "EngineCommandName", "EngineDriver", "Scheduler"]
