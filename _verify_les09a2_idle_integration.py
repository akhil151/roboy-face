"""
LES-09A.2 verification: Real Idle Execution Integration.

Proves the Natural Idle Decision Layer (LES-09A.1) ACTUALLY EXECUTES on the
real, frozen animation engine through the existing LES pipeline:

    IdleContext
        -> IdleBehavior.decide() -> IdleDecision
        -> IdleDecision.to_behavior_intent() (via IdleExecutionBridge)
        -> DefaultScheduler.schedule() -> Timeline
        -> DefaultScheduler.advance() -> EngineCommand
        -> RealEngineDriver -> FaceEngine (real, frozen)

Verifies (mission checklist):
  1. IdleBehavior produces a valid decision.
  2. NONE produces no engine command (legitimate quiet periods).
  3. BLINK reaches the real engine through the Scheduler.
  4. GAZE_DRIFT reaches the real engine through look_at.
  5. CURIOUS_GLANCE reaches the real engine (look away, hold, return).
  6. MICRO_CORRECTION is represented with the smallest existing command.
  7. Current emotion is preserved during idle actions (no set_state).
  8. Idle does not directly call FaceEngine / AnimationEngine.
  9-12. Idle imports no pygame / eyes / face / ROS.
 13. Timeline timing is preserved.
 14. Scheduler ordering is preserved.
 15. EngineCommand ordering is deterministic.
 16. Seeded idle decisions remain deterministic through the pipeline.
 17. NONE results in legitimate quiet periods.
 18. Multiple idle actions execute sequentially.
 19. Higher-priority behavior interrupts idle.
 20. Recovery to idle works after an action / interruption.
 21. Idle plans never emit set_state.
 22. Attention is preserved (idle never overwrites a gaze target).
 23-26. The four earlier suites are re-run separately and stay green.

Plus a deterministic end-to-end scenario through the actual scheduler and
the real driver.

Run:  py _verify_les09a2_idle_integration.py
"""

from __future__ import annotations

import ast
import inspect
import random
import sys
from typing import List, Optional, Tuple, get_args


def _code_without_docstrings(source: str) -> str:
    """The module's executable code with every docstring removed.

    Used so "does idle reference the engine" checks inspect actual code,
    not the docstrings that document why the engine is NOT referenced.
    """
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

# --- Imports under test: the engine-free behaviour layer FIRST ------------
# (imported before les.integration so the forbidden-module check below can
#  assert that idle itself never pulls in pygame / eyes / face.)
from les.behaviors import (
    IdleAction,
    IdleBehavior,
    IdleContext,
    IdleDecision,
    IdleExecutionBridge,
    IdlePolicy,
    IdleTier,
)
from les.behaviors.idle_execution import idle_look_target
from les.director.behavior_director import BehaviorIntent
from les.memory.behavior_memory import BehaviorMemory
from les.timeline.scheduler import EngineCommand, EngineCommandName

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    if cond:
        print(f"  ok:   {name}")
    else:
        print(f"  FAIL: {name} {detail}")


def make_idle(action: IdleAction, seed: int) -> IdleBehavior:
    """An IdleBehavior whose policy forces exactly one action.

    DEMO/TEST SCAFFOLD: single-action weights make the decision layer
    deterministically pick the wanted action (same code path as the
    default policy - weights only). The default policy is exercised in the
    seeded-determinism section below.
    """
    weights = {
        tier: {a: (1.0 if a is action else 0.0) for a in IdleAction}
        for tier in IdleTier
    }
    return IdleBehavior(
        policy=IdlePolicy(action_weights=weights),
        rng=random.Random(seed),
        memory=BehaviorMemory(),
    )


def forced_decision(action: IdleAction, now_ms: float, seed: int) -> IdleDecision:
    """Produce a decision for ``action`` at caller time ``now_ms``."""
    return make_idle(action, seed).decide(IdleContext(now_ms=now_ms))


