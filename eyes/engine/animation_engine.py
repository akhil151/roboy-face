"""
Main animation engine - orchestrates all subsystems.

Composes:
- Config, EyePair rigs
- AnimationMixer + StateMachine
- BlinkController, LookController, MicroMotion
- Renderer

Applies controller outputs on top of the mixer's pose each frame.
Exposes a minimal public API through EyeEngine (set_state, blink, look_at, run_forever).
"""

from __future__ import annotations

import sys
from typing import Optional

import pygame

from .config import EngineConfig
from .eye_pair import EyePair, blend_eye_pair
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

        self._final_pose = self._base_pose.copy()
        self._running = False
        self._fps = self._config.display.fps
        self._clock: Optional[pygame.time.Clock] = None

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
    def renderer(self) -> Renderer:
        return self._renderer

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

    def _apply_controllers(self, pose: EyePair) -> EyePair:
        result = pose.copy()
        look_dx, look_dy = self._look.get_offsets()
        micro_dx, micro_dy = self._micro.get_offsets()
        bw = self._blink.blink_weight

        for eye, sign in [(result.left, -1.0), (result.right, 1.0)]:
            eye.look_offset_x += look_dx
            eye.look_offset_y += look_dy
            eye.micro_offset_x += micro_dx + sign * 0.3
            eye.micro_offset_y += micro_dy
            eye.blink_weight = max(eye.blink_weight, bw)
            if bw > 0.01:
                eye.lid_openness = min(eye.lid_openness, 1.0 - bw)

        return result

    def step(self, dt_ms: float) -> EyePair:
        dt_s = dt_ms / 1000.0

        self._state_machine.update(dt_ms)
        self._mixer.update(dt_ms)
        self._blink.update(dt_ms)
        self._look.update(dt_s)
        self._micro.update(dt_s)

        base = self._mixer.get_pose()
        self._final_pose = self._apply_controllers(base)
        return self._final_pose

    @property
    def current_pose(self) -> EyePair:
        return self._final_pose

    def init_video(self, windowed: bool = True) -> None:
        if not pygame.get_init():
            pygame.init()
        self._renderer.init_display(windowed=windowed)
        self._clock = pygame.time.Clock()

    def render_frame(self) -> None:
        if not self._renderer.initialized:
            raise RuntimeError("Video not initialized. Call init_video() first.")
        self._renderer.render(self._final_pose)

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
