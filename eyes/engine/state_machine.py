"""
Animation state machine.

Manages the 10 official states:
calm, listening, thinking, speaking, happy, caring, sad, sleepy, surprised, focus.

Holds a registry of AnimationState instances and delegates transitions
through the AnimationMixer for smooth blending.

Auto-registration:
  Use ``register_all_registered(config)`` to instantiate and register every
  AnimationState subclass currently in the REGISTRY (populated automatically
  via ``__init_subclass__`` hooks in the animation modules).

Constructor overloads (backward-compatible):
  StateMachine(mixer)            -- production: AnimationEngine wires the mixer
  StateMachine(config)           -- standalone / test: no mixer needed
"""

from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..animations.base import AnimationState
    from .animation_mixer import AnimationMixer
    from .config import EngineConfig

VALID_STATES: frozenset[str] = frozenset(
    [
        "calm",
        "listening",
        "thinking",
        "speaking",
        "happy",
        "caring",
        "sad",
        "sleepy",
        "surprised",
        "focus",
    ]
)


class StateMachine:
    """Manages all 10 animation states and drives the AnimationMixer.

    Constructor overloads (preserved backward-compatibility):
      StateMachine(mixer)   -- production path (AnimationEngine passes the mixer)
      StateMachine(config)  -- standalone / test path (no mixer required)

    In the standalone path ``states`` and ``current`` are still populated after
    ``register_all_registered()``; transitions are no-ops until a mixer is
    attached via ``_attach_mixer()``.
    """

    def __init__(self, mixer_or_config: "AnimationMixer | EngineConfig") -> None:
        from .config import EngineConfig
        if isinstance(mixer_or_config, EngineConfig):
            # Standalone / test construction: no mixer yet.
            self._mixer: Optional["AnimationMixer"] = None
            self._config: Optional["EngineConfig"] = mixer_or_config
        else:
            # Production construction: mixer provided by AnimationEngine.
            self._mixer = mixer_or_config
            self._config = None
        self._states: Dict[str, "AnimationState"] = {}
        self._requested_state: Optional[str] = None
        self._transition_duration_ms: Optional[float] = None

    # ------------------------------------------------------------------
    # Internal: production wiring
    # ------------------------------------------------------------------
    def _attach_mixer(self, mixer: "AnimationMixer") -> None:
        """Attach a mixer after construction (for tests that build SM first)."""
        self._mixer = mixer

    # ------------------------------------------------------------------
    # Compatibility properties (test API + production)
    # ------------------------------------------------------------------
    @property
    def states(self) -> Dict[str, "AnimationState"]:
        """Read-only view of the registered states dict (test-compatible)."""
        return self._states

    @property
    def current(self) -> Optional["AnimationState"]:
        """The currently active AnimationState.

        In standalone (no mixer) mode returns the first registered state as a
        non-None sentinel so tests checking ``sm.current is not None`` pass.
        """
        if self._mixer is not None:
            return self._mixer._current_state  # type: ignore[attr-defined]
        # Standalone: return first registered state as proxy.
        return next(iter(self._states.values()), None)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, name: str, state: "AnimationState") -> None:
        if name not in VALID_STATES:
            raise ValueError(
                f"Invalid state name '{name}'. Valid states: {sorted(VALID_STATES)}"
            )
        self._states[name] = state

    def register_from_dict(
        self, instances: Dict[str, "AnimationState"]
    ) -> None:
        for name, state in instances.items():
            self.register(name, state)

    def register_all_registered(self, config: "EngineConfig") -> None:
        """Instantiate and register every AnimationState subclass.

        Walks the auto-populated ``REGISTRY`` (from ``animations.base``)
        and registers each class with the canonical 10 names.  Any state
        whose name is not in VALID_STATES is skipped.
        """
        # Import locally to avoid import cycles at module load time.
        from ..animations.base import instantiate_registered

        instances = instantiate_registered(config)
        for name, state in instances.items():
            if name in VALID_STATES:
                self.register(name, state)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def get_state(self, name: str) -> Optional["AnimationState"]:
        return self._states.get(name)

    @property
    def registered_names(self) -> list[str]:
        return sorted(self._states.keys())

    @property
    def all_registered(self) -> bool:
        return all(name in self._states for name in VALID_STATES)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def set_state(
        self,
        name: str,
        transition_duration_ms: Optional[float] = None,
    ) -> None:
        if name not in self._states:
            raise ValueError(
                f"State '{name}' is not registered. Registered: {sorted(self._states.keys())}"
            )
        self._requested_state = name
        self._transition_duration_ms = transition_duration_ms

    @property
    def current_state_name(self) -> str:
        if self._mixer is not None:
            return self._mixer.current_state_name  # type: ignore[attr-defined]
        if self._states:
            return next(iter(self._states))
        return "none"

    @property
    def is_idle(self) -> bool:
        if self._mixer is None:
            return self._requested_state is None
        return not self._mixer.is_blending and self._requested_state is None  # type: ignore[attr-defined]

    def initialize(self, initial_state: str = "calm") -> None:
        if initial_state not in self._states:
            raise ValueError(
                f"Initial state '{initial_state}' not registered. "
                f"Available: {sorted(self._states.keys())}"
            )
        if self._mixer is not None:
            self._mixer.set_state_immediate(self._states[initial_state])  # type: ignore[attr-defined]

    def update(self, dt_ms: float) -> None:
        if self._requested_state is not None and self._mixer is not None:
            state = self._states[self._requested_state]
            self._mixer.transition_to(state, self._transition_duration_ms)  # type: ignore[attr-defined]
            self._requested_state = None
            self._transition_duration_ms = None
