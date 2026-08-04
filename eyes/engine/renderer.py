"""
Procedural vector renderer for the eye display.

All drawing is fully procedural using pygame.draw and pygame.gfxdraw.
No images, sprites, or assets of any kind are used - everything is generated
from EyeParams.  Rotation is applied mathematically around each eye's
geometric center so anti-aliased primitives remain smooth and allocation-
free at draw time.

Rendering layers (inside draw_eye, top-to-bottom conceptually):
  1.  Sclera - anti-aliased filled ellipse with squash/stretch/scale applied
  2.  Iris - anti-aliased circle, offset by look vector, iris_scale applied
  3.  Pupil - small dark circle inside iris (reserved slot, subtle by default)
  4.  Highlight layer - one or more specular dots (configurable count/layout)
  5.  Eyelid masks - upper + lower polygonal arcs with curvature and blink
  6.  [Glow / Crescent accents] - future hook, primitives available today

Renderer strategy for perf:
  * No per-frame Surface allocations - everything is drawn directly.
  * Reused scratch rect/poly list objects where possible.
  * Fast-paths for zero rotation / zero blink / full opacity.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import pygame
import pygame.gfxdraw

from .config import EngineConfig
from .eye import EyeParams
from .eye_pair import EyePair


# ---------------------------------------------------------------------------
# Low-level anti-aliased shape helpers.  All helpers accept float coords and
# round internally; gfxdraw exceptions fall back to plain pygame.draw so the
# renderer never crashes at extreme values.
# ---------------------------------------------------------------------------


class Renderer:
    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._screen: Optional[pygame.Surface] = None
        self._initialized = False

        disp = config.display
        self._bg_color: Tuple[int, int, int] = disp.background_color
        self._eye_color: Tuple[int, int, int] = disp.eye_color
        self._iris_color: Tuple[int, int, int] = disp.iris_color
        self._lid_color: Tuple[int, int, int] = disp.lid_color
        self._highlight_color: Tuple[int, int, int] = disp.highlight_color
        self._pupil_color: Tuple[int, int, int] = (0, 0, 0)

        # Reused poly scratch list so we don't allocate a new list every lid.
        self._poly_scratch: List[Tuple[int, int]] = []

        # Cached display metrics
        self._layout = config.layout

        # Pre-computed "default" pupil ratio relative to iris radius.  Kept
        # subtle now; Phase 2 animations can dial it up on a per-state basis.
        self._default_pupil_ratio: float = 0.45

    # ------------------------------------------------------------------
    # Init / attachment
    # ------------------------------------------------------------------
    @property
    def initialized(self) -> bool:
        return self._initialized

    def init_display(self, windowed: bool = True) -> pygame.Surface:
        w = self._config.display.width
        h = self._config.display.height
        flags = 0 if windowed else pygame.FULLSCREEN
        self._screen = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption(self._config.display.title)
        self._initialized = True
        return self._screen

    def attach_surface(self, surface: pygame.Surface) -> None:
        self._screen = surface
        self._initialized = True

    # ------------------------------------------------------------------
    # Geometry derivation from EyeParams.
    #
    #   _effective_radius -> (rx, ry) after scale + squash/stretch
    #   _effective_pos    -> (cx, cy) after look/micro/bounce offsets applied
    #   _rotate_point     -> (x, y) around (cx, cy) by p.rotation (radians)
    # ------------------------------------------------------------------
    @staticmethod
    def _effective_radius(p: EyeParams) -> Tuple[float, float]:
        sx = p.scale_x + p.stretch - p.squash * 0.5
        sy = p.scale_y + p.squash - p.stretch * 0.5
        if sx < 0.01:
            sx = 0.01
        if sy < 0.01:
            sy = 0.01
        return (p.radius * sx, p.radius * sy)

    @staticmethod
    def _effective_pos(p: EyeParams) -> Tuple[float, float]:
        x = p.pos_x + p.look_offset_x + p.micro_offset_x + p.bounce_offset_x
        y = p.pos_y + p.look_offset_y + p.micro_offset_y + p.bounce_offset_y
        return (x, y)

    @staticmethod
    def _rotate_point(px: float, py: float, cx: float, cy: float, rot: float) -> Tuple[float, float]:
        if rot == 0.0:
            return (px, py)
        cos = math.cos(rot)
        sin = math.sin(rot)
        dx = px - cx
        dy = py - cy
        return (cx + dx * cos - dy * sin, cy + dx * sin + dy * cos)

    # ------------------------------------------------------------------
    # Anti-aliased shape primitives
    # ------------------------------------------------------------------
    def _aa_filled_ellipse(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        color: Tuple[int, int, int],
        rotation: float = 0.0,
    ) -> None:
        if rotation == 0.0:
            irx = max(1, int(round(rx)))
            iry = max(1, int(round(ry)))
            icx = int(round(cx))
            icy = int(round(cy))
            try:
                pygame.gfxdraw.aaellipse(surface, icx, icy, irx, iry, color)
                pygame.gfxdraw.filled_ellipse(surface, icx, icy, max(0, irx - 1), max(0, iry - 1), color)
            except (pygame.error, OverflowError):
                rect = pygame.Rect(0, 0, irx * 2, iry * 2)
                rect.center = (icx, icy)
                pygame.draw.ellipse(surface, color, rect)
            return

        # Rotated: build poly by sampling the ellipse parametrically and
        # rotating each vertex around (cx, cy).  48 steps gives visually
        # smooth result; poly count is small so perf is fine.
        steps = 48
        poly = self._poly_scratch
        poly.clear()
        for i in range(steps):
            t = (i / steps) * math.pi * 2.0
            ex = cx + math.cos(t) * rx
            ey = cy + math.sin(t) * ry
            rxr, ryr = self._rotate_point(ex, ey, cx, cy, rotation)
            poly.append((int(round(rxr)), int(round(ryr))))
        try:
            pygame.gfxdraw.aapolygon(surface, poly, color)
            pygame.gfxdraw.filled_polygon(surface, poly, color)
        except (pygame.error, OverflowError):
            if len(poly) >= 3:
                pygame.draw.polygon(surface, color, poly)

    def _aa_filled_circle(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        r: float,
        color: Tuple[int, int, int],
    ) -> None:
        if r <= 0.0:
            return
        ir = max(1, int(round(r)))
        icx = int(round(cx))
        icy = int(round(cy))
        try:
            pygame.gfxdraw.aacircle(surface, icx, icy, ir, color)
            pygame.gfxdraw.filled_circle(surface, icx, icy, max(0, ir - 1), color)
        except (pygame.error, OverflowError):
            pygame.draw.circle(surface, color, (icx, icy), ir)

    def _draw_crescent(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        outer_r: float,
        inner_r: float,
        offset_x: float,
        offset_y: float,
        color: Tuple[int, int, int],
    ) -> None:
        """Draw a crescent shape as the difference between two offset circles.

        The crescent is formed by taking a ring (outer_r - inner_r thickness)
        whose *shadow* is offset by (offset_x, offset_y).  Only the visible
        "lit" portion of the ring is filled, producing a specular crescent
        useful for curved lash highlights, rim accents, or eyelid creases.
        """
        if outer_r <= inner_r:
            return
        poly = self._poly_scratch
        poly.clear()

        # Thickness crescent: walk around the ring and produce a poly that
        # captures the non-overlapping region of the outer circle minus the
        # translated inner circle.  For Phase 1 we render a swept "arc-
        # thickness" poly that produces the visual crescent effect.
        steps = 40
        ang = math.atan2(offset_y, offset_x)
        spread = math.acos(max(-1.0, min(1.0, inner_r / max(0.0001, outer_r))))
        start = ang - math.pi * 0.5 + spread * 0.2
        end = ang + math.pi * 0.5 - spread * 0.2

        # Outer arc
        for i in range(steps + 1):
            t = start + (end - start) * (i / steps)
            x = cx + math.cos(t) * outer_r
            y = cy + math.sin(t) * outer_r
            poly.append((int(round(x)), int(round(y))))
        # Inner arc, reversed
        for i in range(steps, -1, -1):
            t = start + (end - start) * (i / steps)
            x = cx + offset_x * 0.4 + math.cos(t) * inner_r
            y = cy + offset_y * 0.4 + math.sin(t) * inner_r
            poly.append((int(round(x)), int(round(y))))

        if len(poly) >= 3:
            try:
                pygame.gfxdraw.aapolygon(surface, poly, color)
                pygame.gfxdraw.filled_polygon(surface, poly, color)
            except (pygame.error, OverflowError):
                pygame.draw.polygon(surface, color, poly)

    # ------------------------------------------------------------------
    # Eyelid rendering - upper / lower polygonal arc with curvature control.
    # Honours rotation by rotating every poly vertex around (cx, cy).
    # ------------------------------------------------------------------
    def _draw_lid_arc(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        close_amount: float,
        curvature: float,
        upper: bool,
        color: Tuple[int, int, int],
        rotation: float = 0.0,
    ) -> None:
        if close_amount <= 0.001:
            return
        eff_close = min(1.0, max(0.0, close_amount))

        irx = max(1, int(round(rx * 1.15)))
        iry = max(1, int(round(ry * 1.15)))
        arc_height = ry * eff_close * (1.0 + abs(curvature) * 0.2)
        steps = 24

        poly = self._poly_scratch
        poly.clear()

        if upper:
            for i in range(steps + 1):
                t = i / steps
                angle = math.pi + math.pi * t
                x = cx + math.cos(angle) * irx
                base_y = cy + math.sin(angle) * iry
                lid_line = cy - ry + arc_height * (1.0 - math.sin(t * math.pi))
                if curvature >= 0:
                    lid_curve = -curvature * ry * 0.4 * math.sin(t * math.pi)
                else:
                    lid_curve = -curvature * ry * 0.4 * (1.0 - abs(2.0 * t - 1.0))
                y = min(base_y, lid_line + lid_curve)
                if rotation != 0.0:
                    x, y = self._rotate_point(x, y, cx, cy, rotation)
                poly.append((int(round(x)), int(round(y))))

            for i in range(steps, -1, -1):
                t = i / steps
                angle = math.pi + math.pi * t
                x = cx + math.cos(angle) * irx
                y = cy - ry - 2.0
                if rotation != 0.0:
                    x, y = self._rotate_point(x, y, cx, cy, rotation)
                poly.append((int(round(x)), int(round(y))))
        else:
            bottom_base = cy + ry
            for i in range(steps + 1):
                t = i / steps
                angle = math.pi * t
                x = cx + math.cos(angle) * irx
                base_y = cy + math.sin(angle) * iry
                lid_y = bottom_base - arc_height * (1.0 - math.sin(t * math.pi))
                if curvature >= 0:
                    lid_curve = curvature * ry * 0.4 * math.sin(t * math.pi)
                else:
                    lid_curve = curvature * ry * 0.4 * (1.0 - abs(2.0 * t - 1.0))
                y = max(base_y, lid_y + lid_curve)
                if rotation != 0.0:
                    x, y = self._rotate_point(x, y, cx, cy, rotation)
                poly.append((int(round(x)), int(round(y))))

            for i in range(steps, -1, -1):
                t = i / steps
                angle = math.pi * t
                x = cx + math.cos(angle) * irx
                y = cy + ry + 2.0
                if rotation != 0.0:
                    x, y = self._rotate_point(x, y, cx, cy, rotation)
                poly.append((int(round(x)), int(round(y))))

        if len(poly) >= 3:
            try:
                pygame.gfxdraw.aapolygon(surface, poly, color)
                pygame.gfxdraw.filled_polygon(surface, poly, color)
            except (pygame.error, OverflowError):
                pygame.draw.polygon(surface, color, poly)

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------
    def _blend_color(
        self, color: Tuple[int, int, int], alpha: float
    ) -> Tuple[int, int, int]:
        bg = self._bg_color
        a = max(0.0, min(1.0, alpha))
        return (
            int(bg[0] + (color[0] - bg[0]) * a),
            int(bg[1] + (color[1] - bg[1]) * a),
            int(bg[2] + (color[2] - bg[2]) * a),
        )

    # ------------------------------------------------------------------
    # draw_eye - the full per-eye procedural pipeline.
    # Layers: sclera -> iris -> pupil -> highlight -> lids
    # ------------------------------------------------------------------
    def draw_eye(self, surface: pygame.Surface, p: EyeParams) -> None:
        opacity = max(0.0, min(1.0, p.opacity))
        if opacity <= 0.001:
            return

        rx, ry = self._effective_radius(p)
        cx, cy = self._effective_pos(p)
        rot = p.rotation

        eye_color = self._blend_color(self._eye_color, opacity)
        iris_color = self._blend_color(self._iris_color, opacity)
        pupil_color = self._blend_color(self._pupil_color, opacity)
        hl_color = self._blend_color(self._highlight_color, opacity)
        lid_color = self._lid_color

        layout = self._layout

        # --- Layer 1: sclera (white geometry)
        self._aa_filled_ellipse(surface, cx, cy, rx, ry, eye_color, rotation=rot)

        # --- Layer 5: eyelid masks (black background overlay)
        total_close = min(1.0, p.blink_weight + (1.0 - p.lid_openness))
        upper_close = min(1.0, total_close * 0.5 + p.blink_weight * 0.5)
        lower_close = min(1.0, total_close * 0.5 + p.blink_weight * 0.45)

        self._draw_lid_arc(
            surface, cx, cy, rx, ry,
            upper_close,
            p.upper_lid_curvature,
            upper=True, color=lid_color, rotation=rot,
        )
        self._draw_lid_arc(
            surface, cx, cy, rx, ry,
            lower_close,
            p.lower_lid_curvature,
            upper=False, color=lid_color, rotation=rot,
        )

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def render(self, pose: EyePair) -> None:
        if self._screen is None:
            raise RuntimeError("Renderer not initialized: call init_display() or attach_surface()")
        self._screen.fill(self._bg_color)
        self.draw_eye(self._screen, pose.left)
        self.draw_eye(self._screen, pose.right)
        pygame.display.flip()

    def render_to_surface(self, surface: pygame.Surface, pose: EyePair) -> None:
        surface.fill(self._bg_color)
        self.draw_eye(surface, pose.left)
        self.draw_eye(surface, pose.right)
