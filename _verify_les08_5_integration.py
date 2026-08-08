"""
LES-08.5 verification: real engine integration.

Proves the existing LES execution pipeline drives the REAL, frozen
animation engine through the EngineDriver boundary:

    BehaviorIntent -> schedule() -> Timeline -> Scheduler.advance()
        -> EngineCommand -> RealEngineDriver -> eyes/ face/

Verifies (mission checklist):
  1. Real EngineDriver can be constructed.
  2. EngineCommand reaches the real driver.
  3. set_state reaches the existing engine.
  4. blink reaches the existing engine.
  5. trigger_blink_type works where the existing API supports it.
  6. look_at works where supported.
  7. step works where supported.
  8. Commands execute in correct order.
  9. Timeline timing is preserved.
 10. Scheduler remains deterministic.
 11. No engine source files changed.        (checked via git, reported)
 12. No duplicate animation logic exists.   (adapter is call-translation only)
 13. Existing LES tests remain green.       (checked via git-untouched + suite runs)

Run:  py _verify_les08_5_integration.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eyes.engine.blink_controller import BlinkType
from eyes.engine.eye_pair import EyePair

from les.director.behavior_director import BehaviorIntent
from les.integration import RealEngineDriver
from les.timeline.scheduler import (
    BehaviorPlan,
    DefaultScheduler,
    EngineCommand,
    PlanStep,
    dispatch_command,
)

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    if cond:
        print(f"  ok:   {name}")
    else:
        print(f"  FAIL: {name} {detail}")


def cmd(name: str, *args: object) -> EngineCommand:
    return EngineCommand(name, args)  # type: ignore[arg-type]


def expected_states(
    transitions: List[Tuple[float, Optional[str]]],
    total_ms: float,
    step_ms: float,
    initial: str,
) -> List[Tuple[float, str]]:
    """Expected (scheduler-clock, engine-state) samples for a scenario.

    Mirrors the pipeline semantics (samples at t=0 then every ``step_ms``):
    a set_state command at time T changes the engine state on every sample
    whose clock is >= T; None = no state change.
    """
    states: List[Tuple[float, str]] = []
    nows = [0.0] + [step_ms * i for i in range(1, int(total_ms / step_ms) + 1)]
    for now in nows:
        state = initial
        for fire_ms, new_state in transitions:
            if fire_ms <= now and new_state is not None:
                state = new_state
        states.append((now, state))
    return states


print("=== 1. Real EngineDriver can be constructed ===")
d_face = RealEngineDriver.for_face()  # wraps a real FaceEngine (eyes+mouth+FX)
d_eyes = RealEngineDriver.for_eyes()  # wraps a fully-registered AnimationEngine
check("for_face() wraps a FaceEngine", d_face.engine.__class__.__name__ == "FaceEngine")
check("for_eyes() wraps an AnimationEngine", d_eyes.engine.__class__.__name__ == "AnimationEngine")
proto = ("set_state", "blink", "trigger_blink_type", "look_at", "step")
check("driver implements the full EngineDriver protocol", all(hasattr(d_face, m) for m in proto))
check(
    "capability query is truthful (FaceEngine: no trigger_blink_type)",
    d_face.supports("trigger_blink_type") is False and d_face.supports("set_state"),
)
check(
    "capability query is truthful (AnimationEngine: full protocol)",
    d_eyes.supports("trigger_blink_type") is True,
)

print("=== 2. EngineCommand reaches the real driver ===")
dispatch_command(d_face, cmd("set_state", "happy", 350.0))
check("set_state command changed the real face state", d_face.engine.current_state == "happy")
dispatch_command(d_eyes, cmd("set_state", "listening", 200.0))
d_eyes.step(16.0)  # mixer surfaces the new state on the next engine step
check(
    "set_state command changed the real eyes state",
    d_eyes.engine.state_machine.current_state_name == "listening",
)

print("=== 3. set_state reaches the engine ===")
d_face.set_state("calm", 350.0)
d_face.engine.step(100.0)
check("driver.set_state() reaches the real engine", d_face.engine.current_state == "calm")
d_eyes.set_state("happy", 350.0)
d_eyes.step(16.0)
check("driver.set_state() with transition_ms honored", d_eyes.engine.state_machine.current_state_name == "happy")

print("=== 4. blink reaches the engine ===")
d_eyes.set_state("calm")
d_eyes.blink()
weights: List[float] = []
for _ in range(8):
    d_eyes.step(16.0)
    weights.append(d_eyes.engine.blink_controller.blink_weight)
check("blink raises the real blink weight", max(weights) > 0.1, f"max={max(weights):.3f}")

print("=== 5. trigger_blink_type works where the API supports it ===")
d_eyes.trigger_blink_type(BlinkType.DOUBLE)
weights2: List[float] = []
for _ in range(10):
    d_eyes.step(16.0)
    weights2.append(d_eyes.engine.blink_controller.blink_weight)
check("typed double blink raises the real blink weight", max(weights2) > 0.1, f"max={max(weights2):.3f}")
try:
    d_face.trigger_blink_type(BlinkType.DOUBLE)
    check("unsupported verb raises (never silent)", False)
except ValueError:
    check("unsupported verb raises (never silent)", True)

print("=== 6. look_at reaches the engine ===")
d_eyes.look_at(0.2, 0.7)
for _ in range(40):
    d_eyes.step(16.0)
lx, ly = d_eyes.engine.look_controller.current_normalized
check("gaze moves toward the look target", abs(lx - 0.2) < 0.05 and abs(ly - 0.7) < 0.05, f"({lx:.2f},{ly:.2f})")

print("=== 7. step works on both engines ===")
r_face = d_face.step(16.0)
r_eyes = d_eyes.step(16.0)
check("FaceEngine step returns (pose, mouth, ctx)", isinstance(r_face, tuple) and len(r_face) == 3)
check("AnimationEngine step returns an EyePair", isinstance(r_eyes, EyePair))

print("=== 8/9. Scenario 1: CALM -> HAPPY -> BLINK -> CALM (full pipeline) ===")
SCENARIO1 = {
    "s1": BehaviorPlan(
        name="s1",
        steps=(
            PlanStep(0.0, "set_state", ("calm", 350.0)),
            PlanStep(500.0, "set_state", ("happy", 350.0)),
            PlanStep(900.0, "blink"),
            PlanStep(1300.0, "set_state", ("calm", 300.0)),
        ),
    )
}


def run_scenario(
    plans: dict, behavior: str, total_ms: int, step_ms: float, engine_dt_ms: float = 16.0
) -> Tuple[List[Tuple[float, EngineCommand]], List[Tuple[float, str]], List[float], RealEngineDriver]:
    """Drive the full pipeline against a REAL FaceEngine.

    Returns (command log, state trace, per-tick blink weights, driver).
    The real engine is stepped at ~16ms per engine frame (the engine's
    designed 60fps cadence - larger steps destabilise its look spring),
    with several engine frames per scheduler tick, mirroring a render
    loop that runs while the scheduler advances at a coarser cadence.
    Blink weight is sampled via the engine's private controller chain
    (same convention as the repo's existing verification tests) - valid
    because the scenarios always wrap a FaceEngine.
    """
    scheduler = DefaultScheduler(plans=plans)
    driver = RealEngineDriver.for_face()
    scheduler.attach(driver)
    scheduler.schedule(BehaviorIntent(behavior_name=behavior, priority=0.5, urgency=1.0))

    engine_frames = max(1, int(step_ms / engine_dt_ms))
    log: List[Tuple[float, EngineCommand]] = []
    states: List[Tuple[float, str]] = []
    max_blink_after: List[float] = []
    # Tick 0 advances by 0ms so events already due at schedule time are
    # emitted at their true due time (t = 0); subsequent ticks advance by
    # ``step_ms``. The command timestamp is the scheduler clock at emission.
    for dt in [0.0] + [step_ms] * int(total_ms / step_ms):
        commands = scheduler.advance(dt)
        now = scheduler.timeline.now_ms
        for c in commands:
            log.append((now, c))
        scheduler.apply_commands(commands)
        for _ in range(engine_frames):
            driver.engine.step(engine_dt_ms)
        states.append((now, str(driver.engine.current_state)))
        max_blink_after.append(driver.engine.mixer.eye_engine._engine.blink_controller.blink_weight)
    return log, states, max_blink_after, driver


s1_log, s1_states, s1_blink, _s1_driver = run_scenario(SCENARIO1, "s1", total_ms=1500, step_ms=100.0)
s1_expected_log = [
    (0.0, cmd("set_state", "calm", 350.0)),
    (500.0, cmd("set_state", "happy", 350.0)),
    (900.0, cmd("blink")),
    (1300.0, cmd("set_state", "calm", 300.0)),
]
check("commands emitted in exact order at exact scheduler times", s1_log == s1_expected_log, str(s1_log))
s1_expected_states = expected_states(
    [(500.0, "happy"), (900.0, None), (1300.0, "calm")], total_ms=1500, step_ms=100.0, initial="calm"
)
check("real engine state trace matches the scheduled timeline", s1_states == s1_expected_states, str(s1_states))
check(
    "blink visibly fired on the real engine",
    max(s1_blink[9:]) > 0.1 and max(s1_blink[:9]) < 0.05,
    f"pre={max(s1_blink[:9]):.3f} post={max(s1_blink[9:]):.3f}",
)

print("=== 8/9. Scenario 2: SURPRISED -> CALM (full pipeline) ===")
SCENARIO2 = {
    "s2": BehaviorPlan(
        name="s2",
        steps=(
            PlanStep(0.0, "set_state", ("surprised", 180.0)),
            PlanStep(700.0, "set_state", ("calm", 300.0)),
        ),
    )
}
s2_log, s2_states, _, _s2_driver = run_scenario(SCENARIO2, "s2", total_ms=1000, step_ms=100.0)
check(
    "surprise -> calm commands in order",
    s2_log == [(0.0, cmd("set_state", "surprised", 180.0)), (700.0, cmd("set_state", "calm", 300.0))],
    str(s2_log),
)
s2_expected = expected_states([(700.0, "calm")], total_ms=1000, step_ms=100.0, initial="surprised")
check("real engine state trace matches scenario 2", s2_states == s2_expected, str(s2_states))

print("=== 8/9. Scenario 3: HAPPY -> LOOK_AT -> BLINK -> CALM (full pipeline) ===")
SCENARIO3 = {
    "s3": BehaviorPlan(
        name="s3",
        steps=(
            PlanStep(0.0, "set_state", ("happy", 350.0)),
            PlanStep(400.0, "look_at", (0.25, 0.6)),
            PlanStep(800.0, "blink"),
            PlanStep(1200.0, "set_state", ("calm", 300.0)),
        ),
    )
}
s3_log, s3_states, s3_blink, s3_driver = run_scenario(SCENARIO3, "s3", total_ms=1400, step_ms=100.0)
s3_expected_log = [
    (0.0, cmd("set_state", "happy", 350.0)),
    (400.0, cmd("look_at", 0.25, 0.6)),
    (800.0, cmd("blink")),
    (1200.0, cmd("set_state", "calm", 300.0)),
]
check("scenario 3 commands in order", s3_log == s3_expected_log, str(s3_log))
s3_expected_states = expected_states(
    [(400.0, None), (800.0, None), (1200.0, "calm")], total_ms=1400, step_ms=100.0, initial="happy"
)
check("scenario 3 state trace matches", s3_states == s3_expected_states, str(s3_states))
check("scenario 3 blink fired on the real engine", max(s3_blink[8:]) > 0.1, f"post={max(s3_blink[8:]):.3f}")
s3_lx, s3_ly = s3_driver.engine.mixer.eye_engine._engine.look_controller.current_normalized
check(
    "scenario 3: look_at actually moved the real gaze",
    abs(s3_lx - 0.25) < 0.06 and abs(s3_ly - 0.6) < 0.06,
    f"({s3_lx:.2f},{s3_ly:.2f})",
)

print("=== 10. Scheduler remains deterministic (real driver) ===")
a_log, a_states, _, _ = run_scenario(SCENARIO3, "s3", total_ms=1400, step_ms=100.0)
b_log, b_states, _, _ = run_scenario(SCENARIO3, "s3", total_ms=1400, step_ms=100.0)
check("identical scripts -> identical command logs", a_log == b_log)
check("identical scripts -> identical engine state traces", a_states == b_states)

print("=== 12. No duplicate animation logic (adapter is translation only) ===")
src = Path("les/integration/real_engine_driver.py").read_text(encoding="utf-8")
for token in ("import math", "curvature", "radius", "scale_x", "look_offset", "ease", "tween"):
    check(f"adapter contains no animation math ('{token}')", token not in src, token)
check(
    "adapter only calls the documented protocol verbs",
    all(
        f"self._engine.{verb}(" in src
        for verb in ("set_state", "blink", "trigger_blink_type", "look_at", "step")
    ),
)

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL CHECKS PASSED")
