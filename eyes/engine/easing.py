"""
Easing functions for smooth interpolation.

All functions accept a parameter t in range [0.0, 1.0]
and return an eased value in approximately [0.0, 1.0].
Some easing functions (Back, Elastic) may temporarily overshoot.
"""

from __future__ import annotations

import math
from typing import Callable

EasingFunction = Callable[[float], float]


def clamp01(t: float) -> float:
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


def linear(t: float) -> float:
    return clamp01(t)


def ease_in_quad(t: float) -> float:
    t = clamp01(t)
    return t * t


def ease_out_quad(t: float) -> float:
    t = clamp01(t)
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 * 0.5


def ease_in_cubic(t: float) -> float:
    t = clamp01(t)
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = clamp01(t)
    p = t - 1.0
    return p * p * p + 1.0


def ease_in_out_cubic(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 * 0.5


def ease_in_quart(t: float) -> float:
    t = clamp01(t)
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    t = clamp01(t)
    p = t - 1.0
    return 1.0 - p * p * p * p


def ease_in_out_quart(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return 8.0 * t * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 4 * 0.5


def ease_in_sine(t: float) -> float:
    t = clamp01(t)
    return 1.0 - math.cos((t * math.pi) * 0.5)


def ease_out_sine(t: float) -> float:
    t = clamp01(t)
    return math.sin((t * math.pi) * 0.5)


def ease_in_out_sine(t: float) -> float:
    t = clamp01(t)
    return -(math.cos(math.pi * t) - 1.0) * 0.5


def ease_in_expo(t: float) -> float:
    t = clamp01(t)
    if t == 0.0:
        return 0.0
    return 2.0 ** (10.0 * (t - 1.0))


def ease_out_expo(t: float) -> float:
    t = clamp01(t)
    if t == 1.0:
        return 1.0
    return 1.0 - 2.0 ** (-10.0 * t)


def ease_in_out_expo(t: float) -> float:
    t = clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    if t < 0.5:
        return (2.0 ** (20.0 * t - 10.0)) * 0.5
    return (2.0 - 2.0 ** (-20.0 * t + 10.0)) * 0.5


def ease_in_circ(t: float) -> float:
    t = clamp01(t)
    return 1.0 - math.sqrt(1.0 - t * t)


def ease_out_circ(t: float) -> float:
    t = clamp01(t)
    return math.sqrt(1.0 - (t - 1.0) ** 2)


def ease_in_out_circ(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return (1.0 - math.sqrt(1.0 - (2.0 * t) ** 2)) * 0.5
    return (math.sqrt(1.0 - (-2.0 * t + 2.0) ** 2) + 1.0) * 0.5


_BACK_OVERSHOOT = 1.70158
_BACK_OVERSHOOT_DOUBLE = 2.5949095


def ease_in_back(t: float, overshoot: float = _BACK_OVERSHOOT) -> float:
    t = clamp01(t)
    return (overshoot + 1.0) * t * t * t - overshoot * t * t


def ease_out_back(t: float, overshoot: float = _BACK_OVERSHOOT) -> float:
    t = clamp01(t)
    p = t - 1.0
    return 1.0 + (overshoot + 1.0) * p * p * p + overshoot * p * p


def ease_in_out_back(t: float, overshoot: float = _BACK_OVERSHOOT_DOUBLE) -> float:
    t = clamp01(t)
    if t < 0.5:
        m = 2.0 * t
        return (overshoot + 1.0) * m * m * m - overshoot * m * m
    m = 2.0 * t - 2.0
    return 1.0 + 0.5 * ((overshoot + 1.0) * m * m * m + overshoot * m * m)


_ELASTIC_C1 = 1.70158
_ELASTIC_C2 = _ELASTIC_C1 * 1.525


def ease_in_elastic(t: float) -> float:
    t = clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * c4)


def ease_out_elastic(t: float) -> float:
    t = clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return (2.0 ** (-10.0 * t)) * math.sin((t * 10.0 - 0.75) * c4) + 1.0


def ease_in_out_elastic(t: float) -> float:
    t = clamp01(t)
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    c5 = (2.0 * math.pi) / 4.5
    if t < 0.5:
        return -(2.0 ** (20.0 * t - 10.0)) * math.sin((20.0 * t - 11.125) * c5) * 0.5
    return (2.0 ** (-20.0 * t + 10.0)) * math.sin((20.0 * t - 11.125) * c5) * 0.5 + 1.0


def ease_out_bounce(t: float) -> float:
    t = clamp01(t)
    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    elif t < 2.0 / d1:
        t2 = t - 1.5 / d1
        return n1 * t2 * t2 + 0.75
    elif t < 2.5 / d1:
        t2 = t - 2.25 / d1
        return n1 * t2 * t2 + 0.9375
    else:
        t2 = t - 2.625 / d1
        return n1 * t2 * t2 + 0.984375


def ease_in_bounce(t: float) -> float:
    t = clamp01(t)
    return 1.0 - ease_out_bounce(1.0 - t)


def ease_in_out_bounce(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return (1.0 - ease_out_bounce(1.0 - 2.0 * t)) * 0.5
    return (1.0 + ease_out_bounce(2.0 * t - 1.0)) * 0.5


EASING_MAP: dict[str, EasingFunction] = {
    "linear": linear,
    "ease_in": ease_in_quad,
    "ease_out": ease_out_quad,
    "ease_in_out": ease_in_out_quad,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "cubic": ease_in_out_cubic,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
    "ease_in_quart": ease_in_quart,
    "ease_out_quart": ease_out_quart,
    "ease_in_out_quart": ease_in_out_quart,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,
    "ease_in_expo": ease_in_expo,
    "ease_out_expo": ease_out_expo,
    "ease_in_out_expo": ease_in_out_expo,
    "ease_in_circ": ease_in_circ,
    "ease_out_circ": ease_out_circ,
    "ease_in_out_circ": ease_in_out_circ,
    "back": ease_in_out_back,
    "ease_in_back": ease_in_back,
    "ease_out_back": ease_out_back,
    "ease_in_out_back": ease_in_out_back,
    "elastic": ease_in_out_elastic,
    "ease_in_elastic": ease_in_elastic,
    "ease_out_elastic": ease_out_elastic,
    "ease_in_out_elastic": ease_in_out_elastic,
    "ease_in_bounce": ease_in_bounce,
    "ease_out_bounce": ease_out_bounce,
    "ease_in_out_bounce": ease_in_out_bounce,
}


def get_easing(name: str) -> EasingFunction:
    if name not in EASING_MAP:
        raise ValueError(f"Unknown easing: {name}. Available: {sorted(EASING_MAP.keys())}")
    return EASING_MAP[name]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_clamped(a: float, b: float, t: float) -> float:
    return lerp(a, b, clamp01(t))
