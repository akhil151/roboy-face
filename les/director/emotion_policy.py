"""
Emotion policy for the LES Emotion Director.

The policy is the CONFIGURABLE RULES LAYER of the emotion pipeline:

    World State -> Behavior Memory -> Emotion Policy -> Emotion Director
                                                          -> Internal Emotion State

It contains only policy VALUES (thresholds, windows, priorities) and tiny
pure accessors - no orchestration, no decisions, no state. The Emotion
Director (``emotion_director.py``) owns orchestration and consults this
policy for every rule it applies.

Design notes
------------
* Defaults are drawn from the authoritative design documents:
    - persistence window  >= 400 ms        (behavior-spec v1.0 section 10.3)
    - re-entry cooldown   ~= 1500 ms       (behavior-spec v1.0 section 10.3)
    - emotion priority ladder              (behavior-spec v1.0 section 10.4)
    - valence compass                      (emotion-bible v1.0, Mood Compass)
* The policy NEVER hardcodes any specific robot (no Aibi assumptions) - it
  is a plain data object that can be replaced wholesale by a personality-
  derived policy later (see ``EmotionPolicy.from_config`` and the mission's
  "future personalities can replace the policy" requirement).

Responsibility notes
--------------------
* This module holds VALUES ONLY. It must stay import-light (stdlib +
  ``les.config``) so the policy can be swapped, serialized, or user-tuned
  without touching orchestration code.

Extension notes (LES-Phase-1+)
------------------------------
* Add per-emotion confidence floors, custom transition matrices, or
  personality-scaled windows by subclassing or constructing a new
  ``EmotionPolicy`` - the director only reads, never writes, the policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from ..config.defaults import DirectorConfig

# Emotion priority ladder (behavior-spec v1.0 section 10.4):
# Surprised > Focus > Speaking > Thinking > Listening > Happy/Caring/Sad
# > Calm > Sleepy. Values are [0, 1]; used to bias the transition margin
# (higher-priority emotions displace current emotions more easily).
DEFAULT_EMOTION_PRIORITY: Mapping[str, float] = {
    "surprised": 1.00,
    "focus": 0.95,
    "speaking": 0.90,
    "thinking": 0.85,
    "listening": 0.80,
    "happy": 0.75,
    "caring": 0.70,
    "sad": 0.65,
    "calm": 0.40,
    "sleepy": 0.30,
}

# Valence compass (emotion-bible v1.0): +1 positive, -1 negative, 0 neutral.
DEFAULT_EMOTION_VALENCE: Mapping[str, int] = {
    "calm": 0,
    "happy": 1,
    "sad": -1,
    "thinking": 0,
    "listening": 1,
    "speaking": 0,
    "focus": 0,
    "caring": 1,
    "sleepy": 0,
    "surprised": 1,
}


@dataclass(frozen=True)
class EmotionPolicy:
    """Configurable emotional rules consulted by the Emotion Director.

    Attributes:
        min_confidence: detections below this are ignored as weak.
        persistence_ms: minimum time the current emotion must persist
            before a different emotion may replace it (spec 10.3).
        hysteresis_ms: window after a transition during which another
            transition is blocked (rapid-oscillation prevention).
        recovery_cooldown_ms: cannot re-enter the previous emotion within
            this window of having left it (A->B->A flicker prevention).
        transition_threshold: base confidence gap a candidate must beat the
            held emotion by.
        priority_weight: scales the priority difference into the margin.
        stability_ramp_ms: how long persistence takes to reach full
            stability (stability ramps 0 -> 1 over this window).
        confidence_decay_per_sec: how fast the held confidence decays per
            second when there is no valid detection (0 disables decay).
        neutral_emotion: the fallback emotion (calm).
        neutral_confidence: confidence assigned when recovering to neutral.
        neutral_fallback_after_ms: with no valid detection for this long,
            the current emotion recovers toward neutral.
        emotion_priority: per-emotion priority map (see module defaults).
        valence: per-emotion valence map (see module defaults).
        intent_ttl_ms: validity window of produced intents; -1 = until reset.
    """

    min_confidence: float = 0.60
    persistence_ms: float = 400.0
    hysteresis_ms: float = 400.0
    recovery_cooldown_ms: float = 1500.0
    transition_threshold: float = 0.02
    priority_weight: float = 0.02
    stability_ramp_ms: float = 2000.0
    confidence_decay_per_sec: float = 0.15
    neutral_emotion: str = "calm"
    neutral_confidence: float = 0.50
    neutral_fallback_after_ms: float = 2000.0
    emotion_priority: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_EMOTION_PRIORITY)
    )
    valence: Mapping[str, int] = field(
        default_factory=lambda: dict(DEFAULT_EMOTION_VALENCE)
    )
    intent_ttl_ms: float = -1.0

    # ------------------------------------------------------------------
    # Tiny pure accessors (no logic beyond reading configured values).
    # ------------------------------------------------------------------

    def priority_of(self, emotion: Optional[str]) -> float:
        """The configured priority of an emotion (0.5 unknown, 0.0 for None)."""
        if emotion is None:
            return 0.0
        return self.emotion_priority.get(emotion, 0.5)

    def valence_of(self, emotion: Optional[str]) -> int:
        """The configured valence of an emotion (0 unknown/neutral)."""
        if emotion is None:
            return 0
        return self.valence.get(emotion, 0)

    def transition_margin(self, current: Optional[str], candidate: str) -> float:
        """Confidence margin a candidate must clear to replace ``current``.

        The margin grows when the candidate is lower-priority than the
        current emotion (harder to displace) and shrinks when it is
        higher-priority (easier to displace).
        """
        priority_bias = (
            self.priority_of(current) - self.priority_of(candidate)
        ) * self.priority_weight
        return self.transition_threshold + priority_bias

    @classmethod
    def from_config(cls, config: Optional[DirectorConfig] = None) -> "EmotionPolicy":
        """Build a default policy, seeding hysteresis from ``DirectorConfig``.

        Args:
            config: optional ``DirectorConfig``; its ``intent_hysteresis_ms``
                seeds the persistence window (config values are LES defaults).
        """
        if config is None:
            return cls()
        return cls(persistence_ms=config.intent_hysteresis_ms)


__all__ = [
    "EmotionPolicy",
    "DEFAULT_EMOTION_PRIORITY",
    "DEFAULT_EMOTION_VALENCE",
]
