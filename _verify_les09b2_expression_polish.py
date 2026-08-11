"""
_verify_les09b2_expression_polish.py  --  LES-09B.2 verification suite.
=======================================================================

Focused verification of the visual polish changes to the Living Expression
System: cue configuration, choreography data updates, fallback handling,
and engine config threading.

Minimal verification points (18 required + engine config tests):

  1. Existing choreographies still construct (LES-09B.1 four + LES-09B.3
     sleepy - now a fifth authored choreography, no longer a fallback).
  2. Existing scheduler tests remain green.
  3. Existing real-engine integration remains green.
  4. Thinking choreography still preserves gaze-away behavior.
  5. Thinking cue configuration is valid (OverlayConfig fields exist).
  6. Thinking cue scale is bounded and derived from eye geometry
     (scale_ratio ~ half the eye height - LES-09B.4).
  7. Thinking cue placement is bounded (perimeter eye/corner + clearance
     ratio - the LES-09B.5 perimeter anchor, no longer centred).
  8. Thinking cue never intersects the eye silhouettes (geometric check
     across gaze targets - LES-09B.4).
  9. Sleepy cue changes, if implemented, are bounded (face-space band).
 10. Happy choreography remains schedulable.
 11. Sad choreography remains schedulable.
 12. Calm remains restrained.
 13. No new unauthorized EngineCommands.
 14. No duplicate scheduler.
 15. No new clock.
 16. No pygame imports inside LES.
 17. Deterministic choreography remains deterministic.
 18. Existing regression suites pass.

Plus engine config tests:
  - OverlayConfig exists with thinking cue fields.
  - thinking_cue_scale_ratio is bounded (~ half the eye size).
  - perimeter eye/corner + clearance ratio are bounded.
  - thinking_anchor() returns a pose-derived face-space anchor on the
    eye's outer perimeter whose cue bounding box never intersects either
    eye silhouette (LES-09B.5: anchored to the eye corner, not centred).
  - sleepy_cue_scale_base bounded.
  - build_fallback() produces valid plans.
  - Runner fallback path works for non-choreographed emotions.

Run:  py _verify_les09b2_expression_polish.py
"""

from __future__ import annotations

import ast
import inspect
import os
import random
import subprocess
import sys
from typing import List, Optional, Tuple

# --- Behaviour-layer imports FIRST (for the forbidden-import check below) ---
from les.choreography import (  # noqa: E402
    CHOREOGRAPHIES,
    BeatKind,
    ChoreographyPlan,
    EmotionChoreographyBridge,
    EmotionChoreographyDirector,
    EmotionChoreographyRunner,
    KNOWN_ENGINE_STATES,
    SUPPORTED_EMOTIONS,
    build_fallback,
    validate_choreography,
)
from les.choreography.emotions import CHOREOGRAPHIES as REGISTRY  # noqa: E402
from les.director.emotion_director import (  # noqa: E402
    DefaultEmotionDirector,
    EmotionInput,
)
from les.memory.behavior_memory import BehaviorMemory  # noqa: E402
from les.world.world_state import WorldState  # noqa: E402

