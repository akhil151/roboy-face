"""Organic animation and state controller for ELO Face V3.

Coordinates smooth parameter transitions, automatic/manual blinks, subtle
breathing micro-motion, and gaze tracking with framerate-independent easing.
"""

import math
from typing import Optional, Tuple

from config import (
    DEFAULT_BLINK_DURATION,
    BLINK_CLOSE_RATIO,
    BLINK_HOLD_TIME,
    BREATH_PERIOD,
    BREATH_SCALE_AMP,
    SMOOTH_RATE_LOOK,
    SMOOTH_RATE_SCALE,
    SMOOTH_RATE_OPEN,
    MAX_LOOK_OFFSET_X,
    MAX_LOOK_OFFSET_Y,
    MIN_SCALE,
    MAX_SCALE,
    DEFAULT_SCALE,
)
from easing import clamp, exp_decay, cubic_in_out, quad_out
from eye import EyePair


class BlinkState:
    """Tracks the lifecycle of an active blink animation."""

    def __init__(self, duration: float = DEFAULT_BLINK_DURATION) -> None:
        self.active: bool = False
        self.elapsed: float = 0.0
        self.duration: float = duration

    def trigger(self, duration: Optional[float] = None) -> None:
        """Start a new blink."""
        self.active = True
        self.elapsed = 0.0
        if duration is not None:
            self.duration = duration

    def update(self, dt: float) -> float:
        """Advances blink time and returns the squash multiplier [0.0 (closed) .. 1.0 (open)]."""
        if not self.active:
            return 1.0

        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False
            self.elapsed = 0.0
            return 1.0

        progress = self.elapsed / self.duration
        close_phase_end = BLINK_CLOSE_RATIO
        reopen_phase_start = BLINK_CLOSE_RATIO + (BLINK_HOLD_TIME / self.duration)

        if progress < close_phase_end:
            # Closing phase: 1.0 -> 0.0
            t = progress / close_phase_end
            return 1.0 - cubic_in_out(t)
        elif progress < reopen_phase_start:
            # Hold at closed
            return 0.0
        else:
            # Reopening phase: 0.0 -> 1.0
            t = (progress - reopen_phase_start) / (1.0 - reopen_phase_start)
            return quad_out(t)


