"""
Procedural Emotional Overlay Layer for Face Engine (FaceOverlayRenderer).

Draws vector emotional accents ON TOP of Face geometry (Eyes + Mouth) using RenderContext.
All graphics are purely procedural (pygame.draw / pygame.gfxdraw) with zero asset files.
Consumes Eye Engine's OverlayRenderer as a dependency for eye overlays and adds face-level accents.
"""

from __future__ import annotations

import math
from typing import Optional
import pygame

from eyes.engine.config import EngineConfig
from eyes.engine.eye_pair import EyePair
from eyes.engine.overlay_renderer import OverlayRenderer as EyeOverlayRenderer
from eyes.engine.render_context import RenderContext as EyeRenderContext
from face.mouth.mouth_shapes import MouthParams
from face.render_context import RenderContext


class FaceOverlayRenderer:
    """Unified procedural face overlay renderer."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._eye_overlay = EyeOverlayRenderer(config)
        self.enabled: bool = True

    @property
    def eye_overlay(self) -> EyeOverlayRenderer:
        return self._eye_overlay

    def draw(
        self,
        surface: pygame.Surface,
        eye_pose: EyePair,
        mouth_params: MouthParams,
        ctx: RenderContext,
    ) -> None:
        """Render procedural vector overlays on top of the face."""
        if not self.enabled:
            return

        # 1. Draw Eye Engine overlays
        eye_ctx = EyeRenderContext(
            current_state=ctx.current_state,
            blend_progress=ctx.blend_progress,
            speech_pulse=ctx.speech_pulse,
            timeline_stage=ctx.timeline_stage,
            overlay_intensity=ctx.overlay_intensity,
            dt_s=ctx.dt_s,
            elapsed_s=ctx.elapsed_s,
        )
        self._eye_overlay.draw(surface, eye_pose, eye_ctx)

        # 2. Draw Mouth-specific procedural accents
        if ctx.current_state == "speaking" and ctx.speech_pulse > 0.1:
            self._draw_speech_subtle_glow(surface, mouth_params, ctx)

    def _draw_speech_subtle_glow(
        self,
        surface: pygame.Surface,
        mouth_params: MouthParams,
        ctx: RenderContext,
    ) -> None:
        """Draw subtle procedural speech accent dots near mouth sides during speech."""
        alpha = ctx.speech_pulse * ctx.overlay_intensity * 0.4
        if alpha <= 0.01:
            return

        col = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
        cx = mouth_params.pos_x + mouth_params.offset_x
        cy = mouth_params.pos_y + mouth_params.offset_y
        w = mouth_params.width * 0.65

        left_x = int(round(cx - w))
        right_x = int(round(cx + w))
        iy = int(round(cy))

        try:
            pygame.gfxdraw.aacircle(surface, left_x, iy, 2, col)
            pygame.gfxdraw.filled_circle(surface, left_x, iy, 2, col)
            pygame.gfxdraw.aacircle(surface, right_x, iy, 2, col)
            pygame.gfxdraw.filled_circle(surface, right_x, iy, 2, col)
        except Exception:
            pass
