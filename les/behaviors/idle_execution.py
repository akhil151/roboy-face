"""
Idle Execution Bridge (LES-09A.2) - executes IdleDecisions through the
existing LES pipeline.

The Natural Idle Decision Layer (LES-09A.1) decides WHAT idle should do.
This module makes those decisions ACTUALLY HAPPEN through the pipeline
already proven in LES-08.5:

    IdleDecision
        -> BehaviorIntent (IdleBehavior.to_behavior_intent)
        -> DefaultScheduler.schedule() -> Timeline
        -> DefaultScheduler.advance() -> EngineCommand
        -> RealEngineDriver -> FaceEngine / AnimationEngine

It adds NO new execution mechanism: the existing ``DefaultScheduler``
remains the execution authority, and the ``EngineDriver`` protocol remains
the ONLY way LES talks to the engine. This module imports nothing from
pygame / eyes / face - it is pure behavior-layer code.

Per-action mapping (documented EngineCommand vocabulary only):
    NONE ............... nothing is scheduled - no dummy command, no state
                          change, no forced transition ("nothing happens"
                          is a first-class idle decision).
    BLINK .............. one ``blink`` command. The existing blink
                          controller remains authoritative - this bridge
                          never implements blink animation, and typed
                          blinks (``trigger_blink_type``) are deliberately
                          not used because the default driver
                          (``RealEngineDriver.for_face``) does not support
                          them.
    GAZE_DRIFT ......... one ``look_at(x, y)`` with a bounded target. The
                          engine owns the actual gaze movement (look
                          spring) - LES only provides the target.
    MICRO_CORRECTION ... one ``look_at(0.5, 0.5)`` - a deterministic
                          re-centering toward the neutral gaze point. This
                          is the smallest existing representation of a
                          "tiny re-centering of gaze".
    CURIOUS_GLANCE ..... ``look_at(glance)`` then ``look_at(0.5, 0.5)``
                          after a brief hold - look toward a target, hold,
                          return toward the neutral point.

Emotion preservation
--------------------
Idle is a BEHAVIORAL mode, not an emotional reset (behavior-spec v1.0
section 4). Idle plans NEVER issue ``set_state`` - a happy robot stays
happy while it idles, a sad robot stays sad. The director's recovery
instruction is therefore suppressed for idle intents
(``recovery_behavior=None``): the bridge would otherwise cause
``set_state("calm")`` to fire after every idle action, which is exactly
the "set_state('calm') just because the robot is idle" behaviour the phase
mission forbids.

Attention preservation
----------------------
When the context reports a concrete attention target or active tracking,
gaze-producing actions (GAZE_DRIFT / MICRO_CORRECTION / CURIOUS_GLANCE)
are NOT scheduled - idle never blindly overwrites a meaningful gaze
target ("attention always beats idle", interaction-bible v1.0 Part 8.3).
BLINK and NONE are unaffected (blinks do not move gaze). Eye contact
alone carries no target in the context and simply selects the ENGAGED tier
(an existing decision-layer rule) - no new attention rule is invented
here. ``tracking_lost`` on its own is also NOT attention-preserving:
there is no meaningful target to overwrite while lost (a searching
behavior owns that situation through the director), so idle drift stays
harmless.

Determinism / anti-periodicity
------------------------------
Gaze targets are a PURE function of the decision (tier, action,
``decided_at_ms``): identical decision sequences produce identical
targets, consecutive drifts differ over time (no periodic repetition), and
targets are always bounded inside normalized [0, 1]. Timing is NEVER
generated here - the decision layer's ``IdleDecision.next_ms`` remains the
only timing authority, and the caller (not this bridge) owns the clock.

Interruption / recovery
-----------------------
Interruption is the scheduler's existing replacement semantics: a
higher-priority ``BehaviorIntent`` scheduled while idle is pending replaces
the idle timeline (the director arbitrates; the scheduler only executes).
Recovery to idle is simply the next ``IdleDecision`` - the bridge keeps
scheduling idle intents whenever the caller asks, and idle itself yields
to active high-priority behavior through the decision layer.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Mapping, Optional, Tuple

from ..director.behavior_director import BehaviorIntent
from ..timeline.scheduler import (
    DEFAULT_BEHAVIOR_PLANS,
    BehaviorPlan,
    DefaultScheduler,
    PlanStep,
)
from .idle_behavior import IdleBehavior, IdleContext, IdleDecision
from .idle_policy import IdleAction, IdleTier

# ---------------------------------------------------------------------------
# Gaze geometry for idle look targets.
#
# * Targets are normalized (x, y) in [0, 1] - the LookController's native
#   coordinate space (it clamps to [0, 1] and springs toward the target).
# * DRIFT_AMPLITUDE scales how far idle drifts from the neutral center per
#   tier: attentive drifts the most, deep idle drifts the least (reduced
#   gaze movement during deep idle). [ENGINEERING RECOMMENDATION] - the
#   documents describe drift direction/frequency but not amplitudes.
# * The amplitudes keep every target well inside [0.32, 0.68] regardless of
#   the trig phase, so targets are always valid for the LookController.
# ---------------------------------------------------------------------------

DRIFT_AMPLITUDE: Mapping[IdleTier, float] = {
    IdleTier.ATTENTIVE: 0.18,
    IdleTier.ENGAGED: 0.14,
    IdleTier.DEEP: 0.08,
}

# How long a curious glance holds its target before returning to the
# neutral point. [ENGINEERING RECOMMENDATION] - the interaction bible
# describes a "brief hold"; 450 ms is the bridge's chosen value.
CURIOUS_HOLD_MS: float = 450.0

# The neutral gaze point idle returns to (bounded, valid, deterministic).
NEUTRAL_GAZE: Tuple[float, float] = (0.5, 0.5)

# Gaze-producing actions - suppressed while a meaningful attention target
# (or active tracking) exists so idle never overwrites attention.
_GAZE_ACTIONS = frozenset(
    {
        IdleAction.GAZE_DRIFT,
        IdleAction.MICRO_CORRECTION,
        IdleAction.CURIOUS_GLANCE,
    }
)


def idle_look_target(decision: IdleDecision, phase: float = 0.0) -> Tuple[float, float]:
    """A bounded, deterministic idle gaze target for a decision.

    Pure function of the decision - no RNG, no clock. The target is derived
    from the decision's ``decided_at_ms`` (so consecutive drifts differ -
    anti-periodicity), scaled by the tier's drift amplitude, and always
    clamped into normalized [0, 1] (valid for the existing LookController).

    Args:
        decision: the idle decision the target belongs to.
        phase: a per-action phase offset so different actions produce
            different deterministic target streams.
    """
    amplitude = DRIFT_AMPLITUDE.get(decision.tier, 0.14)
    t = decision.decided_at_ms
    x = 0.5 + amplitude * math.sin(t * 0.031 + phase)
    y = 0.5 + amplitude * math.cos(t * 0.027 + phase * 1.7)
    return (max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))


class IdleExecutionBridge:
    """Drives one IdleDecision through the existing LES execution pipeline.

    The bridge is the LES-09A.2 glue between the decision layer and the
    scheduler. It translates a decision into a ``BehaviorIntent`` (variant
    preserved), plans the idle variant's engine steps into the scheduler's
    plan registry, and schedules it. The caller then advances the scheduler
    (caller-owned time) and applies the resulting ``EngineCommand`` objects
    to a driver - exactly as LES-08.5 already does.

    Args:
        idle: the ``IdleBehavior`` decision layer whose
            ``to_behavior_intent`` mapping is used (the same instance the
            caller consults for decisions).
        plans: optional plan registry; defaults to a copy of
            ``DEFAULT_BEHAVIOR_PLANS`` with the ``"idle"`` plan replaced by
            this bridge's variant-based idle plan. Injected registries
            replace the default (the ``"idle"`` entry is still overridden).
    """

    def __init__(
        self,
        idle: IdleBehavior,
        plans: Optional[Mapping[str, BehaviorPlan]] = None,
    ) -> None:
        self._idle = idle
        # The bridge owns a MUTABLE plan registry (and its own
        # ``DefaultScheduler`` - the existing scheduler class, never a
        # parallel mechanism). Gaze actions carry per-decision targets, so
        # the current variant's steps are (re)registered just before each
        # schedule; the scheduler reads the registry at schedule() time.
        self._plans: dict[str, BehaviorPlan] = dict(
            plans if plans is not None else DEFAULT_BEHAVIOR_PLANS
        )
        self._variant_steps: dict[str, Tuple[PlanStep, ...]] = {}
        self._plans["idle"] = BehaviorPlan(
            name="idle", steps=(), variant_steps=self._variant_steps
        )
        self._scheduler = DefaultScheduler(plans=self._plans)

        # Observability (read-only).
        self._last_scheduled: Optional[BehaviorIntent] = None
        self._last_skipped_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def execute(
        self, decision: IdleDecision, ctx: Optional[IdleContext] = None
    ) -> Optional[BehaviorIntent]:
        """Execute one idle decision through the pipeline.

        Returns the ``BehaviorIntent`` that was scheduled, or ``None`` when
        nothing was scheduled (NONE decisions, and gaze actions suppressed
        for attention preservation). The returned intent is the exact
        object the scheduler received; ``last_skipped_reason`` explains why
        nothing was scheduled when ``None`` is returned for a non-NONE
        decision.

        The caller owns time: after this call, advance the scheduler
        (``scheduler.advance(dt_ms)``) and apply the resulting commands
        (``apply_commands``) - exactly the LES-08.5 loop.
        """
        ctx = ctx if ctx is not None else IdleContext(now_ms=decision.decided_at_ms)
        self._last_scheduled = None
        self._last_skipped_reason = None

        # NONE: "the robot does nothing". No dummy command, no state
        # change, no forced transition - the scheduler receives no plan.
        if decision.action is IdleAction.NONE:
            return None

        # Attention preservation: a concrete attention target or active
        # tracking must not be blindly overwritten by an idle gaze action
        # (interaction-bible v1.0 Part 8.3: attention always beats idle).
        # Blinks never move gaze, so they are always allowed.
        if decision.action in _GAZE_ACTIONS and self._attention_active(ctx):
            self._last_skipped_reason = "idle:attention_preserved"
            return None

        # Map decision -> intent (the variant label is derived HERE by the
        # decision layer's own mapping), then register the current variant's
        # concrete engine steps (gaze targets are decision-specific) and
        # schedule. The registry key is the intent's variant - exactly what
        # the scheduler will look up, so the variant can never drift.
        intent = self._intent_for(decision)
        self._variant_steps[intent.variant] = self._steps_for(decision)
        # A new idle action is a discrete event: it supersedes any still
        # pending previous idle plan (in practice the decision layer's
        # ``next_ms`` spacing already prevents overlap; the cancel is a
        # deterministic safety so tight loops can never drop an action).
        self._scheduler.cancel("idle")
        self._scheduler.schedule(intent)
        self._last_scheduled = intent
        return intent

    # ------------------------------------------------------------------
    # Scheduler access (the caller owns the loop and the clock)
    # ------------------------------------------------------------------

    def attach(self, engine) -> None:
        """Attach an ``EngineDriver`` to the bridge's scheduler."""
        self._scheduler.attach(engine)

    def apply_commands(self, commands) -> None:
        """Dispatch engine commands to the attached driver (scheduler API)."""
        self._scheduler.apply_commands(commands)

    @property
    def scheduler(self) -> DefaultScheduler:
        """The bridge's ``DefaultScheduler`` (the execution authority)."""
        return self._scheduler

    @property
    def last_scheduled(self) -> Optional[BehaviorIntent]:
        """The most recently scheduled idle intent (None if skipped)."""
        return self._last_scheduled

    @property
    def last_skipped_reason(self) -> Optional[str]:
        """Why the last non-NONE decision was not scheduled, if any."""
        return self._last_skipped_reason

    # ------------------------------------------------------------------
    # Mapping internals (engine vocabulary only - no geometry invention)
    # ------------------------------------------------------------------

    def _intent_for(self, decision: IdleDecision) -> BehaviorIntent:
        """The intent for a decision, with emotional recovery suppressed.

        ``recovery_behavior`` is cleared because idle is a behavioral mode,
        not an emotional reset: the scheduler's recovery machinery would
        otherwise emit ``set_state("calm")`` after every idle action and
        destroy the current emotion. Everything else (variant, priority,
        timing) comes verbatim from the decision layer's mapping.
        """
        return replace(self._idle.to_behavior_intent(decision), recovery_behavior=None)

    def _steps_for(self, decision: IdleDecision) -> Tuple[PlanStep, ...]:
        """The engine steps for an idle decision (documented verbs only)."""
        action = decision.action
        if action is IdleAction.BLINK:
            return (PlanStep(offset_ms=0.0, command="blink"),)
        if action is IdleAction.GAZE_DRIFT:
            return (
                PlanStep(
                    offset_ms=0.0, command="look_at", args=idle_look_target(decision, phase=0.0)
                ),
            )
        if action is IdleAction.MICRO_CORRECTION:
            return (PlanStep(offset_ms=0.0, command="look_at", args=NEUTRAL_GAZE),)
        if action is IdleAction.CURIOUS_GLANCE:
            return (
                PlanStep(
                    offset_ms=0.0,
                    command="look_at",
                    args=idle_look_target(decision, phase=2.1),
                ),
                PlanStep(
                    offset_ms=CURIOUS_HOLD_MS, command="look_at", args=NEUTRAL_GAZE
                ),
            )
        # NONE is filtered by ``execute`` before this is reached. Anything
        # unknown must fail LOUDLY - unsupported idle actions are reported,
        # never silently dropped (an action with no representation must
        # never produce an empty plan that does nothing).
        raise ValueError(
            f"idle action {action!r} has no EngineCommand representation - "
            "unsupported idle actions are reported loudly, never dropped"
        )

    @staticmethod
    def _attention_active(ctx: IdleContext) -> bool:
        """True when a concrete attention state would be overwritten.

        A concrete attention target or active tracking is a meaningful gaze
        state idle must not blindly overwrite. Eye contact alone carries no
        target in the context - it selects the ENGAGED tier through the
        existing decision-layer rule and is not treated as a target here.
        """
        return ctx.attention_target is not None or ctx.tracking_active


__all__ = [
    "IdleExecutionBridge",
    "idle_look_target",
    "DRIFT_AMPLITUDE",
    "CURIOUS_HOLD_MS",
    "NEUTRAL_GAZE",
]
