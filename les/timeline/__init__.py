"""
LES timeline package.

Owns the temporal machinery of LES:

    * timeline.py  - the behavior event queue (TimelineEvent / Timeline /
                     DefaultTimeline - bounded, deterministic, caller-owned
                     time).
    * scheduler.py - the boundary to the animation engine (EngineCommand /
                     EngineDriver / Scheduler) plus the concrete
                     DefaultScheduler with its plan registry (PlanStep /
                     BehaviorPlan / DEFAULT_BEHAVIOR_PLANS).
"""

from __future__ import annotations

from .timeline import DefaultTimeline, Timeline, TimelineEvent
from .scheduler import (
    DEFAULT_BEHAVIOR_PLANS,
    BehaviorPlan,
    DefaultScheduler,
    EngineCommand,
    EngineCommandName,
    EngineDriver,
    PlanStep,
    Scheduler,
    dispatch_command,
)

__all__ = [
    "Timeline",
    "TimelineEvent",
    "DefaultTimeline",
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
