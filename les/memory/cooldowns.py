"""
Named cooldown timers for the LES Behavior Memory.

Cooldowns track "how long until a behaviour may happen again" (e.g. greeting
cooldown, surprise cooldown - see Interaction Bible Part 4.3 / 4.4). This
module ONLY tracks timers; it never decides whether a behaviour should run.
Future directors query it and make the decision themselves.

Design notes
------------
* Generic: cooldown names are arbitrary strings, so per-person keys
  (e.g. ``"greeting:person-1"``) work without hardcoding any behaviour.
* Time is caller-supplied (``now_ms``) - no clock or hardware dependency.
* Expired entries are pruned automatically to keep the table bounded.

Future extension notes (LES-Phase-1+)
-------------------------------------
* Add priority-aware eviction if distinct cooldown names grow large.
* The entry model (frozen dataclass) allows serializing active cooldowns
  across power cycles without API changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class CooldownEntry:
    """One cooldown timer record.

    Attributes:
        name: caller-defined cooldown key.
        started_ms: when the cooldown began (caller clock).
        duration_ms: how long the cooldown lasts.
    """

    name: str
    started_ms: float
    duration_ms: float

    @property
    def end_ms(self) -> float:
        """The time at which this cooldown expires."""
        return self.started_ms + self.duration_ms


class CooldownTracker:
    """Tracks named cooldown timers; purely informational, never decides.

    Args:
        max_entries: hard cap on distinct cooldown names tracked at once.
            Oldest entries are evicted first if the cap is exceeded.
    """

    def __init__(self, max_entries: int = 64) -> None:
        self._max_entries = max_entries
        self._entries: Dict[str, CooldownEntry] = {}

    def start(self, name: str, duration_ms: float, now_ms: float) -> None:
        """Start (or restart) a cooldown timer for ``name``.

        Args:
            name: caller-defined cooldown key.
            duration_ms: how long the cooldown should last.
            now_ms: caller-supplied clock at the moment of starting.
        """
        self._entries[name] = CooldownEntry(
            name=name, started_ms=now_ms, duration_ms=duration_ms
        )
        self._prune(now_ms)

    def is_active(self, name: str, now_ms: float) -> bool:
        """True while the named cooldown has not yet expired."""
        entry = self._entries.get(name)
        if entry is None:
            return False
        return now_ms < entry.end_ms

    def remaining_ms(self, name: str, now_ms: float) -> float:
        """Milliseconds until the cooldown expires (0 when not active)."""
        entry = self._entries.get(name)
        if entry is None:
            return 0.0
        return max(0.0, entry.end_ms - now_ms)

    def elapsed_ms(self, name: str, now_ms: float) -> float:
        """Milliseconds since the cooldown started (0 when unknown)."""
        entry = self._entries.get(name)
        if entry is None:
            return 0.0
        return max(0.0, now_ms - entry.started_ms)

    def active_names(self, now_ms: float) -> list[str]:
        """Names of all currently-active cooldowns (unsorted)."""
        return [name for name, entry in self._entries.items() if now_ms < entry.end_ms]

    def clear(self, name: str) -> None:
        """Remove one cooldown entry."""
        self._entries.pop(name, None)

    def clear_all(self) -> None:
        """Remove every cooldown (runtime state only; the cap is kept)."""
        self._entries.clear()

    def _prune(self, now_ms: float) -> None:
        # Drop expired entries first, then evict oldest if over the cap.
        self._entries = {
            name: entry
            for name, entry in self._entries.items()
            if now_ms < entry.end_ms
        }
        while len(self._entries) > self._max_entries:
            oldest = min(self._entries.values(), key=lambda e: e.started_ms)
            del self._entries[oldest.name]


__all__ = ["CooldownEntry", "CooldownTracker"]
