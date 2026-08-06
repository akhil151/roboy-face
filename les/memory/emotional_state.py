"""
Emotional state tracking for the LES Behavior Memory.

Records the robot's current and previous emotion and intent, plus the
timestamps needed for emotional-persistence queries (Interaction Bible
Part 4.6). This module ONLY records what callers report - it never changes
emotion on its own, never decides, and never acts.

Design notes
------------
* ``set_emotion`` / ``set_intent`` shift current -> previous and stamp the
  transition time. The caller (future Emotion / Behavior Director) decides
  WHAT to report; this module only remembers.
* Persistence is exposed as pure queries (``emotion_persisted_for``,
  ``emotion_changed_within``). The caller supplies the window and decides
  what to do with the answer.

Future extension notes (LES-Phase-1+)
-------------------------------------
* Add a confidence value per emotion if detectors provide it (the dataclass
  shape allows a new field without breaking existing consumers).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class EmotionalState:
    """Current + previous emotional and intentional context.

    Attributes:
        emotion: current dominant emotion label (``None`` = neutral).
        previous_emotion: emotion before the current one (``None`` = none yet).
        intent: current intent label (caller-defined, e.g. "greeting").
        previous_intent: intent before the current one.
        emotion_since_ms: when the current emotion was set.
        intent_since_ms: when the current intent was set.
        last_emotion_change_ms: time of the most recent emotion transition.
        last_intent_change_ms: time of the most recent intent transition.
    """

    emotion: Optional[str] = None
    previous_emotion: Optional[str] = None
    intent: Optional[str] = None
    previous_intent: Optional[str] = None
    emotion_since_ms: float = 0.0
    intent_since_ms: float = 0.0
    last_emotion_change_ms: float = 0.0
    last_intent_change_ms: float = 0.0

    def set_emotion(self, emotion: str, now_ms: float) -> bool:
        """Record a transition to ``emotion`` as reported by a caller.

        Re-reporting the current emotion is a no-op (keeps ``since``
        timestamps honest - persistence measures the *current* emotion).

        Returns:
            True when the emotion actually changed, False on no-op.
        """
        if emotion == self.emotion:
            return False
        self.previous_emotion = self.emotion
        self.emotion = emotion
        self.last_emotion_change_ms = now_ms
        self.emotion_since_ms = now_ms
        return True

    def set_intent(self, intent: str, now_ms: float) -> bool:
        """Record a transition to ``intent`` as reported by a caller.

        Returns:
            True when the intent actually changed, False on no-op.
        """
        if intent == self.intent:
            return False
        self.previous_intent = self.intent
        self.intent = intent
        self.last_intent_change_ms = now_ms
        self.intent_since_ms = now_ms
        return True

    def emotion_elapsed_ms(self, now_ms: float) -> float:
        """How long the current emotion has persisted (0 when neutral)."""
        if self.emotion is None:
            return 0.0
        return max(0.0, now_ms - self.emotion_since_ms)

    def emotion_persisted_for(self, window_ms: float, now_ms: float) -> bool:
        """True when the current emotion has persisted at least ``window_ms``.

        This is a pure query - the caller decides what "persisted" implies.
        """
        return self.emotion is not None and self.emotion_elapsed_ms(now_ms) >= window_ms

    def emotion_changed_within(self, window_ms: float, now_ms: float) -> bool:
        """True when the emotion last changed within the last ``window_ms``.

        Useful for hysteresis checks: the caller passes the minimum
        persistence window and interprets the answer.
        """
        return now_ms - self.last_emotion_change_ms <= window_ms

    def reset(self) -> None:
        """Return to a neutral state (used by clear / reset)."""
        self.emotion = None
        self.previous_emotion = None
        self.intent = None
        self.previous_intent = None
        self.emotion_since_ms = 0.0
        self.intent_since_ms = 0.0
        self.last_emotion_change_ms = 0.0
        self.last_intent_change_ms = 0.0


__all__ = ["EmotionalState"]
