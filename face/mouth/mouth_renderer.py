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

    def _append_capsule(
        self,
        poly: List[Tuple[int, int]],
        cx: float,
        cy: float,
        half_w: float,
        half_h: float,
        rot: float,
        steps: int = 20,
    ) -> None:
        """Append a rounded capsule polygon, oriented by width/height."""
        if half_h >= half_w:
            body_half = max(0.0, half_h - half_w)
            radius = half_w
            for i in range(steps + 1):
                a = math.pi + (math.pi * i / steps)
                x = cx + math.cos(a) * radius
                y = cy - body_half + math.sin(a) * radius
                rx, ry = self._rotate_point(x, y, cx, cy, rot)
                poly.append((int(round(rx)), int(round(ry))))
            for i in range(steps + 1):
                a = math.pi * i / steps
                x = cx + math.cos(a) * radius
                y = cy + body_half + math.sin(a) * radius
                rx, ry = self._rotate_point(x, y, cx, cy, rot)
                poly.append((int(round(rx)), int(round(ry))))
            return

        body_half = max(0.0, half_w - half_h)
        radius = half_h
        for i in range(steps + 1):
            a = -math.pi * 0.5 + (math.pi * i / steps)
            x = cx + body_half + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            rx, ry = self._rotate_point(x, y, cx, cy, rot)
            poly.append((int(round(rx)), int(round(ry))))
        for i in range(steps + 1):
            a = math.pi * 0.5 + (math.pi * i / steps)
            x = cx - body_half + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            rx, ry = self._rotate_point(x, y, cx, cy, rot)
            poly.append((int(round(rx)), int(round(ry))))

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

        smile_curve = p.smile_amount * eff_h * 0.78
        upper_body = p.upper_curvature * eff_h * 0.26
        lower_body = p.lower_curvature * eff_h * 0.38

        outer = self._outer_poly
        outer.clear()
        steps = 36

        if eff_h > eff_w * 1.20:
            self._append_capsule(
                outer,
                cx,
                cy,
                half_w=max(half_w, thickness * 0.42),
                half_h=half_h,
                rot=rot,
                steps=20,
            )
        else:
            cap_steps = 12
            for i in range(steps + 1):
                t = i / steps
                u = (t - 0.5) * 2.0
                arch = (1.0 - u * u)
                taper = 0.48 + 0.52 * math.pow(arch, 0.72)
                body = thickness * taper
                x = cx + u * half_w
                y_upper = cy + (smile_curve * arch) - (body * 0.5) - (upper_body * arch)
                rx, ry = self._rotate_point(x, y_upper, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            cap_r = max(3.0, thickness * 0.5 * roundness)
            for i in range(1, cap_steps):
                ca = -math.pi * 0.5 + (math.pi * i / cap_steps)
                cap_x = cx + half_w + math.cos(ca) * cap_r
                cap_y = cy + math.sin(ca) * cap_r
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            for i in range(steps, -1, -1):
                t = i / steps
                u = (t - 0.5) * 2.0
                arch = (1.0 - u * u)
                taper = 0.48 + 0.52 * math.pow(arch, 0.72)
                body = thickness * taper
                x = cx + u * half_w
                y_lower = cy + (smile_curve * arch) + (body * 0.5) + (lower_body * arch)
                rx, ry = self._rotate_point(x, y_lower, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

            for i in range(1, cap_steps):
                ca = math.pi * 0.5 + (math.pi * i / cap_steps)
                cap_x = cx - half_w + math.cos(ca) * cap_r
                cap_y = cy + math.sin(ca) * cap_r
                rx, ry = self._rotate_point(cap_x, cap_y, cx, cy, rot)
                outer.append((int(round(rx)), int(round(ry))))

        if len(outer) >= 3:
            try:
                pygame.gfxdraw.aapolygon(surface, outer, color)
                pygame.gfxdraw.filled_polygon(surface, outer, color)
            except (pygame.error, OverflowError):
                pygame.draw.polygon(surface, color, outer)

        if opening > 0.08 and eff_h <= eff_w * 1.20:
            inner = self._inner_poly
            inner.clear()

            inner_thickness = max(3.0, thickness * (0.48 - opening * 0.18))
            inner_half_w = max(6.0, half_w - thickness * 0.95)
            inner_upper = upper_body * 0.35
            inner_lower = lower_body * 0.40

            for i in range(steps + 1):
                t = i / steps
                u = (t - 0.5) * 2.0
                arch = (1.0 - u * u)
                taper = 0.38 + 0.62 * math.pow(arch, 0.78)
                body = inner_thickness * taper
                x = cx + u * inner_half_w
                y_upper = cy + (smile_curve * arch) - (body * 0.5) - (inner_upper * arch)
                rx, ry = self._rotate_point(x, y_upper, cx, cy, rot)
                inner.append((int(round(rx)), int(round(ry))))

            for i in range(steps, -1, -1):
                t = i / steps
                u = (t - 0.5) * 2.0
                arch = (1.0 - u * u)
                taper = 0.38 + 0.62 * math.pow(arch, 0.78)
                body = inner_thickness * taper
                x = cx + u * inner_half_w
                y_lower = cy + (smile_curve * arch) + (body * 0.5) + (inner_lower * arch)
                rx, ry = self._rotate_point(x, y_lower, cx, cy, rot)
                inner.append((int(round(rx)), int(round(ry))))

            if len(inner) >= 3:
                try:
                    pygame.gfxdraw.aapolygon(surface, inner, self._bg_color)
                    pygame.gfxdraw.filled_polygon(surface, inner, self._bg_color)
                except (pygame.error, OverflowError):
                    pygame.draw.polygon(surface, self._bg_color, inner)
