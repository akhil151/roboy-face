"""
LES-09A.1 - Natural Idle Decision Layer verification suite.

Verifies the idle DECISION layer (les/behaviors/idle_policy.py +
les/behaviors/idle_behavior.py) against the phase requirements:

    * the three idle tiers exist and are selected from context
    * idle can legitimately choose NONE (nothing happens is valid)
    * idle NEVER overrides active high-priority behavior / interaction
    * idle respects emotion (happy/sad/sleepy/surprised), attention,
      speaking, and touch context
    * anti-periodicity: bounded uniform-random bands, no fixed periodic
      timer, quiet periods, no immediate repetition of non-blink actions
    * randomness is injectable and seeded execution is deterministic
    * cooldowns (BehaviorMemory) and personality (PersonalityTraits) are
      respected
    * no wall-clock APIs and no forbidden imports (pygame/eyes/face/ROS/
      hardware) anywhere in the idle modules

Run:  py _verify_les09a_idle.py
"""

from __future__ import annotations

import inspect
import random

from les.behaviors import (
    IdleAction,
    IdleBehavior,
    IdleContext,
    IdleDecision,
    IdlePolicy,
    IdleTier,
)
from les.memory.behavior_memory import BehaviorMemory
from les.personality.traits import PersonalityTraits
from les.world.interaction_state import InteractionMode

CHECKS = 0


def ok() -> None:
    global CHECKS
    CHECKS += 1


def simulate(
    idle: IdleBehavior,
    horizon_ms: float,
    *,
    emotion=None,
    traits=None,
    mode=None,
    eye_contact: bool = False,
    active_behavior=None,
    last_interaction_ms: float = 0.0,
):
    """Drive the idle behavior with caller-supplied time only.

    The caller asks for a decision, honors ``next_ms`` (the quiet period),
    and re-asks exactly when due - mirroring how LES-09A.2 will consume it.
    """
    traits = traits if traits is not None else PersonalityTraits()
    out = []
    now = 0.0
    while now < horizon_ms:
        ctx = IdleContext(
            now_ms=now,
            emotion=emotion,
            traits=traits,
            interaction_mode=mode,
            eye_contact=eye_contact,
            active_behavior=active_behavior,
            last_interaction_ms=last_interaction_ms,
        )
        d = idle.decide(ctx)
        out.append(d)
        now = d.next_ms if d.next_ms > now else now + 1.0
    return out


def non_none(decisions):
    return [d for d in decisions if d.action is not IdleAction.NONE]


def seq_key(decisions):
    return [(d.action, round(d.next_ms, 3), d.tier, d.reason) for d in decisions]


# ---------------------------------------------------------------------------
print("=== 1. Idle tiers exist (behavior-spec v1.0 section 4.1) ===")
assert IdleTier.ATTENTIVE.value == "attentive"
assert IdleTier.ENGAGED.value == "engaged"
assert IdleTier.DEEP.value == "deep"
assert len(IdleTier) == 3
ok()
print("OK: attentive / engaged / deep tiers defined")

print("=== 2. Idle action vocabulary exists (behavioral actions, not animation) ===")
for name in ("none", "blink", "gaze_drift", "micro_correction", "curious_glance"):
    assert IdleAction(name).value == name
assert len(IdleAction) == 5
ok()
print("OK: NONE / BLINK / GAZE_DRIFT / MICRO_CORRECTION / CURIOUS_GLANCE")

print("=== 3. Idle can legitimately choose NONE ===")
idle = IdleBehavior(rng=random.Random(1))
run = simulate(idle, 180_000.0)
assert any(d.action is IdleAction.NONE and d.reason == "quiet_period" for d in run)
ok()
print(f"OK: {sum(1 for d in run if d.action is IdleAction.NONE)} NONE decisions in 180 s")

print("=== 4. Idle never overrides active high-priority behavior ===")
for name in ("greeting", "listening", "alert", "thinking", "responding",
             "comforting", "playful", "searching", "celebrating", "confused", "curious"):
    idle = IdleBehavior(rng=random.Random(7))
    d = idle.decide(IdleContext(now_ms=0.0, active_behavior=name))
    assert d.action is IdleAction.NONE, name
    assert d.reason == "yield_active_behavior", (name, d.reason)
