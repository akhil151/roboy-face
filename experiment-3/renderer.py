"""Pygame rendering engine for ELO Face V3.

Renders:
1. Solid white rounded eyes (circle-to-pill stadium geometry) on 800x480 black canvas.
2. Cute pink blush strokes beneath eyes.
3. Floating, drifting sleep 'Z' particles.
4. Minimalist typewriter intro sequence text ("Hii", "This is ELO.").
5. Real-time timeline & performance HUD overlay.
"""

from typing import Tuple, Optional, Dict
import pygame

from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    COLOR_BG,
    COLOR_EYE,
    COLOR_ACCENT,
    COLOR_TEXT,
    BLUSH_WIDTH,
    BLUSH_HEIGHT,
    BLUSH_OFFSET_Y,
)
from eye import EyeGeometry, EyePair
from effects import IntroState, BlushState, SleepZParticles


class Renderer:
    """Handles all Pygame layered drawing operations for the V3 face engine."""

    def __init__(
        self,
        width: int = WINDOW_WIDTH,
        height: int = WINDOW_HEIGHT,
        bg_color: Tuple[int, int, int] = COLOR_BG,
        eye_color: Tuple[int, int, int] = COLOR_EYE,
        accent_color: Tuple[int, int, int] = COLOR_ACCENT,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.bg_color: Tuple[int, int, int] = bg_color
        self.eye_color: Tuple[int, int, int] = eye_color
        self.accent_color: Tuple[int, int, int] = accent_color

        # Primary surface
        self._surface: Optional[pygame.Surface] = None

        # Font caches
        self._fonts: Dict[int, pygame.font.Font] = {}

    def get_surface(self) -> pygame.Surface:
        """Get or initialize the primary rendering surface."""
        if self._surface is None:
            self._surface = pygame.Surface((self.width, self.height))
        return self._surface

    def _get_font(self, size: int) -> Optional[pygame.font.Font]:
        """Lazy-loaded font helper."""
        if not pygame.font.get_init():
            return None
        if size not in self._fonts:
            # Try a clean modern sans-serif font
            for font_name in ["Arial", "Helvetica", "Segoe UI", "DejaVu Sans", "Consolas"]:
                try:
                    self._fonts[size] = pygame.font.SysFont(font_name, size)
                    break
                except Exception:
                    continue
            if size not in self._fonts:
                self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def clear(self, surface: Optional[pygame.Surface] = None) -> None:
        """Clear the target surface with the black background color."""
        surf = surface or self.get_surface()
        surf.fill(self.bg_color)

    def draw_eye(
        self,
        surface: pygame.Surface,
        geometry: EyeGeometry,
        color: Optional[Tuple[int, int, int]] = None,
        alpha: float = 1.0,
    ) -> None:
        """Draw a single eye shape as a solid rounded stadium / pill or circle."""
        fill_color = color or self.eye_color
        rx, ry, rw, rh = geometry.bounding_rect_tuple
        if rw <= 0 or rh <= 0 or alpha <= 0.0:
            return

        radius = int(round(geometry.corner_radius))
        max_r = min(rw, rh) // 2
        radius = min(radius, max_r)

        if alpha >= 0.99:
            rect = pygame.Rect(rx, ry, rw, rh)
            pygame.draw.rect(surface, fill_color, rect, border_radius=radius)
        else:
            # Alpha blend onto surface
            temp_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
            color_with_alpha = (fill_color[0], fill_color[1], fill_color[2], int(alpha * 255))
            pygame.draw.rect(temp_surf, color_with_alpha, (0, 0, rw, rh), border_radius=radius)
            surface.blit(temp_surf, (rx, ry))

    def draw_blush(
        self,
        surface: pygame.Surface,
        blush_state: BlushState,
        left_geom: EyeGeometry,
        right_geom: EyeGeometry,
    ) -> None:
        """Draws soft pink rounded cheek strokes beneath both eyes."""
        alpha_int = int(round(blush_state.alpha))
        if alpha_int <= 0:
            return

        bw = int(BLUSH_WIDTH)
        bh = int(BLUSH_HEIGHT)
        br = bh // 2

        blush_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        color = (self.accent_color[0], self.accent_color[1], self.accent_color[2], alpha_int)
        pygame.draw.rect(blush_surf, color, (0, 0, bw, bh), border_radius=br)

        # Position beneath left and right eyes
        left_x = int(left_geom.cx - bw / 2.0)
        left_y = int(left_geom.cy + BLUSH_OFFSET_Y - bh / 2.0)
        right_x = int(right_geom.cx - bw / 2.0)
        right_y = int(right_geom.cy + BLUSH_OFFSET_Y - bh / 2.0)

        surface.blit(blush_surf, (left_x, left_y))
        surface.blit(blush_surf, (right_x, right_y))

    def draw_sleep_particles(
        self,
        surface: pygame.Surface,
        sleep_particles: SleepZParticles,
    ) -> None:
        """Draws floating, drifting 'Z' particles during sleep."""
        if not sleep_particles.particles:
            return

        for p in sleep_particles.particles:
            p_alpha = p.alpha
            if p_alpha <= 0:
                continue

            font = self._get_font(p.size)
            if not font:
                continue

            # Render 'Z' glyph with alpha
            text_surf = font.render("z", True, (255, 255, 255))
            text_surf.set_alpha(p_alpha)
            surface.blit(text_surf, (int(p.x), int(p.y)))

    def draw_intro_text(
        self,
        surface: pygame.Surface,
        intro_state: IntroState,
    ) -> None:
        """Draws polished typewriter text for the intro sequence."""
        if not intro_state.text_to_show or intro_state.text_alpha <= 0.0:
            return

        font = self._get_font(44)
        if not font:
            return

        display_str = intro_state.text_to_show
        if intro_state.show_cursor:
            display_str += "|"

        text_surf = font.render(display_str, True, COLOR_TEXT)
        if intro_state.text_alpha < 0.99:
            text_surf.set_alpha(int(intro_state.text_alpha * 255))

        # Center on 800x480 canvas
        tx = (self.width - text_surf.get_width()) // 2
        ty = (self.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, ty))

    def render_frame(
        self,
        eye_pair: EyePair,
        target_surface: Optional[pygame.Surface] = None,
        face_alpha: float = 1.0,
        blush_state: Optional[BlushState] = None,
        sleep_particles: Optional[SleepZParticles] = None,
        intro_state: Optional[IntroState] = None,
    ) -> pygame.Surface:
        """Renders the complete layered face frame."""
        surf = target_surface or self.get_surface()

        # 1. Background
        surf.fill(self.bg_color)

        left_geom, right_geom = eye_pair.get_geometries()

        # 2. Eyes (if visible)
        if face_alpha > 0.0:
            self.draw_eye(surf, left_geom, alpha=face_alpha)
            self.draw_eye(surf, right_geom, alpha=face_alpha)

            # 3. Blush overlay beneath eyes
            if blush_state:
                self.draw_blush(surf, blush_state, left_geom, right_geom)

            # 4. Sleep particles
            if sleep_particles:
                self.draw_sleep_particles(surf, sleep_particles)

        # 5. Intro text overlay (when active)
        if intro_state:
            self.draw_intro_text(surf, intro_state)

        return surf

    def render_hud(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        eye_pair: EyePair,
        fps: float,
        segment_name: str,
        segment_progress: float,
        segment_elapsed: float,
        segment_duration: float,
        total_elapsed: float,
        total_duration: float,
        is_paused: bool,
    ) -> None:
        """Renders an informative timeline and diagnostics HUD overlay."""
        l_eye = eye_pair.left_eye
        r_eye = eye_pair.right_eye

        pause_str = " [PAUSED]" if is_paused else ""
        lines = [
            f"FPS: {fps:.1f} | Segment: {segment_name.upper()}{pause_str}",
            f"Segment Time: {segment_elapsed:.1f}s / {segment_duration:.1f}s ({int(segment_progress * 100)}%) | Total: {total_elapsed:.1f}s / {total_duration:.1f}s",
            f"Left Eye  - Open: {l_eye.open_amount:.2f} | Look: ({l_eye.look_x:+.1f}, {l_eye.look_y:+.1f}) | Scale: {l_eye.scale:.2f}",
            f"Right Eye - Open: {r_eye.open_amount:.2f} | Look: ({r_eye.look_x:+.1f}, {r_eye.look_y:+.1f}) | Scale: {r_eye.scale:.2f}",
            "Hotkeys: 1-9, 0, -, = (Jump Expression) | SPACE (Pause/Resume) | R (Restart Intro) | H (HUD)",
        ]

        y_offset = 12
        for line in lines:
            text_surf = font.render(line, True, (0, 255, 180))
            surface.blit(text_surf, (15, y_offset))
            y_offset += 19
