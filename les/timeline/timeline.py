"""
Behavior timeline contracts and the default implementation.

The timeline is a time-ordered queue of behavior events. Behaviors plan
``TimelineEvent`` objects; the Scheduler consumes events that come due
each tick and translates them into engine commands.

``TimelineEvent`` carries NO engine knowledge - it is pure behavior data.
The timeline itself never reads ``payload``; only the Scheduler (which
authored the payload) interprets it.

``DefaultTimeline`` is the concrete bounded implementation:

    * events are kept strictly ordered by start time, with a stable FIFO
      order for equal start times (deterministic same-time ordering);
    * capacity and horizon are bounded at construction, and rejected
      pushes are signalled (bool), never silently evicted;
    * time is caller-owned - it moves only through ``advance(dt_ms)``;
    * due events are extracted in time order and removed;
    * cancellation / replacement is supported via ``cancel``;
    * it never decides behavior - ``priority`` is carried as data only.

The timeline is fully independent of pygame, the animation engine
(``eyes/`` / ``face/``), ROS, hardware, voice, camera and LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from bisect import insort_right
from dataclasses import dataclass, field
from typing import Mapping, Optional

from ..config.defaults import TimelineConfig


@dataclass(frozen=True)
class TimelineEvent:
    """One scheduled behavior moment on the timeline.

    Attributes:
        behavior_name: the behavior this moment belongs to.
        start_ms: absolute timeline time at which the moment comes due.
        duration_ms: how long the behavior holds (metadata - the
            timeline neither interprets nor enforces it).
        priority: the intent's arbitration score (carried as data; the
            timeline never uses it to order or arbitrate).
        payload: opaque behavior data authored by the Scheduler (e.g. the
            planned engine command and variant label). The timeline never
            reads it.
    """

    behavior_name: str
    start_ms: float                      # absolute timeline time
    duration_ms: float                   # how long the behavior holds
    priority: float                      # for collision / interruption rules
    payload: Mapping[str, object] = field(default_factory=dict)
    # TODO(LES-Phase-1): typed payloads per behavior (e.g. look targets,
    # blink type, blend duration).


@dataclass
class _EventSlot:
    """Internal sortable slot; orders by ``(start_ms, seq)`` only.

    ``seq`` is a strictly-increasing insertion counter, so equal start
    times keep a stable FIFO order and slots never compare their events.
    """

    start_ms: float
    seq: int
    event: TimelineEvent

    def __lt__(self, other: "_EventSlot") -> bool:
        return (self.start_ms, self.seq) < (other.start_ms, other.seq)


class Timeline(ABC):
    """Interface for the ordered, bounded event queue.

    The timeline is a pure time-ordered store: it never decides what a
    behavior means, never arbitrates between events and never touches the
    engine. Ordering is strictly by start time (stable FIFO for equal
    start times). Capacity and horizon are bounded at construction.
    """

    @abstractmethod
    def push(self, event: TimelineEvent) -> bool:
        """Schedule an event on the timeline.

        Returns True when the event was accepted, False when it was
        rejected (beyond the horizon, or the queue is at capacity).
        """
        ...

    @abstractmethod
    def cancel(self, behavior_name: Optional[str] = None) -> None:
        """Remove pending events - one behavior's, or all when ``None``.

        Used by the Scheduler for safe cancellation / replacement of an
        obsolete pending timeline (interruption).
        """
        ...

    @abstractmethod
    def advance(self, dt_ms: float) -> None:
        """Move timeline time forward by ``dt_ms`` (caller-owned time)."""
        ...

    @abstractmethod
    def due_events(self) -> list[TimelineEvent]:
        """Return (and remove) every event that has come due, in order."""
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

    @property
    @abstractmethod
    def now_ms(self) -> float:
        """The current caller-owned timeline time (the scheduler's clock)."""
        ...


class DefaultTimeline(Timeline):
    """Bounded, deterministic, caller-owned-time event queue.

    Events are stored sorted by ``(start_ms, insertion order)``. Pushes
    beyond the horizon or at capacity are rejected and return False.
    Time only moves via ``advance(dt_ms)`` - the timeline never reads a
    wall clock.

    Args:
        capacity: maximum number of pending events (default from
            ``TimelineConfig``).
        horizon_ms: furthest-future start time accepted, relative to the
            current timeline time (default from ``TimelineConfig``).
        config: optional ``TimelineConfig`` seeding the two defaults.
    """

    def __init__(
        self,
        capacity: Optional[int] = None,
        horizon_ms: Optional[float] = None,
        config: Optional[TimelineConfig] = None,
    ) -> None:
        cfg = config if config is not None else TimelineConfig()
        self.capacity: int = cfg.capacity if capacity is None else int(capacity)
        self.horizon_ms: float = cfg.max_horizon_ms if horizon_ms is None else float(horizon_ms)
        self._now_ms: float = 0.0
        self._events: list[_EventSlot] = []
        self._seq: int = 0

    # ------------------------------------------------------------------
    # Timeline interface
    # ------------------------------------------------------------------

    def push(self, event: TimelineEvent) -> bool:
        """Insert ``event`` in time order.

        Rejects (returns False) when the event's start time lies beyond
        ``now + horizon_ms`` or the queue is already at capacity. Already
        due events are accepted - they surface on the next
        ``due_events()``. No event is ever silently evicted.
        """
        if event.start_ms > self._now_ms + self.horizon_ms:
            return False
        if len(self._events) >= self.capacity:
            return False
        insort_right(self._events, _EventSlot(event.start_ms, self._seq, event))
        self._seq += 1
        return True

    def cancel(self, behavior_name: Optional[str] = None) -> None:
        """Remove pending events for ``behavior_name`` (all when None)."""
        if behavior_name is None:
            self._events.clear()
            return
        self._events = [
            slot for slot in self._events if slot.event.behavior_name != behavior_name
        ]

    def advance(self, dt_ms: float) -> None:
        """Move the caller-owned clock forward by ``max(0, dt_ms)``."""
        self._now_ms += max(0.0, dt_ms)

    def due_events(self) -> list[TimelineEvent]:
        """Extract and return every due event, in time order.

        Events whose ``start_ms`` is at or before the current timeline
        time are removed from the queue and returned oldest-first.
        """
        due: list[TimelineEvent] = []
        while self._events and self._events[0].start_ms <= self._now_ms:
            due.append(self._events.pop(0).event)
        return due

    def clear(self) -> None:
        """Drop all pending events."""
        self._events.clear()

    @property
    def is_empty(self) -> bool:
        """True when no events are pending."""
        return not self._events

    # ------------------------------------------------------------------
    # Observability (read-only; never used for decisions)
    # ------------------------------------------------------------------

    @property
    def now_ms(self) -> float:
        """Current caller-owned timeline time."""
        return self._now_ms

    @property
    def pending(self) -> list[TimelineEvent]:
        """Snapshot of all pending events, in time order (read-only)."""
        return [slot.event for slot in self._events]

    def __len__(self) -> int:
        return len(self._events)


__all__ = ["TimelineEvent", "Timeline", "DefaultTimeline"]
