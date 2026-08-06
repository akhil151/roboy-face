"""
Behavior Director - decides WHICH behavior the robot should run next.

The Behavior Director answers exactly one question:

    "What should the robot do next?"

NOT "what should the robot feel?" (that is the Emotion Director) and NOT
"how should the animation play?" (that is the Timeline Scheduler). It reads
World State, Behavior Memory, and the current internal emotional state from
the Emotion Director, applies the configurable Behavior Policy, and emits a
single ``BehaviorIntent`` per decision.

Pipeline position:

    World State -> Behavior Memory -> Emotion Director
                                          |
                                          v
    Behavior Policy -> Behavior Director -> Behavior Intent -> Timeline Scheduler (future)

The director NEVER schedules timelines, chooses animation frames, controls
blink timing, moves servos, controls the renderer, draws anything, tracks
the camera, or reads hardware. It only resolves WHICH behavior wins.

Data contracts (backward compatible):
    * ``BehaviorRequest`` - the original request model (kept; the enriched
      ``BehaviorIntent`` IS a ``BehaviorRequest`` with more fields, so the
      Timeline Scheduler's ``schedule(request: BehaviorRequest)`` keeps
      working unchanged).
    * ``BehaviorDirector`` - the interface (ABC, unchanged).
    * ``BehaviorIntentChange`` - one recorded intent transition.
    * ``BehaviorDirectorState`` - observable snapshot of the director.
    * ``DefaultBehaviorDirector`` - concrete orchestration.

Design notes
------------
* All time is internal: ``update(dt_ms)`` advances the director's own
  clock; memory cooldowns and behavior records use that same clock.
* The director writes its decision into Behavior Memory
  (``record_behavior`` + ``start_cooldown``) so memory stays the shared
  store of record and behavior history lives in ONE place.
* Anti-repetition / anti-freeze is layered: per-intent cooldowns,
  continuation bonus (finish what you started), urgency gap (only strong
  competitors interrupt), and per-rule ``max_hold_ms`` (nothing may run
  forever - "the robot never freezes").

Responsibility notes
--------------------
* Reads: ``WorldState`` (perception / attention / interaction facts).
* Reads: ``BehaviorMemory`` (cooldowns, behavior history).
* Reads: ``EmotionDirector`` (internal emotional state - emotion,
  confidence, stability, transitions).
* Writes: ``BehaviorMemory.record_behavior`` + ``start_cooldown`` (its own
  output channel only). Never reads or writes anything else.

Extension notes (LES-Phase-1+)
------------------------------
* A personality-derived policy can replace ``BehaviorPolicy`` wholesale
  (the director only reads the policy; it never writes it).
* New intents / arbitration rules / variants are added in the policy - no
  orchestration changes.
* The ``emotion`` reference may be swapped for any object exposing
  ``internal_state()`` returning an ``InternalEmotionState``-like value.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional

from ..config.defaults import DirectorConfig
from ..memory.behavior_memory import BehaviorMemory
from ..world.value_quality import ValueQuality
from ..world.world_state import WorldState
from .emotion_director import EmotionDirector
from .behavior_policy import BehaviorPolicy, BehaviorRule, VariantRotation


@dataclass(frozen=True)
class BehaviorIntent:
    """A request to run one behavior, produced by the Behavior Director.

    This IS the enriched ``BehaviorRequest`` model: the first three fields
    (``behavior_name`` / ``priority`` / ``urgency``) are identical to the
    original request the Timeline Scheduler consumes, so the scheduler's
    ``schedule(request: BehaviorRequest)`` keeps working unchanged.

    Attributes:
        behavior_name: the intent that won arbitration (Interaction Bible
            Part 6 vocabulary, e.g. ``"greeting"``, ``"listening"``).
        priority: the intent's final arbitration score in [0, 1].
        urgency: how pressing the intent is, in [0, 1] (1.0 on a fresh
            transition, decaying as it persists).
        variant: preferred variant label (e.g. ``"happy_a"``) - a NAME,
            never animation details.
        interruptible: whether the scheduler may stop this behavior for a
            more urgent one (derived from the winning rule).
        recovery_behavior: what the robot should fall back to when this
            behavior ends (e.g. ``"idle"``, ``"searching"``).
        suggested_duration_ms: how long the behavior should run before the
            scheduler checks again (rule ``max_hold_ms`` or default).
        reason: why this intent won (``"arbitration"``, ``"continuation"``,
            ``"interruption"``, ``"idle_fallback"``, ``"max_hold"``).
        confidence: how much the director trusts this choice, in [0, 1].
        expires_ms: the director clock at which this intent expires
            (``-1`` = never).
        continuation_allowed: whether re-selecting this intent next tick is
            appropriate (finish behaviors naturally).
        cancellation_allowed: whether the intent may be cancelled early by
            a change of situation.
        transition_recommendation: the intent the robot should move toward
            after this one (derived from the emotion pairing), or ``None``.
    """

    behavior_name: str
    priority: float
    urgency: float
    variant: Optional[str] = None
    interruptible: bool = True
    recovery_behavior: Optional[str] = None
    suggested_duration_ms: float = 0.0
    reason: str = "arbitration"
    confidence: float = 0.0
    expires_ms: float = -1.0
    continuation_allowed: bool = True
    cancellation_allowed: bool = True
    transition_recommendation: Optional[str] = None


# Backward-compatible alias: the scheduler's ``BehaviorRequest`` contract is
# exactly the original three fields of ``BehaviorIntent``.
BehaviorRequest = BehaviorIntent


@dataclass(frozen=True)
class BehaviorIntentChange:
    """One recorded intent transition (reported to listeners + memory)."""

    from_intent: Optional[str]
    to_intent: str
    reason: str
    timestamp_ms: float


@dataclass(frozen=True)
class BehaviorDirectorState:
    """Observable snapshot of the Behavior Director at one instant."""

    intent: Optional[str]
    variant: Optional[str]
    started_ms: float
    active_for_ms: float
    last_reason: Optional[str]
    last_change_ms: float


class BehaviorDirector(ABC):
    """Interface for behavior selection / prioritisation.

    Future responsibilities (Phase 1):
        * maintain a registry of the available behaviors
        * ask each behavior to evaluate the current context
          (see les.behaviors.Behavior.evaluate)
        * arbitrate between competing behaviors (priority + urgency + context)
        * emit at most one BehaviorRequest per decision tick
    """

    @abstractmethod
    def submit_intent(self, intent) -> None:
        """Hand the current emotion intent to the director."""
        ...

    @abstractmethod
    def select_next(self) -> Optional[BehaviorIntent]:
        """Return the next behavior to run, or None if nothing changes."""
        ...

    @abstractmethod
    def update(self, dt_ms: float) -> None:
        """Advance internal arbitration state. Called once per tick."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Clear arbitration state and fall back to the default behavior."""
        ...


