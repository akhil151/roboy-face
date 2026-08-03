"""
Animation state base class.

Every emotional state is an Animation subclass providing:
- entry_pose(t, pose): initial pose tween at blend t in [0,1]
- loop_pose(dt, elapsed, pose): continuous contribution each frame
- exit_pose(t, pose): final pose tween at blend t in [0,1]

Each animation writes parameter targets to a provided EyePair "pose".
The AnimationMixer blends poses smoothly across state transitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


class AnimationState(ABC):
    name: str = "base"

    def __init__(self, config: "EngineConfig") -> None:
        self._config = config
        self._elapsed_ms: float = 0.0
        self._entry_duration_ms: float = 200.0
        self._exit_duration_ms: float = 200.0

    @property
    def state_name(self) -> str:
        return self.name

    @property
    def entry_duration_ms(self) -> float:
        return self._entry_duration_ms

    @property
    def exit_duration_ms(self) -> float:
        return self._exit_duration_ms

    def on_enter(self) -> None:
        self._elapsed_ms = 0.0

    def on_exit(self) -> None:
        pass

    @abstractmethod
    def entry_pose(self, t: float, pose: "EyePair") -> None:
        ...

    @abstractmethod
    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        ...

    @abstractmethod
    def exit_pose(self, t: float, pose: "EyePair") -> None:
        ...
