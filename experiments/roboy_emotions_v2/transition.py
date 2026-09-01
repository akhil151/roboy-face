"""ROBoy Emotion V2 - live emotion transition system (Canonical Semantic Architecture).

Provides smooth, continuous, shape-family-aware geometric transitions between all 14
ROBoy Emotion V2 expressions (182 directed pairs). Operates in normalized face coordinates
and preserves the locked, approved V2 geometry at all endpoints and static states.

Architecture:
    Emotion definition (emotions.py / face.py)
          |
    current pose / start spec
          |
    TransitionController (transition.py)
          |
    interpolated pose (FaceSpec)
          |
    existing V2 renderer (renderer.py)

Key Principles:
1. Canonical Semantic Coordinates:
   - For every eye, establishes canonical physical endpoints: `left_pt` (left side, x <= cx)
     and `right_pt` (right side, x >= cx), preserving left/right orientation across all shape families.
2. Exact Arc <-> Bezier Conversion:
   - Mathematically exact apex control calculation: p1.y = 2.0 * y_apex - y_base, eliminating
     the 31-pixel apex jump when entering/leaving Happy, Sad, and Disgusted.
3. Mirrored Angry Normalization:
   - Semantic normalization of Angry's left eye (a=outer-left, b=inner-right) and right eye
     (a=outer-right, b=inner-left) so right eye control points never cross in x, eliminating
     all self-intersecting polygon anomalies.
4. Seamless Eyelid Squint / Flattening:
   - Continuous width and thickness matching between solid ellipses and curved strokes without
     abrupt primitive pops.
5. Coordinated Eye/Mouth Timing:
   - Organic lead-lag timing within configured transition duration.
6. Real-time Mid-Transition Interruption:
   - Captures current interpolated pose as new start state without snapping or reset.
7. Purely Deterministic:
   - Driven by update(dt) with no threads, timers, sleep, or background clocks.
"""

import math
import copy

import config as cfg
import geometry as g
import face as fc
import overlays as ov
import emotions as em


# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------

def smootherstep(u: float) -> float:
    """Ken Perlin's smootherstep curve: 6u^5 - 15u^4 + 10u^3.

    Properties:
    - S(0) = 0, S(1) = 1
    - S'(0) = 0, S'(1) = 0 (zero velocity at start and finish)
    - S''(0) = 0, S''(1) = 0 (zero acceleration / zero jerk at endpoints)
    - Strictly monotonic on [0, 1]
    """
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


def ease_in_out_cubic(u: float) -> float:
    """Standard cubic ease-in-out."""
    u = max(0.0, min(1.0, u))
    if u < 0.5:
        return 4.0 * u * u * u
    p = 2.0 * u - 2.0
    return 0.5 * p * p * p + 1.0


# ---------------------------------------------------------------------------
# Scalar & Point Interpolation Helpers
# ---------------------------------------------------------------------------

def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def lerp_pt(p0, p1, u: float):
    if p0 is None and p1 is None:
        return None
    if p0 is None:
        return p1
    if p1 is None:
        return p0
    return (lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u))


# ---------------------------------------------------------------------------
# Eye Shape Classification & Canonical Anchor Extraction
# ---------------------------------------------------------------------------

def get_eye_family(e: fc.EyeSpec) -> str:
    """Classify eye spec into its shape family."""
    if e.shape == "circle":
        return "circle"
    if e.shape == "arc":
        return "arc"
    if e.shape == "sleepy_u":
        return "sleepy_u"
    if e.shape == "angry":
        return "angry"
    if e.shape == "heart":
        return "heart"
    return "other"