class FaceController:
    """Main state machine and motion controller driving the EyePair."""

    def __init__(self, eye_pair: Optional[EyePair] = None) -> None:
        self.eye_pair: EyePair = eye_pair or EyePair()

        # Current continuous values
        self.current_open_left: float = 1.0
        self.current_open_right: float = 1.0
        self.current_look_x: float = 0.0
        self.current_look_y: float = 0.0
        self.current_scale: float = DEFAULT_SCALE

        # Target values (what the system smoothly moves towards)
        self.target_open_left: float = 1.0
        self.target_open_right: float = 1.0
        self.target_look_x: float = 0.0
        self.target_look_y: float = 0.0
        self.target_scale: float = DEFAULT_SCALE

        # Smoothing rates
        self.smooth_rate_look: float = SMOOTH_RATE_LOOK
        self.smooth_rate_scale: float = SMOOTH_RATE_SCALE
        self.smooth_rate_open: float = SMOOTH_RATE_OPEN

        # Subsystems
        self.blink: BlinkState = BlinkState()
        self.breathing_enabled: bool = True
        self.breathing_time: float = 0.0

        # Auto-idle / demo mode
        self.auto_idle: bool = False
        self.idle_timer: float = 0.0
        self.next_idle_action_time: float = 3.0

    # -----------------------------------------------------------------------
    # Target Setters
    # -----------------------------------------------------------------------

    def set_target_open(self, left: float, right: Optional[float] = None) -> None:
        """Set target opening amount [0.0 = closed pill, 1.0 = full circle]."""
        self.target_open_left = clamp(left, 0.0, 1.0)
        self.target_open_right = clamp(left if right is None else right, 0.0, 1.0)

    def set_target_look(self, dx: float, dy: float) -> None:
        """Set target gaze offset."""
        self.target_look_x = clamp(dx, -MAX_LOOK_OFFSET_X, MAX_LOOK_OFFSET_X)
        self.target_look_y = clamp(dy, -MAX_LOOK_OFFSET_Y, MAX_LOOK_OFFSET_Y)

    def set_target_scale(self, scale: float) -> None:
        """Set target scale multiplier."""
        self.target_scale = clamp(scale, MIN_SCALE, MAX_SCALE)

    def look_at(self, direction: str) -> None:
        """Convenience helper to look in cardinal directions."""
        direction = direction.lower().strip()
        dx, dy = 0.0, 0.0
        if "left" in direction:
            dx = -MAX_LOOK_OFFSET_X * 0.85
        elif "right" in direction:
            dx = MAX_LOOK_OFFSET_X * 0.85

        if "up" in direction:
            dy = -MAX_LOOK_OFFSET_Y * 0.85
        elif "down" in direction:
            dy = MAX_LOOK_OFFSET_Y * 0.85

        self.set_target_look(dx, dy)

    def trigger_blink(self, duration: Optional[float] = None) -> None:
        """Trigger an organic eyelid blink."""
        self.blink.trigger(duration)

    def snap_to_targets(self) -> None:
        """Immediately snaps all current values to targets (bypassing smoothing)."""
        self.current_open_left = self.target_open_left
        self.current_open_right = self.target_open_right
        self.current_look_x = self.target_look_x
        self.current_look_y = self.target_look_y
        self.current_scale = self.target_scale

    # -----------------------------------------------------------------------
    # Update Loop
    # -----------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advances physics, smoothing, breathing, and blinks by dt seconds."""
        if dt <= 0.0:
            return

        # 1. Update smooth continuous interpolation towards targets
        self.current_look_x = exp_decay(self.current_look_x, self.target_look_x, self.smooth_rate_look, dt)
        self.current_look_y = exp_decay(self.current_look_y, self.target_look_y, self.smooth_rate_look, dt)
        self.current_scale = exp_decay(self.current_scale, self.target_scale, self.smooth_rate_scale, dt)
        self.current_open_left = exp_decay(self.current_open_left, self.target_open_left, self.smooth_rate_open, dt)
        self.current_open_right = exp_decay(self.current_open_right, self.target_open_right, self.smooth_rate_open, dt)

        # 2. Update breathing cycle
        breath_scale_offset = 0.0
        if self.breathing_enabled:
            self.breathing_time += dt
            breath_scale_offset = math.sin(2.0 * math.pi * (self.breathing_time / BREATH_PERIOD)) * BREATH_SCALE_AMP

        # 3. Update blink state
        blink_mult = self.blink.update(dt)

        # 4. Composite final parameters and feed to EyePair
        final_open_l = clamp(self.current_open_left * blink_mult, 0.0, 1.0)
        final_open_r = clamp(self.current_open_right * blink_mult, 0.0, 1.0)
        final_scale = clamp(self.current_scale + breath_scale_offset, MIN_SCALE, MAX_SCALE)

        self.eye_pair.left_eye.set_open(final_open_l)
        self.eye_pair.right_eye.set_open(final_open_r)
        self.eye_pair.set_look(self.current_look_x, self.current_look_y)
        self.eye_pair.set_scale(final_scale)

        # 5. Optional Auto-Idle Behavior
        if self.auto_idle:
            self._update_auto_idle(dt)

    def _update_auto_idle(self, dt: float) -> None:
        """Generates natural idle saccades, glance shifts, and periodic blinks."""
        self.idle_timer += dt
        if self.idle_timer >= self.next_idle_action_time:
            self.idle_timer = 0.0
            import random
            action = random.choice(["blink", "look_center", "look_glance", "blink_double", "surprise_peek"])
            if action == "blink":
                self.trigger_blink(0.16)
                self.next_idle_action_time = random.uniform(2.5, 4.5)
            elif action == "blink_double":
                self.trigger_blink(0.14)
                self.next_idle_action_time = 0.25
            elif action == "look_center":
                self.set_target_look(0.0, 0.0)
                self.next_idle_action_time = random.uniform(2.0, 3.5)
            elif action == "look_glance":
                gx = random.choice([-1.0, 1.0, 0.0]) * random.uniform(25.0, 50.0)
                gy = random.choice([-1.0, 1.0, 0.0]) * random.uniform(10.0, 30.0)
                self.set_target_look(gx, gy)
                self.next_idle_action_time = random.uniform(1.8, 3.0)
            elif action == "surprise_peek":
                self.set_target_scale(1.15)
                self.next_idle_action_time = 1.0
