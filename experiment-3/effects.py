"""Effects and overlay modules for ELO Face V3.

Contains:
1. IntroState: Typewriter text ("Hii", "This is ELO.") with cursor blinking and smooth alpha fade.
2. BlushState: Cute soft pink rounded cheek strokes with smooth opacity envelope.
3. SleepZParticles: Floating, drifting, swaying 'Z' particles during sleep.
4. ConfusedOverlayState: Question-mark visual accents above eyes during Confused emotion.
5. ThinkingCloudState: Minimalist thought-cloud animation above eyes during Thinking emotion.
"""

import math
import random
from typing import List, Tuple, Optional

from config import (
    BLUSH_MAX_ALPHA,
    SLEEP_PARTICLE_SPAWN_INTERVAL,
    SLEEP_PARTICLE_LIFETIME,
    SLEEP_PARTICLE_SPEED_Y,
    SLEEP_PARTICLE_DRIFT_AMP,
    SLEEP_PARTICLE_DRIFT_FREQ,
    SLEEP_SPAWN_X_MIN,
    SLEEP_SPAWN_X_MAX,
    SLEEP_SPAWN_Y,
    CONFUSED_Q_SPECS,
    CONFUSED_Q_BOB_AMP,
    CONFUSED_Q_BOB_PERIOD,
    THINKING_CLOUD_CX,
    THINKING_CLOUD_CY,
    THINKING_CLOUD_BASE_R,
    THINKING_CLOUD_BOB_AMP,
    THINKING_CLOUD_BOB_PERIOD,
)
from easing import clamp, smoothstep


class IntroState:
    """Manages the 10-second polished typewriter intro sequence."""

    TEXT_1 = "Hii"
    TEXT_2 = "This is ELO."

    def __init__(self) -> None:
        self.text_to_show: str = ""
        self.show_cursor: bool = False
        self.text_alpha: float = 0.0      # 0.0 to 1.0
        self.face_alpha: float = 0.0      # 0.0 to 1.0 (face fade-in at end of intro)
        self.cursor_blink_rate: float = 0.35 # seconds per cursor blink toggle

    def reset(self) -> None:
        self.text_to_show = ""
        self.show_cursor = False
        self.text_alpha = 0.0
        self.face_alpha = 0.0

    def update(self, elapsed: float) -> None:
        """Updates intro text state based on elapsed segment time in seconds."""
        # -------------------------------------------------------------------
        # Phase 1: "Hii" (0.0s to 4.2s)
        # -------------------------------------------------------------------
        if elapsed < 4.2:
            self.face_alpha = 0.0
            typewriter_dur = 0.6
            hold_end = 3.2
            fade_dur = 1.0

            # Typewriter character reveal
            if elapsed < typewriter_dur:
                char_count = int((elapsed / typewriter_dur) * len(self.TEXT_1))
                char_count = max(1, min(len(self.TEXT_1), char_count + 1))
                self.text_to_show = self.TEXT_1[:char_count]
                self.text_alpha = 1.0
            elif elapsed < hold_end:
                self.text_to_show = self.TEXT_1
                self.text_alpha = 1.0
            else:
                # Fade out
                fade_progress = (elapsed - hold_end) / fade_dur
                self.text_to_show = self.TEXT_1
                self.text_alpha = 1.0 - smoothstep(fade_progress)

            # Cursor blinking (visible while typing & holding)
            if elapsed < hold_end:
                self.show_cursor = int(elapsed / self.cursor_blink_rate) % 2 == 0
            else:
                self.show_cursor = False

        # -------------------------------------------------------------------
        # Phase 2: "This is ELO." (4.2s to 8.8s)
        # -------------------------------------------------------------------
        elif elapsed < 8.8:
            self.face_alpha = 0.0
            local_t = elapsed - 4.2
            typewriter_dur = 1.2
            hold_end = 3.6  # local time (elapsed = 7.8s)
            fade_dur = 1.0

            if local_t < typewriter_dur:
                char_count = int((local_t / typewriter_dur) * len(self.TEXT_2))
                char_count = max(1, min(len(self.TEXT_2), char_count + 1))
                self.text_to_show = self.TEXT_2[:char_count]
                self.text_alpha = 1.0
            elif local_t < hold_end:
                self.text_to_show = self.TEXT_2
                self.text_alpha = 1.0
            else:
                fade_progress = (local_t - hold_end) / fade_dur
                self.text_to_show = self.TEXT_2
                self.text_alpha = 1.0 - smoothstep(fade_progress)

            if local_t < hold_end:
                self.show_cursor = int(local_t / self.cursor_blink_rate) % 2 == 0
            else:
                self.show_cursor = False

        # -------------------------------------------------------------------
        # Phase 3: Transition to Face (8.8s to 10.0s)
        # -------------------------------------------------------------------
        else:
            self.text_to_show = ""
            self.show_cursor = False
            self.text_alpha = 0.0
            transition_t = (elapsed - 8.8) / 1.2
            self.face_alpha = smoothstep(clamp(transition_t, 0.0, 1.0))


