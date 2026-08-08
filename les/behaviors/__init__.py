"""
Behavior contracts.

A Behavior is a reusable unit of expressive intent that LES can schedule.
Behaviors:
    * evaluate a context and decide whether they should run
    * plan TimelineEvents that express the behavior through the engine

The base interface lives here; the concrete behavior modules (idle,
attention, curiosity, blink) subclass it and are re-exported from this
facade (same pattern as ``eyes/__init__.py``).

Note on idle (LES-09A.1): the NATURAL IDLE DECISION LAYER lives in
``idle_policy.py`` (policy values) and ``idle_behavior.py`` (decision
orchestration) - ``IdleBehavior`` there is the real decision layer and is
what ``from les.behaviors import IdleBehavior`` resolves to. The original
``les/behaviors/idle.py`` scaffold (a ``Behavior`` ABC subclass for the
BehaviorDirector's registry) remains untouched and is still importable
from ``les.behaviors.idle`` directly; it is a different contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

from ..director.emotion_director import EmotionIntent
from ..personality.traits import PersonalityTraits
from ..timeline.timeline import TimelineEvent


@dataclass(frozen=True)
class BehaviorContext:
    """Snapshot of everything a behavior may consider when deciding."""

    now_ms: float
    intent: Optional[EmotionIntent]
    traits: PersonalityTraits
    attention_target: Optional[Tuple[float, float]] = None  # (x, y) look target
    is_speaking: bool = False
    # TODO(LES-Phase-1): extend with sensor / social inputs as they appear.


class Behavior(ABC):
    """Interface implemented by every LES behavior.

    Subclasses MUST set ``name`` and implement the abstract methods below.
    """

    name: str = "base"
    priority: float = 0.0
    cooldown_ms: float = 0.0

    @abstractmethod
    def evaluate(self, ctx: BehaviorContext) -> float:
        """Return a relevance score in [0, 1] for the given context.

        Used by the BehaviorDirector to arbitrate between behaviors.
        Higher score = more appropriate right now.
        """
        ...

    @abstractmethod
    def should_run(self, ctx: BehaviorContext) -> bool:
        """Decide whether this behavior should run at all in this context."""
        ...

    @abstractmethod
    def plan(self, ctx: BehaviorContext) -> list[TimelineEvent]:
        """Translate the context into timeline events (no engine calls here)."""
        ...

    @abstractmethod
    def on_start(self) -> None:
        """Hook invoked when the behavior becomes active."""
        ...

    @abstractmethod
    def on_end(self) -> None:
        """Hook invoked when the behavior stops being active."""
        ...


# Concrete behavior modules - loaded here so
# ``from les.behaviors import IdleBehavior`` works out of the box.
from .attention import AttentionBehavior  # noqa: E402
from .curiosity import CuriosityBehavior  # noqa: E402
from .blink import BlinkBehavior  # noqa: E402

# Natural Idle Decision Layer (LES-09A.1). NOTE: the real idle decision
# layer is exported as ``IdleBehavior`` here (decision orchestration); the
# Behavior-ABC scaffold in ``les/behaviors/idle.py`` stays importable as
# ``les.behaviors.idle.IdleBehavior`` for director-registry use.
from .idle_behavior import (  # noqa: E402
    IdleBehavior,
    IdleContext,
    IdleDecision,
)
from .idle_policy import (  # noqa: E402
    ActionBand,
    IdleAction,
    IdlePolicy,
    IdleTier,
)

# Idle Execution Bridge (LES-09A.2) - executes IdleDecisions through the
# existing Timeline -> Scheduler -> EngineCommand -> EngineDriver pipeline.
# Purely behavioral: imports no pygame / eyes / face.
from .idle_execution import IdleExecutionBridge  # noqa: E402

__all__ = [
    "BehaviorContext",
    "Behavior",
    "AttentionBehavior",
    "CuriosityBehavior",
    "BlinkBehavior",
    "IdleBehavior",
    "IdleContext",
    "IdleDecision",
    "ActionBand",
    "IdleAction",
    "IdlePolicy",
    "IdleTier",
    "IdleExecutionBridge",
]
