"""
Idle behavior contract (BehaviorDirector-registry scaffold).

NOTE (LES-09A.1): this module is SUPERSEDED by the Natural Idle Decision
Layer in ``les/behaviors/idle_policy.py`` / ``idle_behavior.py``. The real
idle DECISION layer is exported as ``les.behaviors.IdleBehavior``; this
class is the original Behavior-ABC scaffold for the BehaviorDirector's
registry (evaluate / should_run / plan TimelineEvents) and is kept
unchanged for that contract. New idle work should extend the decision
layer, not this scaffold.

The idle behavior represents the robot's resting expressive state - the
"calm" baseline that runs whenever no other behavior is more relevant.
"""

from __future__ import annotations

from . import Behavior, BehaviorContext
from ..timeline.timeline import TimelineEvent


class IdleBehavior(Behavior):
    """Scaffold for the idle behavior (BehaviorDirector registry contract).

    Superseded by ``les/behaviors/idle_behavior.IdleBehavior`` for the
    idle DECISION layer (LES-09A.1). Kept for the Behavior ABC registry.

    Future responsibilities (Phase 1):
        * return a low but non-zero relevance score so it always backstops
        * plan a "return to calm" event when the engine is in another state
        * schedule gentle breathing / micro-motion accents while idle
    """

    name: str = "idle"
    priority: float = 0.0
    cooldown_ms: float = 0.0

    # TODO(LES-Phase-1): implement the evaluation rules below.

    def evaluate(self, ctx: BehaviorContext) -> float:
        """TODO: score how appropriate idle is right now (should rarely be 0)."""
        ...

    def should_run(self, ctx: BehaviorContext) -> bool:
        """TODO: run when no higher-priority behavior is active."""
        ...

    def plan(self, ctx: BehaviorContext) -> list[TimelineEvent]:
        """TODO: plan a calm-state / micro-motion accent event."""
        ...

    def on_start(self) -> None:
        """TODO: hook - announce idle start."""
        ...

    def on_end(self) -> None:
        """TODO: hook - announce idle end."""
        ...


__all__ = ["IdleBehavior"]