# ...but NOT to waiting (attentive-idle state, E16) or idle (itself)
for name in ("waiting", "idle"):
    idle = IdleBehavior(rng=random.Random(7))
    d = idle.decide(IdleContext(now_ms=0.0, active_behavior=name))
    assert d.reason != "yield_active_behavior", name
ok()
print("OK: yields to 11 high-priority intents; never to waiting/idle")

print("=== 5. Idle respects interaction mode ===")
for mode in (InteractionMode.LISTENING, InteractionMode.RESPONDING,
             InteractionMode.GREETING, InteractionMode.THINKING,
             InteractionMode.PLAYFUL, InteractionMode.ALERT,
             InteractionMode.CURIOUS, InteractionMode.CONFUSED):
    idle = IdleBehavior(rng=random.Random(8))
    d = idle.decide(IdleContext(now_ms=0.0, interaction_mode=mode))
    assert d.reason == "yield_interaction_mode", (mode, d.reason)
# Waiting / sleep are idle-compatible modes
idle = IdleBehavior(rng=random.Random(8))
d = idle.decide(IdleContext(now_ms=0.0, interaction_mode=InteractionMode.WAITING))
assert d.reason != "yield_interaction_mode"
idle = IdleBehavior(rng=random.Random(8))
d = idle.decide(IdleContext(now_ms=0.0, interaction_mode=InteractionMode.SLEEP))
assert d.reason != "yield_interaction_mode"
ok()
print("OK: yields to engaged modes; waiting/sleep remain idle-compatible")

print("=== 6. Idle respects robot speaking state ===")
idle = IdleBehavior(rng=random.Random(6))
d = idle.decide(IdleContext(now_ms=0.0, robot_speaking=True))
assert d.action is IdleAction.NONE and d.reason == "yield_robot_speaking"
ok()
print("OK: speaking -> yield_robot_speaking")

print("=== 7. Idle respects touch state ===")
idle = IdleBehavior(rng=random.Random(7))
d = idle.decide(IdleContext(now_ms=0.0, touch_active=True))
assert d.action is IdleAction.NONE and d.reason == "yield_touch"
ok()
print("OK: touch -> yield_touch")

print("=== 8. Idle respects attention state ===")
idle = IdleBehavior(rng=random.Random(9))
d = idle.decide(IdleContext(now_ms=0.0, eye_contact=True))
assert d.tier is IdleTier.ENGAGED, d.tier
idle = IdleBehavior(rng=random.Random(9))
d = idle.decide(IdleContext(now_ms=0.0, attention_target=(0.5, 0.5)))
assert d.tier is IdleTier.ATTENTIVE, d.tier
ok()
print("OK: eye contact -> engaged idle; target w/o gaze -> attentive idle")

print("=== 9. Idle respects current emotion (activity shaping) ===")
happy = simulate(IdleBehavior(rng=random.Random(1)), 180_000.0, emotion="happy")
sad = simulate(IdleBehavior(rng=random.Random(1)), 180_000.0, emotion="sad")
n_happy = len(non_none(happy))
n_sad = len(non_none(sad))
assert n_happy > n_sad, (n_happy, n_sad)
assert n_sad > 0


def none_share(run):
    """Proportion of decisions that are NONE (quieter = higher share)."""
    return sum(1 for d in run if d.action is IdleAction.NONE) / max(1, len(run))


assert none_share(sad) > none_share(happy), (none_share(sad), none_share(happy))
ok()
print(f"OK: happy {n_happy} actions vs sad {n_sad}; NONE-share sad {none_share(sad):.2f} > happy {none_share(happy):.2f}")

print("=== 10. Sleepy -> deep idle with reduced activity ===")
sleepy = simulate(IdleBehavior(rng=random.Random(1)), 180_000.0, emotion="sleepy")
calm = simulate(IdleBehavior(rng=random.Random(1)), 180_000.0, emotion="calm")
assert all(d.tier is IdleTier.DEEP for d in sleepy), {d.tier for d in sleepy}
assert len(non_none(sleepy)) < len(non_none(calm))
ok()
print(f"OK: sleepy {len(non_none(sleepy))} actions (all DEEP) vs calm {len(non_none(calm))}")