def get_canonical_eye_anchors(e: fc.EyeSpec, side: str = "left"):
    """Extract canonical semantic coordinates for any eye shape.

    Returns:
        (left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, is_upward)
        where:
          - left_pt is always the physical left endpoint (x <= cx)
          - right_pt is always the physical right endpoint (x >= cx)
          - top_ctrl is the quadratic control point for upper contour / apex
          - bot_ctrl is the quadratic control point for lower contour
          - p1_mid is the exact Bezier control point reaching the true apex
    """
    cx, cy = e.cx, e.cy
    thick = getattr(e, "thickness", None) or cfg.EYE_THICK

    if e.shape == "circle":
        rx = getattr(e, "rx", None) or cfg.EYE_R
        ry = getattr(e, "ry", None) or rx
        lid = getattr(e, "lid", 0.0) or 0.0
        left_pt = (cx - rx, cy)
        right_pt = (cx + rx, cy)
        top_ctrl = (cx, cy - 2.0 * ry * (1.0 - lid))
        bot_ctrl = (cx, cy + 2.0 * ry)
        p1_mid = (cx, cy)
        return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, True

    if e.shape == "arc":
        r = getattr(e, "r", None) or cfg.EYE_R
        a0 = getattr(e, "a0", 0.0) or 0.0
        a1 = getattr(e, "a1", math.pi) or math.pi
        p0 = (cx + r * math.cos(a0), cy - r * math.sin(a0))
        p1_end = (cx + r * math.cos(a1), cy - r * math.sin(a1))

        # Enforce canonical semantic left vs right endpoints
        if p0[0] <= p1_end[0]:
            left_pt = p0
            right_pt = p1_end
        else:
            left_pt = p1_end
            right_pt = p0

        is_upward = math.sin(a0) > 0 or math.sin(a1) > 0
        y_apex = cy - r if is_upward else cy + r
        y_base = (left_pt[1] + right_pt[1]) / 2.0

        # Exact Bezier control point reaching the true arc apex (eliminates apex pop)
        p1_y_exact = 2.0 * y_apex - y_base
        p1_mid = (cx, p1_y_exact)

        top_y = 2.0 * (cy - r if is_upward else cy + (r - thick)) - y_base
        bot_y = 2.0 * (cy - (r - thick) if is_upward else cy + r) - y_base
        top_ctrl = (cx, top_y)
        bot_ctrl = (cx, bot_y)
        return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, is_upward

    if e.shape == "sleepy_u":
        s = cfg.EYE_R * 1.00
        p0 = getattr(e, "p0", None) or (cx - s, cy - 0.14 * s)
        p1 = getattr(e, "p1", None) or (cx, cy + 0.50 * s)
        p2 = getattr(e, "p2", None) or (cx + s, cy - 0.14 * s)

        if p0[0] <= p2[0]:
            left_pt = p0
            right_pt = p2
        else:
            left_pt = p2
            right_pt = p0

        top_ctrl = (p1[0], p1[1] - thick / 2.0)
        bot_ctrl = (p1[0], p1[1] + thick / 2.0)
        p1_mid = p1
        return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, False

    if e.shape == "angry":
        if side == "left":
            left_pt = e.curve_a
            right_pt = e.curve_b
        else:
            left_pt = e.curve_b
            right_pt = e.curve_a
        top_ctrl = e.curve_t
        bot_ctrl = e.curve_u
        p1_mid = top_ctrl
        return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, True

    if e.shape == "heart":
        hs = getattr(e, "heart_scale", cfg.EYE_R * cfg.HEART_SCALE)
        left_pt = (cx - hs, cy)
        right_pt = (cx + hs, cy)
        top_ctrl = (cx, cy - hs)
        bot_ctrl = (cx, cy + hs)
        p1_mid = (cx, cy)
        return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, True

    # Fallback
    r = cfg.EYE_R
    left_pt = (cx - r, cy)
    right_pt = (cx + r, cy)
    top_ctrl = (cx, cy - 2.0 * r)
    bot_ctrl = (cx, cy + 2.0 * r)
    p1_mid = (cx, cy)
    return left_pt, right_pt, top_ctrl, bot_ctrl, p1_mid, True


# ---------------------------------------------------------------------------
# Shape-Family-Aware Eye Morphing
# ---------------------------------------------------------------------------

def _morph_circle_to_circle(e0: fc.EyeSpec, e1: fc.EyeSpec, u: float) -> fc.EyeSpec:
    """Direct parameter morph between two circular/open eyes."""
    cx = lerp(e0.cx, e1.cx, u)
    cy = lerp(e0.cy, e1.cy, u)
    rx = lerp(e0.rx, e1.rx, u)
    ry = lerp(e0.ry, e1.ry, u)
    lid0 = getattr(e0, "lid", 0.0) or 0.0
    lid1 = getattr(e1, "lid", 0.0) or 0.0
    lid = lerp(lid0, lid1, u)
    thick = lerp(getattr(e0, "thickness", cfg.EYE_THICK), getattr(e1, "thickness", cfg.EYE_THICK), u)
    color = e1.color if u >= 0.5 else e0.color
    return fc.EyeSpec("circle", cx, cy, rx=rx, ry=ry, lid=lid, thickness=thick, color=color)


