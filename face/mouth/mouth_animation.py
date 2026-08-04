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

        self._appear_duration_ms: float = 220.0
        self._appear_elapsed_ms: float = 220.0
        self._appear_direction: int = 1
        self._in_appear: bool = False
        self._prev_opacity: float = 0.0

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

        self._prev_opacity = self._target_params.opacity
        self._appear_elapsed_ms = self._appear_duration_ms
        self._in_appear = False

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

        prev_op = self._prev_opacity
        next_op = target.opacity

        threshold = 0.05
        was_visible = prev_op > threshold
        will_visible = next_op > threshold

        if not was_visible and will_visible:
            self._appear_direction = 1
            self._appear_elapsed_ms = 0.0
            self._in_appear = True
            self._appear_duration_ms = 220.0
        elif was_visible and not will_visible:
            self._appear_direction = -1
            self._appear_elapsed_ms = 0.0
            self._in_appear = True
            self._appear_duration_ms = 200.0
        else:
            self._appear_elapsed_ms = self._appear_duration_ms
            self._in_appear = False

    def set_speech_pulse(self, pulse: float) -> None:
        """Set raw speech input amplitude [0.0, 1.0]."""
        self._speech_sync.set_speech_pulse(pulse)

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> MouthParams:
        """Advance animation by dt_ms and update mouth parameters."""
        dt_s = dt_ms / 1000.0
        self._elapsed_s += dt_s
        self._speech_sync.set_speech_pulse(speech_pulse)
        self._speech_sync.update(dt_s)

        # 1. State transition interpolation
        if self._in_transition:
            self._transition_elapsed_ms += dt_ms
            t = self._transition_elapsed_ms / self._transition_duration_ms
            if t >= 1.0:
                t = 1.0
                self._in_transition = False
                self._prev_opacity = self._target_params.opacity

            ease_t = t * t * (3.0 - 2.0 * t)
            self._current_params.lerp_into(self._start_params, self._target_params, ease_t)
        else:
            self._current_params.copy_from(self._target_params)

        # 2. Base composition
        self._composed_params.copy_from(self._current_params)

        # 3. Appearance animation (fade + scale on enter/exit)
        if self._in_appear:
            self._appear_elapsed_ms += dt_ms
            raw_t = self._appear_elapsed_ms / self._appear_duration_ms
            if raw_t >= 1.0:
                raw_t = 1.0
                self._in_appear = False

            ease_t = 0.5 - 0.5 * math.cos(math.pi * raw_t)

            if self._appear_direction == 1:
                scale_mult = 0.92 + 0.08 * ease_t
                opacity_mult = ease_t
                self._composed_params.width *= scale_mult
                self._composed_params.height *= scale_mult
                self._composed_params.thickness *= scale_mult
                target_opacity = self._target_params.opacity
                self._composed_params.opacity = target_opacity * opacity_mult
            else:
                rev_ease = 1.0 - ease_t
                scale_mult = 0.92 + 0.08 * rev_ease
                opacity_mult = rev_ease
                self._composed_params.width *= scale_mult
                self._composed_params.height *= scale_mult
                self._composed_params.thickness *= scale_mult
                start_opacity = self._start_params.opacity
                self._composed_params.opacity = start_opacity * opacity_mult

        # 4. Dynamic Animated Motion for Specific States
        if self._current_state == "thinking":
            corner_lift = 0.5 + 0.5 * math.sin(self._elapsed_s * 1.9 - 0.6)
            self._composed_params.smile_amount += corner_lift * 0.07
            self._composed_params.rotation += corner_lift * 0.035
            self._composed_params.offset_x += corner_lift * 1.8
            base_op = self._target_params.opacity if not self._in_transition else self._composed_params.opacity
            self._composed_params.opacity = min(0.32, base_op + corner_lift * 0.08)

        # 5. Procedural speaking mouth cycle
        if self._current_state == "speaking":
            self._apply_speaking_cycle(dt_s)

        # 6. Speech sync overlay (multiplies on top of procedural speaking cycle)
        self._speech_sync.apply(self._composed_params)

        # 7. Subtle resting micro-motion
        breathe = math.sin(self._elapsed_s * 1.8) * 0.8
        sway_x = math.cos(self._elapsed_s * 1.3) * 0.5
        sway_rot = math.sin(self._elapsed_s * 0.9) * 0.010

        self._composed_params.offset_x += sway_x
        self._composed_params.offset_y += breathe
        self._composed_params.rotation += sway_rot
        self._composed_params.clamp_safe()

        return self._composed_params

    def _apply_speaking_cycle(self, dt_s: float) -> None:
        """Apply procedural speaking cycle: Closed -> Small Open -> Medium Open -> Small -> Closed."""
        if not hasattr(self, "_speak_phase"):
            self._speak_phase: float = 0.0
            self._speak_cycle_len: float = 0.38
            self._speak_next_reroll: float = 0.0

        self._speak_phase += dt_s
        self._speak_next_reroll -= dt_s

        if self._speak_next_reroll <= 0.0:
            import random
            self._speak_cycle_len = 0.30 + random.uniform(-0.08, 0.10)
            self._speak_next_reroll = self._speak_cycle_len * random.uniform(0.8, 1.6)

        cycle_pos = (self._speak_phase % self._speak_cycle_len) / self._speak_cycle_len

        if cycle_pos < 0.20:
            seg_t = cycle_pos / 0.20
            ease = seg_t * seg_t * (3.0 - 2.0 * seg_t)
            open_amount = ease * 0.30
        elif cycle_pos < 0.45:
            seg_t = (cycle_pos - 0.20) / 0.25
            ease = seg_t * seg_t * (3.0 - 2.0 * seg_t)
            open_amount = 0.30 + ease * 0.35
        elif cycle_pos < 0.70:
            seg_t = (cycle_pos - 0.45) / 0.25
            ease = seg_t * seg_t * (3.0 - 2.0 * seg_t)
            open_amount = 0.65 - ease * 0.35
        else:
            seg_t = (cycle_pos - 0.70) / 0.30
            ease = seg_t * seg_t * (3.0 - 2.0 * seg_t)
            open_amount = 0.30 - ease * 0.30

        self._composed_params.height *= (1.0 + open_amount * 0.85)
        self._composed_params.opening = max(self._composed_params.opening, open_amount * 0.55)
        self._composed_params.corner_roundness = max(0.65, 1.0 - open_amount * 0.30)
        self._composed_params.lower_curvature += open_amount * 0.12
