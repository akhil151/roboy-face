"""
_verify_les09b5_perimeter_cue.py  --  LES-09B.5 verification suite.
===================================================================

LES-09B.5 changes ONLY the thinking "?" cue's PLACEMENT. The human
approved the existing "?" SIZE (must not change); the rejected look was
the cue floating CENTRED above the face:

        ?
        
    👁       👁

The approved look: the "?" grows from the OUTER PERIMETER/CORNER of an
eye (right eye's outer top corner by default):

        ?
       )
      👁

The placement is derived every frame from the ACTUAL effective eye
geometry through the single LES-09B.4 eye-bound calculation
(``OverlayRenderer.eye_silhouette_region`` - the same AABB that carries
the collision guarantees). The cue sits exactly ``clearance`` beyond the
selected eye's outer-top corner (eye perimeter -> small configurable
clearance -> "?"), follows every gaze/look movement, and can never
overlap either eye silhouette. The sleepy ZZZ cue is completely
untouched (same scale, same face-space band, same spawn behaviour).

The LES-09B.5 mission checklist (11 required points):

  1.  ? scale UNCHANGED (thinking_scale() still = 0.85 * eye_radius;
      the human-approved size).
  2.  ? is NO LONGER centred (anchor is outside the eye-pair span at the
      eye's outer perimeter, not the face midpoint).
  3.  ? is anchored to the selected eye's outer perimeter corner (glyph
      box sits exactly clearance beyond the right eye's outer-top corner
      at every pose).
  4.  ? stays outside the eye (never intersects either silhouette, with
      the exact configured clearance as margin).
  5.  ? follows eye movement (the anchor tracks the composed pose: the
      anchor delta equals the effective-eye delta across gaze targets;
      the anchor uses the composed AABB, not the rest position).
  6.  ? remains safe across representative gaze positions (9 cardinal +
      diagonal extremes x 4 pose variants: stretch / squash-droop /
      rotation, with worst-case micro/bounce offsets).
  7.  ? remains safe during the Thinking choreography (every look_at
      target of 5 seeded plans).
  8.  ZZZ remains UNCHANGED (scale base 16.0 and face-space band exactly
      the LES-09B.4 values; the band stays clear of both eyes).
  9.  LES-09B.4 collision tests remain green (subprocess).
 10.  Existing regressions remain green (subprocess).
 11.  Showcase smoke passes (subprocess).

Plus: config no longer carries the centred model
(``thinking_cue_anchor_x_ratio`` is gone); the left-eye / outer-bottom
corner options stay collision-safe; the real-engine pipeline reaches
thinking and composes through the verified OverlayRenderer.

Geometric information used (no fakes - same as LES-09B.4):

  * Eye silhouette: ``eye_silhouette_region`` mirrors the exact sclera
    math of eyes/engine/renderer.py ``_effective_pos`` (pos + look +
    micro + bounce) and ``_effective_radius`` (radius * scale,
    squash/stretch), inflated by rotation - the same AABB that draws the
    white sclera.
  * Cue extents: ``thinking_cue_region`` uses the exact glyph geometry of
    ``_draw_vector_question`` PLUS its stroke (half-width 0.42*scale,
    top 0.62*scale, bottom 0.61*scale) - deliberately CONSERVATIVE boxes.
  * Placement: anchor = (outer_edge +/- (clearance + 0.42*scale),
    top - clearance - 0.61*scale) for outer_top, so the glyph box's
    nearest corner sits exactly one clearance beyond the eye corner.
  * Gaze mapping: normalized look_at (nx, ny) -> pixel offsets
    (nx-0.5)*2*look_max_offset, from LookController.get_offsets().

Run:  py _verify_les09b5_perimeter_cue.py
"""

from __future__ import annotations

import dataclasses
import os
import random
import subprocess
import sys
from typing import List, Optional, Tuple

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from eyes.engine.config import EngineConfig, OverlayConfig  # noqa: E402
from eyes.engine.eye_pair import EyePair  # noqa: E402
from eyes.engine.overlay_renderer import OverlayRenderer  # noqa: E402

