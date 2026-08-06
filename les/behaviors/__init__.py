"""
Behavior contracts.

A Behavior is a reusable unit of expressive intent that LES can schedule.
Behaviors:
    * evaluate a context and decide whether they should run
    * plan TimelineEvents that express the behavior through the engine

The base interface lives here; the concrete behavior modules (idle,
attention, curiosity, blink) subclass it and are re-exported from this
facade (same pattern as ``eyes/__init__.py``).

No behavior logic is implemented yet - see each module for TODO markers.
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
from .idle import IdleBehavior  # noqa: E402
from .attention import AttentionBehavior  # noqa: E402
from .curiosity import CuriosityBehavior  # noqa: E402
from .blink import BlinkBehavior  # noqa: E402

__all__ = [
    "BehaviorContext",
    "Behavior",
    "IdleBehavior",
    "AttentionBehavior",
    "CuriosityBehavior",
    "BlinkBehavior",
]
