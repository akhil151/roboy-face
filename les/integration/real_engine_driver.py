"""
RealEngineDriver - the LES-to-engine integration adapter (LES-08.5).

``les/timeline/scheduler.py`` defines the ``EngineDriver`` protocol as the
ONLY boundary through which LES may talk to the animation engine. No real
implementation of that protocol existed; this module provides the smallest
possible one:

    * an adapter that translates the documented ``EngineCommand`` verbs
      (``set_state`` / ``blink`` / ``trigger_blink_type`` / ``look_at`` /
      ``step``) into the ALREADY-EXISTING public methods of the real
      engines (``face.FaceEngine`` by default, ``eyes.engine`` for the
      full protocol);
    * capability adaptation via introspection only - engines are never
      modified, and unsupported verbs are reported loudly
      (``supports()`` / ``ValueError``), never silently dropped;
    * NO animation logic, NO geometry, NO new behavior - it is purely an
      integration adapter. The engines (``eyes/``, ``face/``) remain
      frozen and unchanged.

Capability notes (verified against the real APIs):
    * ``FaceEngine`` supports set_state(state, transition_ms), blink,
      look_at(x, y), step(dt_ms) - but NOT trigger_blink_type.
    * ``eyes.engine.animation_engine.AnimationEngine`` supports the full
      protocol including ``trigger_blink_type(BlinkType)`` and
      ``step(dt_ms, speech_pulse)`` (constructed via ``for_eyes()``).
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Optional

from face import FaceEngine
from ..timeline.scheduler import EngineDriver

if TYPE_CHECKING:
    from eyes.engine.config import EngineConfig


class RealEngineDriver(EngineDriver):
    """EngineDriver protocol adapter over an existing real engine.

    Args:
        engine: any object exposing the real engine's public methods
            (``FaceEngine`` when omitted). Method arguments that the
            wrapped engine's public API does not accept are adapted away
            (e.g. ``transition_ms`` / ``speech_pulse`` on the simple
            facades); unsupported *verbs* raise ``ValueError``.
        config: optional ``EngineConfig`` used only when constructing the
            default ``FaceEngine``.
    """

    def __init__(
        self, engine: Optional[object] = None, config: Optional["EngineConfig"] = None
    ) -> None:
        if engine is None:
            engine = FaceEngine(config)
        self._engine = engine

        # Capability adaptation - introspection only, engines untouched.
        # Every verb is introspected so ``supports()`` can never lie about
        # an exotic wrapper.
        self._capabilities: dict = {
            verb: hasattr(engine, verb)
            for verb in ("set_state", "blink", "trigger_blink_type", "look_at", "step")
        }
        self._set_state_takes_transition: bool = (
            "transition_ms" in inspect.signature(engine.set_state).parameters
        )
        self._step_takes_speech: bool = (
            "speech_pulse" in inspect.signature(engine.step).parameters
        )

    # ------------------------------------------------------------------
    # Factories (construction only - no animation logic)
    # ------------------------------------------------------------------

    @classmethod
    def for_face(cls, config: Optional["EngineConfig"] = None) -> "RealEngineDriver":
        """Driver over the full character face engine (eyes + mouth + FX).

        ``trigger_blink_type`` is NOT supported by ``FaceEngine`` -
        ``supports()`` reports this truthfully.
        """
        return cls(FaceEngine(config))

    @classmethod
    def for_eyes(cls, config: Optional["EngineConfig"] = None) -> "RealEngineDriver":
        """Driver over the fully-registered eyes AnimationEngine.

        Supports the complete protocol including ``trigger_blink_type``.
        The engine is registered and initialized exactly as ``EyeEngine``
        does internally (the documented engine registration flow).
        """
        from eyes.engine.animation_engine import AnimationEngine
        from eyes.engine.config import EngineConfig

        cfg = config if config is not None else EngineConfig()
        engine = AnimationEngine(cfg)
        engine.state_machine.register_all_registered(cfg)
        engine.initialize("calm")
        return cls(engine)

    # ------------------------------------------------------------------
    # EngineDriver protocol (translation only)
    # ------------------------------------------------------------------

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        """Forward a set_state command, adapting ``transition_ms``."""
        if transition_ms is not None and self._set_state_takes_transition:
            self._engine.set_state(state, transition_ms)
        else:
            self._engine.set_state(state)

    def blink(self) -> None:
        """Forward a blink command."""
        self._engine.blink()

    def trigger_blink_type(self, blink_type) -> None:
        """Forward a typed blink - only when the wrapped engine supports it."""
        if not self._capabilities["trigger_blink_type"]:
            raise ValueError(
                "wrapped engine does not support trigger_blink_type() - "
                "use RealEngineDriver.for_eyes() (AnimationEngine)"
            )
        self._engine.trigger_blink_type(blink_type)

    def look_at(self, x: float, y: float) -> None:
        """Forward a look_at command (normalized coordinates)."""
        self._engine.look_at(x, y)

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> object:
        """Forward a step, adapting ``speech_pulse`` when unsupported."""
        if speech_pulse > 0.0 and self._step_takes_speech:
            return self._engine.step(dt_ms, speech_pulse)
        return self._engine.step(dt_ms)

    # ------------------------------------------------------------------
    # Adapter-specific observability
    # ------------------------------------------------------------------

    @property
    def engine(self) -> object:
        """The wrapped real engine instance."""
        return self._engine

    def supports(self, command: str) -> bool:
        """True when the wrapped engine exposes ``command``.

        Introspected at construction for every protocol verb, so the
        answer is always truthful for the wrapped engine.
        """
        return bool(self._capabilities.get(command, False))


__all__ = ["RealEngineDriver"]
