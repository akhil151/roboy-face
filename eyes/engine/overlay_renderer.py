"""
Procedural Emotion Overlay Layer (EffectsRenderer).

Draws vector emotional accents ON TOP of eye geometry using RenderContext.
All graphics are purely procedural (pygame.draw / pygame.gfxdraw) with zero asset files.

Overlay effects manage their own lifecycles:
- spawn probability
- lifetime
- fade in / fade out
- cooldown
- optional enabled flag
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple
import pygame
import pygame.gfxdraw

from .config import EngineConfig
from .eye_pair import EyePair
from .render_context import RenderContext


class Particle:
    """Generic lifecycle particle for procedural overlays."""

    def __init__(
        self,
        x: float,
        y: float,
        lifetime_s: float,
        fade_in_s: float = 0.2,
        fade_out_s: float = 0.3,
        vx: float = 0.0,
        vy: float = 0.0,
        scale: float = 1.0,
        variant: int = 0,
    ) -> None:
        self.x = x
        self.y = y
        self.initial_x = x
        self.initial_y = y
        self.lifetime_s = lifetime_s
        self.fade_in_s = fade_in_s
        self.fade_out_s = fade_out_s
        self.vx = vx
        self.vy = vy
        self.scale = scale
        self.variant = variant
        self.age_s = 0.0
        self.dead = False

    def update(self, dt_s: float) -> None:
        self.age_s += dt_s
        self.x += self.vx * dt_s
        self.y += self.vy * dt_s
        if self.age_s >= self.lifetime_s:
            self.dead = True

    @property
    def alpha(self) -> float:
        if self.dead or self.lifetime_s <= 0.0:
            return 0.0
        if self.age_s < self.fade_in_s:
            return max(0.0, min(1.0, self.age_s / max(0.001, self.fade_in_s)))
        remain = self.lifetime_s - self.age_s
        if remain < self.fade_out_s:
            return max(0.0, min(1.0, remain / max(0.001, self.fade_out_s)))
        return 1.0


class OverlayRenderer:
    """Dedicated procedural overlay renderer for secondary emotional accents."""

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.enabled: bool = True
        self.global_intensity: float = 1.0

        # Subsystem state timers & cooldowns
        self._sleepy_particles: List[Particle] = []
        self._sleepy_cooldown: float = 0.0

        self._thinking_particle: Optional[Particle] = None
        self._thinking_cooldown: float = 0.0

        self._happy_particles: List[Particle] = []
        self._happy_cooldown: float = 0.0

        self._surprised_burst: Optional[Particle] = None
        self._caring_particles: List[Particle] = []
        self._caring_cooldown: float = 0.0

    def draw(
        self,
        surface: pygame.Surface,
        pose: EyePair,
        ctx: RenderContext,
    ) -> None:
        """Render vector overlay layer on top of the eyes."""
        if not self.enabled:
            return

        state = ctx.current_state
        effective_intensity = ctx.overlay_intensity * self.global_intensity * ctx.blend_progress
        if effective_intensity <= 0.001:
            return

        dt_s = ctx.dt_s
        elapsed_s = ctx.elapsed_s

        # Spatial reference coordinates from EyePair
        l_cx, l_cy = pose.left.pos_x + pose.left.look_offset_x, pose.left.pos_y + pose.left.look_offset_y
        r_cx, r_cy = pose.right.pos_x + pose.right.look_offset_x, pose.right.pos_y + pose.right.look_offset_y
        center_x = (l_cx + r_cx) * 0.5
        center_y = (l_cy + r_cy) * 0.5
        eye_r = (pose.left.radius + pose.right.radius) * 0.5

        if state == "sleepy":
            self._draw_sleepy(surface, r_cx, r_cy, eye_r, dt_s, effective_intensity)
        elif state == "thinking":
            self._draw_thinking(surface, r_cx, r_cy, eye_r, dt_s, elapsed_s, effective_intensity)
        elif state == "happy":
            self._draw_happy(surface, l_cx, l_cy, r_cx, r_cy, eye_r, dt_s, effective_intensity)
        elif state == "speaking":
            self._draw_speaking(surface, center_x, center_y, eye_r, ctx.speech_pulse, elapsed_s, effective_intensity)
        elif state == "surprised":
            self._draw_surprised(surface, center_x, center_y, eye_r, dt_s, ctx.blend_progress, effective_intensity)
        elif state == "caring":
            self._draw_caring(surface, center_x, center_y, eye_r, dt_s, elapsed_s, effective_intensity)
        elif state == "focus":
            self._draw_focus(surface, pose, center_x, center_y, elapsed_s, effective_intensity)

    # ------------------------------------------------------------------
    # 1. Sleepy Overlay: Procedural ZZZ floating upwards with lifecycle
    # ------------------------------------------------------------------
    def _draw_sleepy(
        self,
        surface: pygame.Surface,
        r_cx: float,
        r_cy: float,
        r: float,
        dt_s: float,
        intensity: float,
    ) -> None:
        self._sleepy_cooldown -= dt_s
        if self._sleepy_cooldown <= 0.0 and len(self._sleepy_particles) < 3:
            # Spawn a new Z symbol
            sx = r_cx + random.uniform(r * 0.4, r * 0.8)
            sy = r_cy - random.uniform(r * 0.2, r * 0.5)
            scale = random.uniform(0.7, 1.2)
            p = Particle(
                x=sx,
                y=sy,
                lifetime_s=random.uniform(2.0, 2.8),
                fade_in_s=0.4,
                fade_out_s=0.6,
                vx=random.uniform(8.0, 16.0),
                vy=random.uniform(-25.0, -18.0),
                scale=scale,
            )
            self._sleepy_particles.append(p)
            self._sleepy_cooldown = random.uniform(0.6, 1.0)

        alive: List[Particle] = []
        for p in self._sleepy_particles:
            p.update(dt_s)
            if not p.dead:
                alive.append(p)
                a = p.alpha * intensity
                if a > 0.01:
                    self._draw_vector_z(surface, p.x, p.y, scale=p.scale * 12.0, alpha=a)
        self._sleepy_particles = alive

    def _draw_vector_z(
        self, surface: pygame.Surface, x: float, y: float, scale: float, alpha: float
    ) -> None:
        col = (int(220 * alpha), int(230 * alpha), int(255 * alpha))
        w = scale * 0.8
        h = scale
        pts = [
            (int(x - w * 0.5), int(y - h * 0.5)),
            (int(x + w * 0.5), int(y - h * 0.5)),
            (int(x - w * 0.5), int(y + h * 0.5)),
            (int(x + w * 0.5), int(y + h * 0.5)),
        ]
        try:
            pygame.draw.lines(surface, col, False, pts, max(1, int(round(scale * 0.18))))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 2. Thinking Overlay: Single elegant procedural question mark with orbital path
    # ------------------------------------------------------------------
    def _draw_thinking(
        self,
        surface: pygame.Surface,
        r_cx: float,
        r_cy: float,
        r: float,
        dt_s: float,
        elapsed_s: float,
        intensity: float,
    ) -> None:
        if self._thinking_particle is None or self._thinking_particle.dead:
            self._thinking_cooldown -= dt_s
            if self._thinking_cooldown <= 0.0:
                self._thinking_particle = Particle(
                    x=r_cx + r * 0.7,
                    y=r_cy - r * 0.8,
                    lifetime_s=3.2,
                    fade_in_s=0.5,
                    fade_out_s=0.6,
                )
                self._thinking_cooldown = 1.2
        else:
            self._thinking_particle.update(dt_s)

        p = self._thinking_particle
        if p and not p.dead:
            a = p.alpha * intensity
            if a > 0.01:
                # Orbital movement around upper right corner of eye
                orbit_angle = elapsed_s * 1.5
                ox = r_cx + r * 0.75 + math.cos(orbit_angle) * 10.0
                oy = r_cy - r * 0.85 + math.sin(orbit_angle * 0.7) * 6.0
                self._draw_vector_question(surface, ox, oy, scale=18.0, alpha=a)

    def _draw_vector_question(
        self, surface: pygame.Surface, x: float, y: float, scale: float, alpha: float
    ) -> None:
        color = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
        r = scale * 0.35
        cx, cy = x, y - scale * 0.2
        steps = 14
        pts = []
        # Question mark upper arc
        for i in range(steps + 1):
            t = -math.pi * 0.75 + (i / steps) * math.pi * 1.25
            px = cx + math.cos(t) * r
            py = cy + math.sin(t) * r
            pts.append((int(round(px)), int(round(py))))

        # Stem curve down
        pts.append((int(round(x)), int(round(y + scale * 0.15))))
        pts.append((int(round(x)), int(round(y + scale * 0.32))))

        try:
            pygame.draw.lines(surface, color, False, pts, max(1, int(round(scale * 0.14))))
            # Dot underneath
            dot_y = int(round(y + scale * 0.52))
            dot_r = max(1, int(round(scale * 0.09)))
            pygame.gfxdraw.aacircle(surface, int(round(x)), dot_y, dot_r, color)
            pygame.gfxdraw.filled_circle(surface, int(round(x)), dot_y, dot_r, color)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 3. Happy Overlay: Tiny procedural glints near eye corners
    # ------------------------------------------------------------------
    def _draw_happy(
        self,
        surface: pygame.Surface,
        l_cx: float,
        l_cy: float,
        r_cx: float,
        r_cy: float,
        r: float,
        dt_s: float,
        intensity: float,
    ) -> None:
        self._happy_cooldown -= dt_s
        if self._happy_cooldown <= 0.0 and len(self._happy_particles) < 4:
            # Spawn glints near outer corners of left and right eyes
            is_left = random.choice([True, False])
            base_x = (l_cx - r * 0.8) if is_left else (r_cx + r * 0.8)
            base_y = (l_cy - r * 0.4) if is_left else (r_cy - r * 0.4)
            p = Particle(
                x=base_x + random.uniform(-8, 8),
                y=base_y + random.uniform(-8, 8),
                lifetime_s=random.uniform(0.8, 1.4),
                fade_in_s=0.25,
                fade_out_s=0.3,
                scale=random.uniform(0.8, 1.2),
            )
            self._happy_particles.append(p)
            self._happy_cooldown = random.uniform(0.3, 0.6)

        alive: List[Particle] = []
        for p in self._happy_particles:
            p.update(dt_s)
            if not p.dead:
                alive.append(p)
                a = p.alpha * intensity
                if a > 0.01:
                    self._draw_glint(surface, p.x, p.y, size=p.scale * 10.0, alpha=a)
        self._happy_particles = alive

    def _draw_glint(
        self, surface: pygame.Surface, x: float, y: float, size: float, alpha: float
    ) -> None:
        color = (int(255 * alpha), int(255 * alpha), int(230 * alpha))
        ix, iy = int(round(x)), int(round(y))
        half = size * 0.5
        try:
            # Cross diagonal glint lines
            pygame.draw.line(surface, color, (int(ix - half), iy), (int(ix + half), iy), 2)
            pygame.draw.line(surface, color, (ix, int(iy - half)), (ix, int(iy + half)), 2)
            pygame.gfxdraw.filled_circle(surface, ix, iy, max(1, int(size * 0.15)), color)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 4. Speaking Overlay: Tiny rhythmic speech pulse indicators
    # ------------------------------------------------------------------
    def _draw_speaking(
        self,
        surface: pygame.Surface,
        center_x: float,
        center_y: float,
        r: float,
        speech_pulse: float,
        elapsed_s: float,
        intensity: float,
    ) -> None:
        eff_pulse = max(0.1, min(1.0, speech_pulse if speech_pulse > 0 else (0.5 + 0.5 * math.sin(elapsed_s * 12.0))))
        a = intensity * 0.85
        if a <= 0.01:
            return

        color = (int(255 * a), int(255 * a), int(255 * a))
        bar_y = center_y + r * 1.05
        bar_count = 5
        gap = 10.0
        start_x = center_x - ((bar_count - 1) * gap) * 0.5

        for i in range(bar_count):
            dist_from_center = abs(i - 2) / 2.0
            height_factor = (1.0 - dist_from_center * 0.4) * eff_pulse
            h = max(4.0, 18.0 * height_factor)
            bx = int(round(start_x + i * gap))
            by1 = int(round(bar_y - h * 0.5))
            by2 = int(round(bar_y + h * 0.5))
            try:
                pygame.draw.line(surface, color, (bx, by1), (bx, by2), 3)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 5. Surprised Overlay: Minimal radial burst
    # ------------------------------------------------------------------
    def _draw_surprised(
        self,
        surface: pygame.Surface,
        center_x: float,
        center_y: float,
        r: float,
        dt_s: float,
        blend_t: float,
        intensity: float,
    ) -> None:
        if self._surprised_burst is None or self._surprised_burst.dead:
            self._surprised_burst = Particle(
                x=center_x,
                y=center_y,
                lifetime_s=0.6,
                fade_in_s=0.1,
                fade_out_s=0.3,
            )
        else:
            self._surprised_burst.update(dt_s)

        p = self._surprised_burst
        if p and not p.dead:
            a = p.alpha * intensity
            if a > 0.01:
                progress = p.age_s / p.lifetime_s
                burst_r1 = r * (1.1 + progress * 0.4)
                burst_r2 = burst_r1 + 12.0
                ray_count = 8
                color = (int(255 * a), int(255 * a), int(255 * a))
                for i in range(ray_count):
                    ang = (i / ray_count) * math.pi * 2.0
                    x1 = int(round(center_x + math.cos(ang) * burst_r1))
                    y1 = int(round(center_y + math.sin(ang) * burst_r1))
                    x2 = int(round(center_x + math.cos(ang) * burst_r2))
                    y2 = int(round(center_y + math.sin(ang) * burst_r2))
                    try:
                        pygame.draw.line(surface, color, (x1, y1), (x2, y2), 2)
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # 6. Caring Overlay: Subtle halo / rounded diamond accents
    # ------------------------------------------------------------------
    def _draw_caring(
        self,
        surface: pygame.Surface,
        center_x: float,
        center_y: float,
        r: float,
        dt_s: float,
        elapsed_s: float,
        intensity: float,
    ) -> None:
        self._caring_cooldown -= dt_s
        if self._caring_cooldown <= 0.0 and len(self._caring_particles) < 3:
            p = Particle(
                x=center_x + random.uniform(-r * 0.8, r * 0.8),
                y=center_y - r * (0.8 + random.uniform(0.0, 0.3)),
                lifetime_s=random.uniform(2.0, 3.0),
                fade_in_s=0.5,
                fade_out_s=0.7,
                vy=-12.0,
                scale=random.uniform(0.8, 1.2),
            )
            self._caring_particles.append(p)
            self._caring_cooldown = random.uniform(0.7, 1.2)

        alive: List[Particle] = []
        for p in self._caring_particles:
            p.update(dt_s)
            if not p.dead:
                alive.append(p)
                a = p.alpha * intensity
                if a > 0.01:
                    self._draw_soft_diamond(surface, p.x, p.y, size=p.scale * 10.0, alpha=a)
        self._caring_particles = alive

        # Soft halo arc above the eyes
        halo_a = intensity * (0.4 + 0.2 * math.sin(elapsed_s * 2.0))
        if halo_a > 0.01:
            h_color = (int(255 * halo_a), int(240 * halo_a), int(250 * halo_a))
            rect = pygame.Rect(
                int(center_x - r * 1.2),
                int(center_y - r * 1.3),
                int(r * 2.4),
                int(r * 0.8),
            )
            try:
                pygame.draw.arc(surface, h_color, rect, math.pi * 0.2, math.pi * 0.8, 2)
            except Exception:
                pass

    def _draw_soft_diamond(
        self, surface: pygame.Surface, x: float, y: float, size: float, alpha: float
    ) -> None:
        col = (int(255 * alpha), int(235 * alpha), int(245 * alpha))
        h = size * 0.5
        w = size * 0.4
        pts = [
            (int(x), int(y - h)),
            (int(x + w), int(y)),
            (int(x), int(y + h)),
            (int(x - w), int(y)),
        ]
        try:
            pygame.gfxdraw.aapolygon(surface, pts, col)
            pygame.gfxdraw.filled_polygon(surface, pts, col)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 7. Focus Overlay: Camera-style corner brackets (┌ ┐ └ ┘)
    # ------------------------------------------------------------------
    def _draw_focus(
        self,
        surface: pygame.Surface,
        pose: EyePair,
        center_x: float,
        center_y: float,
        elapsed_s: float,
        intensity: float,
    ) -> None:
        a = intensity * 0.90
        if a <= 0.01:
            return

        color = (int(255 * a), int(255 * a), int(255 * a))

        # Bounding box around both eyes with subtle pulse
        pulse = math.sin(elapsed_s * 4.0) * 3.0
        left_x = pose.left.pos_x - pose.left.radius * 1.2 - pulse
        right_x = pose.right.pos_x + pose.right.radius * 1.2 + pulse
        top_y = min(pose.left.pos_y, pose.right.pos_y) - pose.left.radius * 1.0 - pulse
        bot_y = max(pose.left.pos_y, pose.right.pos_y) + pose.left.radius * 1.0 + pulse

        arm = 18.0
        thick = 2

        l, r, t, b = int(left_x), int(right_x), int(top_y), int(bot_y)

        try:
            # Top-Left ┌
            pygame.draw.line(surface, color, (l, t), (l + int(arm), t), thick)
            pygame.draw.line(surface, color, (l, t), (l, t + int(arm)), thick)

            # Top-Right ┐
            pygame.draw.line(surface, color, (r, t), (r - int(arm), t), thick)
            pygame.draw.line(surface, color, (r, t), (r, t + int(arm)), thick)

            # Bottom-Left └
            pygame.draw.line(surface, color, (l, b), (l + int(arm), b), thick)
            pygame.draw.line(surface, color, (l, b), (l, b - int(arm)), thick)

            # Bottom-Right ┘
            pygame.draw.line(surface, color, (r, b), (r - int(arm), b), thick)
            pygame.draw.line(surface, color, (r, b), (r, b - int(arm)), thick)
        except Exception:
            pass
