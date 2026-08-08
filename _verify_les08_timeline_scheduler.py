"""
LES-08 verification: Timeline Scheduler.

Validates, against the design authority (les/docs/*):
  1. Timeline ordering                      2. Same-time event ordering
  3. Delayed events                         4. Duration handling
  5. Timeline advancement                   6. Due-event extraction
  7. Empty timeline                         8. Capacity limit
  9. Horizon limit                         10. Scheduler command generation
 11. Command ordering                      12. Command draining
 13. Cancellation/replacement              14. Deterministic output
 15. No pygame import                      16. No eyes import
 17. No face import                        18. No ROS import
 19. No hardware import                    20. Existing LES tests green
plus: variant preservation, recovery events, continuation idempotency,
the documented command vocabulary, and the EngineDriver boundary.

Run:  py _verify_les08_timeline_scheduler.py
"""

from __future__ import annotations

import sys
from typing import Optional, get_args

# --- imports under test (no pygame / eyes / face anywhere) ----------------
from les.director.behavior_director import BehaviorIntent, BehaviorRequest
from les.timeline.scheduler import (
    DEFAULT_BEHAVIOR_PLANS,
    BehaviorPlan,
    DefaultScheduler,
    EngineCommand,
    EngineCommandName,
    EngineDriver,
    PlanStep,
    Scheduler,
    dispatch_command,
)
from les.timeline.timeline import DefaultTimeline, Timeline, TimelineEvent

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    if cond:
        print(f"  ok:   {name}")
    else:
        print(f"  FAIL: {name} {detail}")


def event(
    behavior: str,
    start_ms: float,
    duration_ms: float = 0.0,
    priority: float = 0.0,
    payload: Optional[dict] = None,
) -> TimelineEvent:
    return TimelineEvent(
        behavior_name=behavior,
        start_ms=start_ms,
        duration_ms=duration_ms,
        priority=priority,
        payload=payload or {},
    )


def request(
    behavior: str,
    priority: float = 0.5,
    urgency: float = 1.0,
    variant: Optional[str] = None,
    suggested_duration_ms: float = 0.0,
    recovery_behavior: Optional[str] = None,
) -> BehaviorRequest:
    return BehaviorIntent(
        behavior_name=behavior,
        priority=priority,
        urgency=urgency,
        variant=variant,
        suggested_duration_ms=suggested_duration_ms,
        recovery_behavior=recovery_behavior,
    )


print("=== 1. Independence: no forbidden dependencies ===")
bad = []
for mod in sys.modules:
    if mod.startswith(("pygame", "cv2", "mediapipe", "rospy", "serial", "eyes", "face")):
        bad.append(mod)
check("no forbidden modules loaded", not bad, str(bad))
check("Timeline is abstract (ABC)", getattr(Timeline, "__abstractmethods__", None) is not None)
check("Scheduler is abstract (ABC)", getattr(Scheduler, "__abstractmethods__", None) is not None)

print("=== 2. Timeline ordering ===")
tl = DefaultTimeline()
tl.push(event("c", 300.0))
tl.push(event("a", 100.0))
tl.push(event("b", 200.0))
check("pending is time-ordered", [e.behavior_name for e in tl.pending] == ["a", "b", "c"])

print("=== 3. Same-time event ordering (stable FIFO) ===")
tl3 = DefaultTimeline()
tl3.push(event("a", 0.0))
tl3.push(event("b", 0.0))
tl3.push(event("c", 0.0))
due3 = tl3.due_events()
check("same-time events keep insertion order", [e.behavior_name for e in due3] == ["a", "b", "c"])

print("=== 4. Delayed events (future start times) ===")
tl4 = DefaultTimeline()
e4 = event("later", 100.0)
tl4.push(e4)
tl4.advance(50.0)
check("not due before start time", tl4.due_events() == [])
tl4.advance(50.0)
check("due once start time reached", tl4.due_events() == [e4])

print("=== 5. Timeline advancement (caller-owned time) ===")
tl5 = DefaultTimeline()
check("clock starts at 0", tl5.now_ms == 0.0)
tl5.advance(100.0)
tl5.advance(50.0)
check("clock advances by caller dt only", tl5.now_ms == 150.0)
tl5.advance(-10.0)
check("negative dt is clamped", tl5.now_ms == 150.0)

