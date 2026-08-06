"""
Behavior Memory facade - the single entry point for behavioral context.

Composes the memory sub-components (``InteractionHistory``,
``CooldownTracker``, ``EmotionalState``) with the small scalar "current
context" the future decision layers need (active behavior, last blink type,
attention target, recovery state, last interaction time).

STRICT RULES (design authority: Interaction Bible Part 4):
    * Memory NEVER decides. Every method either records what the caller
      reports or answers a pure query.
    * Memory NEVER changes emotion - it records emotion transitions reported
      by a caller.
    * Memory NEVER schedules behavior, never arbitrates, never calls the
      engine, and never touches timelines.
    * Memory has no clock, no hardware, no pygame, no ROS, no servos.

The caller (future Emotion Director / Behavior Director / Timeline) owns
all policy: it chooses event kinds, cooldown names, windows, and
interpretations. This class only exposes the state those layers need.

Future extension notes (LES-Phase-1+)
-------------------------------------
* New history kinds (touch, voice, ros, llm, battery, sensor) require no
  code change - record them via ``record_event`` with the chosen kind tag.
* Additional current-context scalars can be added without changing existing
  methods (this class is a plain state holder, not a frozen contract).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .cooldowns import CooldownTracker
from .emotional_state import EmotionalState
from .interaction_history import InteractionEvent, InteractionHistory


@dataclass(frozen=True)
class MemorySnapshot:
    """Read-only snapshot of the current memory state (observability).

    Never used for decisions - only for logging / debugging / inspection.

    Attributes:
        emotion: current dominant emotion (``None`` = neutral).
        previous_emotion: previous emotion.
        intent: current intent.
        previous_intent: previous intent.
        active_behavior: currently-active behavior label.
        previous_behavior: previously-active behavior label.
        attention_target: current attention target (x, y) or ``None``.
        recovery_state: current recovery-state label or ``None``.
        last_blink_type: most recent blink type or ``None``.
        last_interaction_ms: most recent interaction timestamp.
        history_size: number of stored history events.
        active_cooldowns: names of currently-active cooldowns.
    """

    emotion: Optional[str]
    previous_emotion: Optional[str]
    intent: Optional[str]
    previous_intent: Optional[str]
    active_behavior: Optional[str]
    previous_behavior: Optional[str]
    attention_target: Optional[Tuple[float, float]]
    recovery_state: Optional[str]
    last_blink_type: Optional[str]
    last_interaction_ms: float
    history_size: int
    active_cooldowns: Tuple[str, ...]


class BehaviorMemory:
    """Aggregate behavioral context store (pure state, no decisions).

    Args:
        history: optional shared ``InteractionHistory`` (injected for reuse).
        cooldowns: optional shared ``CooldownTracker`` (injected for reuse).
        emotional: optional shared ``EmotionalState`` (injected for reuse).
        max_history_records: history count cap when creating a new history.
        max_history_age_ms: optional history staleness cap when creating a
            new history (``None`` = bounded by count only).
        max_cooldowns: distinct-cooldown cap when creating a new tracker.
    """

    def __init__(
        self,
        history: Optional[InteractionHistory] = None,
        cooldowns: Optional[CooldownTracker] = None,
        emotional: Optional[EmotionalState] = None,
        max_history_records: int = 256,
        max_history_age_ms: Optional[float] = None,
        max_cooldowns: int = 64,
    ) -> None:
        self.history = history if history is not None else InteractionHistory(
            max_records=max_history_records, max_age_ms=max_history_age_ms
        )
        self.cooldowns = cooldowns if cooldowns is not None else CooldownTracker(
            max_entries=max_cooldowns
        )
        self.emotional = emotional if emotional is not None else EmotionalState()

        # Scalar current-context fields (memory of last-known values).
        self._active_behavior: Optional[str] = None
        self._previous_behavior: Optional[str] = None
        self._attention_target: Optional[Tuple[float, float]] = None
        self._attention_since_ms: float = 0.0
        self._recovery_state: Optional[str] = None
        self._last_blink_type: Optional[str] = None
        self._last_blink_ms: float = 0.0
        self._last_interaction_ms: float = 0.0

    # ------------------------------------------------------------------
    # Recording API - callers report facts; memory only stores them.
    # ------------------------------------------------------------------

    def record_event(
        self,
        kind: str,
        timestamp_ms: float,
        payload: Optional[Mapping[str, object]] = None,
    ) -> None:
        """Record a generic interaction event under a caller-chosen kind.

        Kind examples used by future layers: "greeting", "surprise",
        "touch", "voice", "llm", "battery". The memory does not interpret
        kinds - it only stores and retrieves them.

        Args:
            kind: caller-defined event category.
            timestamp_ms: caller-supplied clock.
            payload: optional structured detail.
        """
        self.history.record(
            InteractionEvent(kind=kind, timestamp_ms=timestamp_ms, payload=payload or {}),
            now_ms=timestamp_ms,  # age-prune relative to the newest event
        )
        self._last_interaction_ms = max(self._last_interaction_ms, timestamp_ms)

    def record_emotion(self, emotion: str, timestamp_ms: float) -> bool:
        """Record an emotion transition reported by a decision layer.

        Updates current/previous emotion and, ONLY when the emotion really
        changed, appends a history event of kind ``"emotion"`` (keeps
        transition counts honest - a no-op re-report is not a transition).

        Returns:
            True when the emotion actually changed, False on no-op.
        """
        changed = self.emotional.set_emotion(emotion, timestamp_ms)
        if changed:
            self.record_event("emotion", timestamp_ms, {"emotion": emotion})
        return changed

    def record_intent(self, intent: str, timestamp_ms: float) -> bool:
        """Record an intent transition reported by a decision layer.

        Updates current/previous intent and, ONLY when the intent really
        changed, appends a history event of kind ``"intent"``.

        Returns:
            True when the intent actually changed, False on no-op.
        """
        changed = self.emotional.set_intent(intent, timestamp_ms)
        if changed:
            self.record_event("intent", timestamp_ms, {"intent": intent})
        return changed

    def record_behavior(self, behavior: str, timestamp_ms: float) -> bool:
        """Record the currently-active behavior (reported by a caller).

        Re-reporting the active behavior is a no-op - the scalar fields
        stay untouched and no history event is appended (only real changes
        are transitions).

        Returns:
            True when the active behavior actually changed, False on no-op.
        """
        if behavior == self._active_behavior:
            return False
        self._previous_behavior = self._active_behavior
        self._active_behavior = behavior
        self.record_event("behavior", timestamp_ms, {"behavior": behavior})
        return True

    def record_blink(self, blink_type: str, timestamp_ms: float) -> None:
        """Record the most recent blink type and time.

        Stores ``last_blink_type`` / ``last_blink_ms`` and appends a
        history event of kind ``"blink"``.
        """
        self._last_blink_type = blink_type
        self._last_blink_ms = timestamp_ms
        self.record_event("blink", timestamp_ms, {"blink_type": blink_type})

    def record_attention(
        self, target: Optional[Tuple[float, float]], timestamp_ms: float
    ) -> None:
        """Record the current attention target (x, y) or its release (``None``).

        Changing the target (or releasing it) restarts the attention
        persistence timer. The attention target *history* is queryable via
        ``history_of_kind("attention")``.
        """
        if target != self._attention_target:
            self._attention_target = target
            self._attention_since_ms = timestamp_ms
        self.record_event("attention", timestamp_ms, {"target": target})

    def record_recovery(self, recovery_state: str, timestamp_ms: float) -> None:
        """Record the current recovery-state label (e.g. "settling")."""
        self._recovery_state = recovery_state
        self.record_event("recovery", timestamp_ms, {"recovery": recovery_state})

    def mark_interaction(self, timestamp_ms: float) -> None:
        """Touch the "last interaction" timestamp (caller-driven heartbeat).

        Does NOT append a history event - use ``record_event`` for events
        that must be queryable.
        """
        self._last_interaction_ms = max(self._last_interaction_ms, timestamp_ms)

    # ------------------------------------------------------------------
    # Query API - pure reads; memory never decides or acts.
    # ------------------------------------------------------------------

    def recent_history(
        self, n: Optional[int] = None, now_ms: Optional[float] = None
    ) -> list[InteractionEvent]:
        """Most recent ``n`` history events, newest first (all if ``n`` is None)."""
        return self.history.recent(n=n, now_ms=now_ms)

    def history_of_kind(
        self, kind: str, n: Optional[int] = None, now_ms: Optional[float] = None
    ) -> list[InteractionEvent]:
        """Most recent ``n`` events of one kind, newest first."""
        return self.history.recent_of_kind(kind, n=n, now_ms=now_ms)

    def last_event_of_kind(
        self, kind: str, now_ms: Optional[float] = None
    ) -> Optional[InteractionEvent]:
        """Most recent event of one kind, or ``None``."""
        return self.history.last_of_kind(kind, now_ms=now_ms)

    def count_of_kind_since(
        self, kind: str, timestamp_ms: float, now_ms: Optional[float] = None
    ) -> int:
        """Number of events of one kind at or after ``timestamp_ms``."""
        return self.history.count_of_kind_since(kind, timestamp_ms, now_ms=now_ms)

    # -- cooldowns ------------------------------------------------------

    def start_cooldown(self, name: str, duration_ms: float, now_ms: float) -> None:
        """Start (or restart) a caller-named cooldown (e.g. "greeting")."""
        self.cooldowns.start(name, duration_ms, now_ms)

    def is_cooling(self, name: str, now_ms: float) -> bool:
        """True while the named cooldown is still active."""
        return self.cooldowns.is_active(name, now_ms)

    def cooldown_remaining_ms(self, name: str, now_ms: float) -> float:
        """Milliseconds remaining on the named cooldown (0 when inactive)."""
        return self.cooldowns.remaining_ms(name, now_ms)

    # -- persistence ----------------------------------------------------

    def attention_elapsed_ms(self, now_ms: float) -> float:
        """How long the current attention target has been held (0 when none)."""
        if self._attention_target is None:
            return 0.0
        return max(0.0, now_ms - self._attention_since_ms)

    def attention_persisted_for(self, window_ms: float, now_ms: float) -> bool:
        """True when the current attention target has been held >= ``window_ms``."""
        return self._attention_target is not None and self.attention_elapsed_ms(now_ms) >= window_ms

    def emotion_persisted_for(self, window_ms: float, now_ms: float) -> bool:
        """True when the current emotion has persisted >= ``window_ms``.

        Pure query - the caller decides what "persisted" implies.
        """
        return self.emotional.emotion_persisted_for(window_ms, now_ms)

    # -- scalar getters -------------------------------------------------

    @property
    def active_behavior(self) -> Optional[str]:
        """Currently-active behavior label, or ``None``."""
        return self._active_behavior

    @property
    def previous_behavior(self) -> Optional[str]:
        """Previously-active behavior label, or ``None``."""
        return self._previous_behavior

    @property
    def attention_target(self) -> Optional[Tuple[float, float]]:
        """Current attention target (x, y), or ``None`` when released."""
        return self._attention_target

    @property
    def recovery_state(self) -> Optional[str]:
        """Current recovery-state label, or ``None``."""
        return self._recovery_state

    @property
    def last_blink_type(self) -> Optional[str]:
        """Most recent blink type, or ``None``."""
        return self._last_blink_type

    @property
    def last_blink_ms(self) -> float:
        """Timestamp of the most recent blink."""
        return self._last_blink_ms

    @property
    def last_interaction_ms(self) -> float:
        """Timestamp of the most recent interaction."""
        return self._last_interaction_ms

    # ------------------------------------------------------------------
    # Lifecycle - resets clear runtime state, never configuration.
    # ------------------------------------------------------------------

    def clear_memory(self) -> None:
        """Clear ALL recorded runtime state (history, cooldowns, context).

        Configuration (caps, injected sub-components) is preserved - the
        memory object stays reusable for the next session.
        """
        self.history.clear()
        self.cooldowns.clear_all()
        self.emotional.reset()
        self._active_behavior = None
        self._previous_behavior = None
        self._attention_target = None
        self._attention_since_ms = 0.0
        self._recovery_state = None
        self._last_blink_type = None
        self._last_blink_ms = 0.0
        self._last_interaction_ms = 0.0

    def reset_session(self) -> None:
        """Reset for a new session - identical to ``clear_memory`` here.

        Kept as a distinct name so future versions can differentiate a hard
        power-on reset from a session boundary without API churn.
        """
        self.clear_memory()

    def snapshot(self, now_ms: float) -> MemorySnapshot:
        """Read-only view of the current memory state (logging/debugging).

        Args:
            now_ms: caller-supplied clock used to list active cooldowns.
                REQUIRED - memory never guesses the current time, so the
                cooldown view is always accurate.
        """
        return MemorySnapshot(
            emotion=self.emotional.emotion,
            previous_emotion=self.emotional.previous_emotion,
            intent=self.emotional.intent,
            previous_intent=self.emotional.previous_intent,
            active_behavior=self._active_behavior,
            previous_behavior=self._previous_behavior,
            attention_target=self._attention_target,
            recovery_state=self._recovery_state,
            last_blink_type=self._last_blink_type,
            last_interaction_ms=self._last_interaction_ms,
            history_size=len(self.history),
            active_cooldowns=tuple(self.cooldowns.active_names(now_ms)),
        )


__all__ = ["BehaviorMemory", "MemorySnapshot"]
