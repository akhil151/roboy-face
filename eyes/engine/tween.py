"""
Generic tween engine for smooth parameter interpolation.

Supports delayed start, callbacks, and chainable easing.
Never snaps values - all transitions are continuous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .easing import EasingFunction, get_easing, lerp, clamp01


@dataclass
class Tween:
    start_value: float
    end_value: float
    duration_ms: float
    easing: EasingFunction
    elapsed_ms: float = 0.0
    delay_ms: float = 0.0
    on_complete: Optional[Callable[[], None]] = None
    on_update: Optional[Callable[[float], None]] = None
    completed: bool = False
    _started: bool = False

    def update(self, dt_ms: float) -> float:
        if self.completed:
            return self.end_value

        if self.delay_ms > 0:
            self.delay_ms -= dt_ms
            if self.delay_ms > 0:
                return self.start_value

        self._started = True
        self.elapsed_ms += dt_ms

        t = self.elapsed_ms / self.duration_ms if self.duration_ms > 0 else 1.0
        t = clamp01(t)

        eased_t = self.easing(t)
        current = lerp(self.start_value, self.end_value, eased_t)

        if self.on_update is not None:
            self.on_update(current)

        if t >= 1.0:
            self.completed = True
            if self.on_complete is not None:
                self.on_complete()

        return current

    @property
    def value(self) -> float:
        if self.completed:
            return self.end_value
        if not self._started:
            return self.start_value
        t = clamp01(self.elapsed_ms / self.duration_ms) if self.duration_ms > 0 else 1.0
        eased_t = self.easing(t)
        return lerp(self.start_value, self.end_value, eased_t)


class TweenEngine:
    def __init__(self) -> None:
        self._tweens: list[Tween] = []

    def tween_to(
        self,
        start: float,
        end: float,
        duration_ms: float,
        easing: str | EasingFunction = "ease_in_out_cubic",
        delay_ms: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
        on_update: Optional[Callable[[float], None]] = None,
    ) -> Tween:
        easing_fn = easing if callable(easing) else get_easing(easing)
        t = Tween(
            start_value=start,
            end_value=end,
            duration_ms=duration_ms,
            easing=easing_fn,
            delay_ms=delay_ms,
            on_complete=on_complete,
            on_update=on_update,
        )
        self._tweens.append(t)
        return t

    def update(self, dt_ms: float) -> None:
        if not self._tweens:
            return
        for tween in self._tweens:
            tween.update(dt_ms)
        self._tweens = [t for t in self._tweens if not t.completed]

    def clear(self) -> None:
        self._tweens.clear()

    @property
    def active_count(self) -> int:
        return len(self._tweens)
