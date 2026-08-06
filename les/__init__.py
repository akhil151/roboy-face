"""
LES - Living Expression System (architecture scaffold).

LES is the next-generation behaviour layer for the Roboy Face Engine.
It sits ABOVE the (stable, frozen) animation engine v1.0 and will DRIVE
it - it does NOT replace it and never imports it at runtime.

Future data flow (not yet wired - interface scaffolding only):

    Emotion Detector (external, future)
        |
        v
    LES Emotion Director .............. les/director/emotion_director.py
        |
        v
    LES Behavior Director ............. les/director/behavior_director.py
        |
        v
    Behavior Timeline ................. les/timeline/timeline.py
        |
        v
    Scheduler -> EngineCommands ...... les/timeline/scheduler.py
        |
        v
    Animation Engine (v1.0 STABLE) ... eyes/  (untouched)
        |
        v
    Renderer

STATUS
------
This package is ARCHITECTURE-ONLY. Every module contains documentation,
interfaces (ABC / Protocol / frozen dataclass contracts), type hints and
TODO markers - and NO behaviour implementation, NO algorithms, NO pygame.

Guarantees:
    * The animation engine (eyes/) is NOT modified, wrapped, or imported
      at runtime by LES.
    * No hardware, servo, ROS, or voice integration lives here.

See les/docs/README.md for the full architecture document.
"""

from __future__ import annotations

__version__ = "0.1.0"
__status__ = "scaffold"
__frozen__ = False  # LES is under active design - not frozen (unlike eyes v1.0).

# --- Config contracts -------------------------------------------------------
from .config.defaults import BehaviorConfig, DirectorConfig, LESConfig, TimelineConfig

# --- Personality contracts --------------------------------------------------
from .personality.traits import PersonalityTraits
from .personality.profiles import PersonalityProfile, PersonalityProvider

# --- Director contracts -----------------------------------------------------
from .director.emotion_director import (
    EmotionDirector,
    EmotionInput,
    EmotionIntent,
    EmotionTransition,
    InternalEmotionState,
    DefaultEmotionDirector,
)
from .director.emotion_policy import EmotionPolicy, DEFAULT_EMOTION_PRIORITY, DEFAULT_EMOTION_VALENCE
from .director.behavior_director import (
    BehaviorDirector,
    BehaviorIntent,
    BehaviorIntentChange,
    BehaviorDirectorState,
    BehaviorRequest,
    DefaultBehaviorDirector,
)
from .director.behavior_policy import BehaviorPolicy, BehaviorRule, VariantRotation

# --- Timeline / scheduler contracts -----------------------------------------
from .timeline.timeline import Timeline, TimelineEvent
from .timeline.scheduler import EngineCommand, EngineCommandName, EngineDriver, Scheduler

# --- Behaviour contracts ----------------------------------------------------
from .behaviors import (
    Behavior,
    BehaviorContext,
    IdleBehavior,
    AttentionBehavior,
    CuriosityBehavior,
    BlinkBehavior,
)

# --- Transition contracts ---------------------------------------------------
from .transitions.transition_director import TransitionDirector, TransitionSpec

# --- Memory contracts (behavior memory - pure state, no decisions) -----------
from .memory import (
    BehaviorMemory,
    MemorySnapshot,
    CooldownEntry,
    CooldownTracker,
    EmotionalState,
    InteractionEvent,
    InteractionHistory,
)

# --- World contracts (world state - current facts only, no decisions) ---------
from .world import (
    AttentionState,
    InteractionMode,
    InteractionState,
    PerceptionState,
    SensorValue,
    ValueQuality,
    SessionStatus,
    SensorValueRegistry,
    WorldSnapshot,
    WorldState,
)

__all__ = [
    # Config
    "LESConfig",
    "DirectorConfig",
    "TimelineConfig",
    "BehaviorConfig",
    # Personality
    "PersonalityTraits",
    "PersonalityProfile",
    "PersonalityProvider",
    # Directors
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
    # Timeline / scheduler
    "Timeline",
    "TimelineEvent",
    "EngineCommand",
    "EngineCommandName",
    "EngineDriver",
    "Scheduler",
    # Behaviours
    "Behavior",
    "BehaviorContext",
    "IdleBehavior",
    "AttentionBehavior",
    "CuriosityBehavior",
    "BlinkBehavior",
    # Transitions
    "TransitionDirector",
    "TransitionSpec",
    # Memory
    "BehaviorMemory",
    "MemorySnapshot",
    "CooldownEntry",
    "CooldownTracker",
    "EmotionalState",
    "InteractionEvent",
    "InteractionHistory",
    # World
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