# ---------------------------------------------------------------------------
print("=== 1. IdleBehavior can produce a valid decision (LES-09A.1 intact) ===")
idle = IdleBehavior(rng=random.Random(1))
d = idle.decide(IdleContext(now_ms=0.0))
check("decision carries a valid action", d.action in IdleAction, str(d.action))
check("decision carries a valid tier", d.tier in IdleTier, str(d.tier))
check("decision carries caller-owned timing", d.next_ms > d.decided_at_ms == 0.0)
check("decision carries a reason", isinstance(d.reason, str) and bool(d.reason))
intent = idle.to_behavior_intent(d)
expected_variant = (
    d.tier.value if d.action is IdleAction.NONE else f"{d.tier.value}_{d.action.value}"
)
check(
    "decision maps to a BehaviorIntent (variant derived from decision)",
    intent.behavior_name == "idle" and intent.variant == expected_variant,
    str(intent),
)

# --- Engine-free import graph check BEFORE the engine-touching import ---
# (the RealEngineDriver import below legitimately loads pygame/eyes/face,
#  so this check must run before it to prove idle itself pulls nothing in.)
_loaded_early = [m for m in sys.modules if m.split(".")[0] in ("pygame", "eyes", "face")]

print("=== 2. NONE produces no engine command ===")
idle_none = make_idle(IdleAction.NONE, 2)
d_none = idle_none.decide(IdleContext(now_ms=0.0))
check("forced NONE decision is NONE", d_none.action is IdleAction.NONE, str(d_none))
bridge = IdleExecutionBridge(idle_none)
scheduled = bridge.execute(d_none, IdleContext(now_ms=0.0))
check("NONE is not scheduled (no fake animation)", scheduled is None and bridge.last_scheduled is None)
check("no timeline events for NONE", bridge.scheduler.timeline.is_empty)
check(
    "advancing produces zero engine commands",
    bridge.scheduler.advance(0.0) == [] and bridge.scheduler.advance(6000.0) == [],
)

print("=== 3. BLINK reaches the real engine through the Scheduler ===")
check("idle-only import graph pulls in no pygame/eyes/face", not _loaded_early, str(_loaded_early))
from les.integration import RealEngineDriver  # noqa: E402  (engine now allowed)

driver = RealEngineDriver.for_face()
d_blink = forced_decision(IdleAction.BLINK, 0.0, 3)
bridge = IdleExecutionBridge(make_idle(IdleAction.BLINK, 3))
bridge.attach(driver)
scheduled = bridge.execute(d_blink, IdleContext(now_ms=0.0))
check(
    "blink intent scheduled with variant preserved",
    scheduled is not None
    and scheduled.behavior_name == "idle"
    and scheduled.variant == "attentive_blink",
    str(scheduled),
)
check("timeline event carries the idle variant label",
      bridge.scheduler.timeline.pending[0].payload.get("variant") == "attentive_blink")
cmds = bridge.scheduler.advance(0.0)
check("BLINK emits exactly one blink command", cmds == [EngineCommand("blink")], str(cmds))
bridge.apply_commands(cmds)
for _ in range(8):
    driver.engine.step(16.0)
bw = driver.engine.mixer.eye_engine._engine.blink_controller.blink_weight
check("real engine blink actually fired", bw > 0.1, f"blink_weight={bw:.3f}")

print("=== 4. GAZE_DRIFT reaches the real engine through look_at ===")
driver4 = RealEngineDriver.for_face()
d_drift = forced_decision(IdleAction.GAZE_DRIFT, 0.0, 4)
bridge4 = IdleExecutionBridge(make_idle(IdleAction.GAZE_DRIFT, 4))
bridge4.attach(driver4)
bridge4.execute(d_drift, IdleContext(now_ms=0.0))
cmds4 = bridge4.scheduler.advance(0.0)
check("GAZE_DRIFT emits exactly one look_at command",
      len(cmds4) == 1 and cmds4[0].command == "look_at", str(cmds4))
tx, ty = cmds4[0].args  # type: ignore[misc]
check("look target is bounded in normalized [0, 1]",
      0.0 <= tx <= 1.0 and 0.0 <= ty <= 1.0, f"({tx:.3f},{ty:.3f})")
check("look target matches the deterministic idle target",
      abs(tx - idle_look_target(d_drift)[0]) < 1e-9
      and abs(ty - idle_look_target(d_drift)[1]) < 1e-9)
