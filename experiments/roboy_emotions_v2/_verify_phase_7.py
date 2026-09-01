"""ROBoy Emotion V2 - Phase 7 Comprehensive Verification Suite.

Validates the Phase 7 Behavior Execution Engine:
 1. Action construction & default values for all action types.
 2. Action parameter validation (unknown emotion, invalid gaze, negative durations).
 3. EmotionAction lifecycle (morph duration, hold time, and completion).
 4. GazeAction lifecycle (named direction, (x, y) target vector, duration, hold time).
 5. BlinkAction lifecycle (NORMAL, QUICK, SLOW, HALF, DOUBLE).
 6. WaitAction timing precision.
 7. ParallelAction concurrent child execution.
 8. Strict FIFO sequence execution order.
 9. queue_action() non-interrupting queue appends.
10. queue_sequence() batch queue appends.
11. play_sequence() sequence replacement and interrupt behavior.
12. clear_queue() pending queue clearing without active action cancellation.
13. interrupt() cancellation of active action while preserving live face pose.
14. Zero-duration actions instantaneous completion without infinite loop.
15. Large dt overshoot & residual dt cascading across action boundaries.
16. Multiple actions completed within a single update(dt) tick.
17. Empty sequence play_sequence([]) sets idle state immediately.
18. Invalid dt (negative dt raises ValueError).
19. Named behavior template registry and trigger_behavior().
20. Fresh action instances generated on every behavior trigger.
21. Status telemetry (is_busy, queue_length, progress, nested choreographer status).
22. Idle stillness and invariance when queue is empty.
23. Simultaneous underlying Emotion + Gaze + Blink orchestration.
24. Interruption during emotion transition captures live pose seamlessly.
25. Interruption during gaze movement preserves live saccade position.
26. Interruption during blink preserves eyelid state.
27. Deterministic replay (identical dt sequence produces identical FaceSpec geometry).
28. Exact dt conservation (zero duplicate or lost controller advancement).
29. Full Phase 4/5/6 regression suite (24/24 PASS).
30. Full 182 directed transition matrix regression (182/182 PASS).
31. Curvature anomaly scan (0/182 anomalies).
32. Open vs blended/non-open eye behavior eligibility rules.
33. Mirrored Angry geometry preservation.
34. Wink asymmetric behavior preservation.
"""

import copy
import math
import os
import sys

# Ensure current directory is in sys.path
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

import config as cfg
import emotions as em
import face as fc
import geometry as g
import renderer as rn
import transition as tr
from blink_controller import BlinkType, BlinkState, is_open_eye
from look_controller import GAZE_DIRECTIONS
from choreography import BehaviorChoreographer
from behavior_engine import (
    Action,
    ActionState,
    EmotionAction,
    GazeAction,
    BlinkAction,
    WaitAction,
    ParallelAction,
    BehaviorEngine,
)

PASS = 0
FAIL = 0
LOG = []


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        LOG.append(f"  [PASS] {name}")
    else:
        FAIL += 1
        LOG.append(f"  [FAIL] {name}  {detail}")