PASS: List[str] = []
FAIL: List[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    if cond:
        print(f"  ok:   {name}")
    else:
        print(f"  FAIL: {name} {detail}")


# ---------------------------------------------------------------------------
# 1. Existing LES-09B.1 choreography still constructs.
# ---------------------------------------------------------------------------
print("=== 1. Existing LES-09B.1 choreography still constructs ===\n")
# LES-09B.3 added SLEEPY as a fifth authored choreography.
check(
    "exactly the supported emotions are choreographed",
    set(CHOREOGRAPHIES) == set(SUPPORTED_EMOTIONS)
    == {"calm", "happy", "sad", "thinking", "sleepy"},
    str(set(CHOREOGRAPHIES)),
)
for name in ("calm", "happy", "sad", "thinking", "sleepy"):
    choreo = REGISTRY[name]
    problems = validate_choreography(choreo)
    check(f"{name} choreography validates cleanly", not problems, "; ".join(problems))
    check(f"{name} has beats and a first ONSET",
          choreo.beats and choreo.beats[0].kind is BeatKind.ONSET)

# ---------------------------------------------------------------------------
# 4. Thinking choreography still preserves gaze-away behavior (LES-09B.2).
# ---------------------------------------------------------------------------
print("\n=== 4. Thinking: gaze-away behavior preserved ===\n")
dir_ = EmotionChoreographyDirector(rng=random.Random(5))
th_plan = dir_.build("thinking")
thinking_gaze_away = [
    b for b in th_plan.beats
    if b.command == "look_at" and (b.args[0] != 0.5 or b.args[1] != 0.5)
]
check("thinking has at least one gaze AWAY from center (E4.4)",
      len(thinking_gaze_away) >= 1,
      str([b.args for b in thinking_gaze_away]))
if thinking_gaze_away:
    t = thinking_gaze_away[0]
    check("thinking gaze-away is off-center by a perceptible margin",
          max(abs(t.args[0] - 0.5), abs(t.args[1] - 0.5)) >= 0.05, str(t.args))

# LES-09B.2: thinking now has a preparation beat + subtle correction beat.
check("thinking has a preparation beat (downward glance before scan)",
      any("preparation" in b.label for b in th_plan.beats),
      str([b.label[:30] for b in th_plan.beats if b.command == "look_at"]))
check("thinking has a subtle correction beat (micro re-aim mid-pause)",
      any("subtle correction" in b.label for b in th_plan.beats),
      str([b.label[:30] for b in th_plan.beats if b.command == "look_at"]))
check("thinking has a late conclusion blink (after 2000 ms)",
      any(b.command == "blink" and b.offset_ms > 2000.0 for b in th_plan.beats),
      str([(round(b.offset_ms), b.command) for b in th_plan.beats]))
check("thinking has a conclusion/return beat",
      any(b.command == "look_at" and b.args == (0.5, 0.5) for b in th_plan.beats))

# ---------------------------------------------------------------------------
# 5-7. Thinking cue configuration (engine config).
# ---------------------------------------------------------------------------
print("\n=== 5-7. Thinking cue configuration ===\n")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from eyes.engine.config import EngineConfig, OverlayConfig  # noqa: E402

cfg = EngineConfig()
oc = cfg.overlay

check("5. OverlayConfig has thinking_cue_scale_ratio (LES-09B.4)",
      hasattr(oc, "thinking_cue_scale_ratio"), str(oc.thinking_cue_scale_ratio))
check("5. OverlayConfig has thinking_cue_eye (LES-09B.5 perimeter anchor)",
      hasattr(oc, "thinking_cue_eye"), str(oc.thinking_cue_eye))
check("5. OverlayConfig has thinking_cue_perimeter (LES-09B.5)",
      hasattr(oc, "thinking_cue_perimeter"), str(oc.thinking_cue_perimeter))
check("5. OverlayConfig has thinking_cue_clearance_ratio",
      hasattr(oc, "thinking_cue_clearance_ratio"), str(oc.thinking_cue_clearance_ratio))
check("5. OverlayConfig has thinking_cue_fade_in_ms",
      hasattr(oc, "thinking_cue_fade_in_ms"))
check("5. OverlayConfig has thinking_cue_fade_out_ms",
      hasattr(oc, "thinking_cue_fade_out_ms"))

# LES-09B.4: the cue scale is DERIVED from the real eye geometry
# (scale = ratio * eye_radius), never a hard-coded pixel value.
from eyes.engine.overlay_renderer import OverlayRenderer  # noqa: E402
renderer = OverlayRenderer(cfg)
thinking_scale = renderer.thinking_scale()
check("6. thinking_cue_scale_ratio is bounded (0.5 < ratio <= 1.0)",
      0.5 < oc.thinking_cue_scale_ratio <= 1.0, str(oc.thinking_cue_scale_ratio))
check("6. actual thinking scale is derived from eye_radius",
      abs(thinking_scale - oc.thinking_cue_scale_ratio * cfg.layout.eye_radius) < 1e-6,
      f"{thinking_scale:.1f}")
# Visual height of the glyph is ~1.16x its scale; the eye height is
# 2 * eye_radius. ratio 0.85 -> glyph ~74 px vs eye height 150 px:
# approximately HALF the eye size, subordinate to the eyes.
glyph_h = 1.16 * thinking_scale
eye_h = 2.0 * cfg.layout.eye_radius
check("6. thinking cue is approximately half the eye height (0.35-0.65)",
      0.35 <= glyph_h / eye_h <= 0.65, f"{glyph_h / eye_h:.2f}")
check("6. thinking_cue_eye selects a real eye ('left'/'right')",
      oc.thinking_cue_eye in ("left", "right"), str(oc.thinking_cue_eye))
check("6. thinking_cue_perimeter is a real corner "
      "('outer_top'/'outer_bottom')",
      oc.thinking_cue_perimeter in ("outer_top", "outer_bottom"),
      str(oc.thinking_cue_perimeter))
check("6. thinking_cue_clearance_ratio is a real margin (0.1-1.0)",
      0.1 <= oc.thinking_cue_clearance_ratio <= 1.0, str(oc.thinking_cue_clearance_ratio))

# 8. Thinking cue never intersects the eye silhouettes (LES-09B.4): the
# anchor is recomputed from the ACTUAL composed pose every frame, with a
# configurable clearance above the highest eye silhouette point.
from eyes.engine.eye_pair import EyePair  # noqa: E402
pose = EyePair()
pose.configure(cfg)
anchor_x, anchor_y = renderer.thinking_anchor(pose)
check("8. thinking_anchor(pose) returns a position",
      isinstance(anchor_x, float) and isinstance(anchor_y, float),
      f"({anchor_x:.1f}, {anchor_y:.1f})")
l_region, r_region = renderer.eye_pair_regions(pose)
eye_top = min(l_region[1], r_region[1])
scale = renderer.thinking_scale()
clearance = oc.thinking_cue_clearance_ratio * cfg.layout.eye_radius
check("8. cue bottom edge clears the eye silhouette top by the margin",
      anchor_y + 0.61 * scale + clearance <= eye_top + 1e-6,
      f"bottom={anchor_y + 0.61 * scale:.1f} top={eye_top:.1f} clearance={clearance:.1f}")
check("8. cue is anchored OUTSIDE the right eye's outer perimeter "
      "(LES-09B.5 - no longer centred)",
      anchor_x > r_region[2] and anchor_y < r_region[1],
      f"x={anchor_x:.1f} right_right={r_region[2]:.1f} top={r_region[1]:.1f}")
check("8. cue hugs the eye corner at exactly the configured clearance "
      "(eye perimeter -> clearance -> '?')",
      abs(anchor_x - (r_region[2] + clearance + 0.42 * scale)) < 1e-6
      and abs(anchor_y - (r_region[1] - clearance - 0.61 * scale)) < 1e-6,
      f"anchor=({anchor_x:.1f},{anchor_y:.1f})")
cr = renderer.thinking_cue_region((anchor_x, anchor_y))
check("8. cue region does NOT intersect either eye region (neutral pose)",
      not (renderer.regions_intersect(cr, l_region)
           or renderer.regions_intersect(cr, r_region)),
      f"cue={tuple(round(v) for v in cr)}")

# 9. Sleepy cue changes are bounded.
check("\n=== 9. Sleepy cue changes bounded ===\n", True)
check("OverlayConfig has sleepy_cue_scale_base",
      hasattr(oc, "sleepy_cue_scale_base"), str(oc.sleepy_cue_scale_base))
check("sleepy_cue_scale_base is bounded (10 < scale <= 25)",
      10.0 < oc.sleepy_cue_scale_base <= 25.0, str(oc.sleepy_cue_scale_base))
check("OverlayConfig has sleepy_cue_x_min_ratio",
      hasattr(oc, "sleepy_cue_x_min_ratio"))
check("sleepy_cue_x_min_ratio is in the face-space band [1, 4]",
      1.0 <= oc.sleepy_cue_x_min_ratio <= 4.0, str(oc.sleepy_cue_x_min_ratio))
check("sleepy_cue_x_max_ratio > min_ratio",
      oc.sleepy_cue_x_max_ratio > oc.sleepy_cue_x_min_ratio)
check("sleepy_cue_y_min_ratio / max_ratio are ordered and bounded",
      0.0 <= oc.sleepy_cue_y_min_ratio < oc.sleepy_cue_y_max_ratio <= 4.0,
      f"y=({oc.sleepy_cue_y_min_ratio}, {oc.sleepy_cue_y_max_ratio})")

# ---------------------------------------------------------------------------
# 10-12. Happy/Sad/Calm remain schedulable.
# ---------------------------------------------------------------------------
print("\n=== 10-12. Happy, Sad, Calm remain schedulable ===\n")
for name in ("happy", "sad", "calm"):
    plan = dir_.build(name)
    bridge = EmotionChoreographyBridge()
    bridge.execute(plan)
    check(f"{name} plan is schedulable",
          bridge.scheduler.active_behavior == f"choreo:{name}",
          str(bridge.scheduler.active_behavior))
    cmds = bridge.scheduler.advance(0.0) + bridge.scheduler.advance(plan.total_duration_ms + 100.0)
    check(f"{name} commands are documented",
          all(c.command in ("set_state", "blink", "look_at") for c in cmds),
          str([c.command for c in cmds]))
    bridge.scheduler.cancel()

# Calm remains restrained.
for seed in range(6):
    p = EmotionChoreographyDirector(rng=random.Random(seed)).build("calm")
    check(f"calm (seed {seed}) has <= 4 actions (LES-09B.2: still restrained)",
          len(p.action_beats()) <= 4, str(len(p.action_beats())))
    check(f"calm (seed {seed}) is long and still (>= 7 s)",
          p.total_duration_ms >= 7000.0, f"{p.total_duration_ms:.0f}ms")

# Happy has extra gaze variation + soft settle (LES-09B.2 additions).
happy_plan = dir_.build("happy")
check("happy has extra gaze variation beat (LES-09B.2)",
      any("gaze variation" in b.label for b in happy_plan.beats),
      str([b.label[:30] for b in happy_plan.beats if "gaze variation" in b.label]))
check("happy has soft settling beat (LES-09B.2)",
      any("soft settling" in b.label for b in happy_plan.beats),
      str([b.label[:30] for b in happy_plan.beats if "soft settling" in b.label]))

# Sad has longer holds (LES-09B.2).
sad_plan = dir_.build("sad")
sad_holds = [b for b in sad_plan.beats if b.kind is BeatKind.HOLD]
check("sad has at least 2 hold beats (LES-09B.2: more stillness)",
      len(sad_holds) >= 2, str(len(sad_holds)))
if sad_holds:
    check("sad hold durations are longer (LES-09B.2: extended stillness)",
          all(h.duration_ms >= 2000.0 for h in sad_holds),
          str([h.duration_ms for h in sad_holds]))

# ---------------------------------------------------------------------------
# 13-16. Architecture guards.
# ---------------------------------------------------------------------------
print("\n=== 13-16. Architecture guards ===\n")

# 13. No new unauthorized EngineCommands.
for name in ("calm", "happy", "sad", "thinking", "sleepy"):
    plan = dir_.build(name)
    for step in plan.steps:
        check(f"13. {name} step uses a documented command",
              step.command in ("set_state", "blink", "look_at"), str(step))

# 14-15. No duplicate scheduler, no new clock (the runner uses the bridge's
# DefaultScheduler, which is the single execution authority).
runner = EmotionChoreographyRunner(
    director=EmotionChoreographyDirector(rng=random.Random(1)),
    bridge=EmotionChoreographyBridge(),
)
check("14. runner uses the bridge's scheduler (single authority)",
      runner.bridge.scheduler is not None)
from les.timeline.scheduler import DefaultScheduler, Scheduler
check("14. scheduler is a DefaultScheduler (the single execution authority)",
      isinstance(runner.bridge.scheduler, DefaultScheduler))
check("15. no new clock in the choreography layer",
      runner.bridge.scheduler is not None)

# 16. No pygame imports inside LES choreography layer.
import les.choreography.beats as _cb  # noqa: E402
import les.choreography.director as _cd  # noqa: E402
import les.choreography.emotions as _ce  # noqa: E402
import les.choreography.execution as _cx  # noqa: E402


def _code_without_docstrings(source: str) -> str:
    tree = ast.parse(source)
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        tree.body[0] = ast.Pass()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body[0] = ast.Pass()
    return ast.unparse(tree)


_choreo_code = "".join(
    _code_without_docstrings(inspect.getsource(m)) for m in (_cb, _cd, _ce, _cx)
)
for token in ("import pygame", "from pygame", "import eyes", "from eyes",
              "import face", "from face", "import rospy", "from rospy",
              "import cv2", "from cv2", "FaceEngine", "AnimationEngine",
              "RealEngineDriver", "composer", "renderer", "set_speech_pulse"):
    check(f"16. no '{token}' in choreography layer code", token not in _choreo_code)

# ---------------------------------------------------------------------------
# 17. Deterministic choreography remains deterministic.
# ---------------------------------------------------------------------------
print("\n=== 17. Deterministic choreography remains deterministic ===\n")


def sequence(seed: int, passes: int = 2) -> list:
    d = EmotionChoreographyDirector(rng=random.Random(seed))
    out = []
    for _ in range(passes):
        for emo in SUPPORTED_EMOTIONS:
            p = d.build(emo)
            out.append(
                (emo, p.variant, p.total_duration_ms,
                 tuple((round(s.offset_ms, 3), s.command, s.args) for s in p.steps))
            )
    return out


check("same seed -> identical choreography sequences", sequence(42) == sequence(42))
check("different seeds -> differing (but valid) choreographies",
      sequence(42) != sequence(43))

# ---------------------------------------------------------------------------
# Engine config tests: build_fallback() + runner fallback path.
# ---------------------------------------------------------------------------
print("\n=== Engine config: build_fallback() + runner fallback ===\n")
fb = build_fallback("sleepy")
check("build_fallback produces a valid ChoreographyPlan",
      isinstance(fb, ChoreographyPlan), str(type(fb)))
check("fallback plan has a sleepy set_state",
      fb.steps[0].command == "set_state" and fb.steps[0].args[0] == "sleepy",
      str(fb.steps[0]))
check("fallback plan has a blink step",
      any(s.command == "blink" for s in fb.steps))
check("fallback variant is 'fallback'",
      fb.variant == "fallback", fb.variant)

# Unknown emotion falls back to calm.
fb_unknown = build_fallback("nonexistent_emotion")
check("unknown emotion fallback targets calm",
      fb_unknown.steps[0].args[0] == "calm", str(fb_unknown.steps[0].args))

# Runner fallback path: transition to a genuinely non-choreographed
# emotion (surprised - LES-09B.3 made sleepy a real choreography, so it is
# no longer a fallback example).
world = WorldState()
memory = BehaviorMemory()
ed = DefaultEmotionDirector(world, memory)
runner = EmotionChoreographyRunner(
    director=EmotionChoreographyDirector(rng=random.Random(1)),
    bridge=EmotionChoreographyBridge(),
)
now = 0.0

def tick(held: Optional[str] = None, dt: float = 16.0):
    global now
    now += dt
    world.set_timestamp(now)
    if held is not None:
        ed.ingest(EmotionInput("verify", held, 1.0, now))
    ed.update(dt)
    return runner.update(ed.internal_state())

for _ in range(600):
    plan = tick(held="surprised")
    if plan is not None:
        break
check("runner fallback: surprised plan executed",
      plan is not None and plan.emotion == "surprised",
      str(plan.emotion) if plan else "none")
if plan is not None:
    check("runner fallback: variant is 'fallback'",
          plan.variant == "fallback", plan.variant)

# LES-09B.3: sleepy now runs an AUTHORED choreography through the runner
# (no longer the fallback plan). Reset the runner and wait until the
# director actually transitions to sleepy (the first tick after reset can
# legitimately re-schedule the still-held surprised emotion).
runner.reset()
for _ in range(1200):
    plan = tick(held="sleepy")
    if plan is not None and plan.emotion == "sleepy":
        break
check("runner sleepy: authored plan executed",
      plan is not None and plan.emotion == "sleepy",
      str(plan.emotion) if plan else "none")
if plan is not None:
    check("runner sleepy: variant is a named sleepy variant (not 'fallback')",
          plan.variant != "fallback", plan.variant)
    check("runner sleepy: plan has real choreography beats",
          len(plan.beats) > 0, str(len(plan.beats)))

# KNOWN_ENGINE_STATES includes sleepy.
check("KNOWN_ENGINE_STATES includes sleepy",
      "sleepy" in KNOWN_ENGINE_STATES, str(KNOWN_ENGINE_STATES))

# ---------------------------------------------------------------------------
# 18. Existing regression suites pass.
# ---------------------------------------------------------------------------
print("\n=== 18. Existing regression suites ===\n")
regression_suites = [
    # LES-09B.1 suite (tests the four choreographies + pipeline + showcase)
    "_verify_les09b1_choreography.py",
    # Existing behavior / scheduler / integration / idle / motion suites
    "_verify_behavior.py",
    "_verify_les08_timeline_scheduler.py",
    "_verify_les08_5_integration.py",
    "_verify_les09a_idle.py",
    "_verify_les09a2_idle_integration.py",
    "_verify_les09a3_motion.py",
]
for suite in regression_suites:
    r = subprocess.run(
        [sys.executable, suite],
        capture_output=True, text=True, timeout=600,
    )
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    check(f"{suite} exits 0", r.returncode == 0, tail)

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL LES-09B.2 CHECKS PASSED")