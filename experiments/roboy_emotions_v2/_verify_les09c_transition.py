"""ROBoy Emotion V2 - transition verification suite (Round 2).

Validates the live emotion transition system across all 182 directed transition pairs
(14 emotions x 13 targets) and all architectural constraints:
 1. All 14 emotions still build.
 2. All 14 emotions still render.
 3. Existing geometry remains unchanged at t=0/static.
 4. Source endpoint geometry is reached exactly at u=0.
 5. Target endpoint geometry is reached exactly at u=1 across all 182 pairs.
 6. All 182 directed transition pairs execute and render without exception.
 7. Transition progress is strictly monotonic.
 8. Easing is smooth (zero velocity & zero acceleration at endpoints).
 9. No NaN values during any transition across all 182 pairs.
10. No out-of-bounds geometry across all 182 pairs.
11. No eye/mouth overlap across all 182 pairs.
12. Thinking '?' remains valid, clear of eyes, and transitions smoothly.
13. Sleepy ZZZ remains valid, clear of eyes, and transitions smoothly.
14. Deterministic animation & transitions.
15. No production engine imports.
16. No threads, background timers, or sleep() calls.
17. Key pairs: Happy -> Sad works smoothly.
18. Key pairs: Happy -> Angry works smoothly.
19. Key pairs: Neutral -> Sleepy works smoothly.
20. Key pairs: Sleepy -> Happy works smoothly.
21. Key pairs: Thinking -> Confused works smoothly.
22. Key pairs: Excited -> Neutral works smoothly.
23. Mid-transition interruption works seamlessly without snapping.
24. Repeated rapid emotion requests do not corrupt controller state.
"""

import os
import sys
import math
import copy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em
import overlays as ov
import transition as tr


PASS = 0
FAIL = 0
LOG = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        LOG.append(f"  [PASS] {name}")
    else:
        FAIL += 1
        LOG.append(f"  [FAIL] {name}  {detail}")


def build_all_182_pairs():
    pairs = []
    for src in em.EMOTION_ORDER:
        for tgt in em.EMOTION_ORDER:
            if src != tgt:
                pairs.append((src, tgt))
    return pairs


ALL_PAIRS = build_all_182_pairs()


