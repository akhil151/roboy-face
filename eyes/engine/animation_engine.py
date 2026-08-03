"""
Main animation engine - orchestrates all subsystems.

Composes:
- Config, EyePair rigs
- AnimationMixer (with internal layered composition: State + Blink + Look + Micro + Speech)
- StateMachine
- BlinkController, LookController, MicroMotion
- Renderer

The mixer now owns the layer-composition pipeline, so this engine is
responsible for:
  * pumping dt_ms through every submodule in the correct order
  * passing controller outputs as *layer inputs* to the mixer
  * exposing the tiny public API required by EyeEngine (set_state / blink / look_at / run_forever)
"""

from __future__ import annotations

from typing import Optional

import pygame

from .config import EngineConfig
from .eye_pair import EyePair
from .renderer import Renderer
from .animation_mixer import AnimationMixer
from .state_machine import StateMachine, VALID_STATES
from .blink_controller import BlinkController, BlinkType
from .look_controller import LookController
from .micro_motion import MicroMotion


class AnimationEngine:
    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self._config = config or EngineConfig()

        self._base_pose = EyePair()
        self._base_pose.configure(self._config)

        self._mixer = AnimationMixer(self._config, self._base_pose)
        self._state_machine = StateMachine(self._mixer)
        self._renderer = Renderer(self._config)
        self._blink = BlinkController(self._config)
        self._look = LookController(self._config)
        self._micro = MicroMotion(self._config)
        from .micro_behaviours import MicroBehaviourSystem
        self._micro_behaviour = MicroBehaviourSystem(self._config)

        # Reused reference - final pose lives inside the mixer now.
        self._running = False
        self._fps = self._config.display.fps
        self._clock: Optional[pygame.time.Clock] = None

    # ------------------------------------------------------------------
    # Public properties (read-only surface for inspection / tests)
    # ------------------------------------------------------------------
    @property
    def config(self) -> EngineConfig:
        return self._config

    @property
    def state_machine(self) -> StateMachine:
        return self._state_machine

    @property
    def mixer(self) -> AnimationMixer:
        return self._mixer

    @property
    def blink_controller(self) -> BlinkController:
        return self._blink

    @property
    def look_controller(self) -> LookController:
        return self._look

    @property
    def micro_motion(self) -> MicroMotion:
        return self._micro

    @property
    def micro_behaviour_system(self) -> "MicroBehaviourSystem":
        return self._micro_behaviour

    @property
    def renderer(self) -> Renderer:
        return self._renderer

    @property
    def current_pose(self) -> EyePair:
        return self._mixer.get_final_pose()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self, initial_state: str = "calm") -> None:
        self._state_machine.initialize(initial_state)

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        if state not in VALID_STATES:
            raise ValueError(f"Unknown state: {state}. Valid: {sorted(VALID_STATES)}")
        self._state_machine.set_state(state, transition_ms)

    def blink(self) -> None:
        self._blink.force_blink()

    def trigger_blink_type(self, blink_type: BlinkType) -> None:
        self._blink.trigger_blink(blink_type)

    def look_at(self, x: float, y: float) -> None:
        self._look.look_at(x, y)

    # ------------------------------------------------------------------
    # Frame step - pure data plumbing, no allocations on the hot path.
    # ------------------------------------------------------------------
    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> EyePair:
        dt_s = dt_ms / 1000.0

        # Update controllers; each controller's internal state mutates, then
        # we read the current output values to pass into the mixer as layers.
        self._state_machine.update(dt_ms)
        self._blink.update(dt_ms)
        self._look.update(dt_s)
        self._micro.update(dt_s)

        bw = self._blink.blink_weight
        look_dx, look_dy = self._look.get_offsets()

        # Mixer updates the state pose and composes layers into internal final_pose.
        self._mixer.update(
            dt_ms,
            blink_weight=bw,
            look_offsets=(look_dx, look_dy),
            speech_pulse=speech_pulse,
        )

        final_pose = self._mixer.get_final_pose()

        # Apply 7-layer autonomous MicroBehaviourSystem to the composed pose.
        current_state = self._state_machine.current
        bundle = None
        if hasattr(current_state, "personality_bundle"):
            bundle = current_state.personality_bundle

        self._micro_behaviour.apply(final_pose, dt_s, bundle)

        return final_pose


    # ------------------------------------------------------------------
    # Video / event loop
    # ------------------------------------------------------------------
    def init_video(self, windowed: bool = True) -> None:
        if not pygame.get_init():
            pygame.init()
        self._renderer.init_display(windowed=windowed)
        self._clock = pygame.time.Clock()

    def render_frame(self) -> None:
        if not self._renderer.initialized:
            raise RuntimeError("Video not initialized. Call init_video() first.")
        self._renderer.render(self._mixer.get_final_pose())

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
                dt_ms = min(dt_ms, 66.0)  # clamp to 15fps minimum step
                self.step(dt_ms)
                self.render_frame()
        finally:
            self._running = False
            pygame.quit()
