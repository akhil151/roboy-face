"""
FaceRenderer compatibility alias. Replaced by FaceComposer per architecture specification.
"""

from .face_composer import FaceComposer as FaceRenderer

__all__ = ["FaceRenderer"]
