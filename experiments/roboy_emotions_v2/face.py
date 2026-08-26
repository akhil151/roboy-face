"""ROBoy Emotion V2 - face specification model.

A :class:`FaceSpec` is a pure, normalized description of the face for one
emotion at one instant. It is independent of pygame, which makes it easy to
build, inspect and verify without a display.

The :func:`build_face` dispatcher produces the correct geometry for each of
the 14 emotions, applying deterministic time-based animation on top of the
base (static) design.
"""

import math

import config as cfg
import animations as anim
import overlays as ov


# ---------------------------------------------------------------------------
# Spec data classes
# ---------------------------------------------------------------------------

class EyeSpec:
    """One eye. Geometry type is selected by ``shape``."""

    def __init__(self, shape, cx, cy, **kw):
        self.shape = shape
        self.cx = cx
        self.cy = cy
        # circle
        self.rx = kw.get("rx", 0.0)
        self.ry = kw.get("ry", 0.0)
        self.lid = kw.get("lid", 0.0)          # 0..1 fraction of top covered
        # arc
        self.r = kw.get("r", 0.0)
        self.a0 = kw.get("a0", 0.0)
        self.a1 = kw.get("a1", 0.0)
        # curve (sleepy u)
        self.p0 = kw.get("p0", None)
        self.p1 = kw.get("p1", None)
        self.p2 = kw.get("p2", None)
        # polygon (unused legacy)
        self.points = kw.get("points", None)
        # angry filled curved shape (two quadratic Beziers)
        self.curve_a = kw.get("curve_a", None)
        self.curve_t = kw.get("curve_t", None)
        self.curve_b = kw.get("curve_b", None)
        self.curve_u = kw.get("curve_u", None)
        # heart
        self.heart_scale = kw.get("heart_scale", 0.0)
        self.thickness = kw.get("thickness", cfg.EYE_THICK)
        self.color = kw.get("color", None)


class MouthSpec:
    def __init__(self, shape, cx, cy, w, **kw):
        self.shape = shape
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = kw.get("h", 0.0)
        self.thickness = kw.get("thickness", cfg.MOUTH_THICK)
        self.amp = kw.get("amp", 0.0)
        self.waves = kw.get("waves", 1.0)
        self.phase = kw.get("phase", 0.0)
        self.color = kw.get("color", None)


class FaceSpec:
    def __init__(self, emotion, eyes, mouth, overlays=None):
        self.emotion = emotion
        self.eyes = eyes              # list[EyeSpec]
        self.mouth = mouth            # MouthSpec
        self.overlays = overlays or []  # list[OverlaySpec]


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def eye_centers():
    lx = 0.5 - cfg.EYE_DX
    rx = 0.5 + cfg.EYE_DX
    return {"left": (lx, cfg.EYE_CY), "right": (rx, cfg.EYE_CY)}


def _circle(cx, cy, r, ry=None, lid=0.0, color=None):
    return EyeSpec("circle", cx, cy, rx=r, ry=ry if ry else r, lid=lid, color=color)


def _arc(cx, cy, r, a0, a1, thickness=None, color=None):
    return EyeSpec("arc", cx, cy, r=r, a0=a0, a1=a1,
                   thickness=thickness or cfg.EYE_THICK, color=color)


# ---------------------------------------------------------------------------
# Per-emotion builders
# ---------------------------------------------------------------------------

def _neutral(t, c):
    eyes = [
        _circle(c["left"][0], c["left"][1], cfg.EYE_R),
        _circle(c["right"][0], c["right"][1], cfg.EYE_R),
    ]
    b = anim.breathe(t, cfg.BREATH_PERIOD, cfg.BREATH_AMP)
    for e in eyes:
        e.rx *= (1.0 + b)
        e.ry *= (1.0 - cfg.BLINK_DEPTH * anim.blink_factor(t, cfg.BLINK_PERIOD, cfg.BLINK_DURATION))
    mouth = MouthSpec("capsule", 0.5, cfg.MOUTH_CY, cfg.MOUTH_W)
    return eyes, mouth


