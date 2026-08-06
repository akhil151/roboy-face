"""
LES director package.

The top of the LES decision pipeline:

    * emotion_director  - turns external emotion detections into intents.
    * behavior_director - turns internal emotion into behavior intents
                          (arbitration, cooldowns, continuation, variants).
"""

from __future__ import annotations

from .emotion_director import (
    EmotionDirector,
    EmotionInput,
    EmotionIntent,
    EmotionTransition,
    InternalEmotionState,
    DefaultEmotionDirector,
)
from .emotion_policy import EmotionPolicy, DEFAULT_EMOTION_PRIORITY, DEFAULT_EMOTION_VALENCE
from .behavior_director import (
    BehaviorDirector,
    BehaviorIntent,
    BehaviorIntentChange,
    BehaviorDirectorState,
    BehaviorRequest,
    DefaultBehaviorDirector,
)
from .behavior_policy import BehaviorPolicy, BehaviorRule, VariantRotation

__all__ = [
    "EmotionDirector",
    "EmotionInput",
    "EmotionIntent",
    "EmotionTransition",
    "InternalEmotionState",
    "DefaultEmotionDirector",
    "EmotionPolicy",
    "DEFAULT_EMOTION_PRIORITY",
    "DEFAULT_EMOTION_VALENCE",
    "BehaviorDirector",
    "BehaviorIntent",
    "BehaviorIntentChange",
    "BehaviorDirectorState",
    "BehaviorRequest",
    "DefaultBehaviorDirector",
    "BehaviorPolicy",
    "BehaviorRule",
    "VariantRotation",
]