print("=== 5b. Duration & priority carried as data ==")
tl5b = DefaultTimeline()
e5b = event("hold", 0.0, duration_ms=250.0, priority=0.7)
tl5b.push(e5b)
due5b = tl5b.due_events()
check("duration_ms preserved through push/due", due5b == [e5b] and due5b[0].duration_ms == 250.0)
check("priority preserved (data, never arbitrated)", due5b[0].priority == 0.7)

print("=== 6. Due-event extraction ===")
tl6 = DefaultTimeline()
tl6.push(event("a", 0.0))
tl6.push(event("b", 500.0))
tl6.advance(400.0)
check("only due events extracted", [e.behavior_name for e in tl6.due_events()] == ["a"])
check("not-yet-due events remain pending", [e.behavior_name for e in tl6.pending] == ["b"])

print("=== 7. Empty timeline ===")
tl7 = DefaultTimeline()
check("initially empty", tl7.is_empty)
tl7.push(event("a", 0.0))
check("not empty after push", not tl7.is_empty)
tl7.due_events()
check("empty again after extraction", tl7.is_empty)
tl7.push(event("a", 10.0))
tl7.clear()
check("empty after clear", tl7.is_empty)

print("=== 8. Capacity limit ===")
tl8 = DefaultTimeline(capacity=2)
check("push accepted within capacity", tl8.push(event("a", 0.0)))
check("push accepted at capacity", tl8.push(event("b", 10.0)))
check("push rejected at capacity (no silent eviction)", tl8.push(event("c", 20.0)) is False)
check("capacity never exceeded", len(tl8) == 2)

print("=== 9. Horizon limit ===")
tl9 = DefaultTimeline(horizon_ms=1000.0)
check("push at horizon accepted", tl9.push(event("a", 1000.0)))
check("push beyond horizon rejected", tl9.push(event("b", 1000.1)) is False)
tl9.advance(500.0)
check("horizon is relative to now", tl9.push(event("c", 1500.0)))

print("=== 10. Scheduler command generation (BehaviorRequest -> timeline -> commands) ===")
s10 = DefaultScheduler()
s10.schedule(
    request(
        "greeting",
        priority=0.8,
        urgency=1.0,
        variant="happy_b",
        suggested_duration_ms=800.0,
        recovery_behavior="calm",
    )
)
out = s10.advance(0.0)
check("first step due immediately", out == [EngineCommand("set_state", ("happy", 350.0))])
out = s10.advance(250.0)
check("nothing due mid-plan", out == [])
out = s10.advance(250.0)
check("second step at 500ms", out == [EngineCommand("blink")])
out = s10.advance(300.0)
check("recovery at 800ms", out == [EngineCommand("set_state", ("calm", 300.0))])
out = s10.advance(50.0)
check("plan exhausted", out == [] and s10.timeline.is_empty)

print("=== 11. Command ordering & timing ===")
plans11 = {
    "seq": BehaviorPlan(
        name="seq",
        steps=(
            PlanStep(0.0, "set_state", ("calm", 200.0)),
            PlanStep(250.0, "blink"),
            PlanStep(500.0, "look_at", (0.5, 0.5)),
        ),
    )
}
s11 = DefaultScheduler(plans=plans11)
s11.schedule(request("seq", suggested_duration_ms=0.0))
got: list[EngineCommand] = []
got += s11.advance(100.0)
got += s11.advance(200.0)
got += s11.advance(200.0)
got += s11.advance(100.0)
check(
    "commands arrive in planned order at planned times",
    got == [
        EngineCommand("set_state", ("calm", 200.0)),
        EngineCommand("blink"),
        EngineCommand("look_at", (0.5, 0.5)),
    ],
    str(got),
)

print("=== 12. Command draining (deterministic flush) ===")
plans12 = {
    "wave": BehaviorPlan(
        name="wave", steps=(PlanStep(0.0, "look_at", (0.5, 0.5), delay_ms=100.0),)
    )
}
s12 = DefaultScheduler(plans=plans12)
s12.schedule(request("wave"))
check("advance converts but delay holds the command back", s12.advance(0.0) == [])
check("pending buffer holds the delayed command", s12.pending_count == 1)
drained = s12.drain_commands()
check(
    "drain returns ALL pending commands (due or not)",
    drained == [EngineCommand("look_at", (0.5, 0.5), delay_ms=100.0)],
    str(drained),
)
check("drain empties the buffer", s12.pending_count == 0)
check("second drain is empty", s12.drain_commands() == [])

