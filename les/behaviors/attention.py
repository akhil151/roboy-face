"""
Attention behavior contract.

The attention behavior expresses directed focus: looking toward an
attention target, holding gaze, and releasing it naturally.
"""

from __future__ import annotations

from . import Behavior, BehaviorContext
from ..timeline.timeline import TimelineEvent


class AttentionBehavior(Behavior):
    """Scaffold for the attention behavior.

    Future responsibilities (Phase 1):
        * react to an attention target present in BehaviorContext
        * plan look_at() engine commands toward the target (via TimelineEvent)
        * schedule saccade / hold / release phases of the gaze
    """

    name: str = "attention"
    priority: float = 0.6
    cooldown_ms: float = 800.0

    # TODO(LES-Phase-1): implement the evaluation rules below.

    def evaluate(self, ctx: BehaviorContext) -> float:
        """TODO: score how much the current attention target deserves focus."""
        ...

    def should_run(self, ctx: BehaviorContext) -> bool:
        """TODO: run when an attention target is present."""
        ...

    def plan(self, ctx: BehaviorContext) -> list[TimelineEvent]:
        """TODO: plan look-to-target / hold / release events."""
        ...

    def on_start(self) -> None:
        """TODO: hook - announce attention start."""
        ...

    def on_end(self) -> None:
        """TODO: hook - announce attention end."""
        ...


__all__ = ["AttentionBehavior"]
