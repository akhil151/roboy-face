"""
LES world package - the robot's current understanding of the environment.

World State stores CURRENT facts only. It never stores history, never
stores cooldowns, never reasons, never predicts, never arbitrates, never
chooses behaviors, and never modifies emotions or memory.

Guarantees:
    * No pygame, no animation engine, no renderer, no hardware drivers,
      no ROS, no servo code, no OpenCV / MediaPipe / Whisper / LLM.
    * Time is caller-supplied - World State owns no clock.
    * Every fact carries an explicit quality (VALID / UNKNOWN /
      UNAVAILABLE / SENSOR_UNAVAILABLE / INVALID) so reads are never
      ambiguous.

World State vs Behavior Memory:
    * Behavior Memory (``les.memory``) answers "What happened?"
    * World State answers "What is true right now?"
"""

from __future__ import annotations

from .attention_state import AttentionState
from .interaction_state import InteractionMode, InteractionState
from .perception_state import PerceptionState
from .value_quality import SensorValue, ValueQuality
from .world_state import SessionStatus, SensorValueRegistry, WorldSnapshot, WorldState

__all__ = [
    "AttentionState",
    "InteractionMode",
    "InteractionState",
    "PerceptionState",
    "SensorValue",
    "ValueQuality",
    "SessionStatus",
    "SensorValueRegistry",
    "WorldSnapshot",
    "WorldState",
]
