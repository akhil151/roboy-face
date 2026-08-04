"""
FaceMixer — Unified Character State & Animation Mixer.

Synchronizes Eyes (EyeEngine), Mouth (MouthAnimationController), and FX
under one emotional state. Guarantees smooth, zero-popping transitions across
all character features simultaneously.
"""

from __future__ import annotations

from typing import Optional, Tuple

from eyes import EyeEngine, VALID_STATES
from eyes.engine.eye_pair import EyePair
from face.mouth.mouth_animation import MouthAnimationController
from face.mouth.mouth_shapes import MouthParams
from face.render_context import RenderContext


class FaceMixer:
    """State & animation mixer driving Eyes, Mouth, and Effects in perfect unison."""

    def __init__(self, eye_engine: Optional[EyeEngine] = None) -> None:
        self._eye_engine = eye_engine or EyeEngine()
        self._mouth_controller = MouthAnimationController()
        self._mouth_controller.initialize("calm")

        self._current_state: str = "calm"
        self._speech_pulse: float = 0.0
        self._elapsed_s: float = 0.0
        self._mouse_look: Tuple[float, float] = (0.0, 0.0)

        # Transition tracking
        self._transition_duration_ms: float = 350.0
        self._transition_elapsed_ms: float = 350.0
        self._in_transition: bool = False

    @property
    def eye_engine(self) -> EyeEngine:
        return self._eye_engine

    @property
    def mouth_controller(self) -> MouthAnimationController:
        return self._mouth_controller

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def valid_states(self) -> list[str]:
        return sorted(VALID_STATES)

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        """Switch character emotional state (drives Eyes + Mouth + FX together)."""
        if state not in VALID_STATES:
            raise ValueError(f"Unknown face state: {state}. Valid: {sorted(VALID_STATES)}")

        dur = transition_ms if transition_ms is not None else 350.0

        self._current_state = state
        self._eye_engine.set_state(state)
        self._mouth_controller.set_state(state, transition_ms=dur)

        self._transition_duration_ms = max(50.0, dur)
        self._transition_elapsed_ms = 0.0
        self._in_transition = True

    def blink(self) -> None:
        """Trigger an autonomous blink on the eye rig."""
        self._eye_engine.blink()

    def look_at(self, x: float, y: float) -> None:
        """Direct gaze and head tilt offset toward target coordinates."""
        self._mouse_look = (x, y)
        self._eye_engine.look_at(x, y)

    def set_speech_pulse(self, pulse: float) -> None:
        """Set continuous audio/speech pulse [0.0, 1.0]."""
        self._speech_pulse = max(0.0, min(1.0, pulse))
        self._mouth_controller.set_speech_pulse(self._speech_pulse)

    def step(self, dt_ms: float) -> Tuple[EyePair, MouthParams, RenderContext]:
        """Step all subsystems synchronously and return current face pose and context."""
        dt_s = dt_ms / 1000.0
        self._elapsed_s += dt_s

        if self._in_transition:
            self._transition_elapsed_ms += dt_ms
            if self._transition_elapsed_ms >= self._transition_duration_ms:
                self._in_transition = False

        blend_t = 1.0
        if self._in_transition and self._transition_duration_ms > 0:
            blend_t = min(1.0, self._transition_elapsed_ms / self._transition_duration_ms)

        # Step Eyes subsystem
        eye_pose = self._eye_engine._engine.step(dt_ms, speech_pulse=self._speech_pulse)

        # Step Mouth subsystem
        mouth_params = self._mouth_controller.step(dt_ms, speech_pulse=self._speech_pulse)

        # Construct frame RenderContext
        ctx = RenderContext(
            current_state=self._current_state,
            blend_progress=blend_t,
            speech_pulse=self._speech_pulse,
            timeline_stage="loop" if not self._in_transition else "enter",
            overlay_intensity=1.0,
            dt_s=dt_s,
            elapsed_s=self._elapsed_s,
            mouse_look=self._mouse_look,
        )

        return (eye_pose, mouth_params, ctx)
