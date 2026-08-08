"""
Natural Idle Decision Layer (LES-09A.1) - decision orchestration.

This module turns an ``IdleContext`` (situational snapshot) into an
``IdleDecision`` (what idle action - if any - the robot performs next, and
when it should next be consulted) using the configurable ``IdlePolicy``.

    Idle Context -> Idle Policy -> Idle Behavior -> Idle Decision

The output of this phase is the DECISION (and a thin ``BehaviorIntent``
mapping for the future integration layer). Nothing here touches the
Timeline, the Scheduler, the EngineDriver, or the animation engine - that
is LES-09A.2.

What this module owns
---------------------
* ``IdleContext`` - an immutable snapshot of everything idle may consider:
  caller-supplied time, emotion (+ confidence/stability), interaction mode,
  robot speaking / touch / face / gaze / tracking facts, the currently
  active behavior, and the last interaction time.
* ``IdleDecision`` - the outcome: an ``IdleAction``, the ``IdleTier`` it
  was decided under, a human-readable reason, and ``next_ms`` (the absolute
  caller-clock time at which the behavior should be consulted again).
* ``IdleBehavior`` - the orchestrator. It yields to higher-priority
  behavior, selects a tier from context, samples an action from weighted
  bands, spaces actions with bounded uniform-random timing, and records
  what happened.

What this module does NOT own
-----------------------------
* Policy VALUES live in ``IdlePolicy`` (idle_policy.py).
* Remembering what happened lives in ``BehaviorMemory`` (injected): idle
  decisions are recorded there as kind ``"idle"`` events, blinks as blink
  records, and cooldowns as named timers. When no memory is injected, a
  tiny bounded deque (max 8 entries) stands in ONLY for the anti-repetition
  working window - it is not a history store.

Architecture notes
------------------
* Caller-owned time: ``now_ms`` comes from the caller via ``IdleContext``.
  This module never reads any clock - there is no wall-clock API call
  anywhere in it (the caller owns time entirely).
* Determinism: all randomness flows through ONE injectable ``random.Random``.
  Given the same policy, context sequence, memory state, and seed, the
  decision sequence is reproducible. Production uses an unseeded Random;
  tests inject a seeded one.
* Anti-periodicity (behavior-spec v1.0 section 4.3): intervals are uniform
  within bands (never fixed), the previous non-blink action is not repeated
  when an alternative exists, and "nothing happens" is a first-class
  decision - long quiet periods are expected.
* High-priority safety (interaction-bible v1.0 Part 8.3): idle is a
  fallback, not a competitor. It yields to every behavior in
  ``IdlePolicy.yield_behavior_names`` and every non-idle interaction mode,
  and re-checks soon so it resumes cleanly when the behavior ends.
* The existing ``Behavior`` ABC (les/behaviors/__init__.py) is NOT used
  here on purpose: it is the BehaviorDirector's registry contract
  (evaluate / should_run / plan TimelineEvents). Planning timeline events is
  explicitly LES-09A.2. This module is the idle DECISION layer that
  LES-09A.2 will consume.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from ..director.behavior_director import BehaviorIntent
from ..memory.behavior_memory import BehaviorMemory
from ..personality.traits import PersonalityTraits
from ..world.interaction_state import InteractionMode
from .idle_policy import ActionBand, IdleAction, IdlePolicy, IdleTier


@dataclass(frozen=True)
class IdleContext:
    """Immutable situational snapshot the idle layer may consider.

    History/cooldown facts (recent blink, recent idle actions, cooldowns)
    are intentionally NOT duplicated here - the injected ``BehaviorMemory``
    is the single store of record and is queried at decision time.

    Attributes:
        now_ms: caller-supplied clock (the behavior never reads a clock).
        emotion: current internal emotion label (``None`` = neutral), e.g.
            "calm", "happy", "sad", "thinking", "sleepy", "surprised".
        emotion_confidence: how strongly the emotion is held, [0, 1].
        emotion_stability: how settled the emotion is, [0, 1].
        interaction_mode: current ``InteractionMode`` or ``None``.
        robot_speaking: whether the robot is currently speaking.
        touch_active: whether a touch is currently active.
        face_present: whether a face is currently detected.
        eye_contact: whether mutual eye contact currently exists.
        attention_target: normalized (x, y) attention target or ``None``.
        tracking_active: whether the tracker is currently running.
        tracking_lost: whether tracking is currently considered lost.
        active_behavior: the currently-active behavior label (from memory),
            e.g. "greeting", "listening", "idle".
        last_interaction_ms: caller-clock time of the last interaction.
        traits: current ``PersonalityTraits`` (influences activity,
            curiosity likelihood, expressiveness, calmness, focus).
    """

    now_ms: float
    emotion: Optional[str] = None
    traits: PersonalityTraits = field(default_factory=PersonalityTraits)
    emotion_confidence: float = 0.0
    emotion_stability: float = 0.0
    interaction_mode: Optional[InteractionMode] = None
    robot_speaking: bool = False
    touch_active: bool = False
    face_present: bool = False
    eye_contact: bool = False
    attention_target: Optional[Tuple[float, float]] = None
    tracking_active: bool = False
    tracking_lost: bool = False
    active_behavior: Optional[str] = None
    last_interaction_ms: float = 0.0


@dataclass(frozen=True)
class IdleDecision:
    """One idle decision: what to do and when to decide again.

    Attributes:
        action: the chosen ``IdleAction`` (NONE is a valid decision).
        tier: the ``IdleTier`` the decision was made under.
        reason: why this decision was made (e.g. "yield_active_behavior",
            "surprise_recovery", "quiet_period", "attentive_idle").
        next_ms: ABSOLUTE caller-clock time at which the caller should ask
            the behavior again (the quiet period between decisions).
        decided_at_ms: caller-clock time this decision was produced.
        payload: optional structured detail (e.g. the action name for
            observability); no animation content ever lives here.
    """

    action: IdleAction
    tier: IdleTier
    reason: str
    next_ms: float
    decided_at_ms: float = 0.0
    payload: Mapping[str, object] = field(default_factory=dict)


# Band used when a yield reason applies: idle re-checks soon so it can
# resume cleanly once the higher-priority behavior ends.
def _uniform_band(rng: random.Random, band: ActionBand) -> float:
    """Sample a uniform-random interval within a band (ms)."""
    return rng.uniform(band.min_ms, band.max_ms)


class IdleBehavior:
    """Decision orchestrator for the natural idle layer.

    Usage: construct with an optional policy / rng / memory, then call
    ``decide(IdleContext)`` whenever the caller wants a decision. The
    returned ``IdleDecision.next_ms`` tells the caller when to ask again;
    calling earlier yields a ``NONE`` "not_due" decision, so quiet periods
    are explicit and caller-driven.

    Args:
        policy: optional ``IdlePolicy`` (default policy if omitted).
        rng: optional injectable ``random.Random`` (deterministic under a
            seed). Defaults to an unseeded ``Random`` for production.
        memory: optional ``BehaviorMemory`` - the shared store of record
            for idle decisions, blinks, and cooldowns. When omitted, a
            bounded local deque (8 entries) stands in for the
            anti-repetition window only.
    """

    name: str = "idle"

    def __init__(
        self,
        policy: Optional[IdlePolicy] = None,
        rng: Optional[random.Random] = None,
        memory: Optional[BehaviorMemory] = None,
    ) -> None:
        self._policy = policy if policy is not None else IdlePolicy()
        self._rng = rng if rng is not None else random.Random()
        self._memory = memory
        # Operational decision state (no wall clock, no history store).
        self._next_due_ms: float = 0.0
        self._last_tier: IdleTier = IdleTier.ATTENTIVE
        # Anti-repetition working window; only used when no memory is
        # injected (with memory, recent actions are read back from it).
        self._recent_fallback: deque[str] = deque(maxlen=8)

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def decide(self, ctx: IdleContext) -> IdleDecision:
        """Produce the idle decision for the given context.

        Deterministic given the same policy / context / memory / seed.
        Never reads a clock: ``ctx.now_ms`` is the only time source.
        """
        now = ctx.now_ms
        policy = self._policy

        # Not due yet - the quiet period is still running. "Nothing
        # happens" is a legitimate decision (long stretches of doing
        # nothing are the point of idle).
        if now < self._next_due_ms:
            return IdleDecision(
                action=IdleAction.NONE,
                tier=self._last_tier,
                reason="not_due",
                next_ms=self._next_due_ms,
                decided_at_ms=now,
            )

        # 1) Yield to higher-priority behavior. Idle is a fallback, never a
        #    competitor (interaction-bible v1.0 Part 8.3).
        yield_reason = self._yield_reason(ctx)
        if yield_reason is not None:
            next_ms = now + _uniform_band(self._rng, policy.yield_recheck_ms)
            self._next_due_ms = next_ms
            return IdleDecision(
                action=IdleAction.NONE,
                tier=self._tier_for(ctx),
                reason=yield_reason,
                next_ms=next_ms,
                decided_at_ms=now,
            )

        tier = self._tier_for(ctx)
        self._last_tier = tier

        # 2) Surprise: allow recovery first - do NOT launch an idle action
        #    immediately (mission: "SURPRISED -> allow recovery first").
        if ctx.emotion == "surprised":
            next_ms = now + _uniform_band(self._rng, policy.surprise_quiet_ms)
            self._next_due_ms = next_ms
            return IdleDecision(
                action=IdleAction.NONE,
                tier=tier,
                reason="surprise_recovery",
                next_ms=next_ms,
                decided_at_ms=now,
            )

        # 3) Choose an action from the tier's weighted, bounded bands.
        action, reason = self._choose_action(ctx, tier)
        band = policy.band_for(tier, action)
        next_ms = now + _uniform_band(self._rng, band)
        # NONE is a transient "nothing happening" decision - it never
        # enters the anti-repetition window (blinks / sweeps / glances do).
        if action is not IdleAction.NONE:
            self._remember(action, tier, reason, now)
        self._next_due_ms = next_ms
        return IdleDecision(
            action=action,
            tier=tier,
            reason=reason,
            next_ms=next_ms,
            decided_at_ms=now,
            payload={"action": action.value, "tier": tier.value, "reason": reason},
        )

    def reset(self) -> None:
        """Clear decision state (clock resets to 0, tier back to attentive).

        Configuration (policy, rng, memory) is preserved.
        """
        self._next_due_ms = 0.0
        self._last_tier = IdleTier.ATTENTIVE
        self._recent_fallback.clear()

    # ------------------------------------------------------------------
    # LES-09A.2 handoff (decision layer only - no timeline/engine calls).
    # ------------------------------------------------------------------

    def to_behavior_intent(self, decision: IdleDecision) -> BehaviorIntent:
        """Map an idle decision onto a ``BehaviorIntent`` for the future
        integration layer.

        This is the phase boundary: LES-09A.2 will feed this intent into
        the Timeline -> Scheduler -> EngineDriver pipeline. This method only
        translates the decision into the existing intent vocabulary - it
        never schedules or executes anything.
        """
        tier_tag = decision.tier.value
        if decision.action is IdleAction.NONE:
            variant = tier_tag
        else:
            variant = f"{tier_tag}_{decision.action.value}"
        duration = max(500.0, decision.next_ms - decision.decided_at_ms)
        return BehaviorIntent(
            behavior_name="idle",
            priority=0.30,
            urgency=0.30,
            variant=variant,
            interruptible=True,
            recovery_behavior="idle",
            suggested_duration_ms=duration,
            reason=f"idle:{decision.reason}",
            confidence=0.50,
            expires_ms=decision.next_ms,
            continuation_allowed=True,
            cancellation_allowed=True,
            transition_recommendation=None,
        )

    # ------------------------------------------------------------------
    # Yield / tier selection
    # ------------------------------------------------------------------

    def _yield_reason(self, ctx: IdleContext) -> Optional[str]:
        """Why idle must yield right now (None = idle may proceed)."""
        policy = self._policy

        if ctx.active_behavior in policy.yield_behavior_names:
            return "yield_active_behavior"

        mode = ctx.interaction_mode
        if mode is not None and mode.value in policy.yield_mode_values:
            return "yield_interaction_mode"

        if ctx.robot_speaking:
            return "yield_robot_speaking"

        if ctx.touch_active:
            return "yield_touch"

        return None

    def _tier_for(self, ctx: IdleContext) -> IdleTier:
        """Select the idle tier from the current context.

        Rules (behavior-spec v1.0 section 4.1):
        * sleep mode or a sleepy emotion        -> DEEP
        * long inactivity (no interaction for a while) -> DEEP
        * detected gaze (eye contact)           -> ENGAGED
        * anything else                         -> ATTENTIVE
        """
        policy = self._policy

        if ctx.interaction_mode is InteractionMode.SLEEP:
            return IdleTier.DEEP
        if ctx.emotion == "sleepy":
            return IdleTier.DEEP
        if (
            ctx.last_interaction_ms > 0.0
            and (ctx.now_ms - ctx.last_interaction_ms) >= policy.deep_idle_after_ms
        ):
            return IdleTier.DEEP
        if ctx.eye_contact:
            return IdleTier.ENGAGED
        return IdleTier.ATTENTIVE

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def _choose_action(self, ctx: IdleContext, tier: IdleTier) -> Tuple[IdleAction, str]:
        """Sample an action from the tier's weighted bands.

        Weights combine: base tier weight x emotion modifier x personality
        factor x activity scale, then cooldown/repeat filters, then a
        weighted random pick from the injectable RNG.
        """
        policy = self._policy
        now = ctx.now_ms

        raw: dict[IdleAction, float] = {}
        for action in IdleAction:
            weight = policy.weight_for(tier, action)
            if ctx.emotion is not None:
                weight *= policy.emotion_modifier_for(ctx.emotion, action)
            weight *= policy.action_trait_factor(action, ctx.traits)
            raw[action] = weight

        # Emotion stability damping: right after an emotional change the
        # robot is conservative (fewer idle actions).
        if ctx.emotion_stability < policy.min_stability_for_activity:
            for action in IdleAction:
                if action is IdleAction.NONE:
                    raw[action] *= 1.3
                else:
                    raw[action] *= 0.6

        # Activity scale from personality (energy vs calmness).
        scale = policy.activity_scale(ctx.traits)
        for action in IdleAction:
            if action is IdleAction.NONE:
                raw[action] /= scale
            else:
                raw[action] *= scale

        # Cooldown + recency filters.
        candidates: dict[IdleAction, float] = {}
        for action, weight in raw.items():
            if weight <= 0.0:
                continue
            if action is not IdleAction.NONE:
                if self._cooling(action, now):
                    continue
                if action is IdleAction.BLINK and self._blink_too_recent(now, tier):
                    continue
            candidates[action] = weight

        if not candidates:
            # Everything gated out - fall back to any positively-weighted
            # action (still bounded; cannot produce a runaway).
            candidates = {a: w for a, w in raw.items() if w > 0.0}
        if not candidates:
            return IdleAction.NONE, "quiet_period"

        # Anti-periodicity: never repeat the immediately-previous non-blink
        # action while an alternative exists (behavior-spec 4.3: no
        # identical sweeps in a row; blinks are band-spaced and repeat
        # naturally). Blink repeats stay allowed - docs want blinks 3-5 s.
        recent = self._recent_actions(now)
        if recent:
            prev = IdleAction(recent[0])
            if prev is not IdleAction.BLINK and prev in candidates and len(candidates) > 1:
                candidates.pop(prev, None)

        action = self._weighted_pick(candidates)
        reason = f"{tier.value}_idle"
        if action is IdleAction.NONE:
            reason = "quiet_period"
        return action, reason

    def _weighted_pick(self, candidates: Mapping[IdleAction, float]) -> IdleAction:
        """Pick one candidate proportionally to weight (injectable RNG)."""
        total = sum(max(0.0, w) for w in candidates.values())
        if total <= 0.0:
            return next(iter(candidates))
        roll = self._rng.random() * total
        for action, weight in candidates.items():
            roll -= max(0.0, weight)
            if roll < 0.0:
                return action
        return next(iter(candidates))

    # ------------------------------------------------------------------
    # Memory interaction (BehaviorMemory is the store of record)
    # ------------------------------------------------------------------

    def _cooling(self, action: IdleAction, now_ms: float) -> bool:
        """True when the action's cooldown is still active (memory)."""
        if self._memory is None:
            return False
        return self._memory.is_cooling(self._policy.cooldown_key(action), now_ms)

    def _blink_too_recent(self, now_ms: float, tier: IdleTier) -> bool:
        """True when the last recorded blink (any source) was too recent.

        Consults the shared blink history so idle blinks respect blinks
        already produced by other LES systems.
        """
        if self._memory is None:
            return False
        last = self._memory.last_blink_ms
        if last <= 0.0:
            return False
        band = self._policy.band_for(tier, IdleAction.BLINK)
        return (now_ms - last) < band.min_ms

    def _recent_actions(self, now_ms: float) -> list[str]:
        """Most-recent non-NONE idle action names (newest first).

        Reads from BehaviorMemory when injected (kind "idle" events);
        otherwise from the bounded local fallback window.
        """
        if self._memory is not None:
            events = self._memory.history_of_kind(
                "idle", n=self._policy.anti_repeat_window, now_ms=now_ms
            )
            return [
                str(e.payload["action"])
                for e in events
                if e.payload.get("action") and e.payload["action"] != IdleAction.NONE.value
            ]
        # deque is oldest -> newest; newest-first is required here. The
        # window matches the memory path (``anti_repeat_window``) so both
        # paths behave identically.
        window = self._policy.anti_repeat_window
        return [
            a
            for a in reversed(self._recent_fallback)
            if a != IdleAction.NONE.value
        ][:window]

    def _remember(
        self, action: IdleAction, tier: IdleTier, reason: str, now_ms: float
    ) -> None:
        """Record a performed idle action.

        With memory: record an "idle" history event (+ blink record and
        cooldown). Without memory: append to the bounded local fallback
        window only (anti-repetition working state, not a history store).
        """
        if self._memory is None:
            self._recent_fallback.append(action.value)
            return

        self._memory.record_event(
            "idle",
            now_ms,
            {"action": action.value, "tier": tier.value, "reason": reason},
        )
        if action is IdleAction.BLINK:
            self._memory.record_blink("soft", now_ms)
        self._memory.start_cooldown(
            self._policy.cooldown_key(action),
            self._policy.cooldown_for(action),
            now_ms,
        )


__all__ = ["IdleContext", "IdleDecision", "IdleBehavior"]
