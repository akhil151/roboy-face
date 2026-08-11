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

from .config import EngineConfig, OverlayConfig
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
        self.overlay_config: OverlayConfig = config.overlay
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

        # Track state entry for persistent thinking cue reset
        self._last_state: Optional[str] = None

    def set_overlay_config(self, config: OverlayConfig) -> None:
        """Hot-swap the overlay configuration (used by the showcase for
        the Q key legacy/polished toggle; never by LES).
        """
        self.overlay_config = config

    # ------------------------------------------------------------------
    # Face-space geometry helpers (LES-09B.4 + LES-09B.5)
    #
    # Both the thinking "?" and the sleepy ZZZ are placed in FACE SPACE
    # derived from the actual eye layout - never in the moving eye's local
    # frame, never at a fixed screen coordinate. Since LES-09B.5 the
    # thinking "?" hugs the selected eye's OUTER PERIMETER corner (via
    # ``thinking_anchor`` below) instead of floating centred above the
    # face; its scale is unchanged. The rendered-eye math mirrors
    # eyes/engine/renderer.py ``_effective_pos`` / ``_effective_radius``
    # (the exact functions that draw the sclera), so the regions below
    # are truthful to what is actually rendered.
    # ------------------------------------------------------------------

    @staticmethod
    def eye_silhouette_region(eye) -> Tuple[float, float, float, float]:
        """Axis-aligned box of one RENDERED eye: (left, top, right, bottom).

        Mirrors ``Renderer._effective_pos`` (pos + look + micro + bounce
        offsets) and ``Renderer._effective_radius`` (radius * scale with
        squash/stretch applied), plus the ``EyePair.clamp_safe`` rotation
        inflation so the box is valid even for rotated eyes. This is the
        white silhouette the (white) cue glyphs would blend into - the
        black eyelid masks are the same colour as the background and do
        not extend the visible silhouette.
        """
        cx = eye.pos_x + eye.look_offset_x + eye.micro_offset_x + eye.bounce_offset_x
        cy = eye.pos_y + eye.look_offset_y + eye.micro_offset_y + eye.bounce_offset_y
        sx = max(0.01, eye.scale_x + eye.stretch - eye.squash * 0.5)
        sy = max(0.01, eye.scale_y + eye.squash - eye.stretch * 0.5)
        rx = eye.radius * sx
        ry = eye.radius * sy
        cos_r = abs(math.cos(eye.rotation))
        sin_r = abs(math.sin(eye.rotation))
        ext_x = rx * cos_r + ry * sin_r
        ext_y = rx * sin_r + ry * cos_r
        return (cx - ext_x, cy - ext_y, cx + ext_x, cy + ext_y)

    def eye_pair_regions(self, pose) -> Tuple[Tuple[float, float, float, float], ...]:
        """The rendered silhouette boxes of both eyes for a composed pose."""
        return (self.eye_silhouette_region(pose.left),
                self.eye_silhouette_region(pose.right))

    @staticmethod
    def regions_intersect(a: Tuple[float, float, float, float],
                          b: Tuple[float, float, float, float],
                          margin_px: float = 0.0) -> bool:
        """True when axis-aligned boxes ``a`` and ``b`` intersect.

        ``margin_px`` inflates ``a`` before the test (a configurable
        safety margin - never a hidden magic number).
        """
        al, at, ar, ab = a
        bl, bt, br, bb = b
        return not (
            ar + margin_px < bl or br + margin_px < al
            or ab + margin_px < bt or bb + margin_px < at
        )

    def thinking_scale(self) -> float:
        """The actual thinking cue scale, DERIVED from the eye layout.

        scale = thinking_cue_scale_ratio * eye_radius, so the cue is
        always a fraction of the real eye size regardless of the display
        resolution (ratio 0.85 * 75 = 63.75 px; the glyph's visual height
        is ~1.16x the scale ~74 px vs the ~150 px eye height = roughly
        half the eye).
        """
        return self.overlay_config.thinking_cue_scale_ratio * self.config.layout.eye_radius

    def thinking_cue_region(self, anchor: Tuple[float, float]) -> Tuple[float, float, float, float]:
        """The "?" glyph's bounding box at ``anchor``: (l, t, r, b).

        Glyph extents are derived from ``_draw_vector_question`` PLUS its
        stroke width (0.14 * scale, half on each side) so the box is
        deliberately CONSERVATIVE: the arc path reaches +/- 0.35 * scale
        horizontally and the stroke extends it to ~0.42 * scale; the arc
        top is y - 0.55 * scale, minus the stroke ~ y - 0.62 * scale; the
        dot bottom (a filled circle at y + 0.52 * scale, radius 0.09 *
        scale) is y + 0.61 * scale - no stroke below it. A box that
        clears the eyes therefore proves the drawn strokes clear them.
        """
        ax, ay = anchor
        s = self.thinking_scale()
        return (ax - 0.42 * s, ay - 0.62 * s, ax + 0.42 * s, ay + 0.61 * s)

    @staticmethod
    def z_cue_region(x: float, y: float, scale: float) -> Tuple[float, float, float, float]:
        """One Z glyph's bounding box: (l, t, r, b).

        Matches ``_draw_vector_z`` (width 0.8 * scale, height 1.0 * scale
        centred on the particle) PLUS its stroke width (0.18 * scale, half
        on each side) so the box is deliberately CONSERVATIVE: the true
        drawn extent is ~0.49 * scale wide and ~0.59 * scale tall.
        """
        return (x - 0.49 * scale, y - 0.59 * scale, x + 0.49 * scale, y + 0.59 * scale)

    def thinking_anchor(self, pose) -> Tuple[float, float]:
        """The thinking "?" cue anchor, on the eye's OUTER PERIMETER (LES-09B.5).

        The cue is anchored to the outer-top corner of one eye's rendered
        silhouette (right eye by default - the human-approved direction:
        the "?" grows from the eye corner instead of floating centred
        above the face). Placement is derived every frame from the ACTUAL
        composed pose through the single LES-09B.4 eye-bound calculation
        (``eye_silhouette_region`` - the same AABB that carries the
        collision guarantees), so the cue:

          * sits exactly ``clearance`` beyond the eye corner - the glyph
            box hugs the perimeter (eye silhouette -> clearance -> "?"),
            never inside the silhouette and never overlapping either eye;
          * follows the eye through gaze/look movement (the region is
            recomputed from the composed pose every frame);
          * keeps the human-approved scale (``thinking_scale()``, which
            is unchanged); the orbital drift is applied at draw time and
            is smaller than the clearance.

        Returns the absolute (x, y) anchor WITHOUT orbital drift.
        """
        cfg = self.overlay_config
        regions = self.eye_pair_regions(pose)
        if cfg.thinking_cue_eye == "left":
            region = regions[0]
            outer_x = region[0]   # the eye's outer (left) edge
            sign = -1.0           # the cue grows toward -x
        else:
            region = regions[1]
            outer_x = region[2]   # the eye's outer (right) edge
            sign = 1.0            # the cue grows toward +x
        scale = self.thinking_scale()
        clearance = cfg.thinking_cue_clearance_ratio * self.config.layout.eye_radius
        # Diagonal outward offset: clearance + the glyph's half-extent, so
        # the glyph box starts exactly one clearance beyond the corner.
        ax = outer_x + sign * (clearance + 0.42 * scale)
        if cfg.thinking_cue_perimeter == "outer_bottom":
            ay = region[3] + clearance + 0.62 * scale
        else:
            ay = region[1] - clearance - 0.61 * scale
        return (ax, ay)

    def sleepy_spawn_band(self, pose) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """The ZZZ spawn band in FACE SPACE: ((x_lo, x_hi), (y_lo, y_hi)).

        The band is relative to the right eye's REST centre (face space -
        it never follows gaze) and is placed so that every Z glyph born in
        it stays clear of BOTH eyes' worst-case silhouettes: each eye can
        move by ``look_max_offset`` toward the band, so the band edges
        clear (rest extent + max gaze offset + glyph half-extent). The Z
        particles drift UP and RIGHT, i.e. away from the eyes, so the
        spawn position is their closest approach to the eye geometry.
        """
        cfg = self.overlay_config
        r = self.config.layout.eye_radius
        bx = pose.right.pos_x
        by = pose.right.pos_y
        x_lo = bx + r * cfg.sleepy_cue_x_min_ratio
        x_hi = bx + r * cfg.sleepy_cue_x_max_ratio
        y_lo = by - r * cfg.sleepy_cue_y_max_ratio
        y_hi = by - r * cfg.sleepy_cue_y_min_ratio
        return ((x_lo, x_hi), (y_lo, y_hi))

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

        # Reset the thinking cue on state entry (so it gets a fresh fade-in
        # each time the robot enters the thinking state).
        if self._last_state == "thinking" and state != "thinking":
            self._thinking_particle = None
        self._last_state = state

        dt_s = ctx.dt_s
        elapsed_s = ctx.elapsed_s

        # Spatial reference coordinates from EyePair
        l_cx, l_cy = pose.left.pos_x + pose.left.look_offset_x, pose.left.pos_y + pose.left.look_offset_y
        r_cx, r_cy = pose.right.pos_x + pose.right.look_offset_x, pose.right.pos_y + pose.right.look_offset_y
        center_x = (l_cx + r_cx) * 0.5
        center_y = (l_cy + r_cy) * 0.5
        eye_r = (pose.left.radius + pose.right.radius) * 0.5

        # Thinking "?" and Sleepy ZZZ are placed in FACE SPACE from the
        # composed pose (LES-09B.4) - the local eye-coordinate references
        # below are only used by the near-eye decorative overlays (happy /
        # speaking / surprised / caring / focus), which are intentionally
        # adjacent to the eye geometry.
        if state == "sleepy":
            self._draw_sleepy(surface, pose, dt_s, effective_intensity)
        elif state == "thinking":
            self._draw_thinking(surface, pose, dt_s, elapsed_s, effective_intensity)
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
        pose: EyePair,
        dt_s: float,
        intensity: float,
    ) -> None:
        cfg = self.overlay_config
        self._sleepy_cooldown -= dt_s
        if self._sleepy_cooldown <= 0.0 and len(self._sleepy_particles) < 3:
            # Spawn a new Z symbol in the FACE-SPACE band (LES-09B.4):
            # outside both eyes' worst-case silhouettes, so the cue can
            # never overlap the eyes while they droop / move.
            (x_lo, x_hi), (y_lo, y_hi) = self.sleepy_spawn_band(pose)
            sx = random.uniform(x_lo, x_hi)
            sy = random.uniform(y_lo, y_hi)
            scale = random.uniform(0.7, 1.2)
            p = Particle(
                x=sx,
                y=sy,
                lifetime_s=random.uniform(cfg.sleepy_cue_min_lifetime_s, cfg.sleepy_cue_max_lifetime_s),
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
                    self._draw_vector_z(surface, p.x, p.y, scale=p.scale * cfg.sleepy_cue_scale_base, alpha=a)
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
        pose: EyePair,
        dt_s: float,
        elapsed_s: float,
        intensity: float,
    ) -> None:
        cfg = self.overlay_config
        # Face-space anchor, recomputed every frame from the actual pose
        # (LES-09B.4) so the cue keeps its clearance margin at every gaze
        # target and during every thinking beat.
        anchor_x, anchor_y = self.thinking_anchor(pose)
        if cfg.thinking_cue_lifetime_ms > 0:
            # Legacy pulsing path (lifetime > 0 means cooldown-gated)
            if self._thinking_particle is None or self._thinking_particle.dead:
                self._thinking_cooldown -= dt_s
                if self._thinking_cooldown <= 0.0:
                    self._thinking_particle = Particle(
                        x=anchor_x, y=anchor_y,
                        lifetime_s=cfg.thinking_cue_lifetime_ms / 1000.0,
                        fade_in_s=cfg.thinking_cue_fade_in_ms / 1000.0,
                        fade_out_s=cfg.thinking_cue_fade_out_ms / 1000.0,
                    )
                    self._thinking_cooldown = 1.2
            else:
                self._thinking_particle.update(dt_s)
        else:
            # Persistent path: a single cue per thinking state entry
            if self._thinking_particle is None or self._thinking_particle.dead:
                self._thinking_particle = Particle(
                    x=anchor_x, y=anchor_y,
                    lifetime_s=3600.0,
                    fade_in_s=cfg.thinking_cue_fade_in_ms / 1000.0,
                    fade_out_s=cfg.thinking_cue_fade_out_ms / 1000.0,
                )
            else:
                self._thinking_particle.update(dt_s)

        p = self._thinking_particle
        if p and not p.dead:
            a = p.alpha * intensity
            if a > 0.01:
                # Re-anchor every frame (the particle's birth position is
                # only the entry anchor) so the cue follows the face and
                # can never drift into an eye as the gaze moves.
                p.x = anchor_x
                p.y = anchor_y
                orbit_angle = elapsed_s * 1.5
                ox = p.x + math.cos(orbit_angle) * cfg.thinking_orbital_amplitude_x
                oy = p.y + math.sin(orbit_angle * 0.7) * cfg.thinking_orbital_amplitude_y
                self._draw_vector_question(surface, ox, oy, scale=self.thinking_scale(), alpha=a)

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