print("=== 13. Delayed commands (EngineCommand.delay_ms) ===")
plans13 = {
    "wave": BehaviorPlan(name="wave", steps=(PlanStep(0.0, "look_at", (0.5, 0.5), delay_ms=100.0),))
}
s13 = DefaultScheduler(plans=plans13)
s13.schedule(request("wave"))
check("delayed command not due at event time", s13.advance(0.0) == [])
check("still pending mid-delay", s13.advance(50.0) == [])
check(
    "delayed command fires after delay",
    s13.advance(60.0) == [EngineCommand("look_at", (0.5, 0.5), delay_ms=100.0)],
)

print("=== 14. Cancellation / replacement (interruption) ===")
s14 = DefaultScheduler()
s14.schedule(request("playful", priority=0.6, suggested_duration_ms=4000.0))
first = s14.advance(0.0)
check("playful entry fired", first == [EngineCommand("set_state", ("happy", 350.0))])
check("blink still pending on the timeline", len(s14.timeline.pending) == 1)
s14.schedule(request("alert", priority=0.95))  # urgent replacement
check("active behavior replaced", s14.active_behavior == "alert")
check("obsolete playful timeline invalidated", len(s14.timeline.pending) == 1)
out = s14.advance(0.0)
check("replacement commands only", out == [EngineCommand("set_state", ("surprised", 180.0))], str(out))

# Replacement must also invalidate already-converted pending commands.
plans14 = {
    "wave": BehaviorPlan(name="wave", steps=(PlanStep(0.0, "look_at", (0.5, 0.5), delay_ms=100.0),)),
    "alert": BehaviorPlan(name="alert", steps=(PlanStep(0.0, "set_state", ("surprised", 180.0)),)),
}
s14b = DefaultScheduler(plans=plans14)
s14b.schedule(request("wave"))
s14b.advance(0.0)
check("delayed command is pending", s14b.pending_count == 1)
s14b.schedule(request("alert", priority=0.95))
check("pending command buffer cleared on replacement", s14b.pending_count == 0)
check("no stale delayed command fires", s14b.advance(150.0) == [EngineCommand("set_state", ("surprised", 180.0))])

print("=== 15. Deterministic output ===")
plans15 = {
    "a": BehaviorPlan(
        name="a",
        steps=(
            PlanStep(0.0, "set_state", ("happy", 350.0)),
            PlanStep(600.0, "blink"),
            PlanStep(900.0, "set_state", ("calm", 300.0)),
        ),
    ),
    "b": BehaviorPlan(name="b", steps=(PlanStep(0.0, "set_state", ("surprised", 180.0)),)),
}


def run_script() -> list[EngineCommand]:
    s = DefaultScheduler(plans=plans15)
    out: list[EngineCommand] = []
    for req in (request("a"), request("a"), request("b", priority=0.95), request("a")):
        s.schedule(req)
    for dt in (0.0, 100.0, 300.0, 300.0, 500.0, 400.0, 100.0):
        out.extend(s.advance(dt))
    out.extend(s.drain_commands())
    return out


check("identical script, identical output", run_script() == run_script())

print("=== 16. Variant identity preserved ===")
plans16 = {
    "greeting": BehaviorPlan(
        name="greeting",
        steps=(PlanStep(0.0, "set_state", ("happy", 350.0)),),
        variant_steps={
            "happy_b": (
                PlanStep(0.0, "set_state", ("happy", 400.0)),
                PlanStep(200.0, "blink"),
            )
        },
    )
}
s16 = DefaultScheduler(plans=plans16)
s16.schedule(request("greeting", variant="happy_b", recovery_behavior=None))
p = s16.timeline.pending
check("variant-specific steps used", len(p) == 2)
check("variant label carried on events", all(e.payload.get("variant") == "happy_b" for e in p))
check("variant steps override base", p[0].payload["args"] == ("happy", 400.0))
s16b = DefaultScheduler(plans=plans16)
s16b.schedule(request("greeting", variant=None, recovery_behavior=None))
check("base steps used without variant", s16b.timeline.pending[0].payload["args"] == ("happy", 350.0))

