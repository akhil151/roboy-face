"""
Curiosity behavior contract.

The curiosity behavior expresses exploratory interest: scanning the
environment, alternating attention between points of interest, and the
characteristic "curious tilt" - all expressed through the engine's
existing choreography helpers.
"""

from __future__ import annotations

from . import Behavior, BehaviorContext
from ..timeline.timeline import TimelineEvent


class CuriosityBehavior(Behavior):
    """Scaffold for the curiosity behavior.

    Future responsibilities (Phase 1):
        * decide when the robot should explore vs. stay still
        * plan look-scan and curious-tilt events
        * reuse the engine's choreography helpers
          (eyes.engine.choreography: look_scan_helper, curious_tilt_helper)
    """

    name: str = "curiosity"
    priority: float = 0.5
    cooldown_ms: float = 2000.0

    # TODO(LES-Phase-1): implement the evaluation rules below.

    def evaluate(self, ctx: BehaviorContext) -> float:
        """TODO: score how much the current context invites exploration."""
        ...

    def should_run(self, ctx: BehaviorContext) -> bool:
        """TODO: run when idle long enough / something new is present."""
        ...

    def plan(self, ctx: BehaviorContext) -> list[TimelineEvent]:
        """TODO: plan a scan / tilt exploration event."""
        ...

    def on_start(self) -> None:
        """TODO: hook - announce curiosity start."""
        ...

    def on_end(self) -> None:
        """TODO: hook - announce curiosity end."""
        ...


__all__ = ["CuriosityBehavior"]
