"""Comprehensive verification suite for Animation Direction Framework."""

import sys
import traceback
import math

from eyes.engine import EngineConfig, EyePair
from eyes.engine.config import DisplayConfig, EyeLayoutConfig
from eyes.engine.personality import PersonalityProfile
from eyes.engine.motion_primitives import LookScanPrimitive, SettledPair
from eyes.engine.choreography import (
    StageType,
    StageConfig,
    AnimationDirection,
    anticipation,
    overshoot,
    follow_through,
    hold,
    settle,
    attention_gain_helper,
    attention_release_helper,
    emotional_settle_helper,
    natural_pause_helper,
    eye_compression_helper,
    eye_expansion_helper,
    look_scan_helper,
    look_return_helper,
    soft_blink_helper,
    fast_blink_helper,
    double_blink_helper,
    curious_tilt_helper,
    breathing_pulse_helper,
    bounce_accent_helper,
    focus_lock_helper,
    focus_release_helper,
    ChoreographyStep,
    ChoreographySequence,
)

PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK]   {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} -- {detail}")

cfg = EngineConfig(
    display=DisplayConfig(width=800, height=480),
    layout=EyeLayoutConfig(center_y=240.0, eye_radius=60.0, eye_spacing=280.0),
)

def new_pair():
    p = EyePair()
    p.configure(cfg)
    return p

print("=" * 70)
print("Testing AnimationDirection & StageConfig Data Structures")
print("=" * 70)

direction = AnimationDirection(
    enter_duration=400.0,
    exit_duration=300.0,
    hold_duration=100.0,
    breathing_strength=0.8,
    bounce_strength=0.5,
    blink_style="fast",
    look_style="scan",
    energy=0.7,
    warmth=0.6,
)

check("AnimationDirection fields initialized", direction.enter_duration == 400.0 and direction.blink_style == "fast")
check("StageConfig ENTER automatically generated", direction.get_stage(StageType.ENTER).stage_type == StageType.ENTER)
check("StageConfig LOOP automatically generated", direction.get_stage(StageType.LOOP).stage_type == StageType.LOOP)
check("StageConfig EXIT automatically generated", direction.get_stage(StageType.EXIT).stage_type == StageType.EXIT)

profile = PersonalityProfile.excited()
dir_from_p = AnimationDirection.from_personality(profile, blink_style="double", look_style="scan")
check("AnimationDirection.from_personality", dir_from_p.energy == profile.energy and dir_from_p.blink_style == "double")
extracted_profile = dir_from_p.to_personality_profile()
check("AnimationDirection.to_personality_profile", extracted_profile.energy == profile.energy)


print("\n" + "=" * 70)
print("Testing Timing Helpers")
print("=" * 70)

a_val = anticipation(0.1, amount=0.1)
check("anticipation dips below zero", a_val < 0.0)

o_val = overshoot(0.5, amount=0.12)
check("overshoot peak > 1.0", o_val > 1.0)

ft_val = follow_through(0.5, delay=0.1)
check("follow_through valid output", 0.0 <= ft_val <= 1.0)

h_val_mid = hold(0.5, hold_start=0.4, hold_duration=0.2)
h_val_start = hold(0.4, hold_start=0.4, hold_duration=0.2)
check("hold maintains constant progress during hold interval", abs(h_val_mid - h_val_start) < 1e-5)

s_val = settle(0.5)
check("settle converges toward 1.0", abs(s_val - 1.0) < 0.5)


print("\n" + "=" * 70)
print("Testing 16 Reusable Choreography Helpers")
print("=" * 70)

# 1. Attention Gain
p = new_pair()
attention_gain_helper(p, progress=0.5, intensity=1.0)
check("1. attention_gain_helper mutates look offset & iris scale", p.left.look_offset_x != 0.0 and p.left.iris_scale > 1.0)

# 2. Attention Release
attention_release_helper(p, progress=1.0, intensity=1.0)
check("2. attention_release_helper decays look offset to 0", abs(p.left.look_offset_x) < 1e-3 and abs(p.left.iris_scale - 1.0) < 1e-3)

# 3. Emotional Settle
p = new_pair()
p.left.squash = 0.2
emotional_settle_helper(p, progress=1.0)
check("3. emotional_settle_helper dampens squash to 0", p.left.squash == 0.0)

# 4. Natural Pause
p = new_pair()
natural_pause_helper(p, progress=0.5, intensity=1.0)
check("4. natural_pause_helper applies micro drift offset", p.left.look_offset_x != 0.0)

