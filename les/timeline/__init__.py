"""
LES timeline package.

Owns the temporal machinery of LES:

    * timeline.py  - the behavior event queue (TimelineEvent / Timeline).
    * scheduler.py - the boundary to the animation engine (EngineCommand /
                     EngineDriver / Scheduler).

Interfaces only - no scheduling logic lives here yet.
"""

from __future__ import annotations

from .timeline import Timeline, TimelineEvent
from .scheduler import EngineCommand, EngineCommandName, EngineDriver, Scheduler

__all__ = [
    "Timeline",
    "TimelineEvent",
    "EngineCommand",
    "EngineCommandName",
    "EngineDriver",
    "Scheduler",
]
