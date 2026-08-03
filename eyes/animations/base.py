"""
Animation state base class with auto-registration.

Every emotional state is an Animation subclass providing:
- entry_pose(t, pose): initial pose tween at blend t in [0,1]
- loop_pose(dt, elapsed, pose): continuous contribution each frame
- exit_pose(t, pose): final pose tween at blend t in [0,1]

Each animation writes parameter targets to a provided EyePair "pose".
The AnimationMixer blends poses smoothly across state transitions.

Auto-registration:
  Every concrete subclass of AnimationState is automatically added to the
  REGISTRY dict keyed by its ``name`` attribute.  StateMachine can then
  instantiate all registered classes via ``instantiate_registered(config)``
  so no manual per-state registration is needed in EyeEngine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Type

if TYPE_CHECKING:
    from ..engine.config import EngineConfig
    from ..engine.eye_pair import EyePair


REGISTRY: Dict[str, Type["AnimationState"]] = {}


class AnimationState(ABC):
    """Abstract base class for a single animation state.

    Subclasses MUST:
      * set ``name`` to one of the strings in VALID_STATES.
      * implement entry_pose / loop_pose / exit_pose.

    Subclasses inherit ``layout_geometry`` - a cached dict of
    ``(left_cx, right_cx, cy, base_radius)`` - computed once from
    ``config`` at construction so every subclass doesn't duplicate these
    four calculations.
    """

    name: str = "base"

    def __init_subclass__(cls, /, **kwargs) -> None:  # type: ignore[override]
        super().__init_subclass__(**kwargs)  # type: ignore[misc]
        if cls.name and cls.name != "base":
            REGISTRY[cls.name] = cls

    def __init__(self, config: "EngineConfig") -> None:
        self._config = config
        self._elapsed_ms: float = 0.0
        self._entry_duration_ms: float = 200.0
        self._exit_duration_ms: float = 200.0

        # Shared layout geometry - every subclass needs these four values.
        layout = config.layout
        display_w = config.display.width
        cx = display_w * 0.5
        self._left_cx: float = cx - layout.eye_spacing * 0.5
        self._right_cx: float = cx + layout.eye_spacing * 0.5
        self._cy: float = layout.center_y
        self._base_radius: float = layout.eye_radius

    # ------------------------------------------------------------------
    # Base-class metadata accessors
    # ------------------------------------------------------------------
    @property
    def state_name(self) -> str:
        return self.name

    @property
    def entry_duration_ms(self) -> float:
        return self._entry_duration_ms

    @property
    def exit_duration_ms(self) -> float:
        return self._exit_duration_ms

    @property
    def layout_left_cx(self) -> float:
        return self._left_cx

    @property
    def layout_right_cx(self) -> float:
        return self._right_cx

    @property
    def layout_center_y(self) -> float:
        return self._cy

    @property
    def layout_base_radius(self) -> float:
        return self._base_radius

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def on_enter(self) -> None:
        self._elapsed_ms = 0.0

    def on_exit(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Abstract pose interface
    # ------------------------------------------------------------------
    @abstractmethod
    def entry_pose(self, t: float, pose: "EyePair") -> None:
        ...

    @abstractmethod
    def loop_pose(self, dt_ms: float, elapsed_ms: float, pose: "EyePair") -> None:
        ...

    @abstractmethod
    def exit_pose(self, t: float, pose: "EyePair") -> None:
        ...


def registered_state_names() -> List[str]:
    """Return the sorted list of state names currently registered."""
    return sorted(REGISTRY.keys())


def instantiate_registered(
    config: "EngineConfig",
) -> Dict[str, AnimationState]:
    """Instantiate one instance of every registered AnimationState subclass.

    Used by EyeEngine / StateMachine to populate the full state set with
    a single call, removing the need to list all 10 states manually.
    """
    result: Dict[str, AnimationState] = {}
    for name, cls in REGISTRY.items():
        result[name] = cls(config)
    return result
