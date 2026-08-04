"""
Public API for the ELO Eye Animation Engine.

Exposes exactly the public interface specified in the project design:
    class EyeEngine:
        def set_state(self, state: str): ...
        def blink(self): ...
        def look_at(self, x: float, y: float): ...
        def run_forever(self): ...

All engine subsystems are composed internally and hidden behind this facade.

State registration strategy:
  AnimationState subclasses auto-register themselves via ``__init_subclass__``.
  The 10 official states are imported here (so the modules load) and then the
  StateMachine registers them all via ``register_all_registered`` in a single
  call.  No per-class manual registration is required.
"""

from __future__ import annotations

__version__ = "1.0.0"
__frozen__ = True

from typing import Optional

from .engine.config import EngineConfig
from .engine.animation_engine import AnimationEngine
from .engine.state_machine import VALID_STATES

# Ensure every animation module is loaded so its __init_subclass__ fires
# and populates the REGISTRY.  Importing the package's __all__ is exactly
# what we want here - it guarantees 10 states are registered.
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
        """Register every official state via the auto-registry.

        Animation classes themselves (the subclasses imported above) populate
        the REGISTRY at import time via __init_subclass__.  Here we simply
        ask the StateMachine to instantiate each registered class with the
        engine's shared config and register them in one call.  There is no
        per-class duplication; the list is the canonical VALID_STATES set.
        """
        sm = self._engine.state_machine
        cfg = self._engine.config
        sm.register_all_registered(cfg)

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