class BlushState:
    """Manages the alpha opacity of the cute pink cheek strokes."""

    def __init__(self) -> None:
        self.alpha: float = 0.0 # 0.0 to 255.0

    def reset(self) -> None:
        self.alpha = 0.0

    def set_normalized_progress(self, u: float) -> None:
        """Sets blush opacity following a smooth bell-shaped curve across segment progress u in [0, 1]."""
        u = clamp(u, 0.0, 1.0)
        # Bell curve: rises smoothly 0->1 in first 35%, holds, fades out in last 35%
        if u < 0.35:
            envelope = smoothstep(u / 0.35)
        elif u < 0.65:
            envelope = 1.0
        else:
            envelope = 1.0 - smoothstep((u - 0.65) / 0.35)

        self.alpha = envelope * BLUSH_MAX_ALPHA


class SleepZParticle:
    """Represents a single floating 'Z' particle."""

    def __init__(self, x: float, y: float, size: int = 22) -> None:
        self.base_x: float = x
        self.x: float = x
        self.y: float = y
        self.size: int = size
        self.age: float = 0.0
        self.lifetime: float = SLEEP_PARTICLE_LIFETIME
        self.phase_offset: float = random.uniform(0.0, 2.0 * math.pi)

    def update(self, dt: float) -> bool:
        """Updates particle motion and returns False when expired."""
        self.age += dt
        if self.age >= self.lifetime:
            return False

        # Upward motion
        self.y -= SLEEP_PARTICLE_SPEED_Y * dt

        # Gentle horizontal sinusoidal sway
        self.x = self.base_x + math.sin(self.age * 2.0 * math.pi * SLEEP_PARTICLE_DRIFT_FREQ + self.phase_offset) * SLEEP_PARTICLE_DRIFT_AMP
        return True

    @property
    def alpha(self) -> int:
        """Calculates particle opacity (fades in quickly, holds, then fades out)."""
        prog = self.age / self.lifetime
        if prog < 0.20:
            factor = prog / 0.20
        elif prog < 0.70:
            factor = 1.0
        else:
            factor = 1.0 - (prog - 0.70) / 0.30
        return int(clamp(factor, 0.0, 1.0) * 220)


class SleepZParticles:
    """Manages the pool of active sleep 'Z' particles."""

    def __init__(self) -> None:
        self.particles: List[SleepZParticle] = []
        self.spawn_timer: float = 0.0

    def reset(self) -> None:
        self.particles.clear()
        self.spawn_timer = 0.0

    def spawn(self) -> None:
        x = random.uniform(SLEEP_SPAWN_X_MIN, SLEEP_SPAWN_X_MAX)
        y = SLEEP_SPAWN_Y + random.uniform(-10.0, 10.0)
        size = random.choice([18, 22, 26])
        self.particles.append(SleepZParticle(x, y, size))

    def update(self, dt: float, is_sleeping: bool) -> None:
        """Advances active particles and spawns new ones if sleep is active."""
        # Update existing particles
        self.particles = [p for p in self.particles if p.update(dt)]

        if is_sleeping:
            self.spawn_timer += dt
            if self.spawn_timer >= SLEEP_PARTICLE_SPAWN_INTERVAL:
                self.spawn_timer = 0.0
                self.spawn()
        else:
            self.spawn_timer = 0.0


class ConfusedOverlayState:
    """Manages question-mark visual accents above the eyes during Confused emotion."""

    def __init__(self) -> None:
        self.alpha: float = 0.0          # 0.0 to 255.0
        self.elapsed: float = 0.0
        self.marks: List[Tuple[float, float, int, float]] = list(CONFUSED_Q_SPECS)
        self.y_offset: float = 0.0

    def reset(self) -> None:
        self.alpha = 0.0
        self.elapsed = 0.0
        self.y_offset = 0.0

    def update(self, elapsed: float, u: float) -> None:
        """Updates question-mark alpha and motion envelope based on segment progress u in [0, 1]."""
        u = clamp(u, 0.0, 1.0)
        self.elapsed = elapsed

        # 3-phase envelope across 4.5s segment:
        # 1. Entrance (u in [0.0, 0.20]): smooth fade in (0 -> 255) & upward float into position
        # 2. Active hold (u in [0.20, 0.80]): full opacity 255, organic bobbing
        # 3. Exit (u in [0.80, 1.00]): smooth fade out (255 -> 0) & gentle upward dissolve
        if u < 0.20:
            t = u / 0.20
            self.alpha = smoothstep(t) * 255.0
            self.y_offset = (1.0 - smoothstep(t)) * 10.0
        elif u < 0.80:
            self.alpha = 255.0
            self.y_offset = 0.0
        else:
            t = (u - 0.80) / 0.20
            self.alpha = (1.0 - smoothstep(t)) * 255.0
            self.y_offset = -smoothstep(t) * 6.0