PASS: List[str] = []
FAIL: List[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    if cond:
        print(f"  ok:   {name}")
    else:
        print(f"  FAIL: {name} {detail}")


cfg = EngineConfig()
renderer = OverlayRenderer(cfg)
oc = cfg.overlay
R = cfg.layout.eye_radius
LOOK_MAX = cfg.layout.look_max_offset

# LES-09B.4 documented values (the baseline LES-09B.5 must preserve).
B4_SCALE_RATIO = 0.85
B4_ZZZ_SCALE = 16.0
B4_ZZZ_X_MIN, B4_ZZZ_X_MAX = 2.40, 2.85
B4_ZZZ_Y_MIN, B4_ZZZ_Y_MAX = 2.40, 2.70

# Worst-case autonomous offsets, DERIVED from the engine configuration
# (same as LES-09B.4 - no invented numbers).
WORST_MICRO = cfg.micro_motion.amplitude
WORST_BOUNCE = cfg.safe_region.max_bounce_ratio * cfg.display.height


def make_pose(
    nx: float = 0.5,
    ny: float = 0.5,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    rotation: float = 0.0,
    micro: Optional[float] = None,
    bounce: Optional[float] = None,
) -> EyePair:
    """A composed pose at the given normalized gaze and eye geometry.

    Micro/bounce default to their configured worst case (toward where the
    cues live) so the no-intersection checks hold for the maximum
    possible excursion.
    """
    micro = WORST_MICRO if micro is None else micro
    bounce = WORST_BOUNCE if bounce is None else bounce
    pose = EyePair()
    pose.configure(cfg)
    off = LOOK_MAX
    pose.left.look_offset_x = pose.right.look_offset_x = (nx - 0.5) * 2.0 * off
    pose.left.look_offset_y = pose.right.look_offset_y = (ny - 0.5) * 2.0 * off
    for eye in (pose.left, pose.right):
        eye.micro_offset_x = micro
        eye.micro_offset_y = micro
        eye.bounce_offset_x = -bounce
        eye.bounce_offset_y = -bounce
        eye.scale_x = scale_x
        eye.scale_y = scale_y
        eye.rotation = rotation
    return pose


# ---------------------------------------------------------------------------
# 1. ? scale unchanged + the centred model is gone from config.
# ---------------------------------------------------------------------------
print("=== 1. ? scale UNCHANGED; centred model removed ===\n")
thinking_scale = renderer.thinking_scale()
check("1. scale still DERIVED from the real eye radius",
      abs(thinking_scale - oc.thinking_cue_scale_ratio * R) < 1e-6,
      f"scale={thinking_scale:.2f}")
check("1. thinking_cue_scale_ratio still 0.85 (human-approved size, "
      "byte-identical to LES-09B.4)",
      abs(oc.thinking_cue_scale_ratio - B4_SCALE_RATIO) < 1e-9,
      str(oc.thinking_cue_scale_ratio))
glyph_h = 1.16 * thinking_scale
eye_h = 2.0 * R
check("1. glyph visual height is still ~half the eye height (0.35-0.65)",
      0.35 <= glyph_h / eye_h <= 0.65, f"{glyph_h / eye_h:.2f}")
check("1. the centred anchor model (thinking_cue_anchor_x_ratio) is gone",
      not hasattr(oc, "thinking_cue_anchor_x_ratio"))
check("1. perimeter fields exist (thinking_cue_eye / thinking_cue_perimeter)",
      hasattr(oc, "thinking_cue_eye") and hasattr(oc, "thinking_cue_perimeter"),
      f"{oc.thinking_cue_eye}/{oc.thinking_cue_perimeter}")
check("1. default anchor eye is 'right' (human-approved direction)",
      oc.thinking_cue_eye == "right", str(oc.thinking_cue_eye))
check("1. default perimeter corner is 'outer_top'",
      oc.thinking_cue_perimeter == "outer_top", str(oc.thinking_cue_perimeter))

# ---------------------------------------------------------------------------
# 2-4. Not centred; perimeter-anchored; outside the eye (neutral pose).
# ---------------------------------------------------------------------------
print("\n=== 2-4. Not centred, perimeter-anchored, outside the eye ===\n")
pose = make_pose(0.5, 0.5, scale_x=1.0, scale_y=1.0, micro=0.0, bounce=0.0)
l_reg, r_reg = renderer.eye_pair_regions(pose)
ax, ay = renderer.thinking_anchor(pose)
clearance = oc.thinking_cue_clearance_ratio * R
scale = renderer.thinking_scale()
face_mid_x = (pose.left.pos_x + pose.right.pos_x) * 0.5

check("2. ? is NOT at the face midpoint (no longer centred)",
      abs(ax - face_mid_x) > 200.0, f"ax={ax:.1f} mid={face_mid_x:.1f}")
check("2. ? is OUTSIDE the eye-pair span (right of the right eye, "
      "not between the eyes)",
      ax > r_reg[2] and not (l_reg[2] < ax < r_reg[0]),
      f"ax={ax:.1f} right_right={r_reg[2]:.1f} left_right={l_reg[2]:.1f}")
check("3. ? is anchored to the right eye's OUTER TOP corner at exactly "
      "the configured clearance (eye perimeter -> clearance -> '?')",
      abs(ax - (r_reg[2] + clearance + 0.42 * scale)) < 1e-6
      and abs(ay - (r_reg[1] - clearance - 0.61 * scale)) < 1e-6,
      f"anchor=({ax:.1f},{ay:.1f}) clearance={clearance:.1f}")
cr = renderer.thinking_cue_region((ax, ay))
check("4. ? bounding box starts exactly one clearance beyond the eye "
      "perimeter (glyph.left = eye.right + clearance, "
      "glyph.bottom = eye.top - clearance)",
      abs(cr[0] - (r_reg[2] + clearance)) < 1e-6
      and abs(cr[3] - (r_reg[1] - clearance)) < 1e-6,
      f"cue={tuple(round(v, 1) for v in cr)}")
check("4. ? does NOT intersect either eye region (neutral pose)",
      not renderer.regions_intersect(cr, l_reg)
      and not renderer.regions_intersect(cr, r_reg),
      f"cue={tuple(round(v) for v in cr)}")

# ---------------------------------------------------------------------------
# 5. ? follows eye movement (anchor tracks the composed pose exactly).
# ---------------------------------------------------------------------------
print("\n=== 5. ? follows eye movement ===\n")
p_neutral = make_pose(0.5, 0.5, micro=0.0, bounce=0.0)
p_up_right = make_pose(1.0, 0.0, micro=0.0, bounce=0.0)  # look (+35, -35)
a0 = renderer.thinking_anchor(p_neutral)
a1 = renderer.thinking_anchor(p_up_right)
check("5. anchor moves with the gaze (delta == effective-eye delta: "
      "look right +35, look up -35)",
      abs((a1[0] - a0[0]) - 35.0) < 1e-6
      and abs((a1[1] - a0[1]) + 35.0) < 1e-6,
      f"anchor {tuple(round(v, 1) for v in a0)} -> {tuple(round(v, 1) for v in a1)}")

# The anchor must be derived from the ACTUAL effective geometry (pos +
# look + micro + bounce), not the eye's rest position: at neutral gaze
# with a -26 px bounce offset, the right eye's composed right edge moves
# left by 26 px and the anchor must follow.
p_bounce = make_pose(0.5, 0.5, micro=WORST_MICRO, bounce=WORST_BOUNCE)
r_reg_b = renderer.eye_pair_regions(p_bounce)[1]
ax_b, ay_b = renderer.thinking_anchor(p_bounce)
check("5. anchor uses the COMPOSED eye AABB (pos + look + micro + bounce), "
      "not the rest centre",
      abs(ax_b - (r_reg_b[2] + clearance + 0.42 * scale)) < 1e-6,
      f"ax={ax_b:.1f} composed_right={r_reg_b[2]:.1f}")

# ---------------------------------------------------------------------------
# 6. No-intersection across representative gaze positions & pose variants.
# ---------------------------------------------------------------------------
print("\n=== 6. Safe across representative gaze positions & poses ===\n")
GAZE_DIRS = [
    ("neutral", 0.0, 0.0), ("up", 0.0, -1.0), ("down", 0.0, 1.0),
    ("left", -1.0, 0.0), ("right", 1.0, 0.0),
    ("up-left", -1.0, -1.0), ("up-right", 1.0, -1.0),
    ("down-left", -1.0, 1.0), ("down-right", 1.0, 1.0),
]
POSE_VARIANTS = [
    ("identity", 1.00, 1.00, 0.00),
    ("stretch", 1.10, 0.90, 0.00),
    ("squash/droop", 0.95, 0.80, 0.00),
    ("rotated", 1.00, 1.00, 0.30),
]
orb_x, orb_y = oc.thinking_orbital_amplitude_x, oc.thinking_orbital_amplitude_y
for name, dx, dy in GAZE_DIRS:
    for vname, sx, sy, rot in POSE_VARIANTS:
        p = make_pose(0.5 + dx * 0.5, 0.5 + dy * 0.5, sx, sy, rot)
        ll, rr = renderer.eye_pair_regions(p)
        axp, ayp = renderer.thinking_anchor(p)
        cue = renderer.thinking_cue_region((axp + orb_x, ayp + orb_y))
        check(f"6. ? avoids LEFT eye  [{name}/{vname}]",
              not renderer.regions_intersect(cue, ll),
              f"cue={tuple(round(v) for v in cue)}")
        check(f"6. ? avoids RIGHT eye [{name}/{vname}]",
              not renderer.regions_intersect(cue, rr),
              f"cue={tuple(round(v) for v in cue)}")

# The configured clearance must hold (undrifted anchor) at every gaze dir.
for name, dx, dy in GAZE_DIRS:
    p = make_pose(0.5 + dx * 0.5, 0.5 + dy * 0.5)
    r_right = renderer.eye_pair_regions(p)[1]
    axp, ayp = renderer.thinking_anchor(p)
    gap_x = axp - 0.42 * scale - r_right[2]
    gap_y = r_right[1] - (ayp + 0.61 * scale)
    check(f"6. clearance holds at [{name}] (exactly {clearance:.0f}px "
          f"from the right eye's outer-top corner)",
          abs(gap_x - clearance) < 1e-6 and abs(gap_y - clearance) < 1e-6,
          f"gap=({gap_x:.1f},{gap_y:.1f})")

# ---------------------------------------------------------------------------
# 7. Safe during the Thinking choreography (every look_at target, 5 seeds).
# ---------------------------------------------------------------------------
print("\n=== 7. Safe during Thinking choreography ===\n")
from les.choreography import EmotionChoreographyDirector  # noqa: E402

th_fail = []
seen_targets = set()
for seed in (1, 2, 3, 4, 5):
    plan = EmotionChoreographyDirector(rng=random.Random(seed)).build("thinking")
    for beat in plan.beats:
        if beat.command != "look_at":
            continue
        nx, ny = beat.args[0], beat.args[1]
        key = (round(nx, 3), round(ny, 3))
        if key in seen_targets:
            continue
        seen_targets.add(key)
        p = make_pose(nx, ny, 1.0, 0.98, 0.0)
        ll, rr = renderer.eye_pair_regions(p)
        axp, ayp = renderer.thinking_anchor(p)
        cue = renderer.thinking_cue_region((axp + orb_x, ayp + orb_y))
        if renderer.regions_intersect(cue, ll) or renderer.regions_intersect(cue, rr):
            th_fail.append((nx, ny))
check("7. ? clear of BOTH eyes at every thinking-choreography gaze "
      "target (5 seeds, incl. gaze-away + preparation + correction)",
      not th_fail, f"failed targets={th_fail}")
check("7. thinking choreography exercises multiple gaze targets",
      len(seen_targets) >= 3, str(sorted(seen_targets)))

# ---------------------------------------------------------------------------
# 8. ZZZ unchanged: exact LES-09B.4 config values + band still clear.
# ---------------------------------------------------------------------------
print("\n=== 8. Sleepy ZZZ UNCHANGED ===\n")
check("8. sleepy_cue_scale_base still 16.0 (byte-identical to LES-09B.4)",
      abs(oc.sleepy_cue_scale_base - B4_ZZZ_SCALE) < 1e-9,
      str(oc.sleepy_cue_scale_base))
check("8. sleepy x band still 2.40..2.85 eye radii (LES-09B.4 value)",
      abs(oc.sleepy_cue_x_min_ratio - B4_ZZZ_X_MIN) < 1e-9
      and abs(oc.sleepy_cue_x_max_ratio - B4_ZZZ_X_MAX) < 1e-9,
      f"x=({oc.sleepy_cue_x_min_ratio},{oc.sleepy_cue_x_max_ratio})")
check("8. sleepy y band still 2.40..2.70 eye radii (LES-09B.4 value)",
      abs(oc.sleepy_cue_y_min_ratio - B4_ZZZ_Y_MIN) < 1e-9
      and abs(oc.sleepy_cue_y_max_ratio - B4_ZZZ_Y_MAX) < 1e-9,
      f"y=({oc.sleepy_cue_y_min_ratio},{oc.sleepy_cue_y_max_ratio})")
sl_fail = []
for name, dx, dy in GAZE_DIRS:
    p = make_pose(0.5 + dx * 0.5, 0.5 + dy * 0.5, 0.95, 0.80, 0.0)
    ll, rr = renderer.eye_pair_regions(p)
    (x_lo, x_hi), (y_lo, y_hi) = renderer.sleepy_spawn_band(p)
    worst_z = renderer.z_cue_region(x_lo, y_hi, oc.sleepy_cue_scale_base * 1.2)
    if renderer.regions_intersect(worst_z, ll) or renderer.regions_intersect(worst_z, rr):
        sl_fail.append(name)
check("8. ZZZ band still clear of BOTH eyes across all gaze targets + "
      "droop pose (worst-case spawn corner, max glyph scale)",
      not sl_fail, str(sl_fail))

# ---------------------------------------------------------------------------
# Bonus: left-eye + outer_bottom options stay collision-safe.
# ---------------------------------------------------------------------------
print("\n=== Bonus. Configurable eye / corner options stay safe ===\n")
for eye in ("left", "right"):
    for corner in ("outer_top", "outer_bottom"):
        variant = dataclasses.replace(oc, thinking_cue_eye=eye,
                                      thinking_cue_perimeter=corner)
        r_var = OverlayRenderer(cfg)
        r_var.overlay_config = variant
        ok = True
        for name, dx, dy in GAZE_DIRS:
            p = make_pose(0.5 + dx * 0.5, 0.5 + dy * 0.5)
            ll, rr = renderer.eye_pair_regions(p)
            axp, ayp = r_var.thinking_anchor(p)
            cue = r_var.thinking_cue_region((axp + orb_x, ayp + orb_y))
            if renderer.regions_intersect(cue, ll) or renderer.regions_intersect(cue, rr):
                ok = False
                break
        check(f"bonus. {eye}/{corner} stays outside BOTH eyes across "
              f"all gaze targets", ok)

# ---------------------------------------------------------------------------
# Real-engine pipeline: thinking reaches the engine; the verified
# OverlayRenderer is the one composed by the real FaceComposer.
# ---------------------------------------------------------------------------
print("\n=== Real-engine pipeline ===\n")
from les.choreography import (  # noqa: E402
    EmotionChoreographyBridge,
    EmotionChoreographyRunner,
)
from les.director.emotion_director import (  # noqa: E402
    DefaultEmotionDirector,
    EmotionInput,
)
from les.integration import RealEngineDriver  # noqa: E402
from les.memory.behavior_memory import BehaviorMemory  # noqa: E402
from les.world.world_state import WorldState  # noqa: E402

world = WorldState()
memory = BehaviorMemory()
ed = DefaultEmotionDirector(world, memory)
runner = EmotionChoreographyRunner(
    director=EmotionChoreographyDirector(rng=random.Random(21)),
    bridge=EmotionChoreographyBridge(),
)
driver = RealEngineDriver.for_face()
runner.bridge.attach(driver)
engine = driver.engine
now = 0.0


def tick(dt: float = 16.0, held: Optional[str] = None) -> None:
    global now
    now += dt
    world.set_timestamp(now)
    if held is not None:
        ed.ingest(EmotionInput("verify", held, 1.0, now))
    ed.update(dt)
    runner.update(ed.internal_state())
    cmds = runner.bridge.scheduler.advance(dt)
    if cmds:
        runner.bridge.apply_commands(cmds)
    engine.step(dt)


for _ in range(1200):
    tick(held="thinking")
    if engine.current_state == "thinking":
        break
check("pipeline. thinking reached the real engine", engine.current_state == "thinking",
      str(engine.current_state))
try:
    real_overlay = engine.composer.overlay_renderer.eye_overlay
    check("pipeline. real engine composes through the verified OverlayRenderer",
          isinstance(real_overlay, OverlayRenderer), str(type(real_overlay)))
    check("pipeline. the real overlay uses the perimeter model (no centred "
          "anchor field)",
          not hasattr(real_overlay.overlay_config, "thinking_cue_anchor_x_ratio")
          and real_overlay.overlay_config.thinking_cue_eye in ("left", "right"),
          str(real_overlay.overlay_config.thinking_cue_eye))
except Exception as exc:  # noqa: BLE001
    check("pipeline. real engine composes through the verified OverlayRenderer",
          False, f"{type(exc).__name__}: {exc}")

# ---------------------------------------------------------------------------
# 9-11. LES-09B.4 collision suite + regressions + showcase smoke (real runs).
# ---------------------------------------------------------------------------
print("\n=== 9-11. LES-09B.4 suite + regressions + showcase smoke ===\n")
regression_suites = [
    # LES-09B.4 collision/geometry suite (also gates b1/b2/b3 + smoke
    # transitively, which in turn gate the six older regression suites).
    "_verify_les09b4_cue_placement.py",
    # Deliberately re-run directly for explicitness: b3 asserts the exact
    # ZZZ config values (mission requirement 8) and the smoke is the
    # mission requirement 11 - running them again here makes the two
    # requirements visible in this suite's own output (b4 also runs them
    # internally, so this is redundant but cheap relative to total time).
    "_verify_les09b3_sleepy.py",
]
for suite in regression_suites:
    r = subprocess.run([sys.executable, suite], capture_output=True, text=True,
                       timeout=900)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    check(f"9/10. {suite} exits 0", r.returncode == 0, tail)

r_show = subprocess.run(
    [sys.executable, "_show_les09b2_expression_polish.py", "--smoke", "2.0"],
    capture_output=True, text=True, timeout=420,
)
tail = r_show.stdout.strip().splitlines()[-1] if r_show.stdout.strip() else ""
check("11. _show_les09b2_expression_polish.py --smoke exits 0",
      r_show.returncode == 0,
      f"{tail} | stderr tail: "
      f"{r_show.stderr.strip().splitlines()[-1] if r_show.stderr.strip() else ''}")

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL LES-09B.5 CHECKS PASSED")
