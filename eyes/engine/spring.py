"""
Spring physics system for smooth, natural motion.

Used for eye movement, look direction, and target following.
Second-order critical-damped spring: produces smooth motion without jitter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class SpringConfig:
    stiffness: float = 180.0
    damping: float = 28.0
    mass: float = 1.0

    @classmethod
    def slow(cls) -> "SpringConfig":
        return cls(stiffness=80.0, damping=18.0, mass=1.0)

    @classmethod
    def medium(cls) -> "SpringConfig":
        return cls(stiffness=180.0, damping=28.0, mass=1.0)

    @classmethod
    def fast(cls) -> "SpringConfig":
        return cls(stiffness=320.0, damping=36.0, mass=1.0)

    @classmethod
    def snappy(cls) -> "SpringConfig":
        return cls(stiffness=480.0, damping=40.0, mass=1.0)


class Spring1D:
    def __init__(
        self,
        config: SpringConfig | None = None,
        initial_value: float = 0.0,
    ) -> None:
        self._config = config or SpringConfig.medium()
        self._value = initial_value
        self._target = initial_value
        self._velocity = 0.0

    @property
    def value(self) -> float:
        return self._value

    @property
    def target(self) -> float:
        return self._target

    @property
    def velocity(self) -> float:
        return self._velocity

    @property
    def stiffness(self) -> float:
        return self._config.stiffness

    @property
    def damping(self) -> float:
        return self._config.damping

    @property
    def mass(self) -> float:
        return self._config.mass

    def set_target(self, target: float) -> None:
        self._target = target

    def set_value_immediate(self, value: float) -> None:
        self._value = value
        self._target = value
        self._velocity = 0.0

    def set_config(self, config: SpringConfig) -> None:
        self._config = config

    def update(self, dt_seconds: float) -> float:
        if dt_seconds <= 0.0:
            return self._value

        dt = min(dt_seconds, 0.05)
        k = self._config.stiffness
        c = self._config.damping
        m = self._config.mass

        force = -k * (self._value - self._target) - c * self._velocity
        acceleration = force / m
        self._velocity += acceleration * dt
        self._value += self._velocity * dt

        if abs(self._velocity) < 0.001 and abs(self._value - self._target) < 0.0001:
            self._value = self._target
            self._velocity = 0.0

        return self._value

    def at_rest(self, tol_value: float = 0.001, tol_velocity: float = 0.001) -> bool:
        return (
            abs(self._velocity) < tol_velocity
            and abs(self._value - self._target) < tol_value
        )


class Spring2D:
    def __init__(
        self,
        config: SpringConfig | None = None,
        initial_value: Tuple[float, float] = (0.0, 0.0),
    ) -> None:
        cfg = config or SpringConfig.medium()
        self._spring_x = Spring1D(cfg, initial_value[0])
        self._spring_y = Spring1D(cfg, initial_value[1])

    @property
    def value(self) -> Tuple[float, float]:
        return (self._spring_x.value, self._spring_y.value)

    @property
    def target(self) -> Tuple[float, float]:
        return (self._spring_x.target, self._spring_y.target)

    @property
    def velocity(self) -> Tuple[float, float]:
        return (self._spring_x.velocity, self._spring_y.velocity)

    def set_target(self, x: float, y: float) -> None:
        self._spring_x.set_target(x)
        self._spring_y.set_target(y)

    def set_value_immediate(self, x: float, y: float) -> None:
        self._spring_x.set_value_immediate(x)
        self._spring_y.set_value_immediate(y)

    def set_config(self, config: SpringConfig) -> None:
        self._spring_x.set_config(config)
        self._spring_y.set_config(config)

    def update(self, dt_seconds: float) -> Tuple[float, float]:
        x = self._spring_x.update(dt_seconds)
        y = self._spring_y.update(dt_seconds)
        return (x, y)

    def at_rest(self, tol_value: float = 0.001, tol_velocity: float = 0.001) -> bool:
        return self._spring_x.at_rest(tol_value, tol_velocity) and self._spring_y.at_rest(
            tol_value, tol_velocity
        )