def _morph_arc_to_arc(e0: fc.EyeSpec, e1: fc.EyeSpec, u: float, side: str = "left") -> fc.EyeSpec:
    """Controlled curve morph between two curved stroke arcs."""
    cx = lerp(e0.cx, e1.cx, u)
    cy = lerp(e0.cy, e1.cy, u)
    thick = lerp(getattr(e0, "thickness", cfg.EYE_THICK), getattr(e1, "thickness", cfg.EYE_THICK), u)
    color = e1.color if u >= 0.5 else e0.color

    l0, r0, _, _, p1_0, is_up0 = get_canonical_eye_anchors(e0, side)
    l1, r1, _, _, p1_1, is_up1 = get_canonical_eye_anchors(e1, side)

    if is_up0 == is_up1:
        # Same orientation: smooth polar arc interpolation
        r = lerp(e0.r, e1.r, u)
        a0 = lerp(e0.a0, e1.a0, u)
        a1 = lerp(e0.a1, e1.a1, u)
        return fc.EyeSpec("arc", cx, cy, r=r, a0=a0, a1=a1, thickness=thick, color=color)
    else:
        # Reversing curvature (Happy smile arc <-> Sad frown arc):
        # Left and right endpoints stay in place while apex translates vertically through 0
        left_pt = lerp_pt(l0, l1, u)
        right_pt = lerp_pt(r0, r1, u)
        p1 = lerp_pt(p1_0, p1_1, u)
        return fc.EyeSpec("sleepy_u", cx, cy, p0=left_pt, p1=p1, p2=right_pt,
                          thickness=thick, color=color)


def _morph_circle_to_arc(circle_e: fc.EyeSpec, arc_e: fc.EyeSpec, u_toward_arc: float, side: str = "left") -> fc.EyeSpec:
    """Eyelid squint / flattening morph between Circle and Arc."""
    u = u_toward_arc
    cx = lerp(circle_e.cx, arc_e.cx, u)
    cy = lerp(circle_e.cy, arc_e.cy, u)
    thick_target = getattr(arc_e, "thickness", cfg.EYE_THICK)
    thick_start = getattr(circle_e, "thickness", cfg.EYE_THICK)
    thick = lerp(thick_start, thick_target, u)
    color = arc_e.color if u >= 0.5 else circle_e.color

    l_arc, r_arc, _, _, p1_arc, is_upward = get_canonical_eye_anchors(arc_e, side)
    span_x = (r_arc[0] - l_arc[0]) / 2.0

    if u <= 0.35:
        # Stage 1: Circle flattens vertically into a rounded horizontal stroke
        phase_u = u / 0.35
        rx = lerp(circle_e.rx, span_x, phase_u)
        ry = lerp(circle_e.ry, thick / 2.0, phase_u)
        lid = lerp(getattr(circle_e, "lid", 0.0) or 0.0, 0.0, phase_u)
        return fc.EyeSpec("circle", cx, cy, rx=rx, ry=ry, lid=lid, thickness=thick, color=color)
    else:
        # Stage 2: Flattened horizontal stroke curves smoothly into the exact arc apex
        phase_u = (u - 0.35) / 0.65
        p0_flat = (cx - span_x, cy)
        p1_flat = (cx, cy)
        p2_flat = (cx + span_x, cy)

        p0 = lerp_pt(p0_flat, l_arc, phase_u)
        p1 = lerp_pt(p1_flat, p1_arc, phase_u)
        p2 = lerp_pt(p2_flat, r_arc, phase_u)
        return fc.EyeSpec("sleepy_u", cx, cy, p0=p0, p1=p1, p2=p2, thickness=thick, color=color)


def _morph_circle_to_sleepy(circle_e: fc.EyeSpec, sleepy_e: fc.EyeSpec, u_toward_sleepy: float, side: str = "left") -> fc.EyeSpec:
    """Eyelid droop & relaxation morph between Circle and Sleepy U."""
    u = u_toward_sleepy
    cx = lerp(circle_e.cx, sleepy_e.cx, u)
    cy = lerp(circle_e.cy, sleepy_e.cy, u)
    thick = lerp(getattr(circle_e, "thickness", cfg.EYE_THICK), getattr(sleepy_e, "thickness", cfg.EYE_THICK), u)
    color = sleepy_e.color if u >= 0.5 else circle_e.color

    l_sleep, r_sleep, _, _, p1_sleep, _ = get_canonical_eye_anchors(sleepy_e, side)
    s = cfg.EYE_R * 1.00

    if u <= 0.35:
        # Upper lid droops down over the circle
        phase_u = u / 0.35
        lid = lerp(getattr(circle_e, "lid", 0.0) or 0.0, 0.70, phase_u)
        rx = lerp(circle_e.rx, s, phase_u)
        ry = lerp(circle_e.ry, circle_e.ry * 0.85, phase_u)
        return fc.EyeSpec("circle", cx, cy, rx=rx, ry=ry, lid=lid, thickness=thick, color=color)
    else:
        # Drooped base forms the relaxed U cup
        phase_u = (u - 0.35) / 0.65
        p0_start = (cx - s, cy)
        p1_start = (cx, cy + 0.10 * s)
        p2_start = (cx + s, cy)

        p0 = lerp_pt(p0_start, l_sleep, phase_u)
        p1 = lerp_pt(p1_start, p1_sleep, phase_u)
        p2 = lerp_pt(p2_start, r_sleep, phase_u)
        return fc.EyeSpec("sleepy_u", cx, cy, p0=p0, p1=p1, p2=p2, thickness=thick, color=color)


