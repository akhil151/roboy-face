"""ROBoy Emotion V2 - expression overlays.

Builds overlay types used by the V2 designs:

* ``thought_cloud``   - the THINKING thought cloud, kept OUTSIDE the eye perimeter
* ``?``               - the CONFUSED question mark, kept OUTSIDE the eye perimeter
* ``Z``               - the SLEEPY drifting ZZZ sequence
* ``listening_waves`` - the LISTENING curved sound waves above the eyes

All are deterministic functions of time. No randomness.
"""

import math

import config as cfg
import animations as anim


class OverlaySpec:
    def __init__(self, kind, text, cx, cy, size_norm, alpha, color, radius_norm, **kw):
        self.kind = kind
        self.text = text
        self.cx = cx
        self.cy = cy
        self.size_norm = size_norm
        self.alpha = alpha
        self.color = color
        self.radius_norm = radius_norm
        self.lobes = kw.get("lobes", None)
        self.dots = kw.get("dots", None)
        self.arcs = kw.get("arcs", None)
        self.thickness = kw.get("thickness", None)


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


def build_thought_cloud(eye_center, t):
    """Build an animated thought cloud that grows from a dot, expands, and fades in a cycle.

    Enhanced for clear visual liveliness matching Sleepy ZZZ animation style.
    """
    ex, ey = eye_center
    side = cfg.CLOUD_EYE_SIDE
    cx, cy = _perimeter_point(ex, ey, cfg.CLOUD_DIST, cfg.CLOUD_ANGLE_DEG, side)

    # Deterministic cycle: local time within the full cycle
    local_t = t % cfg.CLOUD_CYCLE

    # Animate cloud size and alpha through phases
    if local_t < cfg.CLOUD_GROW_PHASE:
        # Phase 1: Small dot grows into cloud (EXTENDED for more visible emergence)
        phase_u = local_t / cfg.CLOUD_GROW_PHASE
        # Non-linear growth: quick burst early, then steady
        size_factor = phase_u * phase_u * (3.0 - 2.0 * phase_u)  # smooth cubic easing
        alpha = int(100 + 155 * phase_u)  # starts at 100, ramps to 255
    elif local_t < cfg.CLOUD_GROW_PHASE + cfg.CLOUD_PEAK_PHASE:
        # Phase 2: Cloud at peak size (SHORTENED to show fade sooner)
        size_factor = 1.0
        alpha = 255
    else:
        # Phase 3: Cloud fades away (EXTENDED for perceptible fade)
        fade_u = (local_t - cfg.CLOUD_GROW_PHASE - cfg.CLOUD_PEAK_PHASE) / cfg.CLOUD_FADE_PHASE
        fade_u = min(1.0, fade_u)
        # Non-linear fade: stays visible longer, then fades fast at end
        size_factor = max(0.0, 1.0 - fade_u * fade_u)
        alpha = int(255 * (1.0 - fade_u) + cfg.CLOUD_ALPHA_MIN * fade_u)

    # Apply stronger bob during peak and fade (more visible motion)
    bob = 0.0
    if local_t > 0.2:  # start bob slightly after growth begins
        if local_t < cfg.CLOUD_GROW_PHASE + cfg.CLOUD_PEAK_PHASE + 0.3:
            bob = cfg.CLOUD_BOB_AMP * math.sin(2 * math.pi * t / cfg.CLOUD_BOB_PERIOD)
    cy += bob

    r_eff = 0.5 * cfg.CLOUD_SIZE * size_factor  # scale cloud with animation

    # Geometric cloud lobes: (rel_x, rel_y, radius) relative to cloud centre
    lobes = [
        (0.00 * r_eff,  0.05 * r_eff, 0.54 * r_eff),   # center
        (-0.52 * r_eff,  0.08 * r_eff, 0.44 * r_eff),  # left
        (0.52 * r_eff,  0.08 * r_eff, 0.44 * r_eff),   # right
        (-0.28 * r_eff, -0.32 * r_eff, 0.46 * r_eff),  # top-left
        (0.28 * r_eff, -0.32 * r_eff, 0.46 * r_eff),   # top-right
        (0.00 * r_eff,  0.22 * r_eff, 0.42 * r_eff),   # bottom filler
    ]

    # Small thought-bubble dots leading from eye toward cloud (max 2)
    dots = []
    if size_factor > 0.25:  # dots visible during growth and peak
        dot_alpha_factor = min(1.0, (size_factor - 0.25) / 0.75)
        dots = [
            (-0.68 * r_eff,  0.88 * r_eff, 0.15 * r_eff * dot_alpha_factor),
            (-0.95 * r_eff,  1.38 * r_eff, 0.09 * r_eff * dot_alpha_factor),
        ]

    return [OverlaySpec("thought_cloud", "", cx, cy, cfg.CLOUD_SIZE * size_factor, int(alpha),
                        cfg.FACE_COLOR, r_eff, lobes=lobes, dots=dots)]


