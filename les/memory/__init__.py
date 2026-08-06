"""
LES memory package - pure behavioral context and history storage.

This package is the ONLY LES subsystem that stores state without deciding.
It provides bounded interaction history, generic named cooldown timers,
emotional state tracking, and a ``BehaviorMemory`` facade that composes them.

Guarantees (design authority: Interaction Bible Part 4):
    * No pygame, ROS, servo, hardware, or animation-engine dependency.
    * No runtime imports of ``eyes``.
    * Time is caller-supplied - memory owns no clock.
    * Memory never decides, schedules, arbitrates, or executes.

Future extension (LES-Phase-1+):
    * New history kinds (touch, voice, ros, llm, battery, sensor) are
      recorded via ``BehaviorMemory.record_event`` with caller-chosen kind
      tags - no package redesign required.
"""

from __future__ import annotations

from .behavior_memory import BehaviorMemory, MemorySnapshot
from .cooldowns import CooldownEntry, CooldownTracker
from .emotional_state import EmotionalState
from .interaction_history import InteractionEvent, InteractionHistory

__all__ = [
    "BehaviorMemory",
    "MemorySnapshot",
    "CooldownEntry",
    "CooldownTracker",
    "EmotionalState",
    "InteractionEvent",
    "InteractionHistory",
]