bridge4.apply_commands(cmds4)
for _ in range(60):
    driver4.engine.step(16.0)
lx, ly = driver4.engine.mixer.eye_engine._engine.look_controller.current_normalized
check("real engine gaze moved toward the idle target",
      abs(lx - tx) < 0.06 and abs(ly - ty) < 0.06, f"got ({lx:.2f},{ly:.2f}) want ({tx:.2f},{ty:.2f})")

print("=== 5. CURIOUS_GLANCE reaches the real engine (look, hold, return) ===")
driver5 = RealEngineDriver.for_face()
d_glance = forced_decision(IdleAction.CURIOUS_GLANCE, 0.0, 5)
bridge5 = IdleExecutionBridge(make_idle(IdleAction.CURIOUS_GLANCE, 5))
bridge5.attach(driver5)
bridge5.execute(d_glance, IdleContext(now_ms=0.0))
first = bridge5.scheduler.advance(0.0)
check("glance step 1 is a look_at away from center",
      len(first) == 1 and first[0].command == "look_at" and first[0].args != (0.5, 0.5),
      str(first))
gx, gy = first[0].args  # type: ignore[misc]
check("glance target bounded", 0.0 <= gx <= 1.0 and 0.0 <= gy <= 1.0)
bridge5.apply_commands(first)
for _ in range(40):
    driver5.engine.step(16.0)
cgx, cgy = driver5.engine.mixer.eye_engine._engine.look_controller.current_normalized
check("real engine gaze moved toward the glance target",
      abs(cgx - gx) < 0.08 and abs(cgy - gy) < 0.08, f"({cgx:.2f},{cgy:.2f}) vs ({gx:.2f},{gy:.2f})")
second = bridge5.scheduler.advance(500.0)
check("glance step 2 returns to neutral after the hold",
      second == [EngineCommand("look_at", (0.5, 0.5))], str(second))
bridge5.apply_commands(second)
for _ in range(70):
    driver5.engine.step(16.0)
rgx, rgy = driver5.engine.mixer.eye_engine._engine.look_controller.current_normalized
check("real engine gaze returned toward neutral center",
      abs(rgx - 0.5) < 0.1 and abs(rgy - 0.5) < 0.1, f"({rgx:.2f},{rgy:.2f})")

print("=== 6. MICRO_CORRECTION: smallest existing representation ===")
d_micro = forced_decision(IdleAction.MICRO_CORRECTION, 0.0, 6)
bridge6 = IdleExecutionBridge(make_idle(IdleAction.MICRO_CORRECTION, 6))
bridge6.execute(d_micro, IdleContext(now_ms=0.0))
cmds6 = bridge6.scheduler.advance(0.0)
check(
    "MICRO_CORRECTION is represented as look_at(0.5, 0.5) (re-centering)",
    cmds6 == [EngineCommand("look_at", (0.5, 0.5))],
    str(cmds6),
)
print("      (documented limitation: it is a deterministic re-center, not a")
print("       'tiny relative-to-current-gaze' move - LES never reads engine")
print("       internals to size it, and no new command exists for it)")

print("=== 7. Current emotion is preserved during idle actions ===")
driver7 = RealEngineDriver.for_face()
driver7.set_state("happy", 350.0)
driver7.engine.step(100.0)
check("engine is happy before idle", driver7.engine.current_state == "happy")
idle_cmds: List[EngineCommand] = []
for action, seed in [
    (IdleAction.BLINK, 71),
    (IdleAction.GAZE_DRIFT, 72),
    (IdleAction.MICRO_CORRECTION, 73),
    (IdleAction.CURIOUS_GLANCE, 74),
]:
    b = IdleExecutionBridge(make_idle(action, seed))
    b.attach(driver7)
    d_a = forced_decision(action, 0.0, seed)
    b.execute(d_a, IdleContext(now_ms=0.0))
    cm = b.scheduler.advance(0.0) + b.scheduler.advance(600.0)
    idle_cmds.extend(cm)
    b.apply_commands(cm)
    for _ in range(30):
        driver7.engine.step(16.0)
    check(f"engine still happy after idle {action.value}", driver7.engine.current_state == "happy")
check("no idle action ever emitted set_state",
      all(c.command != "set_state" for c in idle_cmds),
      str(idle_cmds))
