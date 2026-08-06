"""
Behavior timeline contracts.

The timeline is a time-ordered queue of behavior events. Behaviors plan
``TimelineEvent`` objects; the Scheduler consumes events that come due
each tick and translates them into engine commands.

``TimelineEvent`` carries NO engine knowledge - it is pure behavior data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class TimelineEvent:
    """One scheduled behavior moment on the timeline."""

    behavior_name: str
    start_ms: float                      # absolute timeline time
    duration_ms: float                   # how long the behavior holds
    priority: float                      # for collision / interruption rules
    payload: Mapping[str, object] = field(default_factory=dict)
    # TODO(LES-Phase-1): typed payloads per behavior (e.g. look targets,
    # blink type, blend duration).


class Timeline(ABC):
    """Interface for the ordered event queue.

    Future responsibilities (Phase 1):
        * insert events in time order
        * allow the active behavior to be interrupted by higher priority
        * drop expired / lowest-priority events when over capacity
    """

    @abstractmethod
    def push(self, event: TimelineEvent) -> None:
        """Schedule an event on the timeline."""
        ...

    @abstractmethod
    def advance(self, dt_ms: float) -> None:
        """Move timeline time forward by ``dt_ms``."""
        ...

    @abstractmethod
    def due_events(self) -> list[TimelineEvent]:
        """Return (and remove) every event that has come due."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Drop all pending events."""
        ...

    @property
    @abstractmethod
    def is_empty(self) -> bool:
        """True when no events are pending."""
        ...


__all__ = ["TimelineEvent", "Timeline"]