def _happy(t, c):
    a0, a1 = math.radians(200), math.radians(340)
    th = cfg.EYE_THICK * 1.30
    eyes = [
        _arc(c["left"][0], c["left"][1], cfg.EYE_R * 1.22, a0, a1, th),
        _arc(c["right"][0], c["right"][1], cfg.EYE_R * 1.22, a0, a1, th),
    ]
    comp = anim.pulse(t, 3.0, 0.025)              # soft eye compression
    for e in eyes:
        e.r *= (1.0 - comp)
    mouth = MouthSpec("smile", 0.5, cfg.MOUTH_CY - 0.02, cfg.MOUTH_W * 1.05,
                      h=0.05)
    return eyes, mouth


def _excited(t, c):
    b = anim.breathe(t, cfg.EXCITED_PERIOD, 0.03)
    r = cfg.EYE_R * 1.38 * (1.0 + b)
    eyes = [
        _circle(c["left"][0], c["left"][1], r),
        _circle(c["right"][0], c["right"][1], r),
    ]
    mouth = MouthSpec("open_smile", 0.5, cfg.MOUTH_CY - 0.01, cfg.MOUTH_W * 1.15,
                      h=0.075)
    return eyes, mouth


def _sad(t, c):
    a0, a1 = math.radians(20), math.radians(160)
    settle = anim.breathe(t, cfg.SAD_SETTLE_PERIOD, 0.012)
    eyes = [
        _arc(c["left"][0], c["left"][1] + 0.012 + settle,
             cfg.EYE_R * 1.02, a0, a1, cfg.EYE_THICK * 1.25),
        _arc(c["right"][0], c["right"][1] + 0.012 + settle,
             cfg.EYE_R * 1.02, a0, a1, cfg.EYE_THICK * 1.25),
    ]
    mouth = MouthSpec("frown", 0.5, cfg.MOUTH_CY + 0.01, cfg.MOUTH_W * 0.92,
                      h=0.038)
    return eyes, mouth


def _surprised(t, c):
    # quick open reaction on replay (small t) then gentle settle
    react = 1.0 if t < 0.001 else (1.0 - 0.06 * anim.ease_in_out(min(1.0, t / 0.5)))
    r = cfg.EYE_R * 1.38 * react
    eyes = [
        _circle(c["left"][0], c["left"][1], r),
        _circle(c["right"][0], c["right"][1], r),
    ]
    mouth = MouthSpec("open", 0.5, cfg.MOUTH_CY, 0.085, h=0.12)
    return eyes, mouth


def _thinking(t, c):
    # TWO clearly open, equal-sized eyes (no blink / no wink / no closure)
    gaze = 0.012 * math.sin(2 * math.pi * t / 4.0)
    eyes = [
        _circle(c["left"][0], c["left"][1] + gaze, cfg.EYE_R * 0.95),
        _circle(c["right"][0], c["right"][1] + gaze, cfg.EYE_R * 0.95),
    ]
    mouth = MouthSpec("capsule", 0.5, cfg.MOUTH_CY, cfg.MOUTH_W * 0.85)
    ovs = ov.build_question(c["right"], t)
    return eyes, mouth, ovs


def _confused(t, c):
    # Asymmetric / worried eyes (distinct from Thinking's symmetric pair)
    # plus an uncertain mouth and the '?' cue.
    hes = 0.01 * math.sin(2 * math.pi * t / cfg.CONFUSED_PERIOD)
    left = _arc(c["left"][0], c["left"][1] - 0.020, cfg.EYE_R * 0.92,
                math.radians(200), math.radians(340))      # raised worried eye
    right = _circle(c["right"][0] + 0.012, c["right"][1] + 0.012 + hes,
                    cfg.EYE_R * 0.78)                       # smaller, lower eye
    eyes = [left, right]
    mouth = MouthSpec("wavy", 0.5, cfg.MOUTH_CY, cfg.MOUTH_W * 0.9,
                      amp=0.020, waves=1.0, phase=0.6)
    ovs = ov.build_question(c["right"], t)
    return eyes, mouth, ovs