def _morph_arc_to_sleepy(arc_e: fc.EyeSpec, sleepy_e: fc.EyeSpec, u_toward_sleepy: float, side: str = "left") -> fc.EyeSpec:
    """Direct quadratic curve morph between Arc and Sleepy U."""
    u = u_toward_sleepy
    cx = lerp(arc_e.cx, sleepy_e.cx, u)
    cy = lerp(arc_e.cy, sleepy_e.cy, u)
    thick = lerp(getattr(arc_e, "thickness", cfg.EYE_THICK), getattr(sleepy_e, "thickness", cfg.EYE_THICK), u)
    color = sleepy_e.color if u >= 0.5 else arc_e.color

    l_arc, r_arc, _, _, p1_arc, _ = get_canonical_eye_anchors(arc_e, side)
    l_sleep, r_sleep, _, _, p1_sleep, _ = get_canonical_eye_anchors(sleepy_e, side)

    p0 = lerp_pt(l_arc, l_sleep, u)
    p1 = lerp_pt(p1_arc, p1_sleep, u)
    p2 = lerp_pt(r_arc, r_sleep, u)
    return fc.EyeSpec("sleepy_u", cx, cy, p0=p0, p1=p1, p2=p2, thickness=thick, color=color)


def _morph_angry(e0: fc.EyeSpec, e1: fc.EyeSpec, u: float, side: str = "left") -> fc.EyeSpec:
    """Brow tension / relaxation morph involving Angry filled wedge.

    Uses canonical semantic normalization so endpoints never cross on either eye.
    """
    cx = lerp(e0.cx, e1.cx, u)
    cy = lerp(e0.cy, e1.cy, u)
    thick = lerp(getattr(e0, "thickness", cfg.EYE_THICK), getattr(e1, "thickness", cfg.EYE_THICK), u)
    color = e1.color if u >= 0.5 else e0.color

    l0, r0, t0, u0, _, _ = get_canonical_eye_anchors(e0, side)
    l1, r1, t1, u1, _, _ = get_canonical_eye_anchors(e1, side)

    # Canonical semantic interpolation
    cur_left = lerp_pt(l0, l1, u)
    cur_right = lerp_pt(r0, r1, u)
    cur_top = lerp_pt(t0, t1, u)
    cur_bot = lerp_pt(u0, u1, u)

    # Reconstruct Angry's expected internal format based on eye side
    if side == "left":
        ca = cur_left
        cb = cur_right
    else:
        # Right eye is mirrored: a is outer-right, b is inner-left
        ca = cur_right
        cb = cur_left

    return fc.EyeSpec("angry", cx, cy, curve_a=ca, curve_t=cur_top, curve_b=cb, curve_u=cur_bot,
                      thickness=thick, color=color)