def build_listening_waves(eye_center, t):
    """Build animated listening waves with rightward tilt and enhanced visibility.

    Positioned upper-right above the right eye, anchored relative to the eye perimeter.
    Animation: appear → grow → full → fade → repeat (deterministic phase-based).
    Signal tilted slightly toward the right for directional emphasis.
    """
    ex, ey = eye_center
    side = cfg.LISTENING_WAVES_EYE_SIDE
    cx, cy = _perimeter_point(ex, ey, cfg.LISTENING_WAVES_DIST, cfg.LISTENING_WAVES_ANGLE_DEG, side)

    arcs = []
    # Upward-facing curved arcs: centered at 90 deg (pointing up), then rotated right
    base_angle_deg = 90.0
    angle_center_deg = base_angle_deg + cfg.LISTENING_WAVES_ANGLE_TILT  # tilt toward right
    half_span = cfg.LISTENING_WAVES_SPAN_DEG / 2.0
    a0 = math.radians(angle_center_deg - half_span)
    a1 = math.radians(angle_center_deg + half_span)

    # Fade/pulse cycle: waves fade in/out with clearer amplitude
    fade_phase = (2 * math.pi * t / cfg.LISTENING_WAVES_FADE_PERIOD)
    fade_envelope = 0.5 + 0.5 * math.sin(fade_phase)  # 0..1

    # Map fade envelope to alpha range for more visible modulation
    alpha_min, alpha_max = cfg.LISTENING_WAVES_ALPHA_RANGE
    fade_alpha_envelope = alpha_min + (alpha_max - alpha_min) * fade_envelope

    for i in range(3):
        r_base = cfg.LISTENING_WAVES_R0 + i * cfg.LISTENING_WAVES_SPACING
        phase = (2 * math.pi * t / cfg.LISTENING_WAVES_PERIOD) - i * 0.75
        pulse = 0.5 + 0.5 * math.sin(phase)
        arc_r = r_base * (1.0 + 0.04 * math.sin(phase))  # slightly increased ripple (was 0.03)
        # Alpha combines ripple pulse AND fade envelope for visible cascade
        base_alpha = alpha_min + (alpha_max - alpha_min) * pulse
        arc_alpha = int(base_alpha * fade_envelope)
        arcs.append({
            "r": arc_r,
            "a0": a0,
            "a1": a1,
            "alpha": arc_alpha,
            "thickness": cfg.LISTENING_WAVES_THICK,
        })

    max_r = cfg.LISTENING_WAVES_R0 + 2 * cfg.LISTENING_WAVES_SPACING
    return [OverlaySpec("listening_waves", "", cx, cy, max_r * 2.0, int(fade_alpha_envelope),
                        cfg.FACE_COLOR, max_r, arcs=arcs,
                        thickness=cfg.LISTENING_WAVES_THICK)]


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
