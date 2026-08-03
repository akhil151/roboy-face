"""
Animation state implementations for the ELO eye engine.

Phase 1: All 10 states are registered with placeholder implementations.
Phase 2A (this module): Premium expressive motion system - reusable primitives.
Phase 2B: 10 premium emotional states will inherit from ExpressiveAnimation.
"""

from .base import AnimationState
from .expressive import ExpressiveAnimation
from .calm import CalmAnimation
from .listening import ListeningAnimation
from .thinking import ThinkingAnimation
from .speaking import SpeakingAnimation
from .happy import HappyAnimation
from .caring import CaringAnimation
from .sad import SadAnimation
from .sleepy import SleepyAnimation
from .surprised import SurprisedAnimation
from .focus import FocusAnimation

__all__ = [
    "AnimationState",
    "ExpressiveAnimation",
    "CalmAnimation",
    "ListeningAnimation",
    "ThinkingAnimation",
    "SpeakingAnimation",
    "HappyAnimation",
    "CaringAnimation",
    "SadAnimation",
    "SleepyAnimation",
    "SurprisedAnimation",
    "FocusAnimation",
]
