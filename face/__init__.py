"""
Public API for the ELO Face Engine v1.0.

Provides:
  - class FaceEngine: Public facade
  - class FaceComposer: Modular layer compositor
  - class FaceMixer: Unified emotion state machine
  - class RenderContext: Animation frame metadata
"""

from __future__ import annotations

__version__ = "1.0.0"

from eyes import VALID_STATES
from .face_engine import FaceEngine
from .face_composer import FaceComposer
from .face_mixer import FaceMixer
from .render_context import RenderContext

__all__ = [
    "FaceEngine",
    "FaceComposer",
    "FaceMixer",
    "RenderContext",
    "VALID_STATES",
]
