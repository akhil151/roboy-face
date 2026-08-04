"""
Procedural Vector Mouth Renderer.

Renders thick, soft, rounded, minimal procedural mouth geometry using three
logical regions:
  1. Upper Shape (upper lip contour & curvature)
  2. Lower Shape (lower lip contour & curvature)
  3. Inner Cavity (inner dark background mask when mouth opens)

Draws pure white anti-aliased geometry on a dark background. Zero per-frame allocations.
"""

from __future__ import annotations

import math
from typing import List, Tuple
import pygame
import pygame.gfxdraw

from .mouth_shapes import MouthParams


class MouthRenderer:
    """Procedural vector renderer for the robot face mouth (Silhouette & Scale Aware)."""

    def __init__(self, bg_color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        self._bg_color = bg_color
        self._mouth_color: Tuple[int, int, int] = (255, 255, 255)

        # Preallocated scratch arrays to avoid GC pressure in hot path
        self._outer_poly: List[Tuple[int, int]] = []
        self._inner_poly: List[Tuple[int, int]] = []

    @property
    def bg_color(self) -> Tuple[int, int, int]:
        return self._bg_color

    @bg_color.setter
    def bg_color(self, color: Tuple[int, int, int]) -> None:
        self._bg_color = color

    @staticmethod
    def _rotate_point(px: float, py: float, cx: float, cy: float, rot: float) -> Tuple[float, float]:
        if rot == 0.0:
            return (px, py)
        cos_a = math.cos(rot)
        sin_a = math.sin(rot)
        dx = px - cx
        dy = py - cy
        return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

    def draw_mouth(self, surface: pygame.Surface, p: MouthParams) -> None:
        """Render procedural solid white mouth onto surface with resolution scaling."""
        opacity = max(0.0, min(1.0, p.opacity))
        if opacity <= 0.001:
            return

        # Resolution scaling factor (reference design width = 800.0)
        sw, sh = surface.get_size()
        scale = sw / 800.0

        # Color opacity calculation
        r = int(self._bg_color[0] + (self._mouth_color[0] - self._bg_color[0]) * opacity)
        g = int(self._bg_color[1] + (self._mouth_color[1] - self._bg_color[1]) * opacity)
        b = int(self._bg_color[2] + (self._mouth_color[2] - self._bg_color[2]) * opacity)
        color = (r, g, b)

        # Scaled center position
        cx = (p.pos_x + p.offset_x) * scale
        cy = (p.pos_y + p.offset_y) * scale

        # Scaled dimensions (bounded for visual balance)
        eff_w = max(16.0, p.width * (1.0 + p.stretch - p.squash * 0.5)) * scale
        eff_h = max(6.0, p.height * (1.0 + p.squash - p.stretch * 0.5)) * scale
        thickness = max(4.0, p.thickness) * scale

        half_w = eff_w * 0.5
        half_h = eff_h * 0.5
        rot = p.rotation
        opening = max(0.0, min(1.0, p.opening))
        roundness = max(0.1, min(1.0, p.corner_roundness))

        smile_bias = p.smile_amount * eff_h * 0.65
        up_curve = p.upper_curvature * eff_h * 0.60 + smile_bias
        low_curve = p.lower_curvature * eff_h * 0.60 + smile_bias

        outer = self._outer_poly
        outer.clear()

        steps = 32

        if opening <= 0.02:
            # -------------------------------------------------------------------
            # Solid White Silhouette (Happy, Caring, Sad, Calm, Listening, etc.)
            # -------------------------------------------------------------------
            # Upper contour curve (Left -> Right)
            for i in range(steps + 1):
                t = i / steps  # 0.0 to 1.0
                u = (t - 0.5) * 2.0  # -1.0 to 1.0
                x = cx + u * half_w
                arch = (1.0 - u * u)
                y_upper = cy - (thickness * 0.5) - (up_curve * arch)
                rx, ry = self._rotate_point(x, y_upper, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            # Right rounded end cap
            cap_steps = 10
            for i in range(1, cap_steps):
                ca = (i / cap_steps) * math.pi
                cap_r = (thickness * 0.5) * roundness
                cap_x = cx + half_w + math.sin(ca) * cap_r
                cap_y = cy - (up_curve * 0.1) + math.cos(ca) * (thickness * 0.5)
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            # Lower contour curve (Right -> Left)
            for i in range(steps, -1, -1):
                t = i / steps
                u = (t - 0.5) * 2.0
                x = cx + u * half_w
                arch = (1.0 - u * u)
                # Lower contour includes smile/crescent arch depth
                y_lower = cy + (thickness * 0.5) + (half_h * arch * 0.8) - (low_curve * arch)
                rx, ry = self._rotate_point(x, y_lower, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            # Left rounded end cap
            for i in range(1, cap_steps):
                ca = (i / cap_steps) * math.pi
                cap_r = (thickness * 0.5) * roundness
                cap_x = cx - half_w - math.sin(ca) * cap_r
                cap_y = cy - (up_curve * 0.1) - math.cos(ca) * (thickness * 0.5)
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            # Render solid white polygon
            if len(outer) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, outer, color)
                    pygame.gfxdraw.filled_polygon(surface, outer, color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, color, outer)

        else:
            # -------------------------------------------------------------------
            # Open Cavity Mouth (Surprised O-shape with dark inner mask)
            # -------------------------------------------------------------------
            # Outer Ring (Left -> Right -> Left)
            for i in range(steps + 1):
                t = i / steps
                u = (t - 0.5) * 2.0
                x = cx + u * half_w
                arch = (1.0 - u * u)
                y_upper = cy - half_h * (1.0 - opening * 0.1)
                rx, ry = self._rotate_point(x, y_upper, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            # Right cap
            cap_steps = 8
            for i in range(1, cap_steps):
                ca = (i / cap_steps) * math.pi
                cap_x = cx + half_w + math.sin(ca) * half_h * 0.5
                cap_y = cy + math.cos(ca) * half_h * 0.5
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            for i in range(steps, -1, -1):
                t = i / steps
                u = (t - 0.5) * 2.0
                x = cx + u * half_w
                y_lower = cy + half_h * (1.0 + opening * 0.2)
                rx, ry = self._rotate_point(x, y_lower, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            for i in range(1, cap_steps):
                ca = (i / cap_steps) * math.pi
                cap_x = cx - half_w - math.sin(ca) * half_h * 0.5
                cap_y = cy - math.cos(ca) * half_h * 0.5
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            if len(outer) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, outer, color)
                    pygame.gfxdraw.filled_polygon(surface, outer, color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, color, outer)

            # Inner Cavity Mask (Dark Fill)
            inner = self._inner_poly
            inner.clear()

            cavity_w = max(4.0, half_w - thickness * 0.8)
            cavity_h = max(4.0, half_h - thickness * 0.8)
            cav_steps = 20

            for i in range(cav_steps + 1):
                t = i / cav_steps
                u = (t - 0.5) * 2.0
                x = cx + u * cavity_w
                y = cy - cavity_h
                rx, ry = self._rotate_point(x, y, cx, cy, rot)
                inner.append((int(round(rx)), int(round(ry))))

            for i in range(cav_steps, -1, -1):
                t = i / cav_steps
                u = (t - 0.5) * 2.0
                x = cx + u * cavity_w
                y = cy + cavity_h
                rx, ry = self._rotate_point(x, y, cx, cy, rot)
                inner.append((int(round(rx)), int(round(ry))))

            if len(inner) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, inner, self._bg_color)
                    pygame.gfxdraw.filled_polygon(surface, inner, self._bg_color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, self._bg_color, inner)

