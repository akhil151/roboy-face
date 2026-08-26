"""ROBoy Emotion V2 - expression overlays.

Builds two overlay types used by the V2 designs:

* ``?``  - the THINKING question mark, kept OUTSIDE the eye perimeter
* ``Z``  - the SLEEPY drifting ZZZ sequence

Both are deterministic functions of time. No randomness.
"""

import math

import config as cfg
import animations as anim


class OverlaySpec:
    def __init__(self, kind, text, cx, cy, size_norm, alpha, color, radius_norm):
        self.kind = kind
        self.text = text
        self.cx = cx
        self.cy = cy
        self.size_norm = size_norm
        self.alpha = alpha
        self.color = color
        self.radius_norm = radius_norm


def _perimeter_point(ex, ey, dist, angle_deg, side):
    """A point near the eye perimeter, on the outer-top side.

    ``side`` == 'right' -> outer is +x; 'left' -> outer is -x.
    Angle is measured upward from the horizontal (y grows downward).
    """
    a = math.radians(angle_deg)
    dx = math.cos(a)
    dy = -math.sin(a)                 # upward
    if side == "left":
        dx = -dx
    return (ex + dist * dx, ey + dist * dy)


def build_question(eye_center, t):
    ex, ey = eye_center
    side = cfg.Q_EYE_SIDE
    cx, cy = _perimeter_point(ex, ey, cfg.Q_DIST, cfg.Q_ANGLE_DEG, side)
    # subtle bob + natural fade
    cy += cfg.Q_BOB_AMP * math.sin(2 * math.pi * t / cfg.Q_BOB_PERIOD)
    fade = 0.5 + 0.5 * math.sin(2 * math.pi * t / cfg.Q_FADE_PERIOD)
    alpha = int(cfg.Q_FADE_MIN + (255 - cfg.Q_FADE_MIN) * fade)
    return [OverlaySpec("question", "?", cx, cy, cfg.Q_SIZE, alpha,
                        cfg.FACE_COLOR, 0.5 * cfg.Q_SIZE)]


def build_zzz(eye_center, t):
    ex, ey = eye_center
    side = cfg.ZZZ_EYE_SIDE
    out = []
    for i in range(3):
        offset = i * cfg.ZZZ_STAGGER
        local = (t + offset) % cfg.ZZZ_CYCLE
        if local >= cfg.ZZZ_LIFE:
            continue
        env = anim.saw_fade(local, cfg.ZZZ_LIFE)
        if env <= 0.0:
            continue
        size = cfg.ZZZ_SIZE0 * (cfg.ZZZ_SIZE_STEP ** i)
        peak_alpha = cfg.ZZZ_ALPHA0 * (cfg.ZZZ_ALPHA_STEP ** i)
        alpha = int(peak_alpha * env)
        p = local / cfg.ZZZ_LIFE
        # fixed diagonal anchor (gives clear separation between glyphs) plus
        # a gentle upward drift over each glyph's life.
        base_x, base_y = _perimeter_point(ex, ey, cfg.ZZZ_DIST0,
                                          cfg.ZZZ_ANGLE_DEG, side)
        cx = base_x + cfg.ZZZ_SPREAD_X * i + cfg.ZZZ_DRIFT_X * p
        cy = base_y - cfg.ZZZ_SPREAD_Y * i - cfg.ZZZ_RISE * p
        out.append(OverlaySpec("z", "Z", cx, cy, size, alpha,
                               cfg.FACE_COLOR, 0.5 * size))
    return out
