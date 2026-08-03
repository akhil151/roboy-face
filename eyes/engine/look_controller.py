"""
Look direction controller with spring interpolation.

Exposes look_at(x, y) API with normalized coordinates [0, 1].
Uses spring physics to ensure smooth, non-snapping eye movement.
Both eyes move symmetrically toward the target direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .config import EngineConfig
from .spring import Spring2D, SpringConfig


@dataclass
class LookController:
    _config: EngineConfig
    _look_spring: Spring2D = field(default_factory=lambda: Spring2D(SpringConfig.medium(), (0.5, 0.5)))
    _target_norm: Tuple[float, float] = (0.5, 0.5)

    def look_at(self, nx: float, ny: float) -> None:
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        self._target_norm = (nx, ny)
        self._look_spring.set_target(nx, ny)

    def set_look_config(self, config: SpringConfig) -> None:
        self._look_spring.set_config(config)

    def reset(self) -> None:
        self._look_spring.set_value_immediate(0.5, 0.5)
        self._look_spring.set_target(0.5, 0.5)
        self._target_norm = (0.5, 0.5)

    @property
    def current_normalized(self) -> Tuple[float, float]:
        return self._look_spring.value

    def get_offsets(self) -> Tuple[float, float]:
        nx, ny = self._look_spring.value
        max_off = self._config.layout.look_max_offset
        dx = (nx - 0.5) * 2.0 * max_off
        dy = (ny - 0.5) * 2.0 * max_off
        return (dx, dy)

    def update(self, dt_seconds: float) -> None:
        self._look_spring.update(dt_seconds)

    def at_rest(self) -> bool:
        return self._look_spring.at_rest()
