"""
Procedural blink controller.

Blink timing is never fixed - random intervals between 3-5 seconds.
Supports normal blink, double blink, slow blink, and half blink.
All animations use easing curves for smooth lid motion.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .config import EngineConfig
from .easing import ease_in_out_sine, ease_out_sine
from .tween import TweenEngine


class BlinkType(Enum):
    NORMAL = "normal"
    DOUBLE = "double"
    SLOW = "slow"
    HALF = "half"


@dataclass
class BlinkController:
    _config: EngineConfig
    _tweens: TweenEngine = field(default_factory=TweenEngine)
    _current_blink_weight: float = 0.0
    _next_blink_ms: float = 3000.0
    _elapsed_ms: float = 0.0
    _force_blink_pending: bool = False
    _active: bool = True

    def __post_init__(self) -> None:
        self._schedule_next_blink()

    def _schedule_next_blink(self) -> None:
        timing = self._config.timing
        self._next_blink_ms = random.uniform(
            timing.blink_interval_min_ms, timing.blink_interval_max_ms
        )
        self._elapsed_ms = 0.0

    def _pick_blink_type(self) -> BlinkType:
        r = random.random()
        timing = self._config.timing
        cumulative = timing.double_blink_chance
        if r < cumulative:
            return BlinkType.DOUBLE
        cumulative += timing.slow_blink_chance
        if r < cumulative:
            return BlinkType.SLOW
        cumulative += timing.half_blink_chance
        if r < cumulative:
            return BlinkType.HALF
        return BlinkType.NORMAL

    def trigger_blink(self, blink_type: Optional[BlinkType] = None) -> None:
        if blink_type is None:
            blink_type = self._pick_blink_type()
        self._execute_blink(blink_type)

    def force_blink(self) -> None:
        self._force_blink_pending = True

    def set_active(self, active: bool) -> None:
        self._active = active

    @property
    def blink_weight(self) -> float:
        return self._current_blink_weight

    def _execute_blink(self, blink_type: BlinkType) -> None:
        timing = self._config.timing
        duration = timing.blink_duration_ms

        if blink_type == BlinkType.SLOW:
            duration *= timing.slow_blink_multiplier
            self._tweens.tween_to(
                start=self._current_blink_weight,
                end=1.0,
                duration_ms=duration * 0.5,
                easing=ease_in_out_sine,
                on_update=lambda v: setattr(self, "_current_blink_weight", v),
                on_complete=lambda: self._tweens.tween_to(
                    start=1.0,
                    end=0.0,
                    duration_ms=duration * 0.5,
                    easing=ease_in_out_sine,
                    on_update=lambda v: setattr(self, "_current_blink_weight", v),
                ),
            )

        elif blink_type == BlinkType.HALF:
            half_max = timing.half_blink_ratio
            self._tweens.tween_to(
                start=self._current_blink_weight,
                end=half_max,
                duration_ms=duration * 0.4,
                easing=ease_out_sine,
                on_update=lambda v: setattr(self, "_current_blink_weight", v),
                on_complete=lambda: self._tweens.tween_to(
                    start=half_max,
                    end=0.0,
                    duration_ms=duration * 0.6,
                    easing=ease_in_out_sine,
                    on_update=lambda v: setattr(self, "_current_blink_weight", v),
                ),
            )

        elif blink_type == BlinkType.DOUBLE:
            gap = timing.double_blink_gap_ms

            def second_blink() -> None:
                self._tweens.tween_to(
                    start=0.0,
                    end=1.0,
                    duration_ms=duration * 0.4,
                    easing=ease_out_sine,
                    on_update=lambda v: setattr(self, "_current_blink_weight", v),
                    on_complete=lambda: self._tweens.tween_to(
                        start=1.0,
                        end=0.0,
                        duration_ms=duration * 0.5,
                        easing=ease_in_out_sine,
                        on_update=lambda v: setattr(self, "_current_blink_weight", v),
                    ),
                )

            self._tweens.tween_to(
                start=self._current_blink_weight,
                end=1.0,
                duration_ms=duration * 0.4,
                easing=ease_out_sine,
                on_update=lambda v: setattr(self, "_current_blink_weight", v),
                on_complete=lambda: self._tweens.tween_to(
                    start=1.0,
                    end=0.0,
                    duration_ms=duration * 0.4,
                    easing=ease_in_out_sine,
                    on_update=lambda v: setattr(self, "_current_blink_weight", v),
                    on_complete=lambda: self._tweens.tween_to(
                        start=0.0,
                        end=0.0,
                        duration_ms=gap,
                        easing="linear",
                        on_complete=second_blink,
                    ),
                ),
            )

        else:  # NORMAL
            self._tweens.tween_to(
                start=self._current_blink_weight,
                end=1.0,
                duration_ms=duration * 0.4,
                easing=ease_out_sine,
                on_update=lambda v: setattr(self, "_current_blink_weight", v),
                on_complete=lambda: self._tweens.tween_to(
                    start=1.0,
                    end=0.0,
                    duration_ms=duration * 0.55,
                    easing=ease_in_out_sine,
                    on_update=lambda v: setattr(self, "_current_blink_weight", v),
                ),
            )

    def update(self, dt_ms: float) -> None:
        self._tweens.update(dt_ms)

        if not self._active:
            return

        if self._force_blink_pending:
            self._force_blink_pending = False
            self._execute_blink(BlinkType.NORMAL)
            self._schedule_next_blink()
            return

        self._elapsed_ms += dt_ms
        if self._elapsed_ms >= self._next_blink_ms:
            bt = self._pick_blink_type()
            self._execute_blink(bt)
            self._schedule_next_blink()