def _wink(t, c):
    open_e = _circle(c["left"][0], c["left"][1], cfg.EYE_R)
    # right eye: closed, animate a slow wink (mostly closed, opens briefly)
    wf = anim.blink_factor(t, cfg.WINK_PERIOD, 0.25, phase=0.0)
    if wf > 0.5:
        right = _circle(c["right"][0], c["right"][1], cfg.EYE_R * (1.0 - 0.7 * wf))
        right.ry *= (1.0 - 0.8 * wf)
    else:
        right = _arc(c["right"][0], c["right"][1], cfg.EYE_R * 0.85,
                     math.radians(200), math.radians(340))
    eyes = [open_e, right]
    mouth = MouthSpec("smile", 0.5, cfg.MOUTH_CY - 0.02, cfg.MOUTH_W * 1.05, h=0.05)
    return eyes, mouth


def _love(t, c):
    b = anim.pulse(t, cfg.LOVE_PULSE_PERIOD, cfg.LOVE_PULSE_AMP)
    hs = cfg.EYE_R * cfg.HEART_SCALE * (1.0 + b)
    eyes = [
        EyeSpec("heart", c["left"][0], c["left"][1], heart_scale=hs),
        EyeSpec("heart", c["right"][0], c["right"][1], heart_scale=hs),
    ]
    mouth = MouthSpec("smile", 0.5, cfg.MOUTH_CY - 0.01, cfg.MOUTH_W * 0.9, h=0.04)
    return eyes, mouth


def _tired(t, c):
    lid = cfg.TIRED_LID_BASE + cfg.TIRED_LID_AMP * math.sin(2 * math.pi * t / cfg.TIRED_LID_PERIOD)
    eyes = [
        _circle(c["left"][0], c["left"][1], cfg.EYE_R * 0.95, lid=lid),
        _circle(c["right"][0], c["right"][1], cfg.EYE_R * 0.95, lid=lid),
    ]
    mouth = MouthSpec("capsule", 0.5, cfg.MOUTH_CY + 0.005, cfg.MOUTH_W * 0.9)
    return eyes, mouth


def _sleepy(t, c):
    relax = anim.breathe(t, cfg.SLEEPY_RELAX_PERIOD, cfg.SLEEPY_RELAX_AMP)
    depth = 0.50 + relax * 0.10          # gentle, not a deep U
    s = cfg.EYE_R * 1.00                 # same footprint as an open eye
    eyes = []
    for side in ("left", "right"):
        cx, cy = c[side]
        # relaxed, slightly loose U with softly splayed ends
        p0 = (cx - s, cy - 0.14 * s)
        p1 = (cx, cy + depth * s)
        p2 = (cx + s, cy - 0.14 * s)
        eyes.append(EyeSpec("sleepy_u", cx, cy, p0=p0, p1=p1, p2=p2,
                            thickness=cfg.EYE_THICK * 1.25))
    mouth = MouthSpec("capsule", 0.5, cfg.MOUTH_CY + 0.01, cfg.MOUTH_W * 0.55)
    ovs = ov.build_zzz(c["right"], t)
    return eyes, mouth, ovs


def _angry(t, c):
    tension = anim.breathe(t, cfg.ANGRY_TENSION_PERIOD, cfg.ANGRY_TENSION_AMP)
    eyes = []
    for side in ("left", "right"):
        cx, cy = c[side]
        s = cfg.EYE_R * 1.40 * (1.0 + tension)
        a, tctrl, b, uctrl = _angry_curve(cx, cy, s, side)
        eyes.append(EyeSpec("angry", cx, cy,
                            curve_a=a, curve_t=tctrl, curve_b=b, curve_u=uctrl,
                            color=cfg.FACE_COLOR))
    mouth = MouthSpec("capsule", 0.5, cfg.MOUTH_CY + 0.01, cfg.MOUTH_W * 0.85)
    return eyes, mouth


