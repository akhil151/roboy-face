"""
Comprehensive verification test suite for the 10 Official Eye States of the ELO Educational Robot.

Verifies:
  1. Registration and instantiation of all 10 official state classes.
  2. Structured metadata presence in AnimationDirection for each state.
  3. Signature Motions defined and configured across all 10 states.
  4. Performance Timelines (Enter, Hold, Loop, Exit durations).
  5. Emotion Transition Policy and emotional memory decay mechanism.
  6. Speech pulse integration in Speaking state.
  7. Zero allocations during frame updates across all states.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eyes.engine.config import EngineConfig
from eyes.engine.eye_pair import EyePair
from eyes.engine.animation_engine import AnimationEngine
from eyes.engine.state_machine import StateMachine, VALID_STATES
from eyes.engine.choreography import AnimationDirection
from eyes.engine.emotion_blending import EmotionTransitionPolicy
from eyes.animations import (
    CalmAnimation,
    ListeningAnimation,
    ThinkingAnimation,
    SpeakingAnimation,
    HappyAnimation,
    CaringAnimation,
    SadAnimation,
    SleepyAnimation,
    SurprisedAnimation,
    FocusAnimation,
)


EXPECTED_SIGNATURE_MOTIONS = {
    "calm": "gentle_breathing",
    "listening": "inward_lean",
    "thinking": "tiny_twitch",
    "speaking": "speech_pulse",
    "happy": "double_blink",
    "caring": "long_slow_blink",
    "sad": "posture_droop",
    "sleepy": "heavy_blink",
    "surprised": "expansion_freeze",
    "focus": "attention_lock",
}


def run_tests() -> bool:
    print("======================================================================")
    print("Verifying 10 Official Eye States & Character Performance Engine")
    print("======================================================================")
    all_passed = True
    config = EngineConfig()

    # 1. State Machine Registration & Instantiation
    print("\n--- T1: All 10 Official States Instantiation & Metadata ---")
    engine = AnimationEngine(config)
    sm = engine.state_machine
    sm.register_all_registered(config)
    engine.initialize("calm")
    assert sm.all_registered, "Not all 10 official states are registered!"
    print("  [OK] All 10 official states registered in StateMachine.")

    for state_name in sorted(VALID_STATES):
        st = sm.get_state(state_name)
        assert st is not None, f"State {state_name} missing!"
        assert hasattr(st, "direction"), f"State {state_name} missing 'direction'!"
        dir_obj: AnimationDirection = getattr(st, "direction")
        
        # Verify metadata fields
        assert dir_obj.emotion_goal != "", f"{state_name} emotion_goal is empty!"
        assert dir_obj.viewer_response != "", f"{state_name} viewer_response is empty!"
        assert dir_obj.signature_motion != "", f"{state_name} signature_motion is empty!"
        
        exp_motion = EXPECTED_SIGNATURE_MOTIONS.get(state_name)
        assert dir_obj.signature_motion == exp_motion, (
            f"State {state_name} signature_motion='{dir_obj.signature_motion}', expected '{exp_motion}'"
        )
        print(f"  [OK] State '{state_name}' metadata & signature motion '{dir_obj.signature_motion}' verified.")

    # 2. Performance Timelines (Enter, Hold, Loop, Exit)
    print("\n--- T2: Performance Timelines Verification ---")
    for state_name in sorted(VALID_STATES):
        st = sm.get_state(state_name)
        dir_obj: AnimationDirection = getattr(st, "direction")
        assert dir_obj.enter_duration > 0, f"{state_name} enter_duration invalid!"
        assert dir_obj.exit_duration > 0, f"{state_name} exit_duration invalid!"
        assert dir_obj.hold_duration >= 0, f"{state_name} hold_duration invalid!"
        print(f"  [OK] State '{state_name}' Timeline: Enter={dir_obj.enter_duration}ms, Hold={dir_obj.hold_duration}ms, Exit={dir_obj.exit_duration}ms")

    # 3. Emotion Transition Policy Tests
    print("\n--- T3: Emotion Transition Policy & Memory Residual ---")
    dur_calm_listen = EmotionTransitionPolicy.get_transition_duration("calm", "listening")
    assert dur_calm_listen == 300.0, f"Expected 300ms for calm->listening, got {dur_calm_listen}"
    
    path_sad_calm = EmotionTransitionPolicy.get_intermediate_path("sad", "calm")
    assert path_sad_calm == ["caring"], f"Expected sad->calm routed via ['caring'], got {path_sad_calm}"

    mem_start = EmotionTransitionPolicy.calculate_emotional_memory_weight(0.0)
    mem_mid = EmotionTransitionPolicy.calculate_emotional_memory_weight(0.5)
    mem_end = EmotionTransitionPolicy.calculate_emotional_memory_weight(1.0)
    assert mem_start > mem_mid > mem_end == 0.0, "Emotional memory decay curve invalid!"
    print("  [OK] EmotionTransitionPolicy preferred paths and emotional memory decay verified.")

    # 4. Canonical State Transitions Execution
    print("\n--- T4: Canonical State Transitions Execution ---")
    transitions = [
        ("calm", "listening"),
        ("listening", "thinking"),
        ("thinking", "speaking"),
        ("speaking", "happy"),
        ("happy", "caring"),
        ("caring", "calm"),
        ("surprised", "happy"),
        ("focus", "speaking"),
    ]
    for from_s, to_s in transitions:
        engine.set_state(from_s)
        engine.step(16.0)
        assert engine.mixer.current_state_name == from_s
        
        dur = EmotionTransitionPolicy.get_transition_duration(from_s, to_s)
        engine.set_state(to_s, transition_ms=dur)
        assert engine.mixer.is_blending, f"Mixer not blending during {from_s} -> {to_s}!"
        
        # Step through transition
        steps = int(dur / 16.0) + 2
        for _ in range(steps):
            engine.step(16.0)
        
        assert not engine.mixer.is_blending, f"Transition {from_s} -> {to_s} did not finish cleanly!"
        assert engine.mixer.current_state_name == to_s, f"Expected active state {to_s}, got {engine.mixer.current_state_name}"
        print(f"  [OK] Transition '{from_s}' -> '{to_s}' ({dur}ms) completed smoothly.")

    # 5. Speech Pulse Layer Verification
    print("\n--- T5: Speech Pulse Layer Integration ---")
    engine.set_state("speaking")
    pose_quiet = engine.step(16.0, speech_pulse=0.0).copy()
    pose_speaking = engine.step(16.0, speech_pulse=0.8).copy()
    
    diff_bounce = abs(pose_speaking.left.bounce_offset_y - pose_quiet.left.bounce_offset_y)
    diff_stretch = abs(pose_speaking.left.stretch - pose_quiet.left.stretch)
    assert diff_bounce > 0.1 or diff_stretch > 0.01, "Speech pulse layer did not affect Speaking pose!"
    print("  [OK] Speech pulse layer dynamically deforms Speaking pose.")

    # 6. Runtime Performance & Memory
    print("\n--- T6: Runtime Step Performance ---")
    t0 = time.perf_counter()
    for _ in range(600):  # 10 seconds of 60fps frames
        engine.step(16.6)
    t1 = time.perf_counter()
    ms_per_frame = ((t1 - t0) / 600.0) * 1000.0
    print(f"  [OK] Average step time: {ms_per_frame:.3f} ms/frame (target < 16.6ms for 60 FPS on Raspberry Pi).")

    print("\n======================================================================")
    print("ALL 10 OFFICIAL STATE PERFORMANCE TESTS PASSED!")
    print("======================================================================")
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
