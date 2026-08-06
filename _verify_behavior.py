"""Standalone verification for the LES Behavior Director (design contract)."""

import sys

from les.config.defaults import DirectorConfig, BehaviorConfig
from les.director.behavior_director import (
    BehaviorDirector,
    BehaviorIntent,
    BehaviorRequest,
    DefaultBehaviorDirector,
)
from les.director.behavior_policy import BehaviorPolicy, BehaviorRule, VariantRotation
from les.director.emotion_director import DefaultEmotionDirector, EmotionInput
from les.memory.behavior_memory import BehaviorMemory
from les.world.value_quality import SensorValue, ValueQuality
from les.world.world_state import WorldState

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    if not cond:
        print(f"  FAIL: {name} {detail}")
    else:
        print(f"  ok:   {name}")


def make_rig(emotion: str = "calm", emo_conf: float = 0.9):
    """World + memory + emotion director + behavior director, all wired."""
    w = WorldState()
    w.set_timestamp(0.0)
    w.update_emotion(emotion, emo_conf)
    w.update_camera_available(True)
    w.update_microphone_available(True)
    m = BehaviorMemory()
    ed = DefaultEmotionDirector(w, m)
    bd = DefaultBehaviorDirector(w, m, ed)
    return w, m, ed, bd


def settle(ed, bd, ms, times=1):
    for _ in range(times):
        ed.update(ms)
        bd.update(ms)


print("=== 1. Independence: no forbidden dependencies ===")
bad = []
for mod in sys.modules:
    if mod.startswith(("pygame", "cv2", "mediapipe", "rospy", "serial", "eyes", "face")):
        bad.append(mod)
check("no forbidden modules loaded", not bad, str(bad))
check("BehaviorDirector is abstract (ABC)", getattr(BehaviorDirector, "__abstractmethods__", None) is not None)

print("=== 2. Idle fallback (nothing happening) ===")
w, m, ed, bd = make_rig("calm")
settle(ed, bd, 16)
intent = bd.select_next()
check("idle fallback selected", intent.behavior_name == "idle", str(intent))
check("idle reason", intent.reason == "idle_fallback", intent.reason)
check("BehaviorIntent is a BehaviorRequest", isinstance(intent, BehaviorRequest))

print("=== 3. Arbitration: touch promotes comforting over idle ===")
w.update_touch(True)
settle(ed, bd, 16)
intent = bd.select_next()
check("comforting wins on touch", intent.behavior_name == "comforting", str(intent))
check("comforting is non-interruptible", intent.interruptible is False)
w.update_touch(False)

print("=== 4. Arbitration: speech promotes listening ===")
w.update_speech(True)
settle(ed, bd, 16)
intent = bd.select_next()
check("listening wins on speech", intent.behavior_name == "listening", str(intent))
w.update_speech(False)

print("=== 5. Arbitration: robot speaking promotes responding ===")
w.update_robot_speaking(True)
settle(ed, bd, 16)
intent = bd.select_next()
check("responding wins while robot speaks", intent.behavior_name == "responding", str(intent))
w.update_robot_speaking(False)

print("=== 6. Cooldown respected (greeting cannot repeat immediately) ===")
w.update_face(True, (0.5, 0.5), 0.9)
w.update_eye_contact(True)
settle(ed, bd, 16)
i1 = bd.select_next()
check("greeting wins on eye contact", i1.behavior_name == "greeting", str(i1))
# Greeting is non-interruptible + max_hold 800ms; force it out via max hold.
for _ in range(60):
    settle(ed, bd, 16)
i2 = bd.select_next()
check("greeting yielded after max_hold", i2.behavior_name != "greeting", str(i2))
# Still at eye contact: idle_fallback or another eligible intent - but
# greeting itself must be on cooldown.
check("greeting on cooldown", m.is_cooling("greeting", bd._now_ms), m.cooldown_remaining_ms("greeting", bd._now_ms))

print("=== 7. Persistence / continuation: active intent keeps running ===")
w, m, ed, bd = make_rig("happy")
w.update_eye_contact(True)
settle(ed, bd, 16)
i1 = bd.select_next()
check("initial selection made", i1.behavior_name is not None)
settle(ed, bd, 16)
i2 = bd.select_next()
check("same intent continues", i2.behavior_name == i1.behavior_name, f"{i1.behavior_name} -> {i2.behavior_name}")
check("continuation reason", i2.reason == "continuation", i2.reason)
check("urgency decays on continuation", i2.urgency < i1.urgency, f"{i1.urgency} -> {i2.urgency}")

