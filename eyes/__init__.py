"""
Public API for the ELO Eye Animation Engine.

Exposes exactly the public interface specified in the project design:
    class EyeEngine:
        def set_state(self, state: str): ...
        def blink(self): ...
        def look_at(self, x: float, y: float): ...
        def run_forever(self): ...

All engine subsystems are composed internally and hidden behind this facade.
"""

from __future__ import annotations

from typing import Optional

from .engine.config import EngineConfig
from .engine.animation_engine import AnimationEngine
from .engine.state_machine import VALID_STATES
from .animations.base import AnimationState
from .animations.calm import CalmAnimation
from .animations.listening import ListeningAnimation
from .animations.thinking import ThinkingAnimation
from .animations.speaking import SpeakingAnimation
from .animations.happy import HappyAnimation
from .animations.caring import CaringAnimation
from .animations.sad import SadAnimation
from .animations.sleepy import SleepyAnimation
from .animations.surprised import SurprisedAnimation
from .animations.focus import FocusAnimation


class EyeEngine:
    """Public facade for the procedural eye animation engine."""

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self._engine = AnimationEngine(config)
        self._register_default_states()
        self._engine.initialize(initial_state="calm")

    def _register_default_states(self) -> None:
        sm = self._engine.state_machine
        cfg = self._engine.config
        sm.register("calm", CalmAnimation(cfg))
        sm.register("listening", ListeningAnimation(cfg))
        sm.register("thinking", ThinkingAnimation(cfg))
        sm.register("speaking", SpeakingAnimation(cfg))
        sm.register("happy", HappyAnimation(cfg))
        sm.register("caring", CaringAnimation(cfg))
        sm.register("sad", SadAnimation(cfg))
        sm.register("sleepy", SleepyAnimation(cfg))
        sm.register("surprised", SurprisedAnimation(cfg))
        sm.register("focus", FocusAnimation(cfg))

    def set_state(self, state: str) -> None:
        self._engine.set_state(state)

    def blink(self) -> None:
        self._engine.blink()

    def look_at(self, x: float, y: float) -> None:
        self._engine.look_at(x, y)

    def run_forever(self) -> None:
        self._engine.run_forever()

    @property
    def current_state(self) -> str:
        return self._engine.state_machine.current_state_name

    @property
    def valid_states(self) -> list[str]:
        return sorted(VALID_STATES)
