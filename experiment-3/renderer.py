"""Pygame rendering engine for ELO Face V3.

Renders two solid white rounded eyes on an 800x480 black canvas with
circle-to-pill stadium geometry.
"""

from typing import Tuple, Optional
import pygame

from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    COLOR_BG,
    COLOR_EYE,
    COLOR_ACCENT,
)
from eye import EyeGeometry, EyePair


class Renderer:
    """Handles all Pygame drawing operations for the V3 face engine."""

    def __init__(
        self,
        width: int = WINDOW_WIDTH,
        height: int = WINDOW_HEIGHT,
        bg_color: Tuple[int, int, int] = COLOR_BG,
        eye_color: Tuple[int, int, int] = COLOR_EYE,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.bg_color: Tuple[int, int, int] = bg_color
        self.eye_color: Tuple[int, int, int] = eye_color

        # Reusable primary surface
        self._surface: Optional[pygame.Surface] = None

    def get_surface(self) -> pygame.Surface:
        """Get or initialize the primary rendering surface."""
        if self._surface is None:
            self._surface = pygame.Surface((self.width, self.height))
        return self._surface

    def clear(self, surface: Optional[pygame.Surface] = None) -> None:
        """Clear the target surface with the black background color."""
        surf = surface or self.get_surface()
        surf.fill(self.bg_color)

    def draw_eye(
        self,
        surface: pygame.Surface,
        geometry: EyeGeometry,
        color: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """Draw a single eye shape as a solid rounded stadium / pill or circle.

        Uses pygame.draw.rect with border_radius = corner_radius.
        When width == height, this forms a perfect geometric circle.
        When height < width, this forms a smooth rounded capsule / pill.
        """
        fill_color = color or self.eye_color

        rx, ry, rw, rh = geometry.bounding_rect_tuple
        if rw <= 0 or rh <= 0:
            return

        # Ensure corner radius does not exceed half the shortest dimension
        radius = int(round(geometry.corner_radius))
        max_r = min(rw, rh) // 2
        radius = min(radius, max_r)

        rect = pygame.Rect(rx, ry, rw, rh)
        pygame.draw.rect(
            surface,
            fill_color,
            rect,
            border_radius=radius,
        )

    def render_frame(
        self,
        eye_pair: EyePair,
        target_surface: Optional[pygame.Surface] = None,
    ) -> pygame.Surface:
        """Renders a complete face frame containing both eyes onto the surface.

        Args:
            eye_pair: The EyePair holding current left and right eye states.
            target_surface: Optional destination surface (e.g. the window screen).

        Returns:
            The rendered pygame Surface.
        """
        surf = target_surface or self.get_surface()

        # 1. Clear background
        surf.fill(self.bg_color)

        # 2. Compute geometries
        left_geom, right_geom = eye_pair.get_geometries()

        # 3. Draw left and right eyes
        self.draw_eye(surf, left_geom)
        self.draw_eye(surf, right_geom)

        return surf

    def render_hud(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        eye_pair: EyePair,
        fps: float,
        extra_info: Optional[str] = None,
    ) -> None:
        """Renders an optional debug HUD overlay."""
        l_eye = eye_pair.left_eye
        r_eye = eye_pair.right_eye

        lines = [
            f"FPS: {fps:.1f}",
            f"Left Eye  - Open: {l_eye.open_amount:.2f} | Look: ({l_eye.look_x:+.1f}, {l_eye.look_y:+.1f}) | Scale: {l_eye.scale:.2f}",
            f"Right Eye - Open: {r_eye.open_amount:.2f} | Look: ({r_eye.look_x:+.1f}, {r_eye.look_y:+.1f}) | Scale: {r_eye.scale:.2f}",
        ]
        if extra_info:
            lines.append(extra_info)

        y_offset = 12
        for line in lines:
            text_surf = font.render(line, True, (0, 255, 180))
            surface.blit(text_surf, (15, y_offset))
            y_offset += 20