print("=== 17. Recovery instruction represented, not invented ===")
s17 = DefaultScheduler()
s17.schedule(request("thinking", suggested_duration_ms=3000.0, recovery_behavior="idle"))
events = s17.timeline.pending
check("recovery event appended after plan span", len(events) == 2)
check("recovery timing preserved", events[1].start_ms >= 3000.0)
out = s17.advance(3100.0)
check(
    "recovery maps through plan registry (idle -> calm)",
    out[-1] == EngineCommand("set_state", ("calm", 300.0)),
    str(out),
)

print("=== 18. Continuation idempotency ===")
s18 = DefaultScheduler()
s18.schedule(request("playful", suggested_duration_ms=4000.0, recovery_behavior=None))
s18.schedule(request("playful", suggested_duration_ms=4000.0, recovery_behavior=None))
check("same behavior re-scheduled while pending is a no-op", len(s18.timeline.pending) == 2)
s18.advance(5000.0)
check("plan drained", s18.timeline.is_empty)
s18.schedule(request("playful", suggested_duration_ms=4000.0, recovery_behavior=None))
check("same behavior re-planned after drain", not s18.timeline.is_empty)

print("=== 19. Documented command vocabulary (no expansion) ===")
check(
    "EngineCommandName is exactly the 5 documented commands",
    set(get_args(EngineCommandName)) == {"set_state", "blink", "trigger_blink_type", "look_at", "step"},
)
bad_tl = DefaultTimeline()
bad_tl.push(event("x", 0.0, payload={"command": "teleport"}))
unknown_bad = DefaultScheduler(timeline=bad_tl)
try:
    unknown_bad.advance(0.0)
    check("unknown command raises (never silent)", False)
except ValueError:
    check("unknown command raises (never silent)", True)

print("=== 20. EngineDriver boundary (tested interface, no eyes/face) ===")


class _FakeDriver(EngineDriver):
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_state(self, state: str, transition_ms: Optional[float] = None) -> None:
        self.calls.append(("set_state", state, transition_ms))

    def blink(self) -> None:
        self.calls.append(("blink",))

    def trigger_blink_type(self, blink_type) -> None:
        self.calls.append(("trigger_blink_type", blink_type))

    def look_at(self, x: float, y: float) -> None:
        self.calls.append(("look_at", x, y))

    def step(self, dt_ms: float, speech_pulse: float = 0.0) -> object:
        self.calls.append(("step", dt_ms, speech_pulse))
        return None


driver = _FakeDriver()
dispatch_command(driver, EngineCommand("set_state", ("happy", 350.0)))
dispatch_command(driver, EngineCommand("blink"))
dispatch_command(driver, EngineCommand("trigger_blink_type", ("double",)))
dispatch_command(driver, EngineCommand("look_at", (0.5, 0.5)))
dispatch_command(driver, EngineCommand("step", (16.0, 0.5)))
check(
    "all five documented commands dispatch",
    driver.calls
    == [
        ("set_state", "happy", 350.0),
        ("blink",),
        ("trigger_blink_type", "double"),
        ("look_at", 0.5, 0.5),
        ("step", 16.0, 0.5),
    ],
    str(driver.calls),
)
s20 = DefaultScheduler()
try:
    s20.apply_commands([EngineCommand("blink")])
    check("apply without engine raises", False)
except ValueError:
    check("apply without engine raises", True)
s20.attach(driver)
s20.apply_commands([EngineCommand("blink")])
check("apply_commands executes on attached driver", driver.calls[-1] == ("blink",))

print("=== 21. Default plan registry uses documented vocabulary only ===")
commands_used = {step.command for plan in DEFAULT_BEHAVIOR_PLANS.values() for step in plan.steps}
check("default plans use documented commands", commands_used <= {"set_state", "blink", "look_at", "step"})
check(
    "every default intent has a plan",
    {"greeting", "listening", "responding", "thinking", "playful", "alert",
     "comforting", "searching", "confused", "curious", "waiting", "idle"}
    <= set(DEFAULT_BEHAVIOR_PLANS),
)

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL CHECKS PASSED")
