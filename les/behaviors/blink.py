"""
Blink behavior contract.

The blink behavior owns natural blink scheduling at the LES level: when
blinks happen, which blink type is used, and how blinks interact with the
current emotion / behavior.

NOTE: blink execution itself already lives in the stable engine
(``eyes.engine.blink_controller``). LES only decides and requests; the
engine executes.
"""

from __future__ import annotations

from . import Behavior, BehaviorContext
from ..timeline.timeline import TimelineEvent


class BlinkBehavior(Behavior):
    """Scaffold for the blink behavior.

    Future responsibilities (Phase 1):
        * schedule natural blink timing from personality + context
        * choose blink types (soft / fast / double / slow / half) using the
          engine's BlinkType enum via EngineCommand
        * co-ordinate blinks with speech / emotional accents
    """

    name: str = "blink"
    priority: float = 0.9
    cooldown_ms: float = 2000.0

    # TODO(LES-Phase-1): implement the evaluation rules below.

    def evaluate(self, ctx: BehaviorContext) -> float:
        """TODO: score how much a blink is needed right now."""
        ...

    def should_run(self, ctx: BehaviorContext) -> bool:
        """TODO: run when a scheduled blink comes due."""
        ...

    def plan(self, ctx: BehaviorContext) -> list[TimelineEvent]:
        """TODO: plan a blink event (engine blink / trigger_blink_type)."""
        ...

    def on_start(self) -> None:
        """TODO: hook - announce blink start."""
        ...

    def on_end(self) -> None:
        """TODO: hook - announce blink end."""
        ...


__all__ = ["BlinkBehavior"]