check("idle actions use only the documented blink/look_at verbs",
      set(c.command for c in idle_cmds) <= {"blink", "look_at"})

print("=== 8. Idle never calls FaceEngine / AnimationEngine directly ===")
import les.behaviors.idle_execution as _ie  # noqa: E402
import les.behaviors.idle_behavior as _ib  # noqa: E402
import les.behaviors.idle_policy as _ip  # noqa: E402
_idle_src = inspect.getsource(_ip) + inspect.getsource(_ib) + inspect.getsource(_ie)
# Docstrings stripped PER MODULE (concatenating modules breaks AST docstring
# recognition - each module's docstring becomes a mid-file expression).
_idle_code = "".join(_code_without_docstrings(inspect.getsource(m)) for m in (_ip, _ib, _ie))
for token in ("FaceEngine", "AnimationEngine", "RealEngineDriver", "composer", "pygame"):
    check(f"no direct engine reference '{token}' in idle code", token not in _idle_code)

print("=== 9-12. Idle imports no pygame / eyes / face / ROS ===")
for token in ("import pygame", "from pygame", "import eyes", "from eyes",
              "import face", "from face", "import rospy", "from rospy",
              "import cv2", "from cv2"):
    check(f"no '{token}' in idle modules", token not in _idle_src)

print("=== 13. Timeline timing is preserved ===")
driver13 = RealEngineDriver.for_face()
b13 = IdleExecutionBridge(make_idle(IdleAction.CURIOUS_GLANCE, 13))
b13.attach(driver13)
b13.execute(forced_decision(IdleAction.CURIOUS_GLANCE, 0.0, 13), IdleContext(now_ms=0.0))
t0 = b13.scheduler.advance(0.0)
check("first glance command at t=0", t0 and b13.scheduler.timeline.now_ms == 0.0, str(t0))
t450 = b13.scheduler.advance(450.0)
check("return command at t=450 (hold preserved)",
      t450 == [EngineCommand("look_at", (0.5, 0.5))],
      str(t450))

print("=== 14. Scheduler ordering is preserved across sequential idle actions ===")
driver14 = RealEngineDriver.for_face()
b14 = IdleExecutionBridge(make_idle(IdleAction.BLINK, 14))
b14.attach(driver14)
seq_log: List[EngineCommand] = []
now14 = 0.0
for action, seed, delay in [
    (IdleAction.BLINK, 141, 0.0),
    (IdleAction.GAZE_DRIFT, 142, 2000.0),
    (IdleAction.MICRO_CORRECTION, 143, 2000.0),
    (IdleAction.BLINK, 144, 2000.0),
]:
    d_a = forced_decision(action, now14, seed)
    b14.execute(d_a, IdleContext(now_ms=now14))
    seq_log.extend(b14.scheduler.advance(delay))
    now14 += delay
check(
    "sequential idle actions keep their order",
    [c.command for c in seq_log] == ["blink", "look_at", "look_at", "blink"],
    str(seq_log),
)
check("micro-correction landed third as look_at(0.5, 0.5)",
      seq_log[2] == EngineCommand("look_at", (0.5, 0.5)))
check("gaze-drift target bounded in sequence",
      all(0.0 <= v <= 1.0 for v in seq_log[1].args))

print("=== 15. EngineCommand ordering is deterministic ===")


def scripted_log() -> List[Tuple[float, EngineCommand]]:
    b = IdleExecutionBridge(make_idle(IdleAction.BLINK, 150))
    log: List[Tuple[float, EngineCommand]] = []
    now = 0.0
    for action, seed, gap in [
        (IdleAction.BLINK, 151, 0.0),
        (IdleAction.GAZE_DRIFT, 152, 2000.0),
        (IdleAction.BLINK, 153, 2000.0),
    ]:
        d_a = forced_decision(action, now, seed)
        b.execute(d_a, IdleContext(now_ms=now))
        cm = b.scheduler.advance(gap)
        t = b.scheduler.timeline.now_ms
        for c in cm:
            log.append((round(t, 3), c))
        now += gap
    return log


check("identical script -> identical command logs",
      scripted_log() == scripted_log(), str(scripted_log()))