def _morph_heart(e0: fc.EyeSpec, e1: fc.EyeSpec, u: float) -> fc.EyeSpec:
    """Expressive scale morph for Heart eyes (Love)."""
    cx = lerp(e0.cx, e1.cx, u)
    cy = lerp(e0.cy, e1.cy, u)
    thick = lerp(getattr(e0, "thickness", cfg.EYE_THICK), getattr(e1, "thickness", cfg.EYE_THICK), u)
    color = e1.color if u >= 0.5 else e0.color

    if e0.shape == "heart" and e1.shape == "heart":
        hs = lerp(e0.heart_scale, e1.heart_scale, u)
        return fc.EyeSpec("heart", cx, cy, heart_scale=hs, thickness=thick, color=color)

    if e1.shape == "heart":
        if u < 0.45:
            scale = 1.0 - (u / 0.45) * 0.4
            if e0.shape == "circle":
                return fc.EyeSpec("circle", cx, cy, rx=e0.rx * scale, ry=e0.ry * scale,
                                  lid=getattr(e0, "lid", 0.0) or 0.0, thickness=thick, color=color)
            elif e0.shape == "arc":
                return fc.EyeSpec("arc", cx, cy, r=e0.r * scale, a0=e0.a0, a1=e0.a1,
                                  thickness=thick, color=color)
            elif e0.shape == "sleepy_u":
                return fc.EyeSpec("sleepy_u", cx, cy, p0=e0.p0, p1=e0.p1, p2=e0.p2,
                                  thickness=thick * scale, color=color)
            else:
                return e0
        else:
            phase_u = (u - 0.45) / 0.55
            scale = 0.60 + 0.40 * smootherstep(phase_u)
            hs = e1.heart_scale * scale
            return fc.EyeSpec("heart", cx, cy, heart_scale=hs, thickness=thick, color=color)
    else:
        if u < 0.45:
            phase_u = u / 0.45
            scale = 1.0 - phase_u * 0.40
            hs = e0.heart_scale * scale
            return fc.EyeSpec("heart", cx, cy, heart_scale=hs, thickness=thick, color=color)
        else:
            phase_u = (u - 0.45) / 0.55
            scale = 0.60 + 0.40 * smootherstep(phase_u)
            if e1.shape == "circle":
                return fc.EyeSpec("circle", cx, cy, rx=e1.rx * scale, ry=e1.ry * scale,
                                  lid=getattr(e1, "lid", 0.0) or 0.0, thickness=thick, color=color)
            elif e1.shape == "arc":
                return fc.EyeSpec("arc", cx, cy, r=e1.r * scale, a0=e1.a0, a1=e1.a1,
                                  thickness=thick, color=color)
            elif e1.shape == "sleepy_u":
                return fc.EyeSpec("sleepy_u", cx, cy, p0=e1.p0, p1=e1.p1, p2=e1.p2,
                                  thickness=thick * scale, color=color)
            else:
                return e1


def interpolate_eye(e0: fc.EyeSpec, e1: fc.EyeSpec, u: float, side: str = "left") -> fc.EyeSpec:
    """Smoothly interpolate one eye from state e0 to state e1 at transition progress u (0..1)."""
    if u <= 0.0:
        return e0
    if u >= 1.0:
        return e1

    fam0 = get_eye_family(e0)
    fam1 = get_eye_family(e1)

    # 1. Circle <-> Circle
    if fam0 == "circle" and fam1 == "circle":
        return _morph_circle_to_circle(e0, e1, u)

    # 2. Arc <-> Arc
    if fam0 == "arc" and fam1 == "arc":
        return _morph_arc_to_arc(e0, e1, u, side=side)

    # 3. Circle <-> Arc
    if fam0 == "circle" and fam1 == "arc":
        return _morph_circle_to_arc(e0, e1, u, side=side)
    if fam0 == "arc" and fam1 == "circle":
        return _morph_circle_to_arc(e1, e0, 1.0 - u, side=side)

    # 4. Circle <-> Sleepy U
    if fam0 == "circle" and fam1 == "sleepy_u":
        return _morph_circle_to_sleepy(e0, e1, u, side=side)
    if fam0 == "sleepy_u" and fam1 == "circle":
        return _morph_circle_to_sleepy(e1, e0, 1.0 - u, side=side)

    # 5. Arc <-> Sleepy U
    if fam0 == "arc" and fam1 == "sleepy_u":
        return _morph_arc_to_sleepy(e0, e1, u, side=side)
    if fam0 == "sleepy_u" and fam1 == "arc":
        return _morph_arc_to_sleepy(e1, e0, 1.0 - u, side=side)

    # 6. Sleepy U <-> Sleepy U
    if fam0 == "sleepy_u" and fam1 == "sleepy_u":
        l0, r0, _, _, p1_0, _ = get_canonical_eye_anchors(e0, side)
        l1, r1, _, _, p1_1, _ = get_canonical_eye_anchors(e1, side)
        p0 = lerp_pt(l0, l1, u)
        p1 = lerp_pt(p1_0, p1_1, u)
        p2 = lerp_pt(r0, r1, u)
        thick = lerp(getattr(e0, "thickness", cfg.EYE_THICK), getattr(e1, "thickness", cfg.EYE_THICK), u)
        return fc.EyeSpec("sleepy_u", lerp(e0.cx, e1.cx, u), lerp(e0.cy, e1.cy, u),
                          p0=p0, p1=p1, p2=p2, thickness=thick, color=e1.color if u >= 0.5 else e0.color)

    # 7. Angry <-> Any
    if fam0 == "angry" or fam1 == "angry":
        return _morph_angry(e0, e1, u, side=side)

    # 8. Heart <-> Any
    if fam0 == "heart" or fam1 == "heart":
        return _morph_heart(e0, e1, u)

    # Fallback
    return e1 if u >= 0.5 else e0


# ---------------------------------------------------------------------------
# Shape-Family-Aware Mouth Morphing
# ---------------------------------------------------------------------------

def _get_mouth_h(m: fc.MouthSpec) -> float:
    """Return signed effective curvature for stroke mouths (+ for smile, - for frown)."""
    if m.shape == "smile":
        return getattr(m, "h", 0.0)
    if m.shape == "frown":
        return -getattr(m, "h", 0.0)
    return 0.0


def interpolate_mouth(m0: fc.MouthSpec, m1: fc.MouthSpec, u: float) -> fc.MouthSpec:
    """Smoothly interpolate mouth from m0 to m1 at transition progress u (0..1)."""
    if u <= 0.0:
        return m0
    if u >= 1.0:
        return m1

    cx = lerp(m0.cx, m1.cx, u)
    cy = lerp(m0.cy, m1.cy, u)
    w = lerp(m0.w, m1.w, u)
    thick = lerp(getattr(m0, "thickness", cfg.MOUTH_THICK), getattr(m1, "thickness", cfg.MOUTH_THICK), u)
    color = m1.color if u >= 0.5 else m0.color

    stroke_shapes = ("capsule", "line", "smile", "frown")

    # 1. Stroke curve mouths: capsule, smile, frown
    if m0.shape in stroke_shapes and m1.shape in stroke_shapes:
        h0 = _get_mouth_h(m0)
        h1 = _get_mouth_h(m1)
        h_eff = lerp(h0, h1, u)
        if h_eff > 0.002:
            return fc.MouthSpec("smile", cx, cy, w, h=h_eff, thickness=thick, color=color)
        elif h_eff < -0.002:
            return fc.MouthSpec("frown", cx, cy, w, h=-h_eff, thickness=thick, color=color)
        else:
            return fc.MouthSpec("capsule", cx, cy, w, thickness=thick, color=color)

    # 2. Open mouth (Surprised ellipse) <-> Stroke mouths (Capsule, Smile, Frown)
    if (m0.shape == "open" and m1.shape in stroke_shapes) or (m1.shape == "open" and m0.shape in stroke_shapes):
        h_open = m0.h if m0.shape == "open" else m1.h
        h_stroke = _get_mouth_h(m0) if m0.shape in stroke_shapes else _get_mouth_h(m1)

        u_open = (1.0 - u) if m0.shape == "open" else u
        current_h = lerp(thick, h_open, u_open)
        if u_open > 0.10:
            return fc.MouthSpec("open", cx, cy, w, h=current_h, thickness=thick, color=color)
        else:
            if abs(h_stroke) > 0.002:
                shape = "smile" if h_stroke > 0 else "frown"
                return fc.MouthSpec(shape, cx, cy, w, h=abs(h_stroke), thickness=thick, color=color)
            return fc.MouthSpec("capsule", cx, cy, w, thickness=thick, color=color)

    # 3. Open smile bowl (Excited) <-> Smile / Capsule
    if (m0.shape == "open_smile" and m1.shape in stroke_shapes) or (m1.shape == "open_smile" and m0.shape in stroke_shapes):
        h_bowl = m0.h if m0.shape == "open_smile" else m1.h
        u_open = (1.0 - u) if m0.shape == "open_smile" else u
        current_h = lerp(0.001, h_bowl, u_open)
        if u_open > 0.15:
            return fc.MouthSpec("open_smile", cx, cy, w, h=current_h, thickness=thick, color=color)
        else:
            h_s = _get_mouth_h(m1 if m0.shape == "open_smile" else m0)
            shape = "smile" if h_s > 0.002 else ("frown" if h_s < -0.002 else "capsule")
            return fc.MouthSpec(shape, cx, cy, w, h=abs(h_s), thickness=thick, color=color)

    # 4. Wavy / Curl mouths (Confused / Disgusted) <-> Stroke mouths
    if m0.shape in ("wavy", "curl") or m1.shape in ("wavy", "curl"):
        amp0 = getattr(m0, "amp", 0.0) or 0.0
        amp1 = getattr(m1, "amp", 0.0) or 0.0
        waves0 = getattr(m0, "waves", 1.0) or 1.0
        waves1 = getattr(m1, "waves", 1.0) or 1.0
        phase0 = getattr(m0, "phase", 0.0) or 0.0
        phase1 = getattr(m1, "phase", 0.0) or 0.0

        amp = lerp(amp0, amp1, u)
        waves = lerp(waves0, waves1, u)
        phase = lerp(phase0, phase1, u)

        if abs(amp) > 0.003:
            return fc.MouthSpec("wavy", cx, cy, w, amp=amp, waves=waves, phase=phase,
                                thickness=thick, color=color)
        else:
            h_eff = lerp(_get_mouth_h(m0), _get_mouth_h(m1), u)
            shape = "smile" if h_eff > 0.002 else ("frown" if h_eff < -0.002 else "capsule")
            return fc.MouthSpec(shape, cx, cy, w, h=abs(h_eff), thickness=thick, color=color)

    # 5. Open (Surprised) <-> Open Smile (Excited)
    if (m0.shape == "open" and m1.shape == "open_smile") or (m0.shape == "open_smile" and m1.shape == "open"):
        h_val = lerp(m0.h, m1.h, u)
        shape = "open_smile" if u >= 0.5 else "open"
        return fc.MouthSpec(shape, cx, cy, w, h=h_val, thickness=thick, color=color)

    # Fallback
    return m1 if u >= 0.5 else m0


# ---------------------------------------------------------------------------
# Overlay Interpolation
# ---------------------------------------------------------------------------

def interpolate_overlays(ovs0, ovs1, u: float):
    """Interpolate overlay cues ('?' and 'ZZZ') smoothly across transitions."""
    if u <= 0.0:
        return ovs0
    if u >= 1.0:
        return ovs1

    res = []

    # Thinking '?'
    q0 = [o for o in ovs0 if o.kind == "question"]
    q1 = [o for o in ovs1 if o.kind == "question"]
    if q0 and q1:
        o0, o1 = q0[0], q1[0]
        cx = lerp(o0.cx, o1.cx, u)
        cy = lerp(o0.cy, o1.cy, u)
        sz = lerp(o0.size_norm, o1.size_norm, u)
        al = int(lerp(o0.alpha, o1.alpha, u))
        rad = lerp(o0.radius_norm, o1.radius_norm, u)
        res.append(ov.OverlaySpec("question", "?", cx, cy, sz, al, cfg.FACE_COLOR, rad))
    else:
        for o in q0:
            al = int(o.alpha * (1.0 - u))
            if al > 5:
                res.append(ov.OverlaySpec(o.kind, o.text, o.cx, o.cy, o.size_norm,
                                          al, o.color, o.radius_norm))
        for o in q1:
            al = int(o.alpha * u)
            if al > 5:
                res.append(ov.OverlaySpec(o.kind, o.text, o.cx, o.cy, o.size_norm,
                                          al, o.color, o.radius_norm))

    # Sleepy 'ZZZ'
    z0 = [o for o in ovs0 if o.kind == "z"]
    z1 = [o for o in ovs1 if o.kind == "z"]
    if z0 and z1:
        for i in range(max(len(z0), len(z1))):
            o0 = z0[i] if i < len(z0) else z1[i]
            o1 = z1[i] if i < len(z1) else z0[i]
            cx = lerp(o0.cx, o1.cx, u)
            cy = lerp(o0.cy, o1.cy, u)
            sz = lerp(o0.size_norm, o1.size_norm, u)
            al = int(lerp(o0.alpha, o1.alpha, u))
            rad = lerp(o0.radius_norm, o1.radius_norm, u)
            res.append(ov.OverlaySpec("z", "Z", cx, cy, sz, al, cfg.FACE_COLOR, rad))
    else:
        for o in z0:
            al = int(o.alpha * (1.0 - u))
            if al > 5:
                res.append(ov.OverlaySpec(o.kind, o.text, o.cx, o.cy, o.size_norm,
                                          al, o.color, o.radius_norm))
        for o in z1:
            z_factor = max(0.0, (u - 0.25) / 0.75)
            al = int(o.alpha * (z_factor * z_factor))
            if al > 5:
                res.append(ov.OverlaySpec(o.kind, o.text, o.cx, o.cy, o.size_norm,
                                          al, o.color, o.radius_norm))

    return res


# ---------------------------------------------------------------------------
# Coordinated Face Interpolation
# ---------------------------------------------------------------------------

def interpolate_face(spec0: fc.FaceSpec, spec1: fc.FaceSpec, u: float) -> fc.FaceSpec:
    """Build an interpolated FaceSpec between spec0 and spec1 at progress u (0..1).

    Applies coordinated canonical morphing with semantic left/right eye orientation.
    """
    if u <= 0.0:
        return spec0
    if u >= 1.0:
        return spec1

    u_eyes = u
    u_mouth = u

    emotion_label = spec1.emotion if u >= 0.5 else spec0.emotion

    # Interpolate eyes (pass side="left" and side="right" for canonical mirroring)
    eyes = []
    n_eyes = max(len(spec0.eyes), len(spec1.eyes))
    for i in range(n_eyes):
        side = "left" if i == 0 else "right"
        e0 = spec0.eyes[i] if i < len(spec0.eyes) else spec1.eyes[i]
        e1 = spec1.eyes[i] if i < len(spec1.eyes) else spec0.eyes[i]
        eyes.append(interpolate_eye(e0, e1, u_eyes, side=side))

    # Interpolate mouth
    mouth = interpolate_mouth(spec0.mouth, spec1.mouth, u_mouth)

    # Interpolate overlays
    overlays = interpolate_overlays(spec0.overlays, spec1.overlays, u)

    return fc.FaceSpec(emotion_label, eyes, mouth, overlays)


# ---------------------------------------------------------------------------
# Transition Controller
# ---------------------------------------------------------------------------

class TransitionController:
    """Manages live emotion transitions with interruption support."""

    def __init__(self, initial_emotion: str = "neutral", duration: float = None):
        self.current_emotion = initial_emotion
        self.target_emotion = None
        self.is_active = False
        self.progress = 1.0
        self.elapsed = 0.0
        self.duration = duration or getattr(cfg, "TRANSITION_DURATION", 0.55)
        self.target_t = 0.0

        # Current and start specs
        self.current_spec = fc.build_face(self.current_emotion, 0.0)
        self.start_spec = copy.deepcopy(self.current_spec)

    def request_emotion(self, new_emotion: str, duration: float = None, reset_time: bool = True):
        """Request a transition to new_emotion.

        If a transition is already in progress, interrupts seamlessly from the
        current interpolated pose as the new start state.
        """
        if new_emotion not in em.EMOTION_ORDER:
            raise ValueError(f"Unknown emotion: {new_emotion}")

        if not self.is_active and new_emotion == self.current_emotion:
            if reset_time:
                self.target_t = 0.0
            return

        # Interruption: capture current interpolated pose as start
        self.start_spec = copy.deepcopy(self.current_spec)
        self.target_emotion = new_emotion
        self.duration = duration or getattr(cfg, "TRANSITION_DURATION", 0.55)
        self.elapsed = 0.0
        self.progress = 0.0
        self.is_active = True
        if reset_time:
            self.target_t = 0.0

    def update(self, dt: float) -> fc.FaceSpec:
        """Advance time by dt seconds and return the current FaceSpec."""
        if self.is_active:
            self.elapsed += dt
            self.target_t += dt
            raw_u = min(1.0, self.elapsed / max(0.0001, self.duration))
            self.progress = raw_u
            eased_u = smootherstep(raw_u)

            target_spec = fc.build_face(self.target_emotion, self.target_t)
            self.current_spec = interpolate_face(self.start_spec, target_spec, eased_u)

            if raw_u >= 1.0:
                self.is_active = False
                self.current_emotion = self.target_emotion
                self.target_emotion = None
                self.progress = 1.0
                self.current_spec = target_spec
        else:
            self.target_t += dt
            self.current_spec = fc.build_face(self.current_emotion, self.target_t)

        return self.current_spec

    def get_current_spec(self) -> fc.FaceSpec:
        return self.current_spec

    def is_transitioning(self) -> bool:
        return self.is_active

    def get_progress(self) -> float:
        return self.progress

    def get_status(self) -> dict:
        """Return diagnostic dictionary for HUD display."""
        return {
            "current": self.current_emotion,
            "target": self.target_emotion,
            "is_transitioning": self.is_active,
            "progress": self.progress,
            "elapsed": self.elapsed,
            "duration": self.duration,
            "time": self.target_t,
        }

    def reset(self, emotion: str = "neutral"):
        self.current_emotion = emotion
        self.target_emotion = None
        self.is_active = False
        self.progress = 1.0
        self.elapsed = 0.0
        self.target_t = 0.0
        self.current_spec = fc.build_face(emotion, 0.0)
        self.start_spec = copy.deepcopy(self.current_spec)
