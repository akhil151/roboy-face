"""
Micro-motion system - prevents eyes from appearing frozen.

Implements four layers of subtle procedural movement:
- Breathing: gentle vertical sinusoid (slow, uniform)
- Sway: gentle horizontal sinusoid (different period)
- Drift: slow combined wandering using sine product noise
- Idle jitter: very tiny, very slow position variation

All amplitudes are 1-3 pixels and movements are very slow.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Tuple

from .config import EngineConfig


@dataclass
class MicroMotion:
    _config: EngineConfig
    _elapsed_seconds: float = 0.0
    _phase_offset: float = 0.0
    _drift_seed_x: float = 0.0
    _drift_seed_y: float = 0.0

    def __post_init__(self) -> None:
        self._phase_offset = self._config.micro_motion.phase_offset
        self._drift_seed_x = random.uniform(0.0, 100.0)
        self._drift_seed_y = random.uniform(100.0, 200.0)

    def reset(self) -> None:
        self._elapsed_seconds = 0.0
        self._drift_seed_x = random.uniform(0.0, 100.0)
        self._drift_seed_y = random.uniform(100.0, 200.0)

    def get_offsets(self) -> Tuple[float, float]:
        mm = self._config.micro_motion
        t = self._elapsed_seconds + self._phase_offset

        breathe_y = math.sin(t * 2.0 * math.pi / mm.breathe_period_seconds) * mm.breathe_amplitude

        sway_x = math.sin(t * 2.0 * math.pi / mm.sway_period_seconds + 0.7) * mm.sway_amplitude
        sway_y = math.cos(t * 2.0 * math.pi / (mm.sway_period_seconds * 1.3) + 1.2) * mm.sway_amplitude * 0.6

        drift_t = t / mm.drift_period_seconds
        drift_x = (
            math.sin(drift_t * 2.0 * math.pi + self._drift_seed_x)
            * math.cos(drift_t * 1.7 * math.pi + self._drift_seed_x * 0.3)
            * mm.drift_amplitude
        )
        drift_y = (
            math.cos(drift_t * 2.0 * math.pi * 0.8 + self._drift_seed_y)
            * math.sin(drift_t * 1.3 * math.pi + self._drift_seed_y * 0.5)
            * mm.drift_amplitude
            * 0.8
        )

        x = sway_x + drift_x
        y = breathe_y + sway_y + drift_y

        scale = mm.amplitude / max(mm.amplitude, 1.0)
        return (x * scale, y * scale)

    def update(self, dt_seconds: float) -> None:
        self._elapsed_seconds += dt_seconds