print("=== 16. Seeded idle decisions remain deterministic through the pipeline ===")


def seeded_run(seed: int, total_ms: float = 60_000.0):
    memory = BehaviorMemory()
    idle = IdleBehavior(rng=random.Random(seed), memory=memory)
    b = IdleExecutionBridge(idle)
    driver = RealEngineDriver.for_face()
    b.attach(driver)
    decisions: List[Tuple[str, float, str]] = []
    commands: List[Tuple[float, EngineCommand]] = []
    caller_ms = 0.0
    while caller_ms < total_ms:
        dt = caller_ms - b.scheduler.timeline.now_ms
        if dt > 0.0:
            t = b.scheduler.timeline.now_ms + dt
            for c in b.scheduler.advance(dt):
                commands.append((round(t, 3), c))
        ctx = IdleContext(now_ms=caller_ms)
        d = idle.decide(ctx)
        decisions.append((d.action.value, round(d.next_ms, 3), d.reason))
        b.execute(d, ctx)
        t = b.scheduler.timeline.now_ms
        for c in b.scheduler.advance(0.0):
            commands.append((round(t, 3), c))
        nxt = d.next_ms if d.next_ms > caller_ms else caller_ms + 100.0
        caller_ms = nxt
    return decisions, commands


dec_a, cmd_a = seeded_run(99)
dec_b, cmd_b = seeded_run(99)
check("seeded decision sequences identical", dec_a == dec_b)
check("seeded command logs identical", cmd_a == cmd_b)
check("seeded run actually executed idle actions",
      any(cmd[1].command in ("blink", "look_at") for cmd in cmd_a), str(cmd_a[:5]))
check("seeded run contains NONE quiet periods",
      any(act == "none" for act, _, _ in dec_a))

print("=== 17. NONE results in legitimate quiet periods ===")
idle17 = make_idle(IdleAction.NONE, 17)
b17 = IdleExecutionBridge(idle17)
d17a = idle17.decide(IdleContext(now_ms=0.0))
check("first decision is a real NONE quiet decision", d17a.reason == "quiet_period", d17a.reason)
check("quiet period has caller-owned next_ms", d17a.next_ms > 0.0)
b17.execute(d17a, IdleContext(now_ms=0.0))
d17b = idle17.decide(IdleContext(now_ms=d17a.next_ms + 1.0))
check("a later decision is produced after the quiet period",
      d17b.action is IdleAction.NONE and d17b.reason != "not_due", str(d17b))
check("nothing ever scheduled during quiet", b17.scheduler.timeline.is_empty)

print("=== 18. Multiple idle actions execute sequentially on the real engine ===")
driver18 = RealEngineDriver.for_face()
b18 = IdleExecutionBridge(make_idle(IdleAction.BLINK, 18))
b18.attach(driver18)
b18.execute(forced_decision(IdleAction.BLINK, 0.0, 181), IdleContext(now_ms=0.0))
c1 = b18.scheduler.advance(0.0)
b18.apply_commands(c1)
for _ in range(6):
    driver18.engine.step(16.0)
w1 = driver18.engine.mixer.eye_engine._engine.blink_controller.blink_weight
b18.execute(forced_decision(IdleAction.GAZE_DRIFT, 2000.0, 182), IdleContext(now_ms=2000.0))
c2 = b18.scheduler.advance(2000.0)
b18.apply_commands(c2)
for _ in range(50):
    driver18.engine.step(16.0)
gx18, gy18 = driver18.engine.mixer.eye_engine._engine.look_controller.current_normalized
b18.execute(forced_decision(IdleAction.BLINK, 4000.0, 183), IdleContext(now_ms=4000.0))
c3 = b18.scheduler.advance(2000.0)
b18.apply_commands(c3)
for _ in range(6):
    driver18.engine.step(16.0)
w3 = driver18.engine.mixer.eye_engine._engine.blink_controller.blink_weight
check("blink #1 fired", w1 > 0.1, f"{w1:.3f}")
check(
    "gaze drift #2 moved the real gaze",
    len(c2) == 1 and c2[0].command == "look_at"
    and abs(gx18 - c2[0].args[0]) < 0.1 and abs(gy18 - c2[0].args[1]) < 0.1,
    str(c2),
)
check("blink #3 fired after the drift", w3 > 0.1, f"{w3:.3f}")