class ThinkingCloudState:
    """Manages minimalist thought-cloud animation above eyes during Thinking emotion."""

    def __init__(self) -> None:
        self.cloud_scale: float = 0.0    # 0.0 to 1.0
        self.cloud_alpha: float = 0.0    # 0.0 to 255.0
        self.dot1_scale: float = 0.0     # 0.0 to 1.0 (lower bubble)
        self.dot1_alpha: float = 0.0     # 0.0 to 255.0
        self.dot2_scale: float = 0.0     # 0.0 to 1.0 (upper bubble)
        self.dot2_alpha: float = 0.0     # 0.0 to 255.0
        self.elapsed: float = 0.0
        self.bob_y: float = 0.0

    def reset(self) -> None:
        self.cloud_scale = 0.0
        self.cloud_alpha = 0.0
        self.dot1_scale = 0.0
        self.dot1_alpha = 0.0
        self.dot2_scale = 0.0
        self.dot2_alpha = 0.0
        self.elapsed = 0.0
        self.bob_y = 0.0

    def update(self, elapsed: float, u: float) -> None:
        """Updates thought cloud and bubble elements based on segment progress u in [0, 1]."""
        u = clamp(u, 0.0, 1.0)
        self.elapsed = elapsed

        # 1. Bubble 1 (lower, near eye): emerges earliest (u: 0.02 to 0.12), holds, fades (u: 0.80 to 0.95)
        if u < 0.02:
            self.dot1_scale = 0.0
            self.dot1_alpha = 0.0
        elif u < 0.12:
            t = (u - 0.02) / 0.10
            self.dot1_scale = smoothstep(t)
            self.dot1_alpha = smoothstep(t) * 255.0
        elif u < 0.80:
            self.dot1_scale = 1.0
            self.dot1_alpha = 255.0
        elif u < 0.95:
            t = (u - 0.80) / 0.15
            self.dot1_scale = 1.0 - smoothstep(t)
            self.dot1_alpha = (1.0 - smoothstep(t)) * 255.0
        else:
            self.dot1_scale = 0.0
            self.dot1_alpha = 0.0

        # 2. Bubble 2 (middle): emerges slightly after dot 1 (u: 0.06 to 0.16), holds, fades (u: 0.80 to 0.96)
        if u < 0.06:
            self.dot2_scale = 0.0
            self.dot2_alpha = 0.0
        elif u < 0.16:
            t = (u - 0.06) / 0.10
            self.dot2_scale = smoothstep(t)
            self.dot2_alpha = smoothstep(t) * 255.0
        elif u < 0.80:
            self.dot2_scale = 1.0
            self.dot2_alpha = 255.0
        elif u < 0.96:
            t = (u - 0.80) / 0.16
            self.dot2_scale = 1.0 - smoothstep(t)
            self.dot2_alpha = (1.0 - smoothstep(t)) * 255.0
        else:
            self.dot2_scale = 0.0
            self.dot2_alpha = 0.0

        # 3. Main Cloud: emerges after bubbles (u: 0.10 to 0.22), holds (0.22 to 0.80), dissolves (0.80 to 1.00)
        if u < 0.10:
            self.cloud_scale = 0.0
            self.cloud_alpha = 0.0
        elif u < 0.22:
            t = (u - 0.10) / 0.12
            self.cloud_scale = smoothstep(t)
            self.cloud_alpha = smoothstep(t) * 255.0
        elif u < 0.80:
            self.cloud_scale = 1.0
            self.cloud_alpha = 255.0
        else:
            t = (u - 0.80) / 0.20
            self.cloud_scale = 1.0 - smoothstep(t) * 0.4
            self.cloud_alpha = (1.0 - smoothstep(t)) * 255.0

        # Subtle floating bob during active phase
        if 0.10 <= u < 0.90:
            self.bob_y = THINKING_CLOUD_BOB_AMP * math.sin(2.0 * math.pi * elapsed / THINKING_CLOUD_BOB_PERIOD)
        else:
            self.bob_y = 0.0