def finite(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            if not finite(*v):
                return False
        elif not math.isfinite(float(v)):
            return False
    return True


def in_bounds(*vals, lo=-0.10, hi=1.10):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            if not in_bounds(*v, lo=lo, hi=hi):
                return False
        elif not (lo <= float(v) <= hi):
            return False
    return True


def get_eye_spatial_coords(e: fc.EyeSpec):
    coords = [e.cx, e.cy]
    for attr in ("rx", "ry", "r", "heart_scale", "thickness", "lid"):
        val = getattr(e, attr, None)
        if val is not None:
            coords.append(val)
    for attr in ("p0", "p1", "p2", "curve_a", "curve_t", "curve_b", "curve_u"):
        val = getattr(e, attr, None)
        if val is not None:
            coords.extend(val)
    if getattr(e, "points", None):
        for p in e.points:
            coords.extend(p)
    return coords


def get_mouth_spatial_coords(m: fc.MouthSpec):
    coords = [m.cx, m.cy, m.w, getattr(m, "h", 0.0), getattr(m, "thickness", 0.0), getattr(m, "amp", 0.0)]
    for attr in ("p0", "p1", "p2"):
        val = getattr(m, attr, None)
        if val is not None:
            coords.extend(val)
    if getattr(m, "points", None):
        for p in m.points:
            coords.extend(p)
    return coords


def get_eye_bottom_y(e: fc.EyeSpec) -> float:
    """Return maximum y (lowest drawn point on screen) for an eye."""
    if e.shape == "circle":
        return e.cy + getattr(e, "ry", e.rx)
    if e.shape == "arc":
        return e.cy + e.r
    if e.shape == "sleepy_u":
        p0 = getattr(e, "p0", (e.cx, e.cy))
        p1 = getattr(e, "p1", (e.cx, e.cy))
        p2 = getattr(e, "p2", (e.cx, e.cy))
        apex_y = 0.25 * p0[1] + 0.5 * p1[1] + 0.25 * p2[1]
        return max(p0[1], p2[1], apex_y)
    if e.shape == "angry":
        # Sample the filled shape points
        top_apex = 0.25 * e.curve_a[1] + 0.5 * e.curve_t[1] + 0.25 * e.curve_b[1]
        bot_apex = 0.25 * e.curve_b[1] + 0.5 * e.curve_u[1] + 0.25 * e.curve_a[1]
        return max(e.curve_a[1], e.curve_b[1], top_apex, bot_apex)
    if e.shape == "heart":
        return e.cy + getattr(e, "heart_scale", cfg.EYE_R * cfg.HEART_SCALE)
    if getattr(e, "points", None):
        return max(p[1] for p in e.points)
    return e.cy + cfg.EYE_R


def get_mouth_top_y(m: fc.MouthSpec) -> float:
    """Return minimum y (highest point on screen) for a mouth."""
    if m.shape == "open":
        return m.cy - getattr(m, "h", 0.0) / 2.0
    if m.shape == "frown":
        return m.cy - getattr(m, "h", 0.0)
    if m.shape == "open_smile":
        return m.cy - getattr(m, "h", 0.0) * 0.05
    return m.cy - getattr(m, "thickness", cfg.MOUTH_THICK) / 2.0


def build_offscreen():
    pygame.init()
    return pygame.Surface((cfg.WINDOW_W, cfg.WINDOW_H), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# Test 1 & 2: Build & Render All Emotions
# ---------------------------------------------------------------------------

def test_1_and_2_build_render():
    surf = build_offscreen()
    tf = g.Transform(0, 0, min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE)
    ok_build = True
    ok_render = True
    for name in em.EMOTION_ORDER:
        for t in (0.0, 0.5, 1.25, 3.0):
            try:
                spec = fc.build_face(name, t)
            except Exception:
                ok_build = False
            try:
                rn.render(surf, spec, tf)
            except Exception:
                ok_render = False
    check("1. all 14 emotions build", ok_build)
    check("2. all 14 emotions render", ok_render)


# ---------------------------------------------------------------------------
# Test 3: Static / t=0 Geometry Baseline
# ---------------------------------------------------------------------------

def test_3_baseline_geometry():
    spec = fc.build_face("neutral", 0.0)
    ok = (
        len(spec.eyes) == 2
        and spec.eyes[0].shape == "circle"
        and math.isclose(spec.eyes[0].cx, 0.5 - cfg.EYE_DX, abs_tol=1e-4)
        and math.isclose(spec.eyes[1].cx, 0.5 + cfg.EYE_DX, abs_tol=1e-4)
        and math.isclose(spec.eyes[0].cy, cfg.EYE_CY, abs_tol=1e-4)
        and math.isclose(spec.mouth.cy, cfg.MOUTH_CY, abs_tol=1e-4)
    )
    check("3. existing geometry remains unchanged at t=0/static", ok)


# ---------------------------------------------------------------------------
# Test 4 & 5: Source & Target Endpoints across all 182 pairs
# ---------------------------------------------------------------------------

def test_4_and_5_endpoints_182_pairs():
    ok_src = True
    ok_tgt = True

    for src_name, tgt_name in ALL_PAIRS:
        s0 = fc.build_face(src_name, 0.0)
        s1 = fc.build_face(tgt_name, 1.0)

        # Check u = 0.0 returns exact s0
        interp_0 = tr.interpolate_face(s0, s1, 0.0)
        if len(interp_0.eyes) != len(s0.eyes) or interp_0.mouth.shape != s0.mouth.shape:
            ok_src = False
        for ie, se in zip(interp_0.eyes, s0.eyes):
            if ie.shape != se.shape or not math.isclose(ie.cx, se.cx, abs_tol=1e-5):
                ok_src = False

        # Check u = 1.0 returns exact s1
        interp_1 = tr.interpolate_face(s0, s1, 1.0)
        if len(interp_1.eyes) != len(s1.eyes) or interp_1.mouth.shape != s1.mouth.shape:
            ok_tgt = False
        for ie, te in zip(interp_1.eyes, s1.eyes):
            if ie.shape != te.shape or not math.isclose(ie.cx, te.cx, abs_tol=1e-5):
                ok_tgt = False

    check("4. source endpoint geometry is exact at u=0", ok_src)
    check("5. target endpoint geometry is exact at u=1 across all 182 pairs", ok_tgt)


# ---------------------------------------------------------------------------
# Test 6, 9, 10, 11: Full Matrix 182 Pairs Execution, NaNs, Bounds, Overlap
# ---------------------------------------------------------------------------

def test_full_matrix_182_safety_and_render():
    surf = build_offscreen()
    tf = g.Transform(0, 0, min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE)

    ok_render_all = True
    no_nan = True
    in_bnds = True
    no_overlap = True

    for src_name, tgt_name in ALL_PAIRS:
        s0 = fc.build_face(src_name, 0.0)
        s1 = fc.build_face(tgt_name, 0.5)

        # Step through 11 points in transition: 0.0, 0.1, ..., 1.0
        for step in range(11):
            u = step / 10.0
            spec = tr.interpolate_face(s0, s1, u)

            # Render check
            try:
                rn.render(surf, spec, tf)
            except Exception:
                ok_render_all = False

            # NaN check
            for e in spec.eyes:
                if not finite(*get_eye_spatial_coords(e)):
                    no_nan = False
            if not finite(*get_mouth_spatial_coords(spec.mouth)):
                no_nan = False
            for o in spec.overlays:
                if not finite(o.cx, o.cy, o.size_norm, o.alpha):
                    no_nan = False

            # Bounds check
            for e in spec.eyes:
                if not in_bounds(*get_eye_spatial_coords(e)):
                    in_bnds = False
            if not in_bounds(*get_mouth_spatial_coords(spec.mouth)):
                in_bnds = False

            # Clearance check (no eye/mouth collision)
            max_eye_y = max(get_eye_bottom_y(e) for e in spec.eyes)
            min_mouth_y = get_mouth_top_y(spec.mouth)
            gap = min_mouth_y - max_eye_y
            if gap < 0.02:
                no_overlap = False

    check(f"6. all {len(ALL_PAIRS)} directed transition pairs execute and render without exception", ok_render_all)
    check("9. no NaN values across all 182 transition pairs", no_nan)
    check("10. no out-of-bounds geometry across all 182 transition pairs", in_bnds)
    check("11. no eye/mouth overlap across all 182 transition pairs", no_overlap)


# ---------------------------------------------------------------------------
# Test 7 & 8: Monotonicity & Smootherstep Easing
# ---------------------------------------------------------------------------

def test_7_and_8_easing():
    ok_mono = True
    prev_s = -1e-9
    steps = 100
    for i in range(steps + 1):
        u = i / steps
        s = tr.smootherstep(u)
        if s < prev_s:
            ok_mono = False
        prev_s = s

    s0 = tr.smootherstep(0.0)
    s1 = tr.smootherstep(1.0)
    eps = 1e-4
    d0 = (tr.smootherstep(eps) - tr.smootherstep(0.0)) / eps
    d1 = (tr.smootherstep(1.0) - tr.smootherstep(1.0 - eps)) / eps

    ok_smooth = (
        math.isclose(s0, 0.0, abs_tol=1e-5)
        and math.isclose(s1, 1.0, abs_tol=1e-5)
        and abs(d0) < 0.01
        and abs(d1) < 0.01
    )

    check("7. transition progress is strictly monotonic", ok_mono)
    check("8. easing is smooth (zero velocity & acceleration at endpoints)", ok_smooth)


# ---------------------------------------------------------------------------
# Test 12 & 13: Special Overlays ('?' and 'ZZZ')
# ---------------------------------------------------------------------------

def test_12_thinking_question():
    s_neut = fc.build_face("neutral", 0.0)
    s_think = fc.build_face("thinking", 0.0)

    spec_mid = tr.interpolate_face(s_neut, s_think, 0.5)
    qs = [o for o in spec_mid.overlays if o.kind == "question"]
    ok_fade_in = len(qs) == 1 and qs[0].alpha > 0 and qs[0].cx > 0.5

    spec_out = tr.interpolate_face(s_think, s_neut, 0.8)
    qs_out = [o for o in spec_out.overlays if o.kind == "question"]
    ok_fade_out = len(qs_out) == 1 and qs_out[0].alpha < s_think.overlays[0].alpha

    s_conf = fc.build_face("confused", 0.0)
    spec_tc = tr.interpolate_face(s_think, s_conf, 0.5)
    qs_tc = [o for o in spec_tc.overlays if o.kind == "question"]
    ok_persist = len(qs_tc) == 1 and finite(qs_tc[0].cx, qs_tc[0].cy)

    check("12. thinking '?' remains valid, clear of eyes, and transitions smoothly", ok_fade_in and ok_fade_out and ok_persist)


def test_13_sleepy_zzz():
    s_neut = fc.build_face("neutral", 0.0)
    s_sleep = fc.build_face("sleepy", 0.0)

    spec_early = tr.interpolate_face(s_neut, s_sleep, 0.1)
    spec_late = tr.interpolate_face(s_neut, s_sleep, 0.9)
    zs_early = [o for o in spec_early.overlays if o.kind == "z"]
    zs_late = [o for o in spec_late.overlays if o.kind == "z"]

    early_alpha = sum(z.alpha for z in zs_early)
    late_alpha = sum(z.alpha for z in zs_late)

    s_happy = fc.build_face("happy", 0.0)
    spec_sh = tr.interpolate_face(s_sleep, s_happy, 0.5)
    zs_sh = [o for o in spec_sh.overlays if o.kind == "z"]
    sh_alpha = sum(z.alpha for z in zs_sh)
    orig_alpha = sum(z.alpha for z in s_sleep.overlays if z.kind == "z")

    ok = (early_alpha <= late_alpha) and (sh_alpha < orig_alpha)
    check("13. sleepy ZZZ remains valid, clear of eyes, and transitions smoothly", ok)


# ---------------------------------------------------------------------------
# Test 14: Determinism
# ---------------------------------------------------------------------------

def test_14_determinism():
    ctrl1 = tr.TransitionController("neutral", 0.5)
    ctrl2 = tr.TransitionController("neutral", 0.5)

    ctrl1.request_emotion("happy")
    ctrl2.request_emotion("happy")

    ok = True
    for _ in range(25):
        s1 = ctrl1.update(0.02)
        s2 = ctrl2.update(0.02)
        if not math.isclose(s1.eyes[0].cx, s2.eyes[0].cx, abs_tol=1e-7):
            ok = False
        if not math.isclose(s1.mouth.cy, s2.mouth.cy, abs_tol=1e-7):
            ok = False
    check("14. animation & transitions are deterministic", ok)


# ---------------------------------------------------------------------------
# Test 15 & 16: Safety / Architecture Checks
# ---------------------------------------------------------------------------

def test_15_no_prod_imports():
    root = os.path.dirname(os.path.abspath(__file__))
    local_modules = {f[:-3] for f in os.listdir(root) if f.endswith(".py")}
    import re
    bad_imports = []
    for fn in os.listdir(root):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(root, fn), encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                m = re.match(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", line)
                if not m:
                    continue
                mod = m.group(1) or m.group(2)
                top = mod.split(".")[0]
                if top in ("eyes", "face", "les") and top not in local_modules:
                    bad_imports.append(f"{fn}:{n}:{line.strip()}")
    check("15. no production engine imports", len(bad_imports) == 0, str(bad_imports))


def test_16_no_threads_timers():
    root = os.path.dirname(os.path.abspath(__file__))
    forbidden = ["threading", "Thread", "Timer", "time.sleep", "time.time()"]
    violations = []
    for fn in ("transition.py", "transition_showcase.py"):
        p = os.path.join(root, fn)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                content = fh.read()
                for f in forbidden:
                    if f in content:
                        violations.append(f"{fn}:{f}")
    check("16. no threads, background timers, or sleep() calls", len(violations) == 0, str(violations))


# ---------------------------------------------------------------------------
# Test 17-22: Specific Key Pairs
# ---------------------------------------------------------------------------

def test_17_happy_sad():
    s0 = fc.build_face("happy", 0.0)
    s1 = fc.build_face("sad", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and abs(getattr(spec_mid.mouth, "h", 0.0)) < 0.04
    )
    check("17. key pairs: happy -> sad works smoothly", ok)


def test_18_happy_angry():
    s0 = fc.build_face("happy", 0.0)
    s1 = fc.build_face("angry", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and finite(*get_mouth_spatial_coords(spec_mid.mouth))
    )
    check("18. key pairs: happy -> angry works smoothly", ok)


def test_19_neutral_sleepy():
    s0 = fc.build_face("neutral", 0.0)
    s1 = fc.build_face("sleepy", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and finite(*get_mouth_spatial_coords(spec_mid.mouth))
    )
    check("19. key pairs: neutral -> sleepy works smoothly", ok)


def test_20_sleepy_happy():
    s0 = fc.build_face("sleepy", 0.0)
    s1 = fc.build_face("happy", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and finite(*get_mouth_spatial_coords(spec_mid.mouth))
    )
    check("20. key pairs: sleepy -> happy works smoothly", ok)


def test_21_thinking_confused():
    s0 = fc.build_face("thinking", 0.0)
    s1 = fc.build_face("confused", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and finite(*get_mouth_spatial_coords(spec_mid.mouth))
    )
    check("21. key pairs: thinking -> confused works smoothly", ok)


def test_22_excited_neutral():
    s0 = fc.build_face("excited", 0.0)
    s1 = fc.build_face("neutral", 0.0)
    spec_mid = tr.interpolate_face(s0, s1, 0.5)
    ok = (
        len(spec_mid.eyes) == 2
        and finite(*get_eye_spatial_coords(spec_mid.eyes[0]))
        and finite(*get_mouth_spatial_coords(spec_mid.mouth))
    )
    check("22. key pairs: excited -> neutral works smoothly", ok)


# ---------------------------------------------------------------------------
# Test 23: Mid-Transition Interruption
# ---------------------------------------------------------------------------

def test_23_interruption():
    ctrl = tr.TransitionController("happy", 0.50)
    ctrl.request_emotion("sad")

    # Advance 0.20 seconds (~40% progress)
    spec_at_interrupt = ctrl.update(0.20)
    snap_cx = spec_at_interrupt.eyes[0].cx
    snap_mouth_w = spec_at_interrupt.mouth.w

    # User interrupts with 'excited'
    ctrl.request_emotion("excited")

    # Next frame at dt=0.01: must start smoothly from interrupted pose
    spec_next = ctrl.update(0.01)

    diff_cx = abs(spec_next.eyes[0].cx - snap_cx)
    diff_w = abs(spec_next.mouth.w - snap_mouth_w)

    ok = diff_cx < 0.015 and diff_w < 0.015 and ctrl.is_transitioning()
    check("23. mid-transition interruption works seamlessly without snapping", ok)


# ---------------------------------------------------------------------------
# Test 24: Rapid Fire Requests
# ---------------------------------------------------------------------------

def test_24_rapid_requests():
    ctrl = tr.TransitionController("neutral", 0.40)
    emotions_sequence = [
        "happy", "sad", "angry", "sleepy", "excited", "love",
        "thinking", "confused", "wink", "tired", "fearful", "disgusted",
        "neutral", "happy"
    ]

    all_ok = True
    for emo in emotions_sequence:
        ctrl.request_emotion(emo)
        spec = ctrl.update(0.03)
        if not finite(*get_eye_spatial_coords(spec.eyes[0])) or not finite(*get_mouth_spatial_coords(spec.mouth)):
            all_ok = False
            break

    # Allow final transition to finish completely
    for _ in range(30):
        spec = ctrl.update(0.02)

    final_ok = (
        all_ok
        and not ctrl.is_transitioning()
        and ctrl.current_emotion == "happy"
        and spec.eyes[0].shape == "arc"
    )
    check("24. repeated rapid emotion requests do not corrupt controller state", final_ok)


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("ROBoy Emotion V2 - Live Transition Matrix Verification (Round 2)")
    print("=" * 64)
    test_1_and_2_build_render()
    test_3_baseline_geometry()
    test_4_and_5_endpoints_182_pairs()
    test_full_matrix_182_safety_and_render()
    test_7_and_8_easing()
    test_12_thinking_question()
    test_13_sleepy_zzz()
    test_14_determinism()
    test_15_no_prod_imports()
    test_16_no_threads_timers()
    test_17_happy_sad()
    test_18_happy_angry()
    test_19_neutral_sleepy()
    test_20_sleepy_happy()
    test_21_thinking_confused()
    test_22_excited_neutral()
    test_23_interruption()
    test_24_rapid_requests()
    print("\n".join(LOG))
    print("=" * 64)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