print("=== 11. Surprised: recovery first, no immediate idle action ===")
idle = IdleBehavior(rng=random.Random(11))
d = idle.decide(IdleContext(now_ms=0.0, emotion="surprised"))
assert d.action is IdleAction.NONE and d.reason == "surprise_recovery"
assert d.next_ms >= 1500.0
d2 = idle.decide(IdleContext(now_ms=d.next_ms, emotion="surprised"))
assert d2.action is IdleAction.NONE and d2.reason == "surprise_recovery"
ok()
print("OK: surprise -> NONE recovery; next decision after >=1500 ms")

print("=== 12. Cooldowns (BehaviorMemory) are respected ===")
mem = BehaviorMemory()
mem.start_cooldown("idle_blink", 600_000.0, 0.0)
idle = IdleBehavior(rng=random.Random(12), memory=mem)
run = simulate(idle, 60_000.0)
assert all(d.action is not IdleAction.BLINK for d in run)
ok()
print("OK: active idle_blink cooldown -> zero BLINK decisions in 60 s")

print("=== 13. Recent behavior suppresses inappropriate repetition ===")
idle = IdleBehavior(rng=random.Random(13))
run = simulate(idle, 300_000.0)
names = [d.action for d in non_none(run)]
assert len(names) > 10, len(names)
for i in range(1, len(names)):
    if names[i] is not IdleAction.BLINK:
        assert names[i] is not names[i - 1], (i, names[i - 2:i + 1])
for i in range(2, len(names)):
    if names[i] is not IdleAction.BLINK:
        assert not (names[i] is names[i - 1] is names[i - 2])
ok()
print(f"OK: no immediate repeat / triple of non-blink actions over {len(names)} actions")

print("=== 14. Personality influences activity where supported ===")
high = PersonalityTraits(energy=0.9)
low = PersonalityTraits(energy=0.1)


def actions_for(traits, seed, horizon=180_000.0):
    return len(non_none(simulate(IdleBehavior(rng=random.Random(seed)), horizon, traits=traits)))


n_high = actions_for(high, 1)
n_low = actions_for(low, 1)
assert n_high > n_low, (n_high, n_low)


def glances_for(traits, seed, horizon=300_000.0):
    run = simulate(IdleBehavior(rng=random.Random(seed)), horizon, traits=traits)
    return sum(1 for d in run if d.action is IdleAction.CURIOUS_GLANCE)


cur_high = PersonalityTraits(curiosity=0.9)
cur_low = PersonalityTraits(curiosity=0.1)
g_high = glances_for(cur_high, 11)
g_low = glances_for(cur_low, 11)
assert g_high > g_low, (g_high, g_low)
ok()
print(f"OK: energy 0.9 -> {n_high} actions vs 0.1 -> {n_low}; "
      f"curiosity 0.9 -> {g_high} glances vs 0.1 -> {g_low}")

print("=== 15. Randomness is injectable ===")
idle_a = IdleBehavior(rng=random.Random(1234))
idle_b = IdleBehavior(rng=random.Random(1234))
assert seq_key(simulate(idle_a, 60_000.0)) == seq_key(simulate(idle_b, 60_000.0))
idle_c = IdleBehavior(rng=random.Random(1))
idle_d = IdleBehavior()  # default (system entropy) must also work
assert simulate(idle_c, 5_000.0) and simulate(idle_d, 5_000.0)
ok()
print("OK: same injected seed -> same sequence; rng=None works")

print("=== 16. Seeded execution is deterministic ===")
runs = [seq_key(simulate(IdleBehavior(rng=random.Random(99)), 90_000.0)) for _ in range(3)]
assert runs[0] == runs[1] == runs[2]
ok()
print("OK: three identical runs under seed 99")

print("=== 17. Different seeds can produce different valid sequences ===")
s1 = seq_key(simulate(IdleBehavior(rng=random.Random(1)), 90_000.0))
s2 = seq_key(simulate(IdleBehavior(rng=random.Random(2)), 90_000.0))
assert s1 != s2
ok()
print("OK: seed 1 != seed 2")