print("=== 19. Higher-priority behavior can interrupt idle ===")
driver19 = RealEngineDriver.for_face()
b19 = IdleExecutionBridge(make_idle(IdleAction.BLINK, 19))
b19.attach(driver19)
b19.execute(forced_decision(IdleAction.BLINK, 0.0, 191), IdleContext(now_ms=0.0))
out19 = b19.scheduler.advance(0.0)
check("idle blink ran first", out19 == [EngineCommand("blink")], str(out19))
b19.scheduler.schedule(
    BehaviorIntent(behavior_name="greeting", priority=0.9, urgency=1.0, suggested_duration_ms=800.0)
)
check("scheduler active behavior replaced by greeting", b19.scheduler.active_behavior == "greeting")
out19b = b19.scheduler.advance(0.0)
check("greeting executes its plan (interrupts idle)",
      out19b == [EngineCommand("set_state", ("happy", 350.0))], str(out19b))
b19.apply_commands(out19b)
for _ in range(20):
    driver19.engine.step(16.0)
check("engine reached the interrupting behavior's state",
      driver19.engine.current_state == "happy")
out19c = b19.scheduler.advance(500.0)
check("greeting's follow-up blink fires after the idle plan was cleared",
      out19c == [EngineCommand("blink")], str(out19c))

print("=== 20. Recovery to idle works after an action / interruption ===")
driver20 = RealEngineDriver.for_face()
b20 = IdleExecutionBridge(make_idle(IdleAction.BLINK, 20))
b20.attach(driver20)
b20.execute(forced_decision(IdleAction.BLINK, 0.0, 201), IdleContext(now_ms=0.0))
b20.scheduler.advance(0.0)  # blink executes; timeline empty
check("idle plan drained", b20.scheduler.timeline.is_empty)
d20 = make_idle(IdleAction.GAZE_DRIFT, 202).decide(IdleContext(now_ms=3000.0))
scheduled20 = b20.execute(d20, IdleContext(now_ms=3000.0))
check("idle resumes after a completed action", scheduled20 is not None, str(scheduled20))
out20 = b20.scheduler.advance(0.0)
check("resumed idle executes its action",
      out20 and out20[0].command == "look_at", str(out20))
# ...and after an interruption by greeting, a fresh idle decision schedules again.
b20.scheduler.schedule(
    BehaviorIntent(behavior_name="greeting", priority=0.9, urgency=1.0, suggested_duration_ms=800.0)
)
b20.scheduler.advance(0.0)  # greeting replaces idle
b20.scheduler.advance(900.0)  # greeting plan drains
d20b = make_idle(IdleAction.BLINK, 203).decide(IdleContext(now_ms=6000.0))
scheduled20b = b20.execute(d20b, IdleContext(now_ms=6000.0))
out20b = b20.scheduler.advance(0.0)
check("idle resumes after an interruption", scheduled20b is not None and out20b == [EngineCommand("blink")], str(out20b))

print("=== 21. Idle plans never emit set_state (emotion is behavior, not reset) ===")
all_idle_cmds: List[EngineCommand] = []
for action, seed in [
    (IdleAction.BLINK, 211),
    (IdleAction.GAZE_DRIFT, 212),
    (IdleAction.MICRO_CORRECTION, 213),
    (IdleAction.CURIOUS_GLANCE, 214),
]:
    b = IdleExecutionBridge(make_idle(action, seed))
    b.execute(forced_decision(action, 0.0, seed), IdleContext(now_ms=0.0))
    all_idle_cmds.extend(b.scheduler.advance(0.0))
    all_idle_cmds.extend(b.scheduler.advance(600.0))
check("no set_state in any idle plan",
      all(c.command != "set_state" for c in all_idle_cmds), str(all_idle_cmds))
check("idle commands stay within the documented vocabulary",
      set(c.command for c in all_idle_cmds) <= set(get_args(EngineCommandName)))

