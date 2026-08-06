"""
Public Facade for the ELO Face Animation Engine v1.0.

Provides a simple, clean high-level interface orchestrating:
  - EyeEngine (Frozen dependency)
  - Procedural Mouth Engine & Speech Sync
  - FaceComposer & Emotional Effects

Example usage:
    from face import FaceEngine

    face = FaceEngine()
    face.set_state("happy")
    face.run_forever()
"""

from __future__ import annotations

from typing import Optional, Tuple
import pygame

from eyes import EyeEngine, VALID_STATES
from eyes.engine.config import EngineConfig
from eyes.engine.eye_pair import EyePair
from face.face_composer import FaceComposer
from face.face_mixer import FaceMixer
from face.mouth.mouth_shapes import MouthParams
from face.render_context import RenderContext


class FaceEngine:
    """Public facade for the procedural face animation engine."""

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self._config = config or EngineConfig()
        self._eye_engine = EyeEngine(self._config)
        self._mixer = FaceMixer(self._eye_engine)
        self._composer = FaceComposer(self._config)

        self._running = False
        self._fps = self._config.display.fps
        self._clock: Optional[pygame.time.Clock] = None

    @property
    def config(self) -> EngineConfig:
        return self._config

    @property
    def mixer(self) -> FaceMixer:
        return self._mixer

    @property
    def composer(self) -> FaceComposer:
        return self._composer

    @property
    def current_state(self) -> str:
        return self._mixer.current_state

    @property
    def valid_states(self) -> list[str]:
        return sorted(VALID_STATES)

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        """Set active emotional state for the entire face (Eyes + Mouth + FX)."""
        self._mixer.set_state(state, transition_ms=transition_ms)

    def blink(self) -> None:
        """Trigger an autonomous eye blink."""
        self._mixer.blink()

    def look_at(self, x: float, y: float) -> None:
        """Look toward coordinate target."""
        self._mixer.look_at(x, y)

    def set_speech_pulse(self, pulse: float) -> None:
        """Set continuous speech amplitude [0.0, 1.0]."""
        self._mixer.set_speech_pulse(pulse)

    def step(self, dt_ms: float) -> Tuple[EyePair, MouthParams, RenderContext]:
        """Advance face animation by dt_ms."""
        return self._mixer.step(dt_ms)

    def init_video(self, windowed: bool = True) -> None:
        """Initialize display window."""
        if not pygame.get_init():
            pygame.init()
        self._composer.init_display(windowed=windowed)
        self._clock = pygame.time.Clock()

    def render_frame(self) -> None:
        """Render active composite frame.

        Advances the animation by the real elapsed time since the previous
        frame (measured with the existing clock) and renders the result, so
        embedding apps that drive the loop solely with render_frame() keep
        animating (blinks, look controller, state transitions).  Callers
        should not also call step() in the same frame.
        """
        if self._clock is None:
            self._clock = pygame.time.Clock()
        dt_ms = self._clock.tick(0)
        dt_ms = min(dt_ms, 66.0)
        eye_pose, mouth_params, ctx = self._mixer.step(dt_ms)
        self._composer.render(eye_pose, mouth_params, ctx)

    @staticmethod
    def _process_events() -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True

    def run_forever(self, windowed: bool = True) -> None:
        """Run standard display loop."""
        self.init_video(windowed=windowed)
        self._running = True
        clock = self._clock
        assert clock is not None
        target_fps = self._fps

        try:
            while self._running:
                if not self._process_events():
                    break
                dt_ms = clock.tick(target_fps)
                dt_ms = min(dt_ms, 66.0)
                eye_pose, mouth_params, ctx = self.step(dt_ms)
                self._composer.render(eye_pose, mouth_params, ctx)
        finally:
            self._running = False
            pygame.quit()
