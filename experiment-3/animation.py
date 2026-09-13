"""Organic animation, state controller, and emotion sequencer for ELO Face V3.

Coordinates smooth parameter transitions, the 12-segment 62-second automated
timeline experience, breathing micro-motion, and interactive overrides.
"""

import math
from typing import Optional, Tuple, Dict, Callable

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
from easing import clamp, exp_decay, cubic_in_out, quad_out, quad_in, elastic_out, smoothstep, smootherstep
from eye import EyePair
from timeline import TimelineController
from effects import IntroState, BlushState, SleepZParticles


class BlinkState:
    """Tracks the lifecycle of an active manual/idle blink animation."""

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
        """Advances blink time and returns squash multiplier [0.0 (closed) .. 1.0 (open)]."""
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
            t = progress / close_phase_end
            return 1.0 - cubic_in_out(t)
        elif progress < reopen_phase_start:
            return 0.0
        else:
            t = (progress - reopen_phase_start) / (1.0 - reopen_phase_start)
            return quad_out(t)


class FaceController:
    """Main state machine, emotion sequencer, and motion controller driving the EyePair."""

    def __init__(
        self,
        eye_pair: Optional[EyePair] = None,
        timeline: Optional[TimelineController] = None,
    ) -> None:
        self.eye_pair: EyePair = eye_pair or EyePair()
        self.timeline: TimelineController = timeline or TimelineController()
        self.timeline.on_segment_change = self._on_segment_changed

        # Continuous interpolated state parameters
        self.current_open_left: float = 1.0
        self.current_open_right: float = 1.0
        self.current_look_x: float = 0.0
        self.current_look_y: float = 0.0
        self.current_scale: float = DEFAULT_SCALE

        # Direct animation offsets (for dynamic effects like happy bounce)
        self.offset_look_x: float = 0.0
        self.offset_look_y: float = 0.0

        # Targets (what continuous values smoothly ease towards)
        self.target_open_left: float = 1.0
        self.target_open_right: float = 1.0
        self.target_look_x: float = 0.0
        self.target_look_y: float = 0.0
        self.target_scale: float = DEFAULT_SCALE

        # Smoothing velocities
        self.smooth_rate_look: float = SMOOTH_RATE_LOOK
        self.smooth_rate_scale: float = SMOOTH_RATE_SCALE
        self.smooth_rate_open: float = SMOOTH_RATE_OPEN

        # Subsystems & Effects
        self.blink: BlinkState = BlinkState()
        self.breathing_enabled: bool = True
        self.breathing_time: float = 0.0
        self.breathing_period: float = BREATH_PERIOD
        self.breathing_amp: float = BREATH_SCALE_AMP

        self.intro_state: IntroState = IntroState()
        self.blush_state: BlushState = BlushState()
        self.sleep_particles: SleepZParticles = SleepZParticles()

        # Operational Mode
        # True = follow automated 62s timeline sequence; False = manual control
        self.timeline_driven: bool = True
        self.face_alpha: float = 1.0

        # Map segment names to dedicated handlers
        self._segment_handlers: Dict[str, Callable[[float, float, float], None]] = {
            "intro": self._update_intro,
            "settle": self._update_settle,
            "blink": self._update_blink,
            "look_horizontal": self._update_look_horizontal,
            "look_vertical": self._update_look_vertical,
            "curious": self._update_curious,
            "confused": self._update_confused,
            "surprise": self._update_surprise,
            "excited": self._update_excited,
            "happy_bounce": self._update_happy_bounce,
            "wink": self._update_wink,
            "playful_double_wink": self._update_playful_double_wink,
            "shy": self._update_shy,
            "cute_blush": self._update_cute_blush,
            "thinking": self._update_thinking,
            "suspicious": self._update_suspicious,
            "angry": self._update_angry,
            "scared_nervous": self._update_scared_nervous,
            "sad": self._update_sad,
            "drowsy": self._update_drowsy,
            "sleep": self._update_sleep,
        }

    # -----------------------------------------------------------------------
    # Segment Boundary Management
    # -----------------------------------------------------------------------

    def _on_segment_changed(self, old_seg: str, new_seg: str) -> None:
        """Cleans up transient state between segment transitions."""
        if old_seg == "intro" and new_seg != "intro":
            self.intro_state.reset()
            self.face_alpha = 1.0

        if old_seg in ("cute_blush", "shy") and new_seg not in ("cute_blush", "shy"):
            self.blush_state.reset()

        if old_seg == "sleep" and new_seg != "sleep":
            self.sleep_particles.reset()

        if old_seg in ("sleep", "sad") and new_seg not in ("sleep", "sad"):
            self.breathing_period = BREATH_PERIOD
            self.breathing_amp = BREATH_SCALE_AMP

        self.offset_look_x = 0.0
        self.offset_look_y = 0.0

    # -----------------------------------------------------------------------
    # Manual Target Setters
    # -----------------------------------------------------------------------

    def set_target_open(self, left: float, right: Optional[float] = None) -> None:
        self.target_open_left = clamp(left, 0.0, 1.0)
        self.target_open_right = clamp(left if right is None else right, 0.0, 1.0)

    def set_target_look(self, dx: float, dy: float) -> None:
        self.target_look_x = clamp(dx, -MAX_LOOK_OFFSET_X, MAX_LOOK_OFFSET_X)
        self.target_look_y = clamp(dy, -MAX_LOOK_OFFSET_Y, MAX_LOOK_OFFSET_Y)

    def set_target_scale(self, scale: float) -> None:
        self.target_scale = clamp(scale, MIN_SCALE, MAX_SCALE)

    def look_at(self, direction: str) -> None:
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
        self.blink.trigger(duration)

    def snap_to_targets(self) -> None:
        self.current_open_left = self.target_open_left
        self.current_open_right = self.target_open_right
        self.current_look_x = self.target_look_x
        self.current_look_y = self.target_look_y
        self.current_scale = self.target_scale

    # -----------------------------------------------------------------------
    # Emotion Handlers for Timeline Segments
    # -----------------------------------------------------------------------

    def _update_intro(self, u: float, elapsed: float, dt: float) -> None:
        """Intro typewriter sequence ("Hii" -> "This is ELO." -> Face Fade-in)."""
        self.intro_state.update(elapsed)
        self.face_alpha = self.intro_state.face_alpha
        self.set_target_open(1.0, 1.0)
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

    def _update_settle(self, u: float, elapsed: float, dt: float) -> None:
        """Neutral baseline settle with subtle organic breathing."""
        self.face_alpha = 1.0
        self.set_target_open(1.0, 1.0)
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

    def _update_blink(self, u: float, elapsed: float, dt: float) -> None:
        """Two slow, natural blinks in succession."""
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

        # Blink 1: u in [0.15, 0.42] (close -> hold -> reopen)
        # Blink 2: u in [0.58, 0.85] (close -> hold -> reopen)
        open_val = 1.0

        if 0.15 <= u < 0.42:
            t = (u - 0.15) / 0.27
            if t < 0.40:
                open_val = 1.0 - cubic_in_out(t / 0.40)
            elif t < 0.50:
                open_val = 0.0
            else:
                open_val = quad_out((t - 0.50) / 0.50)
        elif 0.58 <= u < 0.85:
            t = (u - 0.58) / 0.27
            if t < 0.40:
                open_val = 1.0 - cubic_in_out(t / 0.40)
            elif t < 0.50:
                open_val = 0.0
            else:
                open_val = quad_out((t - 0.50) / 0.50)

        self.target_open_left = open_val
        self.target_open_right = open_val

    def _update_look_horizontal(self, u: float, elapsed: float, dt: float) -> None:
        """Smooth horizontal gaze: Center -> Left -> Hold -> Right -> Hold -> Center."""
        self.set_target_open(1.0, 1.0)
        self.set_target_scale(DEFAULT_SCALE)

        max_dx = MAX_LOOK_OFFSET_X * 0.82 # ~53 px
        look_x = 0.0

        if u < 0.20:
            # Center -> Left
            t = u / 0.20
            look_x = -max_dx * cubic_in_out(t)
        elif u < 0.45:
            # Hold Left
            look_x = -max_dx
        elif u < 0.70:
            # Left -> Right
            t = (u - 0.45) / 0.25
            look_x = -max_dx + (2.0 * max_dx) * cubic_in_out(t)
        elif u < 0.85:
            # Hold Right
            look_x = max_dx
        else:
            # Right -> Center
            t = (u - 0.85) / 0.15
            look_x = max_dx * (1.0 - cubic_in_out(t))

        self.set_target_look(look_x, 0.0)

    def _update_look_vertical(self, u: float, elapsed: float, dt: float) -> None:
        """Smooth vertical gaze: Center -> Up -> Hold -> Down -> Hold -> Center."""
        self.set_target_open(1.0, 1.0)
        self.set_target_scale(DEFAULT_SCALE)

        max_dy = MAX_LOOK_OFFSET_Y * 0.75 # ~34 px
        look_y = 0.0

        if u < 0.22:
            # Center -> Up
            t = u / 0.22
            look_y = -max_dy * cubic_in_out(t)
        elif u < 0.45:
            # Hold Up
            look_y = -max_dy
        elif u < 0.72:
            # Up -> Down
            t = (u - 0.45) / 0.27
            look_y = -max_dy + (2.0 * max_dy) * cubic_in_out(t)
        elif u < 0.88:
            # Hold Down
            look_y = max_dy
        else:
            # Down -> Center
            t = (u - 0.88) / 0.12
            look_y = max_dy * (1.0 - cubic_in_out(t))

        self.set_target_look(0.0, look_y)

    def _update_curious(self, u: float, elapsed: float, dt: float) -> None:
        """Curious: gaze shifts inquisitively to one side with subtle eye asymmetry and micro-inspection."""
        max_dx = MAX_LOOK_OFFSET_X * 0.65  # ~42px
        target_dy = -10.0

        if u < 0.25:
            # Gaze shifts right & slight up, right eye subtly squints
            t = u / 0.25
            look_x = max_dx * cubic_in_out(t)
            look_y = target_dy * cubic_in_out(t)
            open_r = 1.0 - (1.0 - 0.82) * quad_out(t)
            scale = DEFAULT_SCALE + 0.04 * quad_out(t)
        elif u < 0.60:
            # Inquisitive hold with subtle micro-inspection adjustment
            micro_x = 3.5 * math.sin(2.0 * math.pi * 1.5 * elapsed)
            micro_y = 2.0 * math.cos(2.0 * math.pi * 1.5 * elapsed)
            look_x = max_dx + micro_x
            look_y = target_dy + micro_y
            open_r = 0.82
            scale = DEFAULT_SCALE + 0.04
        elif u < 0.78:
            # Closer inspection nod
            t = (u - 0.60) / 0.18
            look_x = max_dx + 8.0 * smoothstep(t)
            look_y = target_dy + 4.0 * smoothstep(t)
            open_r = 0.82 + 0.08 * smoothstep(t)
            scale = DEFAULT_SCALE + 0.04
        else:
            # Smooth return to center
            t = (u - 0.78) / 0.22
            look_x = (max_dx + 8.0) * (1.0 - cubic_in_out(t))
            look_y = (target_dy + 4.0) * (1.0 - cubic_in_out(t))
            open_r = 0.90 + 0.10 * quad_out(t)
            scale = (DEFAULT_SCALE + 0.04) - 0.04 * cubic_in_out(t)

        self.set_target_look(look_x, look_y)
        self.set_target_scale(scale)
        self.target_open_left = 1.0
        self.target_open_right = open_r

    def _update_confused(self, u: float, elapsed: float, dt: float) -> None:
        """Confused: hesitant gaze shifting left, pausing, shifting right with alternating subtle asymmetry."""
        max_dx = MAX_LOOK_OFFSET_X * 0.58  # ~38px

        if u < 0.22:
            # Look left, left eye slightly squints
            t = u / 0.22
            look_x = -max_dx * cubic_in_out(t)
            look_y = -6.0 * cubic_in_out(t)
            open_l = 1.0 - 0.18 * quad_out(t)
            open_r = 1.0
        elif u < 0.40:
            # Hesitates back toward center
            t = (u - 0.22) / 0.18
            look_x = -max_dx + (max_dx - 10.0) * cubic_in_out(t)
            look_y = -6.0 * (1.0 - t)
            open_l = 0.82 + 0.18 * quad_out(t)
            open_r = 1.0
        elif u < 0.65:
            # Shifts puzzled to the right, right eye squints
            t = (u - 0.40) / 0.25
            look_x = -10.0 + (max_dx + 10.0) * cubic_in_out(t)
            look_y = 8.0 * cubic_in_out(t)
            open_l = 1.0
            open_r = 1.0 - 0.18 * quad_out(t)
        elif u < 0.80:
            # Puzzled hold
            look_x = max_dx
            look_y = 8.0
            open_l = 1.0
            open_r = 0.82
        else:
            # Smooth resolution back to neutral
            t = (u - 0.80) / 0.20
            look_x = max_dx * (1.0 - cubic_in_out(t))
            look_y = 8.0 * (1.0 - cubic_in_out(t))
            open_l = 1.0
            open_r = 0.82 + 0.18 * quad_out(t)

        self.set_target_look(look_x, look_y)
        self.set_target_scale(DEFAULT_SCALE)
        self.target_open_left = open_l
        self.target_open_right = open_r

    def _update_surprise(self, u: float, elapsed: float, dt: float) -> None:
        """Big eyes surprise reaction: fast smooth growth -> hold -> return."""
        self.set_target_open(1.0, 1.0)
        self.set_target_look(0.0, 0.0)

        peak_scale = 1.35
        scale_val = DEFAULT_SCALE

        if u < 0.18:
            # Fast scale growth
            t = u / 0.18
            scale_val = DEFAULT_SCALE + (peak_scale - DEFAULT_SCALE) * quad_out(t)
        elif u < 0.65:
            # Hold surprised wide eyes
            scale_val = peak_scale
        else:
            # Smoothly settle back down
            t = (u - 0.65) / 0.35
            scale_val = peak_scale - (peak_scale - DEFAULT_SCALE) * cubic_in_out(t)

        self.set_target_scale(scale_val)

    def _update_excited(self, u: float, elapsed: float, dt: float) -> None:
        """Excited: rapid scale burst, energetic vertical bouncing with pulsing scale."""
        self.set_target_open(1.0, 1.0)
        self.set_target_look(0.0, -4.0)

        # Scale burst to 1.25, layered with energetic bounce
        if u < 0.15:
            t = u / 0.15
            scale_val = DEFAULT_SCALE + 0.25 * quad_out(t)
            self.offset_look_y = 0.0
        elif u < 0.75:
            # High-energy bounce (3.2 Hz) + scale pulsation
            t_bounce = elapsed - (0.15 * 4.5)
            freq = 3.2
            decay = math.exp(-0.45 * t_bounce)
            fade = 1.0 - smoothstep((u - 0.60) / 0.15) if u > 0.60 else 1.0
            bounce = -24.0 * decay * abs(math.sin(2.0 * math.pi * freq * t_bounce)) * fade
            pulse = 0.06 * decay * math.cos(2.0 * math.pi * freq * t_bounce) * fade
            scale_val = 1.22 + pulse
            self.offset_look_y = bounce
        else:
            t = (u - 0.75) / 0.25
            scale_val = 1.22 - 0.22 * cubic_in_out(t)
            self.offset_look_y = 0.0

        self.set_target_scale(scale_val)

    def _update_wink(self, u: float, elapsed: float, dt: float) -> None:
        """Single eye wink: Left stays open, Right squashes closed -> holds -> reopens."""
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

        left_open = 1.0
        right_open = 1.0

        if u < 0.22:
            # Right eye closes
            t = u / 0.22
            right_open = 1.0 - cubic_in_out(t)
        elif u < 0.62:
            # Right eye holds closed
            right_open = 0.0
        elif u < 0.92:
            # Right eye reopens
            t = (u - 0.62) / 0.30
            right_open = quad_out(t)
        else:
            right_open = 1.0

        self.target_open_left = left_open
        self.target_open_right = right_open

    def _update_playful_double_wink(self, u: float, elapsed: float, dt: float) -> None:
        """Alternating playful double wink: Right wink -> brief neutral -> Left wink -> neutral."""
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

        left_open = 1.0
        right_open = 1.0

        # Sub-phase 1: Right wink (u: 0.05 to 0.42)
        if 0.05 <= u < 0.42:
            t = (u - 0.05) / 0.37
            if t < 0.35:
                right_open = 1.0 - cubic_in_out(t / 0.35)
            elif t < 0.65:
                right_open = 0.0
            else:
                right_open = quad_out((t - 0.65) / 0.35)
        # Sub-phase 2: Neutral transition (u: 0.42 to 0.52)
        elif 0.42 <= u < 0.52:
            left_open = 1.0
            right_open = 1.0
        # Sub-phase 3: Left wink (u: 0.52 to 0.90)
        elif 0.52 <= u < 0.90:
            t = (u - 0.52) / 0.38
            if t < 0.35:
                left_open = 1.0 - cubic_in_out(t / 0.35)
            elif t < 0.65:
                left_open = 0.0
            else:
                left_open = quad_out((t - 0.65) / 0.35)
        else:
            left_open = 1.0
            right_open = 1.0

        self.target_open_left = left_open
        self.target_open_right = right_open

    def _update_shy(self, u: float, elapsed: float, dt: float) -> None:
        """Shy: bashful downward/side glance, gentle eyelid droop, and subtle low-alpha blush."""
        if u < 0.25:
            t = u / 0.25
            look_x = -22.0 * cubic_in_out(t)
            look_y = 28.0 * cubic_in_out(t)
            open_val = 1.0 - 0.35 * quad_out(t)  # Droops to 0.65
            scale_val = DEFAULT_SCALE - 0.04 * quad_out(t)
            blush_alpha = 70.0 * quad_out(t)
        elif u < 0.65:
            # Bashful hold with gentle micro-repositioning
            micro_x = 2.5 * math.sin(2.0 * math.pi * 0.8 * elapsed)
            micro_y = 1.5 * math.cos(2.0 * math.pi * 0.8 * elapsed)
            look_x = -22.0 + micro_x
            look_y = 28.0 + micro_y
            open_val = 0.65
            scale_val = DEFAULT_SCALE - 0.04
            blush_alpha = 70.0
        elif u < 0.82:
            # Shy peek upward slightly
            t = (u - 0.65) / 0.17
            look_x = -22.0 + 10.0 * smoothstep(t)
            look_y = 28.0 - 12.0 * smoothstep(t)
            open_val = 0.65 + 0.13 * smoothstep(t)
            scale_val = DEFAULT_SCALE - 0.04 + 0.02 * smoothstep(t)
            blush_alpha = 70.0 - 40.0 * smoothstep(t)
        else:
            # Smoothly return to neutral
            t = (u - 0.82) / 0.18
            look_x = -12.0 * (1.0 - cubic_in_out(t))
            look_y = 16.0 * (1.0 - cubic_in_out(t))
            open_val = 0.78 + 0.22 * quad_out(t)
            scale_val = 0.98 + 0.02 * quad_out(t)
            blush_alpha = 30.0 * (1.0 - t)

        self.set_target_look(look_x, look_y)
        self.set_target_open(open_val, open_val)
        self.set_target_scale(scale_val)
        self.blush_state.alpha = blush_alpha

    def _update_happy_bounce(self, u: float, elapsed: float, dt: float) -> None:
        """Happy bounce: vertical rhythmic hopping with decaying amplitude."""
        self.set_target_open(1.0, 1.0)
        self.set_target_look(0.0, 0.0)
        self.set_target_scale(DEFAULT_SCALE)

        # Damped decaying vertical bounce: A * exp(-decay * elapsed) * |sin(omega * elapsed)|
        amplitude = 28.0
        decay_rate = 0.65
        frequency = 2.2 # Hz

        decay = math.exp(-decay_rate * elapsed)
        fade = 1.0 - smoothstep((u - 0.70) / 0.30) if u > 0.70 else 1.0
        bounce = -amplitude * decay * abs(math.sin(2.0 * math.pi * frequency * elapsed)) * fade

        self.offset_look_y = bounce

    def _update_cute_blush(self, u: float, elapsed: float, dt: float) -> None:
        """Cute blush: soft pink cheek strokes with smooth alpha fade in/out."""
        self.blush_state.set_normalized_progress(u)

        # Smooth bell envelope for relaxed open & scale & tilt returning to baseline at end
        env = math.sin(math.pi * clamp(u, 0.0, 1.0))
        open_val = 1.0 - 0.08 * env
        scale_val = DEFAULT_SCALE + 0.04 * env
        look_y = -5.0 * env

        self.set_target_open(open_val, open_val)
        self.set_target_scale(scale_val)
        self.set_target_look(0.0, look_y)

    def _update_thinking(self, u: float, elapsed: float, dt: float) -> None:
        """Thinking: upward sideways gaze drift, thoughtful half-blink/squint."""
        if u < 0.2:
            t = smoothstep(u / 0.2)
            look_x = 24.0 * t
            look_y = -34.0 * t
            open_val = 1.0 - 0.60 * t  # squints to 0.40
        elif u < 0.8:
            # Contemplative hold with subtle drift
            drift = 4.0 * math.sin(2.0 * math.pi * 0.4 * elapsed)
            look_x = 24.0 + drift
            look_y = -34.0 - drift * 0.5
            open_val = 0.40
        else:
            t = smoothstep((u - 0.8) / 0.2)
            look_x = (24.0 + 4.0 * math.sin(2.0 * math.pi * 0.4 * elapsed)) * (1.0 - t)
            look_y = (-34.0 - 2.0 * math.sin(2.0 * math.pi * 0.4 * elapsed)) * (1.0 - t)
            open_val = 0.40 + 0.60 * t

        self.set_target_look(look_x, look_y)
        self.set_target_open(open_val, open_val)

    def _update_suspicious(self, u: float, elapsed: float, dt: float) -> None:
        """Suspicious: deliberate slow sideways side-eye displacement (dx=+50), moderate narrow."""
        if u < 0.3:
            t = quad_out(u / 0.3)
            look_x = 50.0 * t
            look_y = 5.0 * t
            open_val = 1.0 - 0.52 * t  # narrows to 0.48
        elif u < 0.75:
            # Skeptical hold
            look_x = 50.0
            look_y = 5.0
            open_val = 0.48
        else:
            t = smoothstep((u - 0.75) / 0.25)
            look_x = 50.0 * (1.0 - t)
            look_y = 5.0 * (1.0 - t)
            open_val = 0.48 + 0.52 * t

        self.set_target_look(look_x, look_y)
        self.set_target_open(open_val, open_val)

    def _update_angry(self, u: float, elapsed: float, dt: float) -> None:
        """Angry: strong horizontal compression into narrow slits, focused downward hold, tension pulsing."""
        if u < 0.2:
            t = cubic_in_out(u / 0.2)
            open_val = 1.0 - 0.70 * t  # to 0.30
            scale_val = DEFAULT_SCALE - 0.06 * t # to 0.94
            look_y = 5.0 * t
        elif u < 0.8:
            # Locked tension micro-pulsing
            tension = 0.02 * math.cos(2.0 * math.pi * 5.0 * elapsed) # 5 Hz fast pulse
            open_val = 0.30 + tension
            scale_val = 0.94
            look_y = 5.0
        else:
            t = smoothstep((u - 0.8) / 0.2)
            open_val = 0.30 + 0.70 * t
            scale_val = 0.94 + 0.06 * t
            look_y = 5.0 * (1.0 - t)

        self.set_target_open(open_val, open_val)
        self.set_target_scale(scale_val)
        self.set_target_look(0.0, look_y)

    def _update_scared_nervous(self, u: float, elapsed: float, dt: float) -> None:
        """Scared/Nervous: Rapid scale enlargement with high-frequency nervous jitter/tremor in gaze."""
        if u < 0.15:
            t = elastic_out(u / 0.15)
            scale_val = DEFAULT_SCALE + 0.28 * t  # 1.28x
            open_val = 1.0
        elif u < 0.85:
            scale_val = 1.28
            open_val = 1.0
        else:
            t = quad_in((u - 0.85) / 0.15)
            scale_val = 1.28 - 0.28 * t
            open_val = 1.0

        jitter_x = 0.0
        jitter_y = 0.0
        if 0.15 <= u < 0.85:
            # High-frequency nervous tremor during hold
            jitter_x = 2.5 * math.sin(2.0 * math.pi * 14.0 * elapsed)
            jitter_y = 2.0 * math.cos(2.0 * math.pi * 16.0 * elapsed)
        elif u >= 0.85:
            # Smooth fade-out of micro-jitter during return
            fade = 1.0 - (u - 0.85) / 0.15
            jitter_x = 2.5 * math.sin(2.0 * math.pi * 14.0 * elapsed) * fade
            jitter_y = 2.0 * math.cos(2.0 * math.pi * 16.0 * elapsed) * fade

        self.set_target_scale(scale_val)
        self.set_target_open(open_val, open_val)
        self.set_target_look(jitter_x, jitter_y)

    def _update_sad(self, u: float, elapsed: float, dt: float) -> None:
        """Sad: Gradual droop to 0.52, heavy downward gaze (+34), deflated scale, sluggish breathing."""
        if u < 0.3:
            t = quad_out(u / 0.3)
            open_val = 1.0 - 0.48 * t  # droop to 0.52
            look_y = 34.0 * t
            scale_val = DEFAULT_SCALE - 0.06 * t  # deflate to 0.94
        elif u < 0.8:
            open_val = 0.52
            look_y = 34.0
            scale_val = 0.94
        else:
            t = quad_in((u - 0.8) / 0.2)
            open_val = 0.52 + 0.48 * t
            look_y = 34.0 * (1.0 - t)
            scale_val = 0.94 + 0.06 * t

        self.set_target_open(open_val, open_val)
        self.set_target_look(0.0, look_y)
        self.set_target_scale(scale_val)

    def _update_drowsy(self, u: float, elapsed: float, dt: float) -> None:
        """Drowsy: eyes droop to half-closed with gentle sleepy settling wobble."""
        self.set_target_scale(DEFAULT_SCALE)

        # Eye droop from 1.0 -> 0.38
        droop_target = 0.38
        droop_progress = smoothstep(clamp(u / 0.70, 0.0, 1.0))
        base_open = 1.0 - (1.0 - droop_target) * droop_progress

        # Settle factor ensures wobble and nod decay to zero as segment finishes
        settle_factor = 1.0 - smoothstep(clamp((u - 0.75) / 0.25, 0.0, 1.0))

        # Sleepy wobble
        wobble = 0.025 * math.sin(2.0 * math.pi * 0.55 * elapsed) * settle_factor
        open_val = clamp(base_open + wobble, 0.15, 1.0)

        # Gentle subtle head nod
        nod_y = 5.0 * math.sin(2.0 * math.pi * 0.45 * elapsed) * droop_progress * settle_factor

        self.target_open_left = open_val
        self.target_open_right = open_val
        self.set_target_look(0.0, nod_y)

    def _update_sleep(self, u: float, elapsed: float, dt: float) -> None:
        """Sleep: smoothly glides from drowsy droop down to fully closed, floating Z particles drift."""
        self.set_target_scale(DEFAULT_SCALE)
        self.set_target_look(0.0, 0.0)

        # Smooth closing from drowsy 0.38 baseline over the first 1.2s
        close_dur = 1.2
        if elapsed < close_dur:
            t = elapsed / close_dur
            open_val = 0.38 * (1.0 - cubic_in_out(t))
        else:
            open_val = 0.0

        self.target_open_left = open_val
        self.target_open_right = open_val

        # Spawn sleep particles up to 6.5s so remaining particles clear before loop
        is_spawning = elapsed < 6.5
        self.sleep_particles.update(dt, is_sleeping=is_spawning)

        # Slower calm breathing
        self.breathing_period = 5.5
        self.breathing_amp = 0.012

    # -----------------------------------------------------------------------
    # Main Update Loop
    # -----------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advances physics, smoothing, breathing, particles, and timeline progression."""
        if dt <= 0.0:
            return

        # 1. Update Timeline progression if timeline_driven
        if self.timeline_driven:
            seg_name, progress, _ = self.timeline.update(dt)
            handler = self._segment_handlers.get(seg_name)
            if handler:
                handler(progress, self.timeline.segment_elapsed, dt)
        else:
            # Manual mode: update sleep particles if active
            self.sleep_particles.update(dt, is_sleeping=False)

        # 2. Smooth continuous interpolation towards targets
        self.current_look_x = exp_decay(self.current_look_x, self.target_look_x, self.smooth_rate_look, dt)
        self.current_look_y = exp_decay(self.current_look_y, self.target_look_y, self.smooth_rate_look, dt)
        self.current_scale = exp_decay(self.current_scale, self.target_scale, self.smooth_rate_scale, dt)
        self.current_open_left = exp_decay(self.current_open_left, self.target_open_left, self.smooth_rate_open, dt)
        self.current_open_right = exp_decay(self.current_open_right, self.target_open_right, self.smooth_rate_open, dt)

        # 3. Update breathing oscillation
        breath_scale_offset = 0.0
        if self.breathing_enabled:
            self.breathing_time += dt
            breath_scale_offset = (
                math.sin(2.0 * math.pi * (self.breathing_time / self.breathing_period))
                * self.breathing_amp
            )

        # 4. Update manual blink state
        blink_mult = self.blink.update(dt)

        # 5. Composite final parameters and feed to EyePair
        final_open_l = clamp(self.current_open_left * blink_mult, 0.0, 1.0)
        final_open_r = clamp(self.current_open_right * blink_mult, 0.0, 1.0)
        final_scale = clamp(self.current_scale + breath_scale_offset, MIN_SCALE, MAX_SCALE)
        final_look_x = self.current_look_x + self.offset_look_x
        final_look_y = self.current_look_y + self.offset_look_y

        self.eye_pair.left_eye.set_open(final_open_l)
        self.eye_pair.right_eye.set_open(final_open_r)
        self.eye_pair.set_look(final_look_x, final_look_y)
        self.eye_pair.set_scale(final_scale)
