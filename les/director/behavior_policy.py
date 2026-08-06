"""
Behavior policy for the LES Behavior Director.

The policy is the CONFIGURABLE RULES LAYER of the behavior pipeline:

    World State -> Behavior Memory -> Emotion Director
                                          |
                                          v
    Behavior Policy -> Behavior Director -> Behavior Intent

It contains only policy VALUES (priority ladder, arbitration rules,
cooldown / persistence / recovery windows, interruptibility, variant
rotation) and tiny pure accessors - no orchestration, no decisions, no
state. The Behavior Director (``behavior_director.py``) owns orchestration
and consults this policy for every rule it applies.

Design notes
------------
* Defaults are drawn from the authoritative design documents:
    - intent library + arbitration        (interaction-bible v1.0 Parts 6/8)
    - greeting / surprise cooldowns       (interaction-bible v1.0 Part 4)
    - emotional persistence windows       (behavior-spec v1.0 section 10.3)
    - emotion -> intent pairing           (emotion-bible v1.0, Mood Compass)
* The policy NEVER hardcodes any specific robot - it is a plain data object
  that can be replaced wholesale by a personality-derived policy later.
* Arbitration is expressed as declarative ``BehaviorRule`` entries
  (intent + base priority + situational preconditions). Adding or tuning a
  rule requires no orchestration changes - the director only reads rules.

Responsibility notes
--------------------
* This module holds VALUES ONLY. It must stay import-light (stdlib +
  ``les.config`` + ``les.world`` enums) so the policy can be swapped,
  serialized, or user-tuned without touching orchestration code.

Extension notes (LES-Phase-1+)
------------------------------
* Add new intents by appending a ``BehaviorRule`` (or adjusting the
  priority ladder) - no director changes needed.
* Add new situational inputs (LLM state, voice sentiment, battery) as new
  precondition flags or by reading ``WorldState.sensors`` - the rule model
  accepts any precondition flags the director knows how to evaluate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional

from ..config.defaults import BehaviorConfig, DirectorConfig
from ..world.interaction_state import InteractionMode


class VariantRotation(str, Enum):
    """How the director chooses among a behavior's named variants.

    Members:
        CYCLIC: step through the preference list in order (A, B, C, D, ...).
        AVOID_RECENT: skip variants used most recently (diversity bias).
        STICKY: keep the current variant while the behavior continues.
    """

    CYCLIC = "cyclic"
    AVOID_RECENT = "avoid_recent"
    STICKY = "sticky"


@dataclass(frozen=True)
class BehaviorRule:
    """One declarative arbitration rule: promote an intent in a situation.

    A rule says "when these preconditions hold, this intent is a candidate
    with this base priority" - the director computes the final score by
    adding the configured situational bonuses for every condition that
    currently holds.

    Attributes:
        intent: the intent name (Interaction Bible Part 6 vocabulary, e.g.
            ``"greeting"``, ``"listening"``, ``"comforting"``).
        priority: base priority in [0, 1] - the ladder position of the intent.
        requires_person: a face is currently detected.
        requires_eye_contact: mutual eye contact currently exists.
        requires_speech: speech is currently detected from the person.
        requires_robot_speaking: the robot is currently speaking.
        requires_touch: a touch is currently active.
        requires_face_lost: tracking is active but lost (searching).
        requires_emotion: the current internal emotion equals this label
            (e.g. ``"surprised"`` promotes ``"alert"``).
        requires_no_emotion: only eligible while the robot is emotionally
            neutral (e.g. ``"searching"``).
        self_sustaining: True when the intent is eligible without ANY
            external precondition (it can start on its own, e.g. idle,
            thinking). Precondition flags are then ignored.
        non_interruptible: once active, this intent may NOT be displaced by
            another intent (continuation wins; used for brief, atomic
            behaviors like greeting or speaking).
        max_hold_ms: hard cap on how long this intent may stay active
            (0 = no cap). After it, the intent yields even if nothing
            displaced it (anti-freeze rule).
    """

    intent: str
    priority: float
    requires_person: bool = False
    requires_eye_contact: bool = False
    requires_speech: bool = False
    requires_robot_speaking: bool = False
    requires_touch: bool = False
    requires_face_lost: bool = False
    requires_emotion: Optional[str] = None
    requires_no_emotion: bool = False
    self_sustaining: bool = False
    non_interruptible: bool = False
    max_hold_ms: float = 0.0


# ---------------------------------------------------------------------------
# Default arbitration ruleset (interaction-bible v1.0 Parts 6 & 8).
# ---------------------------------------------------------------------------

DEFAULT_INTENT_RULES: tuple[BehaviorRule, ...] = (
    # Priority 9 - interrupts everything (interaction-bible v1.0 Part 6).
    # ``alert`` sits BEFORE ``listening`` at the same base priority: on a
    # surprised + speech overlap both score 1.05 and the tie resolves by
    # rule order (alert wins - it is brief, non-interruptible, and surprise
    # outranks social responding in Part 8.2). Keep this order.
    BehaviorRule(intent="alert", priority=0.95, requires_emotion="surprised", non_interruptible=True, max_hold_ms=600.0),
    BehaviorRule(intent="listening", priority=0.95, requires_speech=True, max_hold_ms=60000.0),
    # Priority 8-9 - strong social intents.
    BehaviorRule(intent="comforting", priority=0.88, requires_touch=True, non_interruptible=True, max_hold_ms=1500.0),
    BehaviorRule(intent="responding", priority=0.85, requires_robot_speaking=True, non_interruptible=True, max_hold_ms=30000.0),
    BehaviorRule(intent="greeting", priority=0.80, requires_person=True, requires_eye_contact=True, non_interruptible=True, max_hold_ms=800.0),
    # Priority 7-6 - internal / shared-joy intents.
    BehaviorRule(intent="thinking", priority=0.70, requires_emotion="thinking", max_hold_ms=5000.0),
    BehaviorRule(intent="playful", priority=0.60, requires_emotion="happy", max_hold_ms=4000.0),
    BehaviorRule(intent="celebrating", priority=0.60, requires_emotion="happy", requires_speech=True, max_hold_ms=1200.0),
    # Priority 5-4 - lower social intents.
    BehaviorRule(intent="searching", priority=0.55, requires_face_lost=True, max_hold_ms=60000.0),
    BehaviorRule(intent="confused", priority=0.45, requires_no_emotion=True, max_hold_ms=2000.0),
    BehaviorRule(intent="curious", priority=0.40, requires_person=True, max_hold_ms=4000.0),
    # Priority 2 - neutral presence. NOT the fallback: idle is the default,
    # not a competitor (interaction-bible v1.0 Part 8.3), so the director's
    # ``idle_fallback`` path handles empty arbitration.
    BehaviorRule(intent="waiting", priority=0.30, requires_no_emotion=True, max_hold_ms=15000.0),
)

# Situational bonuses added per holding precondition (so a rule wins over
# its ladder position when the situation is strongly present).
DEFAULT_CONDITION_BONUS: Mapping[str, float] = {
    "person": 0.05,
    "eye_contact": 0.10,
    "speech": 0.10,
    "robot_speaking": 0.05,
    "touch": 0.15,
    "face_lost": 0.05,
    "emotion": 0.05,
    "no_emotion": 0.00,
}


@dataclass(frozen=True)
class BehaviorPolicy:
    """Configurable behavioral rules consulted by the Behavior Director.

    Attributes:
        intent_rules: the arbitration ruleset (see ``BehaviorRule``).
        condition_bonus: situational score bonus per holding precondition.
        idle_intent: the fallback intent used when nothing else is eligible.
        cooldown_ms: default cooldown applied to every intent when it ends
            (per-intent override: a rule's ``intent`` key in ``cooldown_overrides``).
        cooldown_overrides: per-intent cooldown overrides (e.g. greeting
            longer than idle).
        continuation_bonus: score bonus for the currently-active intent
            (favours finishing behaviors naturally).
        continuation_window_ms: how long after starting an intent the
            continuation bonus applies (persistence window).
        min_change_gap: a competing intent must beat the active intent's
            score by at least this much to interrupt it.
        urgent_interrupt_gap: if a competing intent beats the active intent
            by at least this much, it may interrupt even mid-continuation
            (urgent interruptions - alert, comforting, greeting).
        recovery_ms: how long the director keeps its last decision state
            after a behavior ends before fully relaxing to idle.
        variant_rotation: how variants are chosen among ``variant_preferences``.
        variant_preferences: ordered list of variant labels per intent
            (e.g. ``{"happy": ["happy_a", "happy_b", ...]}``).
        emotion_to_intent: map from internal emotion labels to the intent
            they primarily pair with (emotion-bible pairing).
        neutral_intent: the intent chosen while the robot is emotionally
            neutral (typically ``"idle"`` or ``"searching"``).
    """

    intent_rules: tuple[BehaviorRule, ...] = DEFAULT_INTENT_RULES
    condition_bonus: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_CONDITION_BONUS))
    idle_intent: str = "idle"
    cooldown_ms: float = 1500.0
    cooldown_overrides: Mapping[str, float] = field(
        default_factory=lambda: {
            "greeting": 4000.0,
            "alert": 2500.0,
            "comforting": 3000.0,
            "idle": 200.0,
            "searching": 800.0,
        }
    )
    continuation_bonus: float = 0.12
    continuation_window_ms: float = 1200.0
    min_change_gap: float = 0.05
    urgent_interrupt_gap: float = 0.20
    recovery_ms: float = 800.0
    variant_rotation: VariantRotation = VariantRotation.CYCLIC
    variant_preferences: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    emotion_to_intent: Mapping[str, str] = field(
        default_factory=lambda: {
            "calm": "idle",
            "happy": "playful",
            "sad": "comforting",
            "thinking": "thinking",
            "listening": "listening",
            "speaking": "responding",
            "focus": "curious",
            "caring": "comforting",
            "sleepy": "waiting",
            "surprised": "alert",
        }
    )
    neutral_intent: str = "idle"

    # ------------------------------------------------------------------
    # Tiny pure accessors (no logic beyond reading configured values).
    # ------------------------------------------------------------------

    def rule_for(self, intent: str) -> Optional[BehaviorRule]:
        """The rule for an intent, or ``None`` if not configured."""
        for rule in self.intent_rules:
            if rule.intent == intent:
                return rule
        return None

    def cooldown_for(self, intent: str) -> float:
        """The cooldown duration for an intent (override or default)."""
        return self.cooldown_overrides.get(intent, self.cooldown_ms)

    def priority_for(self, intent: str) -> float:
        """The base priority of an intent (0.0 if unknown)."""
        rule = self.rule_for(intent)
        return rule.priority if rule is not None else 0.0

    def intent_for_emotion(self, emotion: Optional[str]) -> str:
        """The intent primarily paired with an emotion (neutral -> neutral_intent)."""
        if emotion is None:
            return self.neutral_intent
        return self.emotion_to_intent.get(emotion, self.neutral_intent)

    def variants_for(self, intent: str) -> tuple[str, ...]:
        """The preferred variant labels for an intent (empty = none)."""
        return self.variant_preferences.get(intent, ())

    @classmethod
    def from_config(
        cls,
        config: Optional[DirectorConfig] = None,
        behavior: Optional[BehaviorConfig] = None,
    ) -> "BehaviorPolicy":
        """Build a default policy, seeding cooldowns from ``BehaviorConfig``.

        Args:
            config: optional ``DirectorConfig`` (kept for symmetry with the
                emotion policy; values seed nothing yet).
            behavior: optional ``BehaviorConfig``; its
                ``default_cooldown_ms`` seeds the default cooldown.
        """
        if behavior is not None:
            return cls(cooldown_ms=behavior.default_cooldown_ms)
        return cls()


__all__ = [
    "BehaviorPolicy",
    "BehaviorRule",
    "VariantRotation",
    "DEFAULT_INTENT_RULES",
    "DEFAULT_CONDITION_BONUS",
]