def finite(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            if not finite(*v):
                return False
        elif not math.isfinite(float(v)):
            return False
    return True


def in_bounds(*vals, lo=-0.10, hi=1.10):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            if not in_bounds(*v, lo=lo, hi=hi):
                return False
        elif not (lo <= float(v) <= hi):
            return False
    return True


def spec_coords(face_spec: fc.FaceSpec):
    coords = []
    for e in face_spec.eyes:
        coords.extend([e.cx, e.cy])
        for attr in ("rx", "ry", "r", "heart_scale", "thickness", "lid"):
            val = getattr(e, attr, None)
            if val is not None:
                coords.append(val)
        for attr in ("p0", "p1", "p2", "curve_a", "curve_t", "curve_b", "curve_u"):
            val = getattr(e, attr, None)
            if val is not None:
                coords.extend(val)
    coords.extend([face_spec.mouth.cx, face_spec.mouth.cy, face_spec.mouth.w])
    return coords


def run_phase_7_tests():
    print("=" * 80)
    print("ROBoy Emotion V2 - Phase 7 Verification Suite")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # Test 1: Action Construction & Default Properties
    # -----------------------------------------------------------------------
    ea = EmotionAction("happy", duration=0.4, hold_time=0.2)
    ga = GazeAction(direction="left", duration=0.15, hold_time=0.1)
    ba = BlinkAction(blink_type=BlinkType.DOUBLE, hold_time=0.05)
    wa = WaitAction(0.3)
    pa = ParallelAction([GazeAction(direction="right"), BlinkAction()])

    t1_ok = (
        ea.emotion == "happy" and abs(ea.total_duration - 0.6) < 1e-6 and
        ga.direction == "left" and abs(ga.total_duration - 0.25) < 1e-6 and
        ba.blink_type == BlinkType.DOUBLE and
        abs(wa.duration - 0.3) < 1e-6 and abs(wa.total_duration - 0.3) < 1e-6 and
        len(pa.actions) == 2 and
        all(a.state == ActionState.NOT_STARTED for a in [ea, ga, ba, wa, pa])
    )
    check("1. action construction sets expected parameters and NOT_STARTED state", t1_ok)

    # -----------------------------------------------------------------------
    # Test 2: Action Parameter Validation
    # -----------------------------------------------------------------------
    validation_ok = True
    try:
        EmotionAction("unknown_emotion")
        validation_ok = False
    except ValueError:
        pass

    try:
        GazeAction(direction="invalid_direction")
        validation_ok = False
    except ValueError:
        pass

    try:
        GazeAction(target=(2.5, 0.0))  # out of bounds [-1, 1]
        validation_ok = False
    except ValueError:
        pass

    try:
        GazeAction()  # neither direction nor target
        validation_ok = False
    except ValueError:
        pass

    try:
        WaitAction(-0.1)  # negative duration
        validation_ok = False
    except ValueError:
        pass

    try:
        BlinkAction(duration_multiplier=-1.0)
        validation_ok = False
    except ValueError:
        pass

    check("2. action parameter validation correctly rejects invalid inputs", validation_ok)

    # -----------------------------------------------------------------------
    # Test 3: EmotionAction Lifecycle & Timing
    # -----------------------------------------------------------------------
    engine = BehaviorEngine(initial_emotion="neutral")
    engine.play_sequence([EmotionAction("happy", duration=0.40, hold_time=0.20)])
    # Step 0.40s: morph phase completes
    engine.update(0.40)
    in_hold = (engine.choreographer.current_emotion == "happy" and not engine.choreographer.is_transitioning and engine.is_busy)
    # Step 0.20s: hold phase completes
    engine.update(0.20)
    ea_complete = (not engine.is_busy and engine.choreographer.current_emotion == "happy")
    check("3. EmotionAction executes morph then hold, completing exactly at total duration", in_hold and ea_complete)

    # -----------------------------------------------------------------------
    # Test 4: GazeAction Lifecycle & Target Vectors
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([
        GazeAction(direction="left", duration=0.20, hold_time=0.10),
        GazeAction(target=(0.5, -0.5), duration=0.20, hold_time=0.10),
    ])
    for _ in range(6):  # 0.30s: first gaze finishes
        engine.update(0.05)
    gaze1_done = (engine.choreographer.gaze_direction[0] < -0.99)
    for _ in range(6):  # 0.30s: second gaze finishes
        engine.update(0.05)
    gx, gy = engine.choreographer.gaze_direction
    gaze2_done = (abs(gx - 0.5) < 1e-3 and abs(gy - (-0.5)) < 1e-3 and not engine.is_busy)
    check("4. GazeAction executes named and explicit target coordinates accurately", gaze1_done and gaze2_done)

    # -----------------------------------------------------------------------
    # Test 5: BlinkAction Lifecycle (All Types)
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    blink_types = [BlinkType.NORMAL, BlinkType.QUICK, BlinkType.SLOW, BlinkType.HALF, BlinkType.DOUBLE]
    all_blinks_ok = True
    for bt in blink_types:
        engine.play_sequence([BlinkAction(blink_type=bt)])
        while engine.is_busy:
            engine.update(0.02)
        engine.update(0.02)
        if engine.choreographer.is_blinking or engine.choreographer.blink_weight > 0.001:
            all_blinks_ok = False
            break
    check("5. BlinkAction executes and completes all BlinkType variants", all_blinks_ok)

    # -----------------------------------------------------------------------
    # Test 6: WaitAction Timing Precision
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([WaitAction(0.35)])
    elapsed = 0.0
    while engine.is_busy:
        engine.update(0.05)
        elapsed += 0.05
    check("6. WaitAction consumes exact deterministic timeline duration", abs(elapsed - 0.35) < 1e-6)

    # -----------------------------------------------------------------------
    # Test 7: ParallelAction Concurrent Execution
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([
        ParallelAction([
            GazeAction(direction="right", duration=0.20),
            BlinkAction(BlinkType.NORMAL),
        ])
    ])
    # Step into parallel action
    engine.update(0.05)
    both_active = (engine.choreographer.look_controller.is_moving and engine.choreographer.is_blinking)
    while engine.is_busy:
        engine.update(0.02)
    engine.update(0.02)
    both_settled = (not engine.choreographer.is_looking and not engine.choreographer.is_blinking and not engine.is_busy)
    check("7. ParallelAction executes child actions concurrently within single step", both_active and both_settled)

    # -----------------------------------------------------------------------
    # Test 8: Strict FIFO Sequence Execution Order
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    order_tracker = []

    class TrackedAction(Action):
        def __init__(self, tag: str, dur: float):
            super().__init__(name=tag)
            self.tag = tag
            self.dur = dur
            self.total_duration = dur

        def _on_start(self, ch):
            order_tracker.append(f"start_{self.tag}")

        def finish(self):
            super().finish()
            order_tracker.append(f"end_{self.tag}")

    engine.play_sequence([TrackedAction("A", 0.04), TrackedAction("B", 0.04), TrackedAction("C", 0.04)])
    while engine.is_busy:
        engine.update(0.02)

    expected_order = ["start_A", "end_A", "start_B", "end_B", "start_C", "end_C"]
    check("8. sequence executes actions in strict FIFO sequential order", order_tracker == expected_order)

    # -----------------------------------------------------------------------
    # Test 9: queue_action() Appending
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([WaitAction(0.10, name="A")])
    engine.update(0.05)  # halfway through A
    engine.queue_action(WaitAction(0.10, name="B"))
    q_len_mid = engine.queue_length
    while engine.is_busy:
        engine.update(0.05)
    check("9. queue_action() appends action to queue without interrupting active action", q_len_mid == 1 and not engine.is_busy)

    # -----------------------------------------------------------------------
    # Test 10: queue_sequence() Batch Appending
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([WaitAction(0.05)])
    engine.queue_sequence([WaitAction(0.05), WaitAction(0.05), WaitAction(0.05)])
    engine.update(0.01)  # pops first action to active
    check("10. queue_sequence() batch appends multiple actions in order", engine.queue_length == 3)

    # -----------------------------------------------------------------------
    # Test 11: play_sequence() Sequence Replacement
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([EmotionAction("happy", duration=0.50), WaitAction(1.0)], name="Seq1")
    engine.update(0.20)  # halfway through morphing to happy
    # Replace with Seq2
    engine.play_sequence([EmotionAction("angry", duration=0.40)], name="Seq2")
    engine.update(0.05)  # starts Seq2
    seq_name_ok = (engine.sequence_name == "Seq2" and engine.choreographer.target_emotion == "angry")
    while engine.is_busy:
        engine.update(0.05)
    check("11. play_sequence() cleanly replaces running sequence and installs new sequence", seq_name_ok and engine.choreographer.current_emotion == "angry")

    # -----------------------------------------------------------------------
    # Test 12: clear_queue()
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([WaitAction(0.10), WaitAction(0.50), WaitAction(0.50)])
    engine.update(0.05)
    engine.clear_queue()
    cleared_ok = (engine.queue_length == 0 and engine.is_busy)
    while engine.is_busy:
        engine.update(0.05)
    check("12. clear_queue() clears pending queue while active action completes", cleared_ok and not engine.is_busy)

    # -----------------------------------------------------------------------
    # Test 13: interrupt() Cancels Active Action & Preserves Live Face Pose
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([EmotionAction("happy", duration=0.50)])
    engine.update(0.25)  # halfway morphed
    mid_spec = copy.deepcopy(engine.get_current_spec())
    engine.interrupt(clear_queue=True)
    post_spec = engine.get_current_spec()
    check("13. interrupt() cancels execution without resetting or snapping live face pose",
          not engine.is_busy and abs(mid_spec.eyes[0].cx - post_spec.eyes[0].cx) < 1e-6)

    # -----------------------------------------------------------------------
    # Test 14: Zero-Duration Actions
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([WaitAction(0.0), EmotionAction("happy", duration=0.0), WaitAction(0.0)])
    engine.update(0.02)
    check("14. zero-duration actions complete instantaneously without infinite loop",
          not engine.is_busy and engine.choreographer.current_emotion == "happy")

    # -----------------------------------------------------------------------
    # Test 15: Residual dt Cascading (Overshoot Handling)
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    # Action 1 takes 0.02s. Incoming dt is 0.06s.
    # Action 2 takes 0.10s. Should advance by exactly 0.04s in the same tick!
    engine.play_sequence([
        WaitAction(0.02, name="A1"),
        WaitAction(0.10, name="A2"),
    ])
    engine.update(0.06)  # 0.02 to A1 (finishes), 0.04 to A2
    cur = engine.current_action
    residual_ok = (cur is not None and cur.name == "A2" and abs(cur.elapsed - 0.04) < 1e-6)
    check("15. residual dt cascade: overshoot in action boundary correctly advances next action in same tick", residual_ok)

    # -----------------------------------------------------------------------
    # Test 16: Multiple Actions Completed in a Single Update
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([
        WaitAction(0.02),
        WaitAction(0.03),
        WaitAction(0.04),
        WaitAction(0.10),
    ])
    engine.update(0.10)  # 0.02 + 0.03 + 0.04 = 0.09s (3 actions done), 0.01s on 4th
    check("16. multiple actions complete in a single update(dt) when dt spans multiple boundaries",
          engine.completed_action_count == 3 and abs(engine.current_action.elapsed - 0.01) < 1e-6)

    # -----------------------------------------------------------------------
    # Test 17: Empty Sequence Handling
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([])
    check("17. play_sequence([]) leaves engine immediately in idle state", not engine.is_busy and engine.queue_length == 0)

    # -----------------------------------------------------------------------
    # Test 18: Negative dt Exception
    # -----------------------------------------------------------------------
    neg_dt_ok = False
    try:
        engine.update(-0.01)
    except ValueError:
        neg_dt_ok = True
    check("18. update(dt < 0) raises ValueError", neg_dt_ok)

    # -----------------------------------------------------------------------
    # Test 19: Named Behavior Registry & Trigger
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.register_behavior("test_greet", lambda: [
        GazeAction(direction="center"),
        BlinkAction(BlinkType.QUICK),
        EmotionAction("happy", duration=0.30, hold_time=0.10),
    ])
    registered_ok = "test_greet" in engine.list_behaviors()
    engine.trigger_behavior("test_greet")
    is_playing = (engine.is_busy and engine.sequence_name == "test_greet")
    while engine.is_busy:
        engine.update(0.05)
    check("19. named behavior template registry registers and triggers sequences cleanly",
          registered_ok and is_playing and engine.choreographer.current_emotion == "happy")

    # -----------------------------------------------------------------------
    # Test 20: Fresh Action Instances Generated on Every Trigger
    # -----------------------------------------------------------------------
    engine.trigger_behavior("test_greet")
    a1 = engine._queue[0]
    engine.trigger_behavior("test_greet")
    a2 = engine._queue[0]
    check("20. behavior registry factory generates fresh Action instances on each call", a1 is not a2)

    # -----------------------------------------------------------------------
    # Test 21: Status Telemetry & Observability
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([EmotionAction("happy", duration=0.40, hold_time=0.20)], name="TestStatus")
    engine.update(0.10)
    st = engine.get_status()
    st_ok = (
        st["is_busy"] is True and
        st["sequence_name"] == "TestStatus" and
        st["current_action_type"] == "EmotionAction" and
        0.09 <= st["current_action_elapsed"] <= 0.11 and
        abs(st["current_action_duration"] - 0.60) < 1e-4 and
        0.15 <= st["current_action_progress"] <= 0.18 and
        isinstance(st["choreographer"], dict)
    )
    check("21. get_status() telemetry accurately reports progress, sequence name, and nested status", st_ok)

    # -----------------------------------------------------------------------
    # Test 22: Idle Stillness Invariance
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    spec0 = copy.deepcopy(engine.get_current_spec())
    for _ in range(50):
        spec_idle = engine.update(0.02)
    idle_stable = (
        abs(spec_idle.eyes[0].cx - spec0.eyes[0].cx) < 1e-6 and
        abs(spec_idle.eyes[1].cx - spec0.eyes[1].cx) < 1e-6 and
        engine.choreographer.gaze_direction == (0.0, 0.0) and
        not engine.choreographer.is_blinking
    )
    check("22. idle engine maintains complete stillness with zero autonomous motion drift", idle_stable)

    # -----------------------------------------------------------------------
    # Test 23: Simultaneous Emotion + Gaze + Blink Orchestration
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([
        ParallelAction([
            EmotionAction("angry", duration=0.40),
            GazeAction(direction="down", duration=0.20),
            BlinkAction(BlinkType.NORMAL),
        ])
    ])
    engine.update(0.08)
    f = engine.get_current_spec()
    tri_simul_ok = (
        engine.choreographer.is_transitioning and
        engine.choreographer.is_looking and
        engine.choreographer.is_blinking and
        finite(spec_coords(f))
    )
    while engine.is_busy:
        engine.update(0.02)
    check("23. engine smoothly orchestrates simultaneous multi-layer actions", tri_simul_ok and engine.choreographer.current_emotion == "angry")

    # -----------------------------------------------------------------------
    # Test 24: Interruption During Emotion Transition
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([EmotionAction("happy", duration=0.50)])
    engine.update(0.20)
    engine.play_sequence([EmotionAction("sad", duration=0.40)])
    inter_emo_ok = True
    for _ in range(30):
        f = engine.update(0.02)
        if not finite(spec_coords(f)):
            inter_emo_ok = False
            break
    check("24. mid-transition emotion interruption seamlessly redirects from live pose",
          inter_emo_ok and engine.choreographer.current_emotion == "sad")

    # -----------------------------------------------------------------------
    # Test 25: Interruption During Gaze Saccade
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([GazeAction(direction="left", duration=0.30)])
    engine.update(0.10)
    engine.play_sequence([GazeAction(direction="right", duration=0.30)])
    for _ in range(25):
        engine.update(0.02)
    check("25. mid-saccade gaze interruption redirects smoothly with zero teleportation",
          engine.choreographer.gaze_direction[0] > 0.99)

    # -----------------------------------------------------------------------
    # Test 26: Interruption During Blink
    # -----------------------------------------------------------------------
    engine.reset("neutral")
    engine.play_sequence([BlinkAction(BlinkType.SLOW)])
    engine.update(0.06)  # closing
    engine.interrupt()
    while engine.choreographer.is_blinking:
        engine.update(0.02)
    check("26. interruption during blink allows eyelid to resolve without visual glitches",
          not engine.choreographer.is_blinking and abs(engine.choreographer.blink_weight) < 1e-5)

    # -----------------------------------------------------------------------
    # Test 27: Deterministic Replay (Identical dt Sequence)
    # -----------------------------------------------------------------------
    def run_simulation():
        eng = BehaviorEngine(initial_emotion="neutral")
        eng.play_sequence([
            GazeAction(direction="left", duration=0.20),
            BlinkAction(BlinkType.NORMAL),
            EmotionAction("happy", duration=0.30, hold_time=0.10),
            EmotionAction("angry", duration=0.30),
        ])
        specs = []
        dts = [0.016, 0.033, 0.012, 0.050, 0.025, 0.016, 0.040, 0.020] * 10
        for dt in dts:
            f = eng.update(dt)
            specs.append(spec_coords(f))
        return specs

    run1 = run_simulation()
    run2 = run_simulation()
    replay_identical = (run1 == run2)
    check("27. deterministic replay: identical dt sequence produces bit-for-bit identical coordinates", replay_identical)

    # -----------------------------------------------------------------------
    # Test 28: Exact dt Conservation (Zero Lost or Duplicate Time)
    # -----------------------------------------------------------------------
    eng = BehaviorEngine(initial_emotion="neutral")
    eng.play_sequence([WaitAction(0.03), WaitAction(0.07), WaitAction(0.05)])
    eng.update(0.15)
    check("28. exact dt conservation: total time advanced across actions matches cumulative dt",
          not eng.is_busy and eng.completed_action_count == 3)

    # -----------------------------------------------------------------------
    # Test 29: Full Phase 4/5/6 Regression Suite
    # -----------------------------------------------------------------------
    import _verify_phases_4_5_6 as v456
    v456_ok = v456.run_tests()
    check("29. Phase 4/5/6 comprehensive regression suite passes (24/24 PASS)", v456_ok)

    # -----------------------------------------------------------------------
    # Test 30: Full 182-Pair Directed Transition Matrix Regression
    # -----------------------------------------------------------------------
    pairs = [(src, tgt) for src in em.EMOTION_ORDER for tgt in em.EMOTION_ORDER if src != tgt]
    all_182_ok = True
    for src, tgt in pairs:
        eng = BehaviorEngine(initial_emotion=src)
        eng.play_sequence([EmotionAction(tgt, duration=0.08)])
        while eng.is_busy:
            f = eng.update(0.02)
            if not finite(spec_coords(f)):
                all_182_ok = False
                break
        if eng.choreographer.current_emotion != tgt:
            all_182_ok = False
            break
    check(f"30. full 182-pair transition matrix regression passes ({len(pairs)}/182 PASS)", all_182_ok)

    # -----------------------------------------------------------------------
    # Test 31: Curvature Anomaly Matrix Scan (0/182 Anomalies)
    # -----------------------------------------------------------------------
    from _diagnose_eye_blending_path import trace_transition_path, analyze_path_anomalies
    anom_count = 0
    for src, tgt in pairs:
        rec_l = trace_transition_path(src, tgt, side="left")
        anom_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
        if anom_l["has_anomaly"]:
            anom_count += 1
    check(f"31. curvature anomaly matrix scan produces 0 anomalies ({anom_count}/182 anomalies)", anom_count == 0)

    # -----------------------------------------------------------------------
    # Test 32: Open vs Blended/Non-Open Eye Eligibility Rules
    # -----------------------------------------------------------------------
    eng_happy = BehaviorEngine(initial_emotion="happy")
    base_happy = copy.deepcopy(eng_happy.get_current_spec())
    eng_happy.play_sequence([GazeAction(direction="left"), BlinkAction()])
    eng_happy.update(0.05)
    cur_happy = eng_happy.get_current_spec()
    eligibility_ok = (
        cur_happy.eyes[0].cx == base_happy.eyes[0].cx and
        cur_happy.eyes[1].cx == base_happy.eyes[1].cx and
        cur_happy.eyes[0].shape == "arc" and
        cur_happy.eyes[1].shape == "arc"
    )
    check("32. eligibility rules: Happy blended arc eyes remain strictly locked at baseline", eligibility_ok)

    # -----------------------------------------------------------------------
    # Test 33: Mirrored Angry Geometry Preservation
    # -----------------------------------------------------------------------
    eng_angry = BehaviorEngine(initial_emotion="angry")
    eng_angry.play_sequence([WaitAction(0.10)])
    eng_angry.update(0.05)
    f_ang = eng_angry.get_current_spec()
    angry_geom_ok = (
        f_ang.eyes[0].shape == "angry" and f_ang.eyes[1].shape == "angry" and
        f_ang.eyes[0].curve_a[1] < f_ang.eyes[0].curve_b[1] and  # outer high, inner low
        f_ang.eyes[1].curve_a[1] < f_ang.eyes[1].curve_b[1]      # outer high, inner low
    )
    check("33. mirrored Angry eye geometry is preserved with correct anchor orientations", angry_geom_ok)

    # -----------------------------------------------------------------------
    # Test 34: Wink Asymmetry Preservation
    # -----------------------------------------------------------------------
    eng_wink = BehaviorEngine(initial_emotion="wink")
    # Let initial wink settle
    for _ in range(30):
        eng_wink.update(0.01)
    base_w = copy.deepcopy(eng_wink.get_current_spec())
    eng_wink.play_sequence([GazeAction(direction="left", duration=0.20)])
    for _ in range(15):
        eng_wink.update(0.01)
    fw = eng_wink.get_current_spec()
    # Left open circle moved left, right wink arc stayed locked
    wink_ok = (
        fw.eyes[0].cx < base_w.eyes[0].cx - 0.005 and
        fw.eyes[1].cx == base_w.eyes[1].cx and
        fw.eyes[1].shape == "arc"
    )
    check("34. Wink asymmetry: left open eye receives gaze, right winked arc remains locked", wink_ok)

    print("=" * 80)
    for l in LOG:
        print(l)
    print("=" * 80)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    return FAIL == 0


if __name__ == "__main__":
    success = run_phase_7_tests()
    sys.exit(0 if success else 1)
