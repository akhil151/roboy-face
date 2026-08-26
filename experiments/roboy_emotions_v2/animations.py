"""ROBoy Emotion V2 - deterministic animation helpers.

All motion is a pure function of time ``t`` (seconds). No randomness, no
stateful drift. This keeps the animation reproducible and verifiable.
"""

import math


def breathe(t, period, amp):
    """Smooth scale modulation in [-amp, +amp] (sine based)."""
    return amp * math.sin((2.0 * math.pi * t) / period)


def blink_factor(t, period, duration, phase=0.0):
    """Return 0 (open) .. 1 (fully closed) using a smooth close/open pulse.

    The blink occupies ``duration`` seconds once per ``period``.
    """
    x = ((t + phase) % period) / period
    window = duration / period
    if x < window:
        u = x / window
        return math.sin(u * math.pi)  # 0 -> 1 -> 0
    return 0.0


def pulse(t, period, amp, phase=0.0):
    """Sine pulse in [0, amp] returning a positive value."""
    return amp * (0.5 + 0.5 * math.sin((2.0 * math.pi * t) / period + phase))


def ease_in_out(u):
    """Smooth 0..1 easing (cosine)."""
    u = max(0.0, min(1.0, u))
    return 0.5 * (1.0 - math.cos(math.pi * u))


def saw_fade(z_local, life):
    """Alpha envelope (0..1) for a lifecycle item of given ``life``.

    Quick fade-in, hold, then fade-out. ``z_local`` is seconds since spawn.
    """
    if z_local < 0 or z_local > life:
        return 0.0
    fade_in = life * 0.18
    fade_out = life * 0.34
    if z_local < fade_in:
        return ease_in_out(z_local / fade_in)
    if z_local > life - fade_out:
        return ease_in_out((life - z_local) / fade_out)
    return 1.0
