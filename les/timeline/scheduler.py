"""
Behavior scheduler contracts and the default implementation.

The Scheduler is the BOUNDARY between LES and the animation engine. It
consumes ``BehaviorRequest`` objects, plans ``TimelineEvent`` objects on
a ``Timeline``, and emits ``EngineCommand`` objects that drive the
engine's stable public API.

The engine (``eyes/``, v1.0 STABLE) is referenced ONLY through the
``EngineDriver`` protocol - LES never imports or modifies the engine at
runtime. The type-only import below documents the exact engine types used.

Engine API surface LES relies on (stable since v1.0):
    * set_state(state, transition_ms)
    * blink()
    * trigger_blink_type(blink_type)
    * look_at(x, y)
    * step(dt_ms, speech_pulse)

``DefaultScheduler`` (LES-08) realizes the pipeline:

    BehaviorIntent / BehaviorRequest
        -> plan registry (behavior + variant -> PlanStep sequence)
        -> TimelineEvent per step (time-ordered, variant preserved)
        -> due events converted to EngineCommands (with delay support)
        -> deterministic drain / safe cancellation

The scheduler NEVER decides behavior (the Behavior Director already
arbitrated) and never invents animation geometry - plans use only the
documented engine vocabulary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Literal, Mapping, Optional, Protocol, Sequence, Tuple, TYPE_CHECKING, get_args

from ..config.defaults import TimelineConfig
from ..director.behavior_director import BehaviorRequest
from .timeline import DefaultTimeline, Timeline, TimelineEvent

if TYPE_CHECKING:
    from eyes.engine.blink_controller import BlinkType


EngineCommandName = Literal[
    "set_state",
    "blink",
    "trigger_blink_type",
    "look_at",
    "step",
]

# Runtime vocabulary guard, derived from the single source of truth
# (the ``EngineCommandName`` Literal) so the guard can never drift from
# the documented command set. The Scheduler will not translate events
# carrying anything else (no silent vocabulary expansion).
_COMMAND_NAMES: frozenset[str] = frozenset(get_args(EngineCommandName))


@dataclass(frozen=True)
class EngineCommand:
    """One imperative call into the animation engine."""

    command: EngineCommandName
    args: Tuple[object, ...] = ()
    delay_ms: float = 0.0


@dataclass(frozen=True)
class PlanStep:
    """One engine call within a behavior plan - a scheduled moment.

    Attributes:
        offset_ms: when the step fires, relative to behavior start.
        command: a documented ``EngineCommandName``.
        args: positional arguments for the engine call.
        delay_ms: extra relative delay applied on top of ``offset_ms``
            (the resulting command fires ``delay_ms`` after the step
            comes due). Supports delayed commands.
    """

    offset_ms: float
    command: EngineCommandName
    args: Tuple[object, ...] = ()
    delay_ms: float = 0.0


@dataclass(frozen=True)
class BehaviorPlan:
    """Authoring mapping: a behavior (+ variants) to its engine steps.

    Plans use ONLY the documented engine vocabulary - engine state names
    and blink names, never animation geometry (eye curvature, pupil
    geometry, etc.). The engine remains responsible for visual execution.

    Attributes:
        name: the behavior name this plan belongs to.
        steps: the base step sequence (used when no variant matches).
        variant_steps: optional per-variant step sequences, keyed by the
            variant label emitted by the Behavior Director (e.g.
            ``"happy_b"``). Variant identity is preserved - a variant is
            a NAME, never animation details.
    """

    name: str
    steps: Tuple[PlanStep, ...] = ()
    variant_steps: Mapping[str, Tuple[PlanStep, ...]] = field(default_factory=dict)

    def steps_for(self, variant: Optional[str]) -> Tuple[PlanStep, ...]:
        """The step sequence for ``variant`` (base steps as fallback)."""
        if variant is not None and variant in self.variant_steps:
            return self.variant_steps[variant]
        return self.steps


# ---------------------------------------------------------------------------
# Default plan registry.
#
# A conservative starter mapping from the Interaction Bible Part 6 intent
# library to its associated engine states (E1-E10 of the Emotion Bible),
# using only the documented engine vocabulary. Recovery is NOT baked in
# here: the director's ``recovery_behavior`` instruction is represented
# by the Scheduler (see ``DefaultScheduler.schedule``). Fully overridable
# by injecting a custom registry.
# ---------------------------------------------------------------------------

DEFAULT_BEHAVIOR_PLANS: Dict[str, BehaviorPlan] = {
    "greeting": BehaviorPlan(
        name="greeting",
        steps=(
            PlanStep(offset_ms=0.0, command="set_state", args=("happy", 350.0)),
            PlanStep(offset_ms=500.0, command="blink"),
        ),
    ),
    "listening": BehaviorPlan(
        name="listening",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("listening", 280.0)),),
    ),
    "responding": BehaviorPlan(
        name="responding",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("speaking", 250.0)),),
    ),
    "thinking": BehaviorPlan(
        name="thinking",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("thinking", 320.0)),),
    ),
    "playful": BehaviorPlan(
        name="playful",
        steps=(
            PlanStep(offset_ms=0.0, command="set_state", args=("happy", 350.0)),
            PlanStep(offset_ms=600.0, command="blink"),
        ),
    ),
    "celebrating": BehaviorPlan(
        name="celebrating",
        steps=(
            PlanStep(offset_ms=0.0, command="set_state", args=("happy", 350.0)),
            PlanStep(offset_ms=500.0, command="blink"),
        ),
    ),
    "alert": BehaviorPlan(
        name="alert",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("surprised", 180.0)),),
    ),
    "comforting": BehaviorPlan(
        name="comforting",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("caring", 450.0)),),
    ),
    "searching": BehaviorPlan(
        name="searching",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("thinking", 320.0)),),
    ),
    "confused": BehaviorPlan(
        name="confused",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("thinking", 320.0)),),
    ),
    "curious": BehaviorPlan(
        name="curious",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("thinking", 320.0)),),
    ),
    "waiting": BehaviorPlan(
        name="waiting",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("calm", 350.0)),),
    ),
    "idle": BehaviorPlan(
        name="idle",
        steps=(PlanStep(offset_ms=0.0, command="set_state", args=("calm", 350.0)),),
    ),
}


class EngineDriver(Protocol):
    """The minimal engine surface LES is allowed to call.

    Implemented by ``eyes.engine.AnimationEngine`` / ``eyes.EyeEngine``
    (both unchanged - the protocol only describes what LES needs).
    """

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        ...

    def blink(self) -> None:
        ...

    def trigger_blink_type(self, blink_type: "BlinkType") -> None:
        ...

    def look_at(self, x: float, y: float) -> None:
        ...

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> object:
        ...


class Scheduler(ABC):
    """Interface for translating behavior requests into engine commands.

    The Scheduler owns CONVERTING due timeline events into engine
    commands (and, through ``schedule``, planning a request's events).
    It never decides behavior - the Behavior Director already did.

    Responsibilities (LES-08):
        * attach to an EngineDriver (the tested boundary)
        * plan one or more TimelineEvents per BehaviorRequest
        * each tick: advance the timeline and emit EngineCommands for
          events that come due
        * preserve event ordering and timing, support delayed commands,
          allow deterministic draining
        * support safe cancellation / replacement of a pending timeline
    """

    @abstractmethod
    def attach(self, engine: EngineDriver) -> None:
        """Bind the scheduler to a running engine instance."""
        ...

    @abstractmethod
    def schedule(self, request: BehaviorRequest) -> None:
        """Accept a behavior request and plan its timeline events."""
        ...

    @abstractmethod
    def advance(self, dt_ms: float) -> list[EngineCommand]:
        """Advance scheduling state and return any due engine commands."""
        ...

    @abstractmethod
    def drain_commands(self) -> list[EngineCommand]:
        """Return and clear all pending engine commands."""
        ...

    @abstractmethod
    def cancel(self, behavior_name: Optional[str] = None) -> None:
        """Invalidate pending work - one behavior's, or all when ``None``."""
        ...


class DefaultScheduler(Scheduler):
    """Concrete Scheduler: request -> timeline events -> engine commands.

    Pipeline (LES-08):

        1. ``schedule(request)`` - the request is the director's decision;
           the scheduler never re-arbitrates. The plan registry maps
           ``(behavior_name, variant)`` to ``PlanStep`` sequences; each
           step becomes a time-ordered ``TimelineEvent`` whose payload
           preserves the variant label and the step's engine command.
           A recovery event (``set_state`` toward the director's
           ``recovery_behavior``) is appended when the director supplies
           one - the scheduler represents the instruction, it never
           invents recovery content. Re-scheduling the SAME behavior
           while its plan is still pending is a no-op (idempotent
           continuation); a DIFFERENT behavior replaces the pending
           timeline (interruption per the director's arbitration).
        2. ``advance(dt_ms)`` - moves the caller-owned clock, converts
           each due event into an ``EngineCommand`` (honouring
           ``delay_ms``), and returns every command that is now due, in
           order.
        3. ``drain_commands()`` - returns and clears the pending command
           buffer deterministically (flush, e.g. on shutdown).

    Variant identity is preserved on every planned event (``payload``).
    No randomness anywhere: identical inputs produce identical outputs.

    Args:
        timeline: the ``Timeline`` to use (a ``DefaultTimeline`` is
            created when omitted).
        plans: the plan registry to use (``DEFAULT_BEHAVIOR_PLANS`` when
            omitted). Injected registries fully replace the default.
        config: optional ``TimelineConfig`` seeding a created timeline.
    """

    def __init__(
        self,
        timeline: Optional[Timeline] = None,
        plans: Optional[Mapping[str, BehaviorPlan]] = None,
        config: Optional[TimelineConfig] = None,
    ) -> None:
        self._timeline: Timeline = (
            timeline if timeline is not None else DefaultTimeline(config=config)
        )
        self._plans: Mapping[str, BehaviorPlan] = (
            plans if plans is not None else DEFAULT_BEHAVIOR_PLANS
        )
        self._engine: Optional[EngineDriver] = None
        # Pending commands: (absolute due time, behavior name, command).
        self._pending: list[Tuple[float, str, EngineCommand]] = []
        self._active_behavior: Optional[str] = None

    # ------------------------------------------------------------------
    # Scheduler interface
    # ------------------------------------------------------------------

    def attach(self, engine: EngineDriver) -> None:
        """Bind the scheduler to a running engine instance."""
        self._engine = engine

    def schedule(self, request: BehaviorRequest) -> None:
        """Plan the request's timeline events (variant preserved).

        Replacement semantics: a request for the SAME behavior while its
        plan is still pending is a no-op (continuation); any other
        request cancels the pending timeline and command buffer first
        (the director already arbitrated the interruption). A behavior
        with no authored plan is dropped and the current plan (if any)
        keeps running - the scheduler never invents behavior.

        Bounded structures: planned events rejected by the timeline
        (beyond its horizon or at capacity) are simply not planned - a
        plan is bounded by the timeline's construction limits.
        """
        if self._active_behavior == request.behavior_name and not self._timeline.is_empty:
            return

        plan = self._plans.get(request.behavior_name)
        if plan is None:
            # Nothing authored to represent - the scheduler never invents
            # behavior for unknown names.
            return

        self._timeline.clear()
        self._pending.clear()
        self._active_behavior = request.behavior_name

        now = self._timeline.now_ms
        steps = plan.steps_for(request.variant)
        for step in steps:
            self._timeline.push(
                TimelineEvent(
                    behavior_name=request.behavior_name,
                    start_ms=now + step.offset_ms,
                    duration_ms=request.suggested_duration_ms,
                    priority=request.priority,
                    payload={
                        "variant": request.variant,
                        "command": step.command,
                        "args": step.args,
                        "delay_ms": step.delay_ms,
                    },
                )
            )

        # Represent the director's recovery instruction (if any) after
        # the behavior's planned span. Timing is preserved, never
        # invented: the director's duration budget (or the last planned
        # step, whichever is later).
        if request.recovery_behavior:
            self._timeline.push(
                TimelineEvent(
                    behavior_name=request.behavior_name,
                    start_ms=now + self._recovery_offset_ms(steps, request.suggested_duration_ms),
                    duration_ms=request.suggested_duration_ms,
                    priority=request.priority,
                    payload={
                        "variant": request.variant,
                        "command": "set_state",
                        "args": (self._state_for(request.recovery_behavior), 300.0),
                        "delay_ms": 0.0,
                    },
                )
            )

    def advance(self, dt_ms: float) -> list[EngineCommand]:
        """Advance time; return every engine command that is now due.

        Due timeline events are converted to commands (honouring each
        step's ``delay_ms``) and appended to the pending buffer; commands
        whose absolute due time has arrived are returned in order and
        removed. Commands returned here are DUE NOW - the scheduler has
        already waited out any delay (the ``delay_ms`` field is kept as
        metadata). ``drain_commands()`` flushes commands that may still
        be inside their delay. The caller owns time - ``dt_ms`` is the
        only clock.
        """
        self._timeline.advance(max(0.0, dt_ms))
        now = self._timeline.now_ms

        for event in self._timeline.due_events():
            command = self._to_command(event)
            self._pending.append((event.start_ms + command.delay_ms, event.behavior_name, command))

        ready: list[EngineCommand] = []
        kept: list[Tuple[float, str, EngineCommand]] = []
        for entry in self._pending:
            if entry[0] <= now:
                ready.append(entry[2])
            else:
                kept.append(entry)
        self._pending = kept
        return ready

    def drain_commands(self) -> list[EngineCommand]:
        """Return and clear ALL pending commands (due or not), in order.

        Deterministic flush used e.g. on shutdown or handoff to a caller
        that owns execution.
        """
        ready = [entry[2] for entry in self._pending]
        self._pending.clear()
        return ready

    def cancel(self, behavior_name: Optional[str] = None) -> None:
        """Invalidate pending work.

        With a behavior name: remove that behavior's pending timeline
        events AND already-converted commands. With ``None``: cancel
        everything. Never re-arbitrates - it only discards obsolete
        scheduled work.
        """
        if behavior_name is None:
            self._timeline.clear()
            self._pending.clear()
            self._active_behavior = None
            return
        self._timeline.cancel(behavior_name)
        self._pending = [entry for entry in self._pending if entry[1] != behavior_name]
        if self._active_behavior == behavior_name:
            self._active_behavior = None

    # ------------------------------------------------------------------
    # Engine boundary (tested interface - never imports eyes/face)
    # ------------------------------------------------------------------

    def apply_commands(
        self, commands: Sequence[EngineCommand], engine: Optional[EngineDriver] = None
    ) -> None:
        """Dispatch commands to an EngineDriver (attached or passed).

        This is the ONLY way LES talks to the engine: through the
        ``EngineDriver`` protocol, never through ``eyes`` / ``face``
        imports. Raises ValueError when no driver is available.
        """
        driver = engine if engine is not None else self._engine
        if driver is None:
            raise ValueError(
                "no EngineDriver attached - call attach(engine) or pass engine=..."
            )
        for command in commands:
            dispatch_command(driver, command)

    # ------------------------------------------------------------------
    # Observability (read-only)
    # ------------------------------------------------------------------

    @property
    def timeline(self) -> Timeline:
        """The scheduler's timeline."""
        return self._timeline

    @property
    def active_behavior(self) -> Optional[str]:
        """The behavior currently planned on the timeline."""
        return self._active_behavior

    @property
    def pending_count(self) -> int:
        """Number of commands waiting in the pending buffer."""
        return len(self._pending)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_command(self, event: TimelineEvent) -> EngineCommand:
        """Translate one scheduler-planned event into an EngineCommand.

        Events planned by ``schedule`` carry the step's engine command in
        their payload. Events without a documented command are rejected
        loudly - the scheduler never silently invents commands.
        """
        payload = event.payload
        command = payload.get("command")
        args = payload.get("args", ())
        delay_ms = payload.get("delay_ms", 0.0)
        if not isinstance(command, str) or command not in _COMMAND_NAMES:
            raise ValueError(
                f"timeline event for '{event.behavior_name}' carries an "
                f"unknown engine command: {command!r}"
            )
        if not isinstance(args, tuple):
            raise ValueError(
                f"timeline event for '{event.behavior_name}' carries non-tuple args: {args!r}"
            )
        return EngineCommand(command=command, args=args, delay_ms=float(delay_ms))

    def _recovery_offset_ms(self, steps: Tuple[PlanStep, ...], suggested_duration_ms: float) -> float:
        """When the recovery event fires: after the behavior's span."""
        last = max((step.offset_ms for step in steps), default=0.0)
        return max(suggested_duration_ms, last + 100.0)

    def _state_for(self, recovery_behavior: str) -> str:
        """The engine state the recovery behavior enters.

        Resolved through the plan registry (a behavior's entry state);
        falls back to ``"calm"`` (the documented neutral recovery state)
        when the behavior has no authored plan.
        """
        plan = self._plans.get(recovery_behavior)
        if plan is not None:
            for step in plan.steps:
                if step.command == "set_state" and step.args:
                    first = step.args[0]
                    if isinstance(first, str):
                        return first
        return "calm"


def dispatch_command(engine: EngineDriver, command: EngineCommand) -> None:
    """Execute one EngineCommand on an EngineDriver.

    The scheduler never imports the engine; it only calls the methods
    the ``EngineDriver`` protocol declares. An unknown command name or a
    driver lacking the method raises ValueError.
    """
    method = getattr(engine, command.command, None)
    if method is None:
        raise ValueError(f"engine driver has no method '{command.command}'")
    method(*command.args)


__all__ = [
    "EngineCommand",
    "EngineCommandName",
    "EngineDriver",
    "Scheduler",
    "PlanStep",
    "BehaviorPlan",
    "DEFAULT_BEHAVIOR_PLANS",
    "DefaultScheduler",
    "dispatch_command",
]
