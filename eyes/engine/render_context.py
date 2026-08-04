"""
RenderContext data model.

Immutable context carrying frame metadata alongside EyePair geometry:
- current_state: name of active state ("calm", "happy", etc.)
- blend_progress: state transition blend t in [0.0, 1.0] (1.0 when settled)
- speech_pulse: current speech articulation intensity in [0.0, 1.0]
- timeline_stage: active state stage ("enter", "loop", "exit")
- overlay_intensity: global overlay opacity scaling in [0.0, 1.0]
- dt_s: delta time since last frame in seconds
- elapsed_s: total elapsed animation time in seconds
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderContext:
    current_state: str = "calm"
    blend_progress: float = 1.0
    speech_pulse: float = 0.0
    timeline_stage: str = "loop"
    overlay_intensity: float = 1.0
    dt_s: float = 0.016
    elapsed_s: float = 0.0
