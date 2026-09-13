"""Easing and interpolation functions for organic, smooth motion curves.

Includes standard normalized easing curves (t in [0, 1]) and framerate-independent
exponential decay smoothing for continuous real-time state tracking.
"""

import math


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value within [min_val, max_val]."""
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val


def lerp(a: float, b: float, t: float) -> float:
    """Standard linear interpolation between a and b."""
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    """Cubic Hermite interpolation: 3t^2 - 2t^3."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t: float) -> float:
    """Ken Perlin's smootherstep: 6t^5 - 15t^4 + 10t^3."""
    t = clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def cubic_in_out(t: float) -> float:
    """Cubic ease-in-out curve for smooth acceleration and deceleration."""
    t = clamp(t, 0.0, 1.0)
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        p = 2.0 * t - 2.0
        return 0.5 * p * p * p + 1.0


def quad_out(t: float) -> float:
    """Quadratic ease-out curve."""
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) * (1.0 - t)


def elastic_out(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
    """Elastic ease-out for expressive bounce/rebound effects."""
    t = clamp(t, 0.0, 1.0)
    if t == 0.0 or t == 1.0:
        return t
    s = period / 4.0
    return amplitude * math.pow(2.0, -10.0 * t) * math.sin((t - s) * (2.0 * math.pi) / period) + 1.0


def exp_decay(current: float, target: float, rate: float, dt: float) -> float:
    """Framerate-independent exponential smoothing.

    Mathematically exact critically-damped convergence:
    new_val = target + (current - target) * exp(-rate * dt)

    Args:
        current: Current floating point value.
        target: Target destination value.
        rate: Decay velocity constant (higher = faster convergence).
        dt: Delta time elapsed in seconds.
    """
    if dt <= 0.0:
        return current
    decay = math.exp(-max(0.0, rate) * dt)
    return target + (current - target) * decay
