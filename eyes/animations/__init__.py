"""
Animation state implementations for the ELO eye engine.

Phase 1: All 10 states are registered with placeholder implementations.
Phase 2 will flesh out detailed emotional expressions (squash/stretch,
lid curvature, iris scale, bounce, etc.) for each state.
"""

from .base import AnimationState
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
