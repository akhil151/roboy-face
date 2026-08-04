"""
Mouth Animation Controller.

Handles smooth interpolation (lerp_into) between target mouth states, zero-allocation
state transitions, organic resting micro-motion, and multi-parameter procedural speech sync.
"""

from __future__ import annotations

import math
from typing import Optional

from .mouth_shapes import MouthParams, get_mouth_preset
from .speech_sync import SpeechSync


class MouthAnimationController:
    """Controller for mouth state transitions, interpolation, micro-motion, and speech sync."""

    def __init__(self) -> None:
        self._current_state: str = "calm"
        self._current_params: MouthParams = get_mouth_preset("calm")
        self._start_params: MouthParams = get_mouth_preset("calm")
        self._target_params: MouthParams = get_mouth_preset("calm")
        self._composed_params: MouthParams = get_mouth_preset("calm")

        self._transition_duration_ms: float = 300.0
        self._transition_elapsed_ms: float = 300.0
        self._in_transition: bool = False

        self._elapsed_s: float = 0.0
        self._speech_sync: SpeechSync = SpeechSync()

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def current_params(self) -> MouthParams:
        return self._composed_params

    @property
    def speech_sync(self) -> SpeechSync:
        return self._speech_sync

    def initialize(self, initial_state: str = "calm") -> None:
        self._current_state = initial_state
        self._current_params = get_mouth_preset(initial_state)
        self._start_params.copy_from(self._current_params)
        self._target_params.copy_from(self._current_params)
        self._composed_params.copy_from(self._current_params)
        self._transition_elapsed_ms = self._transition_duration_ms
        self._in_transition = False

    def set_state(self, state_name: str, transition_ms: Optional[float] = None) -> None:
        if state_name == self._current_state and not self._in_transition:
            return

        self._current_state = state_name
        target = get_mouth_preset(state_name)

        self._start_params.copy_from(self._current_params)
        self._target_params.copy_from(target)

        dur = transition_ms if transition_ms is not None else 300.0
        self._transition_duration_ms = max(50.0, dur)
        self._transition_elapsed_ms = 0.0
        self._in_transition = True

    def set_speech_pulse(self, pulse: float) -> None:
        """Set raw speech input amplitude [0.0, 1.0]."""
        self._speech_sync.set_speech_pulse(pulse)

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> MouthParams:
        """Advance animation by dt_ms and update mouth parameters."""
        dt_s = dt_ms / 1000.0
        self._elapsed_s += dt_s

        # 1. State transition interpolation
        if self._in_transition:
            self._transition_elapsed_ms += dt_ms
            t = self._transition_elapsed_ms / self._transition_duration_ms
            if t >= 1.0:
                t = 1.0
                self._in_transition = False

            ease_t = t * t * (3.0 - 2.0 * t)
            self._current_params.lerp_into(self._start_params, self._target_params, ease_t)
        else:
            self._current_params.copy_from(self._target_params)

        # 2. Base composition
        self._composed_params.copy_from(self._current_params)

        # 3. Dynamic Animated Motion for Specific States
        if self._current_state == "thinking":
            # Animated corner motion for Thinking (no permanent static skew)
            thinking_offset_x = math.sin(self._elapsed_s * 2.2) * 5.0
            thinking_rotation = math.cos(self._elapsed_s * 1.7) * 0.04
            self._composed_params.offset_x += thinking_offset_x
            self._composed_params.rotation += thinking_rotation

        # 4. Subtle resting micro-motion
        breathe = math.sin(self._elapsed_s * 1.8) * 0.8
        sway_x = math.cos(self._elapsed_s * 1.3) * 0.5
        sway_rot = math.sin(self._elapsed_s * 0.9) * 0.010

        self._composed_params.offset_x += sway_x
        self._composed_params.offset_y += breathe
        self._composed_params.rotation += sway_rot
        self._composed_params.clamp_safe()

        return self._composed_params