print("=== 18. Anti-periodicity: bounded bands, no fixed periodic timer ===")
policy = IdlePolicy()
for tier in IdleTier:
    for action in IdleAction:
        band = policy.band_for(tier, action)
        assert band.min_ms < band.max_ms, (tier, action)
        assert band.min_ms > 0.0
# The policy exposes NO fixed interval anywhere (bands only).
for tier in IdleTier:
    for action in IdleAction:
        assert not hasattr(policy.band_for(tier, action), "fixed_ms")
ok()
print("OK: all 15 (tier x action) bands are non-degenerate ranges")

print("=== 19. Long idle: quiet periods exist, no runaway, no periodicity ===")
idle = IdleBehavior(rng=random.Random(5))
run = simulate(idle, 300_000.0)
actions = non_none(run)
assert actions, "expected actions in a 5-minute calm idle"
times = [d.decided_at_ms for d in actions]
gaps = [b - a for a, b in zip(times, times[1:])]
distinct = {round(g, 3) for g in gaps}
assert len(distinct) > 1, "intervals must not all be identical"
assert min(gaps) >= 2000.0, f"runaway frequency: min gap {min(gaps):.0f} ms"
assert max(gaps) >= 3000.0, f"no quiet period: max gap {max(gaps):.0f} ms"
n_none = sum(1 for d in run if d.action is IdleAction.NONE)
assert n_none > 0
print(f"OK: {len(actions)} actions, {n_none} NONE decisions, "
      f"min gap {min(gaps):.0f} ms, max gap {max(gaps):.0f} ms, "
      f"{len(distinct)} distinct intervals")
ok()

print("=== 20. No wall-clock APIs in the idle modules ===")
import les.behaviors.idle_behavior as ib  # noqa: E402
import les.behaviors.idle_policy as ip  # noqa: E402
src = inspect.getsource(ip) + inspect.getsource(ib)
for token in ("time.time", "get_ticks", "monotonic", "perf_counter", "clock()"):
    assert token not in src, token
ok()
print("OK: no wall-clock / hardware clock calls found")

print("=== 21. No forbidden imports in the idle modules ===")
for token in ("import pygame", "from pygame", "import eyes", "from eyes",
              "import face", "from face", "import rospy", "from rospy",
              "import cv2", "from cv2", "import serial", "from serial"):
    assert token not in src, token
ok()
print("OK: no pygame / eyes / face / ROS / OpenCV / serial imports")

print("=== 22. LES-09A.2 handoff: decision -> BehaviorIntent mapping ===")
idle = IdleBehavior(rng=random.Random(22))
d = IdleDecision(
    action=IdleAction.BLINK, tier=IdleTier.ATTENTIVE, reason="attentive_idle",
    next_ms=5000.0, decided_at_ms=1000.0,
)
intent = idle.to_behavior_intent(d)
assert intent.behavior_name == "idle"
assert intent.variant == "attentive_blink"
assert intent.suggested_duration_ms == 4000.0
assert intent.reason == "idle:attentive_idle"
d_none = IdleDecision(
    action=IdleAction.NONE, tier=IdleTier.DEEP, reason="quiet_period",
    next_ms=9000.0, decided_at_ms=4000.0,
)
assert idle.to_behavior_intent(d_none).variant == "deep"
ok()
print("OK: idle decision maps onto BehaviorIntent (variant preserved, no engine calls)")

print("=== 23. not_due guard enforces explicit quiet periods ===")
idle = IdleBehavior(rng=random.Random(23))
d = idle.decide(IdleContext(now_ms=0.0))
assert d.next_ms > 0.0
d_early = idle.decide(IdleContext(now_ms=0.0))
assert d_early.action is IdleAction.NONE and d_early.reason == "not_due"
assert d_early.next_ms == d.next_ms
ok()
print("OK: early polls yield NONE(not_due) with the due time preserved")

print("=== 24. Reset clears decision state ===")
idle = IdleBehavior(rng=random.Random(24))
simulate(idle, 30_000.0)
idle.reset()
d = idle.decide(IdleContext(now_ms=0.0))
assert d.next_ms > 0.0 and d.reason not in ("not_due",)
ok()
print("OK: reset() restores a fresh decision state")

print()
print(f"ALL {CHECKS} LES-09A.1 CHECKS PASSED")