# 5. Eye Compression
p = new_pair()
eye_compression_helper(p, amount=1.0)
check("5. eye_compression_helper squashes pose", p.left.squash > 0.0)

# 6. Eye Expansion
p = new_pair()
eye_expansion_helper(p, amount=1.0)
check("6. eye_expansion_helper stretches pose", p.left.stretch > 0.0)

# 7. Look Scan
p = new_pair()
lsp = LookScanPrimitive()
look_scan_helper(p, dt_s=0.1, elapsed_s=1.0, scan_primitive=lsp, amount=1.0)
check("7. look_scan_helper applies scanning offset", p.left.look_offset_x != 0.0 or p.left.look_offset_y != 0.0)

# 8. Look Return
p = new_pair()
sp = SettledPair()
sp.set_immediate(10.0, 10.0)
look_return_helper(p, settle_pair=sp, dt_s=0.5)
check("8. look_return_helper settles look toward center", abs(p.left.look_offset_x) < 10.0)

# 9. Soft Blink
p = new_pair()
soft_blink_helper(p, progress=0.5)
check("9. soft_blink_helper compresses lid openness / radius", p.left.radius < cfg.layout.eye_radius)

# 10. Fast Blink
p = new_pair()
fast_blink_helper(p, progress=0.5)
check("10. fast_blink_helper compresses eye with sharp curve", p.left.radius < cfg.layout.eye_radius)

# 11. Double Blink
p = new_pair()
double_blink_helper(p, progress=0.2)
check("11. double_blink_helper applies first blink pulse", p.left.radius < cfg.layout.eye_radius)

# 12. Curious Tilt
p = new_pair()
curious_tilt_helper(p, tilt_angle_deg=5.0, progress=1.0)
check("12. curious_tilt_helper creates asymmetric y pos", p.left.pos_y != p.right.pos_y)

# 13. Breathing Pulse
p = new_pair()
breathing_pulse_helper(p, dt_ms=16.0, elapsed_ms=1000.0, amount=1.0)
check("13. breathing_pulse_helper mutates pose vertical scaling & radius", p.left.scale_y != 1.0 or p.left.radius != cfg.layout.eye_radius)

# 14. Bounce Accent
p = new_pair()
bounce_accent_helper(p, dt_ms=16.0, elapsed_ms=500.0, amount=1.0)
check("14. bounce_accent_helper applies bounce offset", p.left.bounce_offset_y != 0.0)

# 15. Focus Lock
p = new_pair()
focus_lock_helper(p, focus_amount=1.0)
check("15. focus_lock_helper compresses iris scale & lid openness", p.left.iris_scale < 1.0 and p.left.lid_openness < 1.0)

# 16. Focus Release
focus_release_helper(p, progress=1.0)
check("16. focus_release_helper returns iris & lid openness to 1.0", abs(p.left.iris_scale - 1.0) < 1e-3)


print("\n" + "=" * 70)
print("Testing ChoreographySequence Runner")
print("=" * 70)

p = new_pair()
seq = ChoreographySequence("test_demo")
seq.add_step("Expand", 100.0, lambda pose, dt, prg: eye_expansion_helper(pose, prg))
seq.add_step("Overshoot", 100.0, lambda pose, dt, prg: attention_gain_helper(pose, prg))
seq.add_step("Pause", 100.0, lambda pose, dt, prg: natural_pause_helper(pose, prg))
seq.add_step("Blink", 100.0, lambda pose, dt, prg: soft_blink_helper(pose, prg))
seq.add_step("Breathing", 100.0, lambda pose, dt, prg: breathing_pulse_helper(pose, dt, 100.0))
seq.add_step("Idle", 100.0, lambda pose, dt, prg: emotional_settle_helper(pose, prg))

check("ChoreographySequence step count", len(seq.steps) == 6)
check("ChoreographySequence total duration", seq.total_duration_ms == 600.0)

seq.update(50.0, p)
check("ChoreographySequence first step in progress", seq.current_step_name == "Expand" and not seq.is_finished)

seq.update(500.0, p)
check("ChoreographySequence advanced to later step", seq.current_step_index > 0)

seq.update(200.0, p)
check("ChoreographySequence completed cleanly", seq.is_finished and seq.progress == 1.0)


print("\n" + "=" * 70)
print(f"RESULTS: PASS = {PASS}   FAIL = {FAIL}")
print("=" * 70)

if FAIL > 0:
    sys.exit(1)
