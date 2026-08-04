"""
RenderContext data model for Face Engine.

Immutable context carrying frame animation metadata across Eyes, Mouth, and FX:
- current_state: active state name ("calm", "happy", etc.)
- blend_progress: state transition blend t in [0.0, 1.0]
- speech_pulse: current speech articulation intensity in [0.0, 1.0]
- timeline_stage: active state stage ("enter", "loop", "exit")
- overlay_intensity: global overlay opacity scaling in [0.0, 1.0]
- dt_s: delta time since last frame in seconds
- elapsed_s: total elapsed animation time in seconds
- mouse_look: normalized look target coordinates (x, y)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RenderContext:
    current_state: str = "calm"
    blend_progress: float = 1.0
    speech_pulse: float = 0.0
    timeline_stage: str = "loop"
    overlay_intensity: float = 1.0
    dt_s: float = 0.016
    elapsed_s: float = 0.0
    mouse_look: Tuple[float, float] = (0.0, 0.0)