print("=== 22. Attention is preserved (idle never overwrites a gaze target) ===")
b22 = IdleExecutionBridge(make_idle(IdleAction.GAZE_DRIFT, 22))
ctx_attn = IdleContext(now_ms=0.0, attention_target=(0.5, 0.55))
res = b22.execute(forced_decision(IdleAction.GAZE_DRIFT, 0.0, 221), ctx_attn)
check("gaze drift suppressed while a target exists", res is None and b22.last_skipped_reason == "idle:attention_preserved")
check("no look_at issued for the suppressed drift", b22.scheduler.advance(0.0) == [])
b22c = IdleExecutionBridge(make_idle(IdleAction.CURIOUS_GLANCE, 22))
res2 = b22c.execute(forced_decision(IdleAction.CURIOUS_GLANCE, 0.0, 222), ctx_attn)
check("curious glance suppressed while a target exists", res2 is None)
b22t = IdleExecutionBridge(make_idle(IdleAction.GAZE_DRIFT, 22))
ctx_track = IdleContext(now_ms=0.0, tracking_active=True)
res3 = b22t.execute(forced_decision(IdleAction.GAZE_DRIFT, 0.0, 223), ctx_track)
check("gaze drift suppressed while tracking is active", res3 is None and b22t.last_skipped_reason == "idle:attention_preserved")
b22b = IdleExecutionBridge(make_idle(IdleAction.BLINK, 22))
res4 = b22b.execute(forced_decision(IdleAction.BLINK, 0.0, 224), ctx_attn)
check("BLINK still allowed under attention (blinks never move gaze)", res4 is not None)
b22n = IdleExecutionBridge(make_idle(IdleAction.GAZE_DRIFT, 22))
res5 = b22n.execute(forced_decision(IdleAction.GAZE_DRIFT, 0.0, 225), IdleContext(now_ms=0.0))
check("gaze drift allowed when no target exists (idle is free)", res5 is not None)

print("=== 23. Anti-periodicity / no parallel timers in the integration layer ===")
for token in ("while True", "time.time", "monotonic", "get_ticks", "sleep(", "threading", "Timer(", "Clock("):
    check(f"no '{token}' in idle_execution.py", token not in inspect.getsource(_ie))

print()
print("=== 24. End-to-end deterministic scenario through the real scheduler+driver ===")
print("      calm -> idle NONE -> idle BLINK -> idle GAZE_DRIFT -> idle NONE")
print("            -> GREETING interrupts -> idle resumes (BLINK) ===")
driver_e2e = RealEngineDriver.for_face()
driver_e2e.set_state("calm", 300.0)
driver_e2e.engine.step(50.0)
bridge_e2e = IdleExecutionBridge(make_idle(IdleAction.BLINK, 9001))
bridge_e2e.attach(driver_e2e)
e2e_log: List[Tuple[float, EngineCommand]] = []
now_e2e = 0.0
gaze_decision: Optional[IdleDecision] = None


def e2e_advance(target_ms: float) -> List[EngineCommand]:
    """Advance the scheduler clock to ``target_ms`` and apply due commands."""
    global now_e2e
    dt = max(0.0, target_ms - now_e2e)
    now_e2e = max(now_e2e, target_ms)
    t = bridge_e2e.scheduler.timeline.now_ms
    cmds = bridge_e2e.scheduler.advance(dt)
    for c in cmds:
        e2e_log.append((round(t + dt, 3), c))
    bridge_e2e.apply_commands(cmds)
    return cmds


def e2e_idle_phase(action: IdleAction, at_ms: float, seed: int) -> IdleDecision:
    """Advance to ``at_ms``, decide the wanted action, schedule + fire it."""
    global gaze_decision
    e2e_advance(at_ms)
    d = make_idle(action, seed).decide(IdleContext(now_ms=at_ms))
    if action is IdleAction.GAZE_DRIFT:
        gaze_decision = d
    bridge_e2e.execute(d, IdleContext(now_ms=at_ms))
    t = bridge_e2e.scheduler.timeline.now_ms
    due = bridge_e2e.scheduler.advance(0.0)
    for c in due:
        e2e_log.append((round(t, 3), c))
    bridge_e2e.apply_commands(due)
    return d