class DefaultBehaviorDirector(BehaviorDirector):
    """Concrete Behavior Director: reads world + memory + emotion, applies
    the Behavior Policy, and emits at most one BehaviorIntent per decision.

    Orchestration (``update(dt_ms)`` advances the clock, ``select_next()``
    computes the intent):

    1. Read the current context: internal emotional state, world facts
       (person / eye contact / speech / touch / tracking), memory cooldowns.
    2. Score every policy rule whose preconditions currently hold.
    3. Gate candidates by cooldown (memory) - a cooling intent is
       ineligible, EXCEPT the currently-active intent (its own cooldown
       blocks re-selection after it ends, never its continuation).
    4. Apply the continuation bonus to the currently-active intent so
       behaviors finish naturally (persistence).
    5. Pick the winner:
         a. active intent exceeded its rule ``max_hold_ms`` -> yield even
            without a competitor (anti-freeze, checked FIRST so nothing
            runs forever - including non-interruptible behaviors)
         b. active intent still eligible + non-interruptible  -> continue
         c. active intent still eligible and within its persistence
            window -> continue unless a candidate beats it by the urgent
            gap (urgent interruption: alert, comforting, greeting)
         d. a candidate beats the active intent by the min change gap ->
            switch (arbitration)
         e. nothing eligible -> idle fallback
    6. On a change: record the behavior in memory, start its cooldown,
       fire listeners, emit the BehaviorIntent.

    Reasons used: ``"arbitration"`` (a new intent won), ``"continuation"``
    (the active intent kept running), ``"interruption"`` (an urgent intent
    displaced the active one), ``"idle_fallback"`` (nothing else eligible),
    ``"max_hold"`` (the active intent exceeded its cap).

    Args:
        world: the World State facade (read-only here).
        memory: the Behavior Memory facade (read + behavior recording).
        emotion: the Emotion Director (read-only: internal emotional state).
        policy: the BehaviorPolicy to apply (default policy if omitted).
        config: optional DirectorConfig (kept for symmetry; seeds nothing).
    """

    def __init__(
        self,
        world: WorldState,
        memory: BehaviorMemory,
        emotion: EmotionDirector,
        policy: Optional[BehaviorPolicy] = None,
        config: Optional[DirectorConfig] = None,
    ) -> None:
        self._world = world
        self._memory = memory
        self._emotion = emotion
        self._policy = policy if policy is not None else BehaviorPolicy.from_config(config)

        # Director-owned clock and arbitration bookkeeping.
        self._now_ms: float = 0.0
        self._active_intent: Optional[str] = None
        self._active_variant: Optional[str] = None
        self._active_since_ms: float = 0.0
        self._last_reason: Optional[str] = None
        self._last_change: Optional[BehaviorIntentChange] = None
        self._intent_listeners: list[Callable[[BehaviorIntentChange], None]] = []

    # ------------------------------------------------------------------
    # BehaviorDirector interface
    # ------------------------------------------------------------------

    def submit_intent(self, intent) -> None:
        """Accept an emotion intent (kept for interface compatibility).

        The concrete director reads the Emotion Director's internal state
        directly each tick; submitting an intent is a no-op for the default
        implementation but remains part of the interface so alternative
        directors can use it.
        """
        # Intentional no-op: state is read from ``self._emotion`` each tick.

    def update(self, dt_ms: float) -> None:
        """Advance the director by one tick.

        The clock advance lets cooldowns / persistence windows measured in
        memory and the director's own ``active_for_ms`` stay consistent.
        The intent itself is computed by ``select_next()``.
        """
        self._now_ms += max(0.0, dt_ms)

    def select_next(self) -> Optional[BehaviorIntent]:
        """Compute and return the BehaviorIntent that should run now.

        Emits at most ONE intent per call; the intent may equal the active
        one (continuation) or change it (arbitration / interruption /
        max-hold yield / idle fallback).
        """
        now = self._now_ms
        policy = self._policy

        emotion_state = self._emotion.internal_state()
        emotion = emotion_state.emotion

        scores = self._score_candidates(now, emotion)
        if not scores:
            # Nothing eligible at all - idle fallback (never freeze).
            return self._emit(
                intent=policy.idle_intent,
                priority=policy.priority_for(policy.idle_intent),
                reason="idle_fallback",
                now=now,
                emotion=emotion,
            )

        active = self._active_intent
        active_rule = policy.rule_for(active) if active is not None else None
        active_in_window = active is not None and (now - self._active_since_ms) < policy.continuation_window_ms

        # (a) Max-hold yield - anti-freeze, checked FIRST so even
        #     non-interruptible behaviors yield when their cap is hit
        #     (nothing may run forever). The active intent is forced OUT
        #     (its cooldown started on selection, so it cannot re-select
        #     itself): switch to the best other candidate, or fall back to
        #     idle when nothing else is eligible.
        if active is not None and active_rule is not None and active_rule.max_hold_ms > 0.0:
            if (now - self._active_since_ms) >= active_rule.max_hold_ms:
                others = {k: v for k, v in scores.items() if k != active}
                if others:
                    best, best_score = max(others.items(), key=lambda kv: kv[1])
                    return self._emit(
                        intent=best,
                        priority=best_score,
                        reason="arbitration",
                        now=now,
                        emotion=emotion,
                    )
                return self._emit(
                    intent=policy.idle_intent,
                    priority=policy.priority_for(policy.idle_intent),
                    reason="max_hold",
                    now=now,
                    emotion=emotion,
                )

        # (b) Non-interruptible active behavior continues.
        if active is not None and active_rule is not None and active_rule.non_interruptible:
            if active in scores:
                return self._emit(
                    intent=active,
                    priority=scores[active],
                    reason="continuation",
                    now=now,
                    emotion=emotion,
                )

        # (c) Urgent interruption: a candidate beats the active intent by a
        #     large margin even inside the continuation window.
        if active is not None and active_in_window and active in scores:
            best, best_score = max(scores.items(), key=lambda kv: kv[1])
            if best != active and best_score - scores[active] >= policy.urgent_interrupt_gap:
                return self._emit(
                    intent=best,
                    priority=best_score,
                    reason="interruption",
                    now=now,
                    emotion=emotion,
                )
            return self._emit(
                intent=active,
                priority=scores[active],
                reason="continuation",
                now=now,
                emotion=emotion,
            )

        # (d) General arbitration: the best candidate beats the active
        #     intent by the min change gap (or there is no active intent).
        best, best_score = max(scores.items(), key=lambda kv: kv[1])
        if active is None or active not in scores or (best_score - scores.get(active, 0.0)) >= policy.min_change_gap:
            return self._emit(
                intent=best,
                priority=best_score,
                reason="arbitration",
                now=now,
                emotion=emotion,
            )

        # (e) No change - the active intent stays.
        return self._emit(
            intent=active,
            priority=scores[active],
            reason="continuation",
            now=now,
            emotion=emotion,
        )

    def reset(self) -> None:
        """Clear arbitration state and fall back to idle.

        Clears the director's runtime decision state; cooldowns recorded in
        memory are cleared too (runtime state only) and the clock restarts.
        """
        self._now_ms = 0.0
        self._active_intent = None
        self._active_variant = None
        self._active_since_ms = 0.0
        self._last_reason = None
        self._last_change = None
        self._memory.cooldowns.clear_all()

    # ------------------------------------------------------------------
    # Director-specific API
    # ------------------------------------------------------------------

    def current_state(self) -> BehaviorDirectorState:
        """Observable snapshot of the current arbitration state."""
        return BehaviorDirectorState(
            intent=self._active_intent,
            variant=self._active_variant,
            started_ms=self._active_since_ms,
            active_for_ms=max(0.0, self._now_ms - self._active_since_ms) if self._active_intent else 0.0,
            last_reason=self._last_reason,
            last_change_ms=self._last_change.timestamp_ms if self._last_change is not None else 0.0,
        )

    def last_change(self) -> Optional[BehaviorIntentChange]:
        """The most recent intent change, or ``None`` if none yet."""
        return self._last_change

    def add_intent_listener(self, listener: Callable[[BehaviorIntentChange], None]) -> None:
        """Register a callback invoked with every intent change."""
        self._intent_listeners.append(listener)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _score_candidates(self, now: float, emotion: Optional[str]) -> dict[str, float]:
        """Score every policy rule whose preconditions currently hold.

        A rule scores: base priority + situational bonuses for each holding
        precondition + continuation bonus if it is the active intent within
        its persistence window + a small emotion-pairing bonus. Cooling
        intents (memory cooldown) are excluded.
        """
        world = self._world
        memory = self._memory
        policy = self._policy

        person_present = (
            world.perception.face_present.quality is ValueQuality.VALID
            and bool(world.perception.face_present.value)
        )
        eye_contact = (
            world.attention.eye_contact.quality is ValueQuality.VALID
            and bool(world.attention.eye_contact.value)
        )
        speech = (
            world.perception.speech_detected.quality is ValueQuality.VALID
            and bool(world.perception.speech_detected.value)
        )
        robot_speaking = (
            world.interaction.robot_speaking.quality is ValueQuality.VALID
            and bool(world.interaction.robot_speaking.value)
        )
        touch = (
            world.interaction.touch_active.quality is ValueQuality.VALID
            and bool(world.interaction.touch_active.value)
        )
        face_lost = (
            world.attention.tracking_active.quality is ValueQuality.VALID
            and bool(world.attention.tracking_active.value)
            and world.attention.tracking_lost.quality is ValueQuality.VALID
            and bool(world.attention.tracking_lost.value)
        )

        bonus = policy.condition_bonus
        scores: dict[str, float] = {}

        for rule in policy.intent_rules:
            # Cooldown gate. The ACTIVE intent is exempt: its own cooldown
            # (started when it was selected) must not block continuation - a
            # cooldown prevents RE-selection after a behavior ends, not the
            # behavior finishing naturally.
            if rule.intent != self._active_intent and memory.is_cooling(rule.intent, now):
                continue

            # Precondition evaluation (self-sustaining rules ignore them).
            if not rule.self_sustaining:
                if rule.requires_person and not person_present:
                    continue
                if rule.requires_eye_contact and not eye_contact:
                    continue
                if rule.requires_speech and not speech:
                    continue
                if rule.requires_robot_speaking and not robot_speaking:
                    continue
                if rule.requires_touch and not touch:
                    continue
                if rule.requires_face_lost and not face_lost:
                    continue
                if rule.requires_emotion is not None and emotion != rule.requires_emotion:
                    continue
                if rule.requires_no_emotion and emotion is not None:
                    continue

            score = rule.priority
            if rule.requires_person and person_present:
                score += bonus.get("person", 0.0)
            if rule.requires_eye_contact and eye_contact:
                score += bonus.get("eye_contact", 0.0)
            if rule.requires_speech and speech:
                score += bonus.get("speech", 0.0)
            if rule.requires_robot_speaking and robot_speaking:
                score += bonus.get("robot_speaking", 0.0)
            if rule.requires_touch and touch:
                score += bonus.get("touch", 0.0)
            if rule.requires_face_lost and face_lost:
                score += bonus.get("face_lost", 0.0)
            if rule.requires_emotion is not None and emotion == rule.requires_emotion:
                score += bonus.get("emotion", 0.0)

            # Emotion pairing: an intent that matches how the robot feels
            # gets a small boost (emotional continuity).
            if rule.intent == policy.intent_for_emotion(emotion):
                score += bonus.get("emotion", 0.0)

            # Continuation bonus: finish what you started (persistence).
            if rule.intent == self._active_intent and (now - self._active_since_ms) < policy.continuation_window_ms:
                score += policy.continuation_bonus

            scores[rule.intent] = score

        return scores

    def _emit(
        self,
        intent: str,
        priority: float,
        reason: str,
        now: float,
        emotion: Optional[str],
    ) -> BehaviorIntent:
        """Produce the BehaviorIntent, recording any intent change."""
        policy = self._policy
        rule = policy.rule_for(intent)

        changed = intent != self._active_intent
        if changed:
            from_intent = self._active_intent
            self._active_intent = intent
            self._active_since_ms = now
            self._last_reason = reason
            self._memory.record_behavior(intent, now)
            self._memory.start_cooldown(intent, policy.cooldown_for(intent), now)
            self._last_change = BehaviorIntentChange(
                from_intent=from_intent, to_intent=intent, reason=reason, timestamp_ms=now
            )
            for listener in self._intent_listeners:
                listener(self._last_change)

        variant = self._select_variant(intent, changed, now)
        self._active_variant = variant

        active_for = max(0.0, now - self._active_since_ms)
        urgency = 1.0 if changed else max(0.2, 1.0 - active_for / 5000.0)
        duration = rule.max_hold_ms if rule is not None and rule.max_hold_ms > 0.0 else policy.continuation_window_ms

        return BehaviorIntent(
            behavior_name=intent,
            priority=priority,
            urgency=urgency,
            variant=variant,
            interruptible=not (rule is not None and rule.non_interruptible),
            recovery_behavior=policy.idle_intent if rule is None else policy.intent_for_emotion(emotion),
            suggested_duration_ms=duration,
            reason=reason,
            confidence=min(1.0, priority),
            expires_ms=now + duration,
            continuation_allowed=reason in ("continuation", "arbitration", "interruption"),
            cancellation_allowed=True,
            transition_recommendation=policy.intent_for_emotion(emotion),
        )

    def _select_variant(self, intent: str, changed: bool, now: float) -> Optional[str]:
        """Choose the variant preference for an intent (policy-driven).

        The director expresses a variant NAME and rotation STRATEGY only -
        never animation details (the Emotion Bible defines what each variant
        means; the scheduler maps names to sequences later).
        """
        policy = self._policy
        prefs = policy.variants_for(intent)
        if not prefs:
            return None

        # STICKY: keep the current variant while the same intent continues.
        if policy.variant_rotation is VariantRotation.STICKY:
            if not changed and self._active_variant in prefs:
                return self._active_variant
            return prefs[0]

        # Rotation base: the director's own last-emitted variant for this
        # intent (memory records behavior events, not variant choices, so
        # variant rotation is director-local state). Falls back to memory
        # history when the director has not emitted a variant yet.
        last = self._active_variant if self._active_variant in prefs else None
        if last is None:
            last_event = self._memory.last_event_of_kind("behavior", now_ms=now)
            if last_event is not None and isinstance(last_event.payload.get("variant"), str):
                last = last_event.payload["variant"]

        if policy.variant_rotation is VariantRotation.CYCLIC:
            if last in prefs:
                idx = (prefs.index(last) + 1) % len(prefs)
                return prefs[idx]
            return prefs[0]

        # AVOID_RECENT: choose the least-recently-used preference.
        for pref in prefs:
            if pref != last:
                return pref
        return prefs[0]


__all__ = [
    "BehaviorIntent",
    "BehaviorRequest",
    "BehaviorIntentChange",
    "BehaviorDirectorState",
    "BehaviorDirector",
    "DefaultBehaviorDirector",
]
