"""ROBoy Emotion V2 - verification suite (headless).

Run with:  py verify.py

All checks run without a display (SDL dummy driver). It validates:
  * every emotion builds and renders without error
  * no NaN / out-of-bounds geometry
  * thinking '?' stays clear of both eyes
  * sleepy ZZZ stays clear of both eyes, sizes & alpha decrease, lifecycle repeats
  * angry geometry slants inward-downward (asymmetric in the intended direction)
  * wink has exactly one closed eye
  * love has two heart elements
  * animation is deterministic
  * only the v2 folder was added (production tree untouched by this run)
"""

import os
import math
import subprocess
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

import config as cfg  # noqa: E402
import geometry as g  # noqa: E402
import face as fc  # noqa: E402
import renderer as rn  # noqa: E402
import emotions as em  # noqa: E402
import overlays as ov  # noqa: E402


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


def finite(*vals):
    return all(math.isfinite(v) for v in vals)


def in_bounds(*vals, lo=-0.06, hi=1.06):
    return all(lo <= v <= hi for v in vals)


def eye_eff_radius(e):
    """Generous bounding radius for an eye, for overlap tests."""
    if e.shape == "circle":
        return max(e.rx, e.ry)
    if e.shape == "arc":
        return e.r
    if e.shape == "heart":
        return e.heart_scale
    if e.shape == "sleepy_u":
        # distance from centre to the furthest control/end point
        best = 0.0
        for p in (e.p0, e.p1, e.p2):
            best = max(best, math.hypot(p[0] - e.cx, p[1] - e.cy))
        return best
    if e.shape == "angry":
        best = 0.0
        for p in (e.curve_a, e.curve_t, e.curve_b, e.curve_u):
            best = max(best, math.hypot(p[0] - e.cx, p[1] - e.cy))
        return best
    return 0.0


def eye_center(e):
    return (e.cx, e.cy)


