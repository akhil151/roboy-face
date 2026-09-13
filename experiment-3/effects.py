"""Effects and overlay modules for ELO Face V3.

Contains:
1. IntroState: Typewriter text ("Hii", "This is ELO.") with cursor blinking and smooth alpha fade.
2. BlushState: Cute soft pink rounded cheek strokes with smooth opacity envelope.
3. SleepZParticles: Floating, drifting, swaying 'Z' particles during sleep.
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