def _fearful(t, c):
    # worried, tense eyes: tall wide-open ovals (a staring "wide-eyed" look)
    # with a slight asymmetric tilt so it reads as anxious, not surprised.
    j = cfg.FEARFUL_AMP * math.sin(2 * math.pi * t / cfg.FEARFUL_PERIOD)
    j2 = cfg.FEARFUL_AMP * 0.6 * math.sin(2 * math.pi * t / cfg.FEARFUL_PERIOD + 1.3)
    rx = cfg.EYE_R * 1.05
    ry = cfg.EYE_R * 1.22               # taller than wide -> wide-eyed stare
    eyes = [
        _circle(c["left"][0],  c["left"][1]  + j - 0.008, rx, ry=ry),
        _circle(c["right"][0], c["right"][1] + j2 + 0.006, rx, ry=ry),
    ]
    # small tense curved-down mouth (worried), distinct from surprised's O
    mouth = MouthSpec("frown", 0.5, cfg.MOUTH_CY + 0.005, cfg.MOUTH_W * 0.66,
                      h=0.028)
    return eyes, mouth


def _disgusted(t, c):
    a0, a1 = math.radians(20), math.radians(160)
    eyes = [
        _arc(c["left"][0], c["left"][1] + 0.005, cfg.EYE_R * 0.92, a0, a1,
             thickness=cfg.EYE_THICK * 1.3),
        _arc(c["right"][0] - 0.015, c["right"][1] - 0.02, cfg.EYE_R * 0.72,
             a0, a1, thickness=cfg.EYE_THICK * 1.3),
    ]
    mouth = MouthSpec("curl", 0.5, cfg.MOUTH_CY, cfg.MOUTH_W * 0.9,
                      amp=-0.03, waves=1.5, phase=0.0)
    return eyes, mouth


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------

def _angry_curve(cx, cy, s, side):
    """Anchors for a FILLED slanted angry eye matching reference.

    The shape is bounded by two quadratic Beziers:
      * top edge    : a (outer-top, high) -> b (inner-bottom, dropped) via t
      * bottom edge : b -> a via u (smooth rounded bowl)

    Inner corner ``b`` drops downward toward center; outer corner ``a`` is high.
    Both eyes are mirrored across their respective centres.
    """
    # left eye geometry; right eye is mirrored about cx
    a = (cx - 1.25 * s, cy - 0.48 * s)   # outer top (high)
    b = (cx + 0.95 * s, cy + 0.52 * s)   # inner bottom (dropped)
    t = (cx - 0.10 * s, cy - 0.08 * s)   # top control (straight/slanted slash)
    u = (cx - 0.15 * s, cy + 0.85 * s)   # bottom control (rounded lower contour)
    if side == "right":
        a = (2 * cx - a[0], a[1])
        b = (2 * cx - b[0], b[1])
        t = (2 * cx - t[0], t[1])
        u = (2 * cx - u[0], u[1])
    return a, t, b, u


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_BUILDERS = {
    "neutral": _neutral,
    "happy": _happy,
    "excited": _excited,
    "sad": _sad,
    "surprised": _surprised,
    "thinking": _thinking,
    "confused": _confused,
    "wink": _wink,
    "love": _love,
    "tired": _tired,
    "sleepy": _sleepy,
    "angry": _angry,
    "fearful": _fearful,
    "disgusted": _disgusted,
}


def build_face(emotion, t, color=None):
    """Build a :class:`FaceSpec` for ``emotion`` at time ``t`` (seconds)."""
    if emotion not in _BUILDERS:
        raise ValueError(f"unknown emotion: {emotion}")
    c = eye_centers()
    result = _BUILDERS[emotion](t, c)
    eyes, mouth = result[0], result[1]
    overlays = result[2] if len(result) > 2 else []
    if color is not None:
        for e in eyes:
            if e.color is None:
                e.color = color
        if mouth.color is None:
            mouth.color = color
    return FaceSpec(emotion, eyes, mouth, overlays)
