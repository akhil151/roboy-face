"""
FaceComposer — Unified Character Face Compositor.

Replaces monolithic renderer with a modular compositor.
Renders and combines procedural geometry drawn by:
  - EyeRenderer (Eye Engine)
  - MouthRenderer (Procedural Mouth Engine)
  - FaceOverlayRenderer (Emotional Effects)

All drawing is solid white geometry on a pure black background.
Zero per-frame allocations.
"""

from __future__ import annotations

from typing import Optional, Tuple
import pygame

from eyes.engine.config import EngineConfig
from eyes.engine.eye_pair import EyePair
from eyes.engine.renderer import Renderer as EyeRenderer
from face.mouth.mouth_shapes import MouthParams
from face.mouth.mouth_renderer import MouthRenderer
from face.effects.overlay_renderer import FaceOverlayRenderer
from face.render_context import RenderContext


class FaceComposer:
    """Composites Eyes, Mouth, and Effects into a unified character frame."""

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self._config = config or EngineConfig()
        self._screen: Optional[pygame.Surface] = None
        self._initialized = False

        self._eye_renderer = EyeRenderer(self._config)
        self._mouth_renderer = MouthRenderer(bg_color=self._config.display.background_color)
        self._overlay_renderer = FaceOverlayRenderer(self._config)

        self._bg_color: Tuple[int, int, int] = self._config.display.background_color

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def eye_renderer(self) -> EyeRenderer:
        return self._eye_renderer

    @property
    def mouth_renderer(self) -> MouthRenderer:
        return self._mouth_renderer

    @property
    def overlay_renderer(self) -> FaceOverlayRenderer:
        return self._overlay_renderer

    def init_display(self, windowed: bool = True) -> pygame.Surface:
        """Initialize Pygame display window."""
        w = self._config.display.width
        h = self._config.display.height
        flags = 0 if windowed else pygame.FULLSCREEN
        self._screen = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption("ELO Robot Face - Procedural Face Engine v1.0")
        self._eye_renderer.attach_surface(self._screen)
        self._initialized = True
        return self._screen

    def attach_surface(self, surface: pygame.Surface) -> None:
        """Attach to an existing Pygame surface (for showcase/studio embedding)."""
        self._screen = surface
        self._eye_renderer.attach_surface(surface)
        self._initialized = True

    def compose(
        self,
        surface: pygame.Surface,
        eye_pose: EyePair,
        mouth_params: MouthParams,
        ctx: RenderContext,
    ) -> None:
        """Compose all face layers onto surface in correct z-order."""
        # 1. Clear background to black
        surface.fill(self._bg_color)

        # 2. Layer 1: Eye Engine geometry
        self._eye_renderer.draw_eye(surface, eye_pose.left)
        self._eye_renderer.draw_eye(surface, eye_pose.right)

        # 3. Layer 2: Procedural Mouth geometry
        self._mouth_renderer.draw_mouth(surface, mouth_params)

        # 4. Layer 3: Emotional Overlays / Effects
        self._overlay_renderer.draw(surface, eye_pose, mouth_params, ctx)

    def render(
        self,
        eye_pose: EyePair,
        mouth_params: MouthParams,
        ctx: RenderContext,
    ) -> None:
        """Render composite frame to display window and flip buffer."""
        if self._screen is None:
            raise RuntimeError("FaceComposer not initialized: call init_display() or attach_surface()")
        self.compose(self._screen, eye_pose, mouth_params, ctx)
        pygame.display.flip()