check("engine starts calm", driver_e2e.engine.current_state == "calm")
# 1) idle NONE -> quiet (nothing scheduled)
d1 = e2e_idle_phase(IdleAction.NONE, 0.0, 901)
check("phase 1: idle decision is NONE", d1.action is IdleAction.NONE, str(d1))
# 2) idle BLINK -> scheduler -> real engine blink
d2 = e2e_idle_phase(IdleAction.BLINK, 1000.0, 902)
check("phase 2: idle decision is BLINK", d2.action is IdleAction.BLINK)
for _ in range(6):
    driver_e2e.engine.step(16.0)
bw_e2e = driver_e2e.engine.mixer.eye_engine._engine.blink_controller.blink_weight
check("phase 2: real engine blinked", bw_e2e > 0.1, f"{bw_e2e:.3f}")
check("phase 2: engine state still calm (emotion preserved)",
      driver_e2e.engine.current_state == "calm")
# 3) idle GAZE_DRIFT -> scheduler -> real engine look_at
d3 = e2e_idle_phase(IdleAction.GAZE_DRIFT, 3000.0, 903)
check("phase 3: idle decision is GAZE_DRIFT", d3.action is IdleAction.GAZE_DRIFT)
for _ in range(60):
    driver_e2e.engine.step(16.0)
lx_e2e, ly_e2e = driver_e2e.engine.mixer.eye_engine._engine.look_controller.current_normalized
assert gaze_decision is not None
want = idle_look_target(gaze_decision)
check("phase 3: real engine gaze reached the idle target",
      abs(lx_e2e - want[0]) < 0.08 and abs(ly_e2e - want[1]) < 0.08,
      f"({lx_e2e:.2f},{ly_e2e:.2f}) vs ({want[0]:.2f},{want[1]:.2f})")
check("phase 3: engine state still calm (idle is not an emotional reset)",
      driver_e2e.engine.current_state == "calm")
# 4) idle NONE -> recovery / quiet
d4 = e2e_idle_phase(IdleAction.NONE, 5000.0, 904)
check("phase 4: idle NONE (quiet recovery)", d4.action is IdleAction.NONE)
# 5) interruption: higher-priority greeting appears and executes
e2e_advance(7000.0)
bridge_e2e.scheduler.schedule(
    BehaviorIntent(behavior_name="greeting", priority=0.9, urgency=1.0, suggested_duration_ms=800.0)
)
due5 = bridge_e2e.scheduler.advance(0.0)
for c in due5:
    e2e_log.append((round(7000.0, 3), c))
bridge_e2e.apply_commands(due5)
# greeting's follow-up blink fires at 7500 on its own timeline step
e2e_advance(7500.0)
for _ in range(20):
    driver_e2e.engine.step(16.0)
check("phase 5: greeting displaced idle", bridge_e2e.scheduler.active_behavior == "greeting")
check("phase 5: engine entered the interrupting behavior's state",
      driver_e2e.engine.current_state == "happy")
# 6) recovery to idle: a fresh idle decision schedules and executes again
d6 = e2e_idle_phase(IdleAction.BLINK, 9000.0, 906)
check("phase 6: idle decision resumes after interruption", d6.action is IdleAction.BLINK)
for _ in range(6):
    driver_e2e.engine.step(16.0)
bw6 = driver_e2e.engine.mixer.eye_engine._engine.blink_controller.blink_weight
check("phase 6: idle blink executed after recovery", bw6 > 0.1, f"{bw6:.3f}")
check("phase 6: idle did NOT reset the emotion (still happy)",
      driver_e2e.engine.current_state == "happy")

expected_e2e = [
    (1000.0, EngineCommand("blink")),
    (3000.0, EngineCommand("look_at", (want[0], want[1]))),
    (7000.0, EngineCommand("set_state", ("happy", 350.0))),
    (7500.0, EngineCommand("blink")),
    (9000.0, EngineCommand("blink")),
]
check(
    "full e2e command log is exactly the expected sequence",
    e2e_log == expected_e2e,
    str(e2e_log),
)
check(
    "e2e idle commands are blink/look_at only (greeting owns the only set_state)",
    all(c.command != "set_state" or (t, c) == expected_e2e[2] for t, c in e2e_log),
)

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL LES-09A.2 CHECKS PASSED")
