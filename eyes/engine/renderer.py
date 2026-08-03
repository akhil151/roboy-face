"""
Procedural renderer for the eye display.

All drawing is fully procedural using pygame.draw and pygame.gfxdraw.
No images, sprites, or assets are used - everything is generated from EyeParams.

Rendering strategy:
- Pure black background
- Pure white eyes
- Anti-aliased drawing via gfxdraw where available
- Reused surfaces to avoid per-frame allocations
- Efficient compositing for opacity/glow
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import pygame
import pygame.gfxdraw

from .config import EngineConfig
from .eye import EyeParams
from .eye_pair import EyePair


class Renderer:
    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._screen: Optional[pygame.Surface] = None
        self._eye_cache: dict[str, pygame.Surface] = {}
        self._initialized = False

        self._bg_color = config.display.background_color
        self._eye_color = config.display.eye_color
        self._iris_color = config.display.iris_color
        self._lid_color = config.display.lid_color
        self._highlight_color = config.display.highlight_color

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

    def _effective_radius(self, p: EyeParams) -> Tuple[float, float]:
        sx = p.scale_x + p.stretch - p.squash * 0.5
        sy = p.scale_y + p.squash - p.stretch * 0.5
        sx = max(0.01, sx)
        sy = max(0.01, sy)
        return (p.radius * sx, p.radius * sy)

    def _effective_pos(self, p: EyeParams) -> Tuple[float, float]:
        x = p.pos_x + p.look_offset_x + p.micro_offset_x + p.bounce_offset_x
        y = p.pos_y + p.look_offset_y + p.micro_offset_y + p.bounce_offset_y
        return (x, y)

    def _draw_aa_filled_ellipse(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        color: Tuple[int, int, int],
    ) -> None:
        irx = max(1, int(round(rx)))
        iry = max(1, int(round(ry)))
        icx = int(round(cx))
        icy = int(round(cy))
        try:
            pygame.gfxdraw.aaellipse(surface, icx, icy, irx, iry, color)
            pygame.gfxdraw.filled_ellipse(surface, icx, icy, irx - 1, iry - 1, color)
        except (pygame.error, OverflowError):
            rect = pygame.Rect(0, 0, irx * 2, iry * 2)
            rect.center = (icx, icy)
            pygame.draw.ellipse(surface, color, rect)

    def _draw_aa_filled_circle(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        r: float,
        color: Tuple[int, int, int],
    ) -> None:
        ir = max(1, int(round(r)))
        icx = int(round(cx))
        icy = int(round(cy))
        try:
            pygame.gfxdraw.aacircle(surface, icx, icy, ir, color)
            pygame.gfxdraw.filled_circle(surface, icx, icy, max(0, ir - 1), color)
        except (pygame.error, OverflowError):
            pygame.draw.circle(surface, color, (icx, icy), ir)

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
    ) -> None:
        if close_amount <= 0.001:
            return
        icx = int(round(cx))
        icy = int(round(cy))
        irx = max(1, int(round(rx * 1.15)))
        iry = max(1, int(round(ry * 1.15)))

        eff_close = min(1.0, max(0.0, close_amount))
        half_pi = math.pi * 0.5
        curvation_angle = curvature * half_pi * 0.5

        if upper:
            start_angle_deg = 180.0
            end_angle_deg = 360.0
            arc_height = ry * eff_close * (1.0 + abs(curvature) * 0.2)
            top_y = icy - ry + arc_height * 0.3

            poly_points: list[Tuple[int, int]] = []
            steps = 24
            for i in range(steps + 1):
                t = i / steps
                angle = math.pi + math.pi * t
                x = icx + int(round(math.cos(angle) * irx))
                base_y = icy + int(round(math.sin(angle) * iry))
                lid_line = icy - ry + int(round(arc_height * (1.0 - math.sin(t * math.pi))))
                if curvature >= 0:
                    lid_curve = int(round(-curvature * ry * 0.4 * math.sin(t * math.pi)))
                else:
                    lid_curve = int(round(-curvature * ry * 0.4 * (1.0 - abs(2.0 * t - 1.0))))
                y = min(base_y, lid_line + lid_curve)
                poly_points.append((x, y))

            for i in range(steps, -1, -1):
                t = i / steps
                angle = math.pi + math.pi * t
                x = icx + int(round(math.cos(angle) * irx))
                y = icy - ry - 2
                poly_points.append((x, y))

            if len(poly_points) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, poly_points, color)
                    pygame.gfxdraw.filled_polygon(surface, poly_points, color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, color, poly_points)
        else:
            poly_points = []
            steps = 24
            arc_height = ry * eff_close * (1.0 + abs(curvature) * 0.2)
            bottom_base = icy + ry
            lid_line = bottom_base - int(round(arc_height * 0.3))

            for i in range(steps + 1):
                t = i / steps
                angle = math.pi * t
                x = icx + int(round(math.cos(angle) * irx))
                base_y = icy + int(round(math.sin(angle) * iry))
                lid_y = bottom_base - int(round(arc_height * (1.0 - math.sin(t * math.pi))))
                if curvature >= 0:
                    lid_curve = int(round(curvature * ry * 0.4 * math.sin(t * math.pi)))
                else:
                    lid_curve = int(round(curvature * ry * 0.4 * (1.0 - abs(2.0 * t - 1.0))))
                y = max(base_y, lid_y + lid_curve)
                poly_points.append((x, y))

            for i in range(steps, -1, -1):
                t = i / steps
                angle = math.pi * t
                x = icx + int(round(math.cos(angle) * irx))
                y = icy + ry + 2
                poly_points.append((x, y))

            if len(poly_points) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, poly_points, color)
                    pygame.gfxdraw.filled_polygon(surface, poly_points, color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, color, poly_points)

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

    def draw_eye(self, surface: pygame.Surface, p: EyeParams) -> None:
        opacity = max(0.0, min(1.0, p.opacity))
        if opacity <= 0.001:
            return

        rx, ry = self._effective_radius(p)
        cx, cy = self._effective_pos(p)

        eye_color = self._blend_color(self._eye_color, opacity)
        iris_color = self._blend_color(self._iris_color, opacity)
        hl_color = self._blend_color(self._highlight_color, opacity)
        lid_color = self._lid_color

        self._draw_aa_filled_ellipse(surface, cx, cy, rx, ry, eye_color)

        layout = self._config.layout
        iris_ratio = layout.iris_radius_ratio * p.iris_scale
        max_iris_r = min(rx, ry) * iris_ratio
        look_mag = math.hypot(p.look_offset_x, p.look_offset_y)
        max_look = self._config.layout.look_max_offset
        if max_look > 0:
            look_t = min(1.0, look_mag / max_look)
            iris_r = max_iris_r * (1.0 - look_t * 0.05)
        else:
            iris_r = max_iris_r

        iris_cx = cx + p.look_offset_x * (1.0 - iris_ratio * 0.3)
        iris_cy = cy + p.look_offset_y * (1.0 - iris_ratio * 0.3)
        self._draw_aa_filled_circle(surface, iris_cx, iris_cy, iris_r, iris_color)

        hl_r = min(rx, ry) * layout.highlight_radius_ratio
        hl_off_x = rx * layout.highlight_offset_ratio * (-0.5)
        hl_off_y = -ry * layout.highlight_offset_ratio * 0.8
        hl_cx = cx + hl_off_x + p.look_offset_x * 0.3
        hl_cy = cy + hl_off_y + p.look_offset_y * 0.3
        self._draw_aa_filled_circle(surface, hl_cx, hl_cy, hl_r, hl_color)

        total_close = min(1.0, p.blink_weight + (1.0 - p.lid_openness))
        upper_close = total_close * 0.5 + p.blink_weight * 0.5
        lower_close = total_close * 0.5 + p.blink_weight * 0.5

        self._draw_lid_arc(
            surface, cx, cy, rx, ry,
            min(1.0, upper_close),
            p.upper_lid_curvature,
            upper=True, color=lid_color,
        )
        self._draw_lid_arc(
            surface, cx, cy, rx, ry,
            min(1.0, lower_close),
            p.lower_lid_curvature,
            upper=False, color=lid_color,
        )

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