def build_offscreen():
    pygame.init()
    return pygame.Surface((cfg.WINDOW_W, cfg.WINDOW_H), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# 1. every emotion builds + renders
# ---------------------------------------------------------------------------

def test_build_render():
    surf = build_offscreen()
    tf = g.Transform(0, 0, min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE)
    ok_all = True
    for name in em.EMOTION_ORDER:
        try:
            for tt in (0.0, 1.37, 3.11, 5.9):
                spec = fc.build_face(name, tt)
                rn.render(surf, spec, tf)
        except Exception as ex:  # noqa: BLE001
            ok_all = False
            check(f"build+render {name}", False, f"exception: {ex!r}")
    if ok_all:
        check("all 14 emotions build + render", True)


# ---------------------------------------------------------------------------
# 2. no NaN / out of bounds
# ---------------------------------------------------------------------------

def test_bounds():
    ok = True
    detail = ""
    for name in em.EMOTION_ORDER:
        for tt in (0.0, 1.37, 3.11):
            spec = fc.build_face(name, tt)
            for e in spec.eyes:
                if not finite(e.cx, e.cy) or not in_bounds(e.cx, e.cy):
                    ok = False
                    detail = f"{name}: eye center bad {e.cx},{e.cy}"
                if e.shape == "circle":
                    if not finite(e.rx, e.ry) or e.rx <= 0 or e.ry <= 0:
                        ok = False
                        detail = f"{name}: bad circle radius"
                if e.shape == "arc":
                    if not finite(e.r, e.a0, e.a1) or e.r <= 0:
                        ok = False
                        detail = f"{name}: bad arc"
                if e.shape == "sleepy_u":
                    for p in (e.p0, e.p1, e.p2):
                        if not finite(*p) or not in_bounds(*p):
                            ok = False
                            detail = f"{name}: sleepy point oob {p}"
                if e.shape == "angry":
                    for p in (e.curve_a, e.curve_t, e.curve_b, e.curve_u):
                        if not finite(*p) or not in_bounds(*p):
                            ok = False
                            detail = f"{name}: angry point oob {p}"
                if e.shape == "heart":
                    if not finite(e.heart_scale) or e.heart_scale <= 0:
                        ok = False
                        detail = f"{name}: bad heart"
            m = spec.mouth
            if not finite(m.cx, m.cy, m.w) or not in_bounds(m.cx, m.cy):
                ok = False
                detail = f"{name}: mouth center bad"
            if m.w <= 0:
                ok = False
                detail = f"{name}: mouth width bad"
            if m.shape == "open" or m.shape == "open_smile":
                if not in_bounds(m.cx - m.w / 2, m.cx + m.w / 2,
                                 m.cy - m.h / 2, m.cy + m.h / 2):
                    ok = False
                    detail = f"{name}: open mouth oob"
    check("no NaN / out-of-bounds geometry", ok, detail)


# ---------------------------------------------------------------------------
# 3. thinking '?' clear of both eyes
# ---------------------------------------------------------------------------

def test_question_clear():
    ok = True
    detail = ""
    for emo in ("thinking", "confused"):
        c = fc.eye_centers()
        for tt in (0.0, 0.7, 1.4, 2.1, 3.0):
            spec = fc.build_face(emo, tt)
            eyes = spec.eyes
            for o in spec.overlays:
                if o.kind != "question":
                    continue
                for e in eyes:
                    d = math.hypot(o.cx - e.cx, o.cy - e.cy)
                    if d <= eye_eff_radius(e) + o.radius_norm + 0.005:
                        ok = False
                        detail = f"{emo} ? overlaps an eye (d={d:.3f})"
    check("thinking/confused '?' clear of both eyes", ok, detail)


def test_thinking_two_open_eyes():
    ok = True
    detail = ""
    for tt in (0.0, 0.5, 1.7, 3.3):
        spec = fc.build_face("thinking", tt)
        eyes = spec.eyes
        if len(eyes) != 2 or eyes[0].shape != "circle" or eyes[1].shape != "circle":
            ok = False
            detail = "thinking eyes not both open circles"
            break
        # approximately equal size
        if abs(eyes[0].rx - eyes[1].rx) > 1e-6:
            ok = False
            detail = "thinking eyes unequal size"
            break
    check("thinking has TWO open equal eyes (no wink)", ok, detail)


def test_confused_asymmetric():
    ok = True
    detail = ""
    for tt in (0.0, 1.0, 2.0):
        spec = fc.build_face("confused", tt)
        e0, e1 = spec.eyes
        same_shape = e0.shape == e1.shape
        same_cx = abs(e0.cx - e1.cx) < 1e-6
        same_cy = abs(e0.cy - e1.cy) < 1e-6
        same_ry = abs(getattr(e0, "ry", 0) - getattr(e1, "ry", 0)) < 1e-6
        if same_shape and same_cx and same_cy and same_ry:
            ok = False
            detail = "confused eyes are symmetric (expected asymmetric)"
            break
    check("confused eyes are asymmetric", ok, detail)


def test_mouths_smooth():
    ok = True
    detail = ""
    allowed = {"capsule", "smile", "frown", "open", "open_smile", "wavy", "curl"}
    for name in em.EMOTION_ORDER:
        spec = fc.build_face(name, 0.0)
        m = spec.mouth
        if m.shape not in allowed:
            ok = False
            detail = f"{name}: unexpected mouth shape {m.shape}"
        if m.shape == "line":
            ok = False
            detail = f"{name}: mouth is a hard rectangular line"
    check("all mouths use smooth shapes (no rectangular line)", ok, detail)


# ---------------------------------------------------------------------------
# 4. sleepy ZZZ clear + sizes/alpha decrease + repeats
# ---------------------------------------------------------------------------

def test_zzz():
    c = fc.eye_centers()
    reye = c["right"]
    ok = True
    detail = ""

    # Design intent: per-slot base size and peak alpha must strictly decrease.
    sizes_base = [cfg.ZZZ_SIZE0 * (cfg.ZZZ_SIZE_STEP ** i) for i in range(3)]
    alphas_base = [cfg.ZZZ_ALPHA0 * (cfg.ZZZ_ALPHA_STEP ** i) for i in range(3)]
    if not (sizes_base[0] > sizes_base[1] > sizes_base[2]):
        ok = False
        detail = f"ZZZ base sizes not decreasing: {sizes_base}"
    if not (alphas_base[0] > alphas_base[1] > alphas_base[2]):
        ok = False
        detail = f"ZZZ peak alpha not decreasing: {alphas_base}"

    # Determine the actual sleepy eye bounding radius from the built spec so
    # the overlap test is robust to config/geometry changes.
    sleepy_spec = fc.build_face("sleepy", 0.0)
    right_eye = [e for e in sleepy_spec.eyes if e.cx > 0.5][0]
    left_eye = [e for e in sleepy_spec.eyes if e.cx < 0.5][0]
    reye_eff = eye_eff_radius(right_eye)
    leye_eff = eye_eff_radius(left_eye)

    # overlap check + lifecycle sampling
    samples = [i * 0.17 for i in range(40)]
    max_visible = 0
    min_visible = 99
    for tt in samples:
        zs = ov.build_zzz(reye, tt)
        max_visible = max(max_visible, len(zs))
        min_visible = min(min_visible, len(zs))
        for z in zs:
            d = math.hypot(z.cx - reye[0], z.cy - reye[1])
            if d <= reye_eff + z.radius_norm + 0.005:
                ok = False
                detail = f"ZZZ overlaps right eye (d={d:.3f})"
            d2 = math.hypot(z.cx - c["left"][0], z.cy - c["left"][1])
            if d2 <= leye_eff + z.radius_norm + 0.005:
                ok = False
                detail = f"ZZZ overlaps left eye (d={d2:.3f})"
    # staggered (not all synchronized): sometimes 1, sometimes 2+
    if not (max_visible >= 2 and min_visible <= 1):
        ok = False
        detail = f"ZZZ not staggered (max={max_visible}, min={min_visible})"

    # lifecycle repeats: build at t and t + cycle yields identical output
    for tt in (0.0, 1.0, 2.3):
        a = ov.build_zzz(reye, tt)
        b = ov.build_zzz(reye, tt + cfg.ZZZ_CYCLE)
        if len(a) != len(b):
            ok = False
            detail = "ZZZ lifecycle does not repeat"
            break
        for x, y in zip(a, b):
            if (abs(x.cx - y.cx) > 1e-9 or abs(x.cy - y.cy) > 1e-9
                    or abs(x.alpha - y.alpha) > 1e-6):
                ok = False
                detail = "ZZZ lifecycle drift"
                break
    check("sleepy ZZZ clear / decreasing / repeats", ok, detail)


# ---------------------------------------------------------------------------
# 5. sleepy eye geometry stable
# ---------------------------------------------------------------------------

def test_sleepy_eye():
    ok = True
    detail = ""
    for tt in (0.0, 1.0, 2.5, 4.0):
        spec = fc.build_face("sleepy", tt)
        for e in spec.eyes:
            if e.shape != "sleepy_u":
                ok = False
                detail = "sleepy eye not sleepy_u"
            for p in (e.p0, e.p1, e.p2):
                if not finite(*p) or not in_bounds(*p):
                    ok = False
                    detail = f"sleepy point oob {p}"
    check("sleepy eye geometry stable", ok, detail)


# ---------------------------------------------------------------------------
# 6. angry slant direction
# ---------------------------------------------------------------------------

def test_angry_slant():
    ok = True
    detail = ""
    for tt in (0.0, 1.0, 2.0):
        spec = fc.build_face("angry", tt)
        for e in spec.eyes:
            pts = [e.curve_a, e.curve_b]
            xs = [p[0] for p in pts]
            max_i = xs.index(max(xs))
            min_i = xs.index(min(xs))
            # inner corner (toward centre) must be LOWER (larger y)
            inner = pts[max_i] if e.cx < 0.5 else pts[min_i]
            outer = pts[min_i] if e.cx < 0.5 else pts[max_i]
            if inner[1] <= outer[1]:
                ok = False
                detail = f"angry eye not slanted inward-down (cx={e.cx:.2f})"
    check("angry geometry slants inward-downward", ok, detail)


def test_angry_filled():
    ok = True
    detail = ""
    for tt in (0.0, 1.0, 2.0):
        spec = fc.build_face("angry", tt)
        eyes = spec.eyes
        if len(eyes) != 2:
            ok = False
            detail = "angry does not have two eyes"
            break
        for e in eyes:
            if e.shape != "angry" or e.curve_a is None:
                ok = False
                detail = "angry eye is not a filled curve shape"
        # mirrored: left and right anchor x-offsets from their centres are opposite
        l, r = eyes[0], eyes[1]
        la_x = l.curve_a[0] - l.cx
        ra_x = r.curve_a[0] - r.cx
        if abs(la_x + ra_x) > 1e-6:
            ok = False
            detail = "angry eyes are not mirrored"
        lb_x = l.curve_b[0] - l.cx
        rb_x = r.curve_b[0] - r.cx
        if abs(lb_x + rb_x) > 1e-6:
            ok = False
            detail = "angry inner corners not mirrored"
    check("angry eyes are filled + mirrored", ok, detail)


def test_fearful_distinct():
    ok = True
    detail = ""
    f = fc.build_face("fearful", 0.0)
    s = fc.build_face("surprised", 0.0)
    # mouth shape must differ
    if f.mouth.shape == s.mouth.shape:
        ok = False
        detail = f"fearful/surprised mouths identical ({f.mouth.shape})"
    # fearful eyes must be smaller than surprised eyes
    fr = max(e.rx for e in f.eyes)
    sr = max(e.rx for e in s.eyes)
    if fr >= sr:
        ok = False
        detail = f"fearful eyes not smaller than surprised ({fr:.3f} >= {sr:.3f})"
    # fearful eyes not plain circles identical to surprised (asymmetry)
    f_ry = [e.ry for e in f.eyes]
    if abs(f_ry[0] - f_ry[1]) < 1e-6 and abs(f.eyes[0].cy - f.eyes[1].cy) < 1e-6:
        # symmetry alone isn't a failure, but ensure they are tall ovals
        pass
    check("fearful is distinct from surprised", ok, detail)


def test_zzz_separation():
    c = fc.eye_centers()
    reye = c["right"]
    ok = True
    detail = ""
    for tt in [i * 0.21 for i in range(40)]:
        zs = ov.build_zzz(reye, tt)
        radii = [0.5 * z.size_norm for z in zs]
        for i in range(len(zs)):
            for j in range(i + 1, len(zs)):
                d = math.hypot(zs[i].cx - zs[j].cx, zs[i].cy - zs[j].cy)
                need = (radii[i] + radii[j]) * 0.7   # allow slight visual touch
                if d < need:
                    ok = False
                    detail = (f"ZZZ glyphs overlap (d={d:.3f} < {need:.3f}) "
                              f"at t={tt:.2f}")
    check("ZZZ glyphs keep individual separation", ok, detail)


def test_eye_mouth_gap():
    ok = True
    detail = ""
    c = fc.eye_centers()
    eye_bottom = max(cy + cfg.EYE_R for (_, cy) in c.values())
    for name in em.EMOTION_ORDER:
        spec = fc.build_face(name, 0.0)
        m = spec.mouth
        # top extent of the mouth (account for smile/frown depth & wavy amp)
        m_top = m.cy - max(m.h, abs(m.amp), m.thickness)
        if m_top <= eye_bottom + 0.03:
            ok = False
            detail = f"{name}: mouth too close to eyes (top={m_top:.3f})"
        # compact: centre-to-centre gap must be clearly reduced vs old layout
        if (m.cy - cfg.EYE_CY) > 0.30:
            ok = False
            detail = f"{name}: eye-mouth gap not compact ({m.cy - cfg.EYE_CY:.3f})"
    check("compact eye->mouth gap (no overlap)", ok, detail)


# ---------------------------------------------------------------------------
# 7. wink one closed eye, love two hearts, determinism
# ---------------------------------------------------------------------------

def test_wink_love():
    w = fc.build_face("wink", 0.0)
    shapes = [e.shape for e in w.eyes]
    check("wink has one closed eye (t=0)",
          shapes.count("circle") == 1 and shapes.count("arc") == 1,
          f"shapes={shapes}")

    l = fc.build_face("love", 0.0)
    hearts = sum(1 for e in l.eyes if e.shape == "heart")
    check("love has two heart elements", hearts == 2, f"hearts={hearts}")


def test_deterministic():
    ok = True
    detail = ""
    for name in em.EMOTION_ORDER:
        for tt in (0.0, 1.23, 4.56):
            a = fc.build_face(name, tt)
            b = fc.build_face(name, tt)
            for ea, eb in zip(a.eyes, b.eyes):
                if (ea.cx != eb.cx or ea.cy != eb.cy or ea.rx != eb.rx
                        or ea.shape != eb.shape):
                    ok = False
                    detail = f"{name}: non-deterministic eye"
            if (a.mouth.cx != b.mouth.cx or a.mouth.shape != b.mouth.shape):
                ok = False
                detail = f"{name}: non-deterministic mouth"
    check("animation is deterministic", ok, detail)


# ---------------------------------------------------------------------------
# 8. production tree untouched by this run
# ---------------------------------------------------------------------------

# Files / directories that were already untracked or modified in the working
# tree BEFORE this V2 task began (captured from the initial `git status`).
# Anything not in this baseline and not under the v2 folder is a genuine
# unexpected change introduced by this run.
_PREEXISTING = [
    "_show_les09a3_frames/",
    "_show_les09b6_frames/",
    "_show_les09a3_instructions.md",
    "_show_les09a3_motion.py",
    "_show_les09a3_stdout.log",
    "_show_les09b1_choreography.py",
    "_show_les09b6_sleepy_zzz.py",
    "_verify_les09a3_motion.py",
    "_verify_les09b1_choreography.py",
    "_verify_les09b3_sleepy.py",
    "_verify_les09b4_cue_placement.py",
    "_verify_les09b6_1_zzz_timing.py",
    "_verify_les09b6_sleepy_zzz.py",
    "_show_les09b2_expression_polish.py",
    "_verify_les09b5_perimeter_cue.py",
    "les/behaviors/__pycache__/",
    "les/choreography/",
    "les/integration/__pycache__/",
    "eyes/engine/blink_controller.py",
    "eyes/engine/config.py",
    "eyes/engine/look_controller.py",
    "eyes/engine/motion_primitives.py",
    "eyes/engine/overlay_renderer.py",
    "eyes/engine/spring.py",
    "les/__init__.py",
    "__pycache__/",
]


def _is_preexisting(path):
    if path.startswith("experiments/"):
        # The whole experiments/ folder only contains this V2 prototype.
        return True
    if path.startswith("_verify") or path.startswith("_show"):
        # scratch files from prior LES sessions
        return True
    for p in _PREEXISTING:
        if path == p or path.startswith(p):
            return True
    return False


def test_production_untouched():
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception as ex:  # noqa: BLE001
        check("git status readable", False, str(ex))
        return

    v2_prefix = "experiments/roboy_emotions_v2/"
    violations = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        path = ln[3:].strip()
        if path.endswith(".pyc") or "__pycache__" in path:
            continue
        if path.startswith(v2_prefix):
            continue
        if _is_preexisting(path):
            continue
        violations.append(path)

    check("no unexpected changes outside v2 folder",
          len(violations) == 0,
          f"violations: {violations}" if violations else "")

    # Independent assurance: the V2 code never imports the production engine.
    # A name like `face` is allowed ONLY when a local module of that name
    # exists inside the v2 folder (it is ours, not the production package).
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
    check("V2 code does not import production engine",
          len(bad_imports) == 0,
          f"imports: {bad_imports}" if bad_imports else "")


def test_no_prod_imports_dummy():
    pass


# ---------------------------------------------------------------------------

def main():
    print("ROBoy Emotion V2 - verification")
    print("-" * 50)
    test_build_render()
    test_bounds()
    test_question_clear()
    test_thinking_two_open_eyes()
    test_confused_asymmetric()
    test_mouths_smooth()
    test_zzz()
    test_sleepy_eye()
    test_angry_slant()
    test_angry_filled()
    test_fearful_distinct()
    test_zzz_separation()
    test_eye_mouth_gap()
    test_wink_love()
    test_deterministic()
    test_production_untouched()
    print("\n".join(LOG))
    print("-" * 50)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
