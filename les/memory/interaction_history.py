"""
Bounded interaction history for the LES Behavior Memory.

Stores a time-ordered, size- and age-bounded record of interaction events.
The history NEVER interprets events - it only stores and retrieves them.
Interpretation (what an event means, whether to react) belongs to future
decision layers (Emotion Director, Behavior Director).

Design notes
------------
* Time is caller-supplied (``timestamp_ms`` / ``now_ms``) - this module has
  no clock, no hardware, and no engine dependency.
* Bounded by ``max_records`` (count cap) and optionally ``max_age_ms``
  (staleness cap) so long-running robots never grow unboundedly.
* Kinds are caller-defined strings (e.g. "emotion", "intent", "blink",
  "attention", "greeting", "surprise", "touch", "voice", "llm"). This keeps
  the memory generic and extensible to touch / voice / ROS / LLM / battery
  events later without redesign.

Future extension notes (LES-Phase-1+)
-------------------------------------
* Add richer query helpers (e.g. frequency over a window, latest payload
  extraction) without changing the record model.
* The record model is intentionally payload-based
  (``Mapping[str, object]``) so new event kinds carry arbitrary detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class InteractionEvent:
    """One recorded interaction moment.

    Attributes:
        kind: caller-defined event category (e.g. "emotion", "blink").
        timestamp_ms: when the event occurred (caller-supplied clock).
        payload: arbitrary structured detail attached to the event.
    """

    kind: str
    timestamp_ms: float
    payload: Mapping[str, object] = field(default_factory=dict)


class InteractionHistory:
    """Bounded, time-ordered store of interaction events.

    This class ONLY stores and retrieves. It never decides, never schedules,
    and never touches any engine or hardware.

    Args:
        max_records: hard cap on stored events (oldest are dropped).
        max_age_ms: optional staleness cap; events older than
            ``now_ms - max_age_ms`` are pruned. ``None`` disables age
            pruning (bounded by count only).
    """

    def __init__(self, max_records: int = 256, max_age_ms: Optional[float] = None) -> None:
        self._max_records = max_records
        self._max_age_ms = max_age_ms
        self._events: list[InteractionEvent] = []

    def record(self, event: InteractionEvent, now_ms: Optional[float] = None) -> None:
        """Append one event and prune to stay within bounds.

        Args:
            event: the event to store.
            now_ms: optional caller clock used for age pruning.
        """
        self._events.append(event)
        self._prune(now_ms)

    def _prune(self, now_ms: Optional[float]) -> None:
        if self._max_age_ms is not None and now_ms is not None:
            cutoff = now_ms - self._max_age_ms
            self._events = [e for e in self._events if e.timestamp_ms >= cutoff]
        if len(self._events) > self._max_records:
            overflow = len(self._events) - self._max_records
            self._events = self._events[overflow:]

    def recent(
        self, n: Optional[int] = None, now_ms: Optional[float] = None
    ) -> list[InteractionEvent]:
        """Return the most recent ``n`` events, newest first.

        Args:
            n: how many events to return; ``None`` returns everything.
            now_ms: optional caller clock used for age pruning.
        """
        self._prune(now_ms)
        if n is None:
            return list(reversed(self._events))
        n = max(0, n)
        if n == 0:
            return []
        return list(reversed(self._events[-n:]))

    def recent_of_kind(
        self, kind: str, n: Optional[int] = None, now_ms: Optional[float] = None
    ) -> list[InteractionEvent]:
        """Return the most recent ``n`` events of one kind, newest first."""
        self._prune(now_ms)
        matched = [e for e in self._events if e.kind == kind]
        if n is None:
            return list(reversed(matched))
        n = max(0, n)
        if n == 0:
            return []
        return list(reversed(matched[-n:]))

    def last_of_kind(
        self, kind: str, now_ms: Optional[float] = None
    ) -> Optional[InteractionEvent]:
        """Return the most recent event of one kind, or ``None`` if none."""
        self._prune(now_ms)
        for e in reversed(self._events):
            if e.kind == kind:
                return e
        return None

    def count_of_kind_since(
        self, kind: str, timestamp_ms: float, now_ms: Optional[float] = None
    ) -> int:
        """Count events of one kind at or after ``timestamp_ms``."""
        self._prune(now_ms)
        return sum(1 for e in self._events if e.kind == kind and e.timestamp_ms >= timestamp_ms)

    def clear(self) -> None:
        """Drop all stored events (configuration such as caps is kept)."""
        self._events.clear()

    @property
    def is_empty(self) -> bool:
        """True when no events are stored."""
        return not self._events

    @property
    def max_records(self) -> int:
        """The configured count cap."""
        return self._max_records

    def __len__(self) -> int:
        return len(self._events)


__all__ = ["InteractionEvent", "InteractionHistory"]