print("=== 8. Interruption: urgent intent displaces mid-continuation ===")
w.update_speech(True)  # listening appears while something else is active
settle(ed, bd, 16)
i3 = bd.select_next()
# listening (0.80+0.10) vs idle-ish — it should switch via arbitration or
# interruption; assert an actual change happened at some point.
check("speech interrupts", i3.behavior_name == "listening", str(i3))
check("change recorded in memory", m.active_behavior == "listening")

print("=== 9. Non-interruptible behavior holds during its window ===")
w, m, ed, bd = make_rig("surprised")
w.update_face(True, (0.5, 0.5), 0.9)
w.update_eye_contact(True)
w.update_touch(True)
settle(ed, bd, 16)
i1 = bd.select_next()
check("alert wins on surprised (priority 0.95)", i1.behavior_name == "alert", str(i1))
settle(ed, bd, 16)
i2 = bd.select_next()
check("alert holds (non-interruptible)", i2.behavior_name == "alert", str(i2))
# Once the surprised emotion decays away the alert rule stops matching.

print("=== 10. Emotion pairing: happy promotes playful ===")
w, m, ed, bd = make_rig("happy")
w.update_face(True, (0.5, 0.5), 0.9)
settle(ed, bd, 16)
intent = bd.select_next()
check("playful promoted by happy", intent.behavior_name == "playful", str(intent))
check("transition recommendation is emotion-paired", intent.transition_recommendation == "playful", intent.transition_recommendation)

print("=== 11. Variant rotation (CYCLIC) ===")
policy = BehaviorPolicy(
    variant_preferences={"playful": ("happy_a", "happy_b", "happy_c")},
)
w, m, ed, bd = make_rig("happy")
bd = DefaultBehaviorDirector(w, m, ed, policy=policy)
w.update_face(True, (0.5, 0.5), 0.9)
settle(ed, bd, 16)
i1 = bd.select_next()
i2 = bd.select_next()
check("variant is a name, not animation", i1.variant in ("happy_a", "happy_b", "happy_c"), str(i1.variant))
check("variant cycles forward", i1.variant == "happy_a" and i2.variant == "happy_b", f"{i1.variant} -> {i2.variant}")

print("=== 12. Variant rotation (STICKY) ===")
policy = BehaviorPolicy(
    variant_rotation=VariantRotation.STICKY,
    variant_preferences={"playful": ("happy_a", "happy_b")},
)
w, m, ed, bd = make_rig("happy")
bd = DefaultBehaviorDirector(w, m, ed, policy=policy)
w.update_face(True, (0.5, 0.5), 0.9)
settle(ed, bd, 16)
i1 = bd.select_next()
settle(ed, bd, 16)
i2 = bd.select_next()
check("sticky keeps variant", i1.variant == i2.variant, f"{i1.variant} vs {i2.variant}")

print("=== 13. Policy replacement works ===")
policy = BehaviorPolicy(
    intent_rules=(
        BehaviorRule("playful", 0.99, requires_emotion="happy"),
        BehaviorRule("idle", 0.10, self_sustaining=True),
    ),
)
w, m, ed, bd = make_rig("happy")
bd = DefaultBehaviorDirector(w, m, ed, policy=policy)
w.update_face(True, (0.5, 0.5), 0.9)
settle(ed, bd, 16)
intent = bd.select_next()
check("custom policy drives selection", intent.behavior_name == "playful", str(intent))

print("=== 14. from_config seeds cooldown ===")
p = BehaviorPolicy.from_config(behavior=BehaviorConfig(default_cooldown_ms=2500.0))
check("from_config seeds cooldown", p.cooldown_ms == 2500.0, str(p.cooldown_ms))

print("=== 15. Intent listeners fire on change ===")
w, m, ed, bd = make_rig("calm")
seen = []
bd.add_intent_listener(lambda c: seen.append(c))
settle(ed, bd, 16)
bd.select_next()
check("listener fired on first selection", len(seen) == 1 and seen[0].to_intent == "idle", str([(c.from_intent, c.to_intent) for c in seen]))

print("=== 16. reset restores neutral arbitration state ===")
bd.reset()
st = bd.current_state()
check("intent cleared on reset", st.intent is None)
check("cooldowns cleared on reset", len(m.cooldowns.active_names(0.0)) == 0)

print()
print(f"RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL CHECKS PASSED")
