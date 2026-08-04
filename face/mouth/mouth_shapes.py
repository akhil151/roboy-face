"""
Procedural Mouth State Parameters & State Presets.

Defines MouthParams, structured identically to EyeParams with zero-allocation
in-place interpolation (lerp_into), copy_from, clamp_safe, and presets for all
10 official character emotional states.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


_DEFAULT_MOUTH_PARAMS = {
    "pos_x": 400.0,
    "pos_y": 340.0,
    "width": 68.0,
    "height": 16.0,
    "thickness": 14.0,
    "upper_curvature": 0.0,
    "lower_curvature": 0.0,
    "smile_amount": 0.0,
    "opening": 0.0,
    "stretch": 0.0,
    "squash": 0.0,
    "rotation": 0.0,
    "corner_roundness": 1.0,
    "offset_x": 0.0,
    "offset_y": 0.0,
    "opacity": 1.0,
}

_PARAM_NAMES: Tuple[str, ...] = tuple(_DEFAULT_MOUTH_PARAMS.keys())


@dataclass
class MouthParams:
    pos_x: float = 400.0
    pos_y: float = 340.0
    width: float = 68.0
    height: float = 16.0
    thickness: float = 14.0
    upper_curvature: float = 0.0
    lower_curvature: float = 0.0
    smile_amount: float = 0.0
    opening: float = 0.0
    stretch: float = 0.0
    squash: float = 0.0
    rotation: float = 0.0
    corner_roundness: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    opacity: float = 1.0

    def copy(self) -> "MouthParams":
        new_params = MouthParams()
        for name in _PARAM_NAMES:
            setattr(new_params, name, getattr(self, name))
        return new_params

    def copy_from(self, other: "MouthParams") -> None:
        for name in _PARAM_NAMES:
            setattr(self, name, getattr(other, name))

    def reset(self) -> None:
        for name, value in _DEFAULT_MOUTH_PARAMS.items():
            setattr(self, name, value)

    def lerp_into(self, a: "MouthParams", b: "MouthParams", t: float) -> None:
        """Zero-allocation linear interpolation: self = a + (b - a) * t."""
        t = max(0.0, min(1.0, t))
        for name in _PARAM_NAMES:
            av = getattr(a, name)
            bv = getattr(b, name)
            setattr(self, name, av + (bv - av) * t)

    def clamp_safe(self) -> None:
        """Clamp parameters to safe physical and aesthetic rendering bounds."""
        self.opacity = max(0.0, min(1.0, self.opacity))
        self.width = max(16.0, min(105.0, self.width))  # Max ~35-40% of face width scale
        self.height = max(6.0, min(80.0, self.height))
        self.thickness = max(4.0, min(30.0, self.thickness))
        self.upper_curvature = max(-1.0, min(1.0, self.upper_curvature))
        self.lower_curvature = max(-1.0, min(1.0, self.lower_curvature))
        self.smile_amount = max(-1.0, min(1.0, self.smile_amount))
        self.opening = max(0.0, min(1.0, self.opening))
        self.stretch = max(-0.5, min(0.8, self.stretch))
        self.squash = max(-0.5, min(0.8, self.squash))
        self.rotation = max(-0.4, min(0.4, self.rotation))
        self.corner_roundness = max(0.1, min(1.0, self.corner_roundness))
        self.offset_x = max(-60.0, min(60.0, self.offset_x))
        self.offset_y = max(-60.0, min(60.0, self.offset_y))


# ---------------------------------------------------------------------------
# Presets for the 10 official character emotional states (Silhouette Focus)
# ---------------------------------------------------------------------------

MOUTH_PRESETS: Dict[str, MouthParams] = {
    "calm": MouthParams(
        width=58.0,
        height=10.0,
        thickness=10.0,
        upper_curvature=0.0,
        lower_curvature=0.0,
        smile_amount=0.0,
        corner_roundness=1.0,
        opening=0.0,
        opacity=0.0,
    ),
    "happy": MouthParams(
        width=116.0,
        height=34.0,
        thickness=22.0,
        upper_curvature=0.10,
        lower_curvature=0.42,
        smile_amount=0.82,
        corner_roundness=1.0,
        opening=0.0,
        offset_y=3.0,
    ),
    "caring": MouthParams(
        width=74.0,
        height=24.0,
        thickness=16.0,
        upper_curvature=0.08,
        lower_curvature=0.24,
        smile_amount=0.34,
        corner_roundness=1.0,
        opening=0.0,
        opacity=0.92,
    ),
    "speaking": MouthParams(
        width=52.0,
        height=10.0,
        thickness=12.0,
        upper_curvature=0.0,
        lower_curvature=0.04,
        smile_amount=0.0,
        corner_roundness=0.92,
        opening=0.0,
        opacity=0.72,
    ),
    "thinking": MouthParams(
        width=50.0,
        height=10.0,
        thickness=11.0,
        upper_curvature=0.0,
        lower_curvature=0.04,
        smile_amount=0.0,
        corner_roundness=0.95,
        offset_x=0.0,
        rotation=0.0,
        opening=0.0,
        opacity=0.22,
    ),
    "sad": MouthParams(
        width=86.0,
        height=30.0,
        thickness=20.0,
        upper_curvature=-0.10,
        lower_curvature=0.58,
        smile_amount=-0.72,
        corner_roundness=0.95,
        opening=0.0,
        offset_y=4.0,
    ),
    "surprised": MouthParams(
        width=28.0,
        height=60.0,
        thickness=18.0,
        upper_curvature=0.0,
        lower_curvature=0.0,
        smile_amount=0.0,
        corner_roundness=1.0,
        opening=0.0,
        opacity=0.98,
        offset_y=6.0,
    ),
    "sleepy": MouthParams(
        width=46.0,
        height=10.0,
        thickness=10.0,
        upper_curvature=0.0,
        lower_curvature=0.02,
        smile_amount=0.0,
        corner_roundness=1.0,
        opening=0.0,
        opacity=0.06,
    ),
    "focus": MouthParams(
        width=40.0,
        height=9.0,
        thickness=10.0,
        upper_curvature=0.0,
        lower_curvature=0.0,
        smile_amount=0.0,
        corner_roundness=0.86,
        opening=0.0,
        opacity=0.88,
    ),
    "listening": MouthParams(
        width=60.0,
        height=14.0,
        thickness=12.0,
        upper_curvature=0.02,
        lower_curvature=0.10,
        smile_amount=0.12,
        corner_roundness=1.0,
        opening=0.0,
        opacity=0.52,
    ),
}


def get_mouth_preset(state_name: str) -> MouthParams:
    """Return a copy of the default MouthParams for a given state name."""
    preset = MOUTH_PRESETS.get(state_name.lower())
    if preset is None:
        preset = MOUTH_PRESETS["calm"]
    return preset.copy()
