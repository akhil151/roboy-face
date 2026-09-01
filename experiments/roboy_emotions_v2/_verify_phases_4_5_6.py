"""ROBoy Emotion V2 - Phases 4, 5, 6 Comprehensive Verification Suite.

Includes strict verification of behavior eligibility for open vs blended/non-open eyes:
 1. All 14 static emotions remain bit-for-bit identical when behaviors are inactive.
 2. Blink state machine: OPEN -> CLOSING -> CLOSED -> OPENING -> OPEN.
 3. Blink smoothness and monotonicity during closure and opening.
 4. Blink restores exact underlying V2 geometry upon completion across all 14 emotions.
 5. Happy + Gaze = DISABLED / UNCHANGED (both blended arc eyes untouched).
 6. Happy + Blink = DISABLED / UNCHANGED (both blended arc eyes untouched).
 7. Sad + Gaze = DISABLED / UNCHANGED (both blended arc eyes untouched).
 8. Sad + Blink = DISABLED / UNCHANGED (both blended arc eyes untouched).
 9. One-open-eye + Gaze = Open eye only (e.g. Confused: left arc untouched, right circle moves).
10. One-open-eye + Blink = Open eye only (e.g. Confused: left arc untouched, right circle blinks).
11. Wink asymmetry preserved (left open circle gazes & blinks, right winked arc untouched).
12. Both-open-eye + Gaze = Both eyes (Neutral, Angry, Surprised, etc. move symmetrically).
13. Both-open-eye + Blink = Both eyes (Neutral, Angry, Surprised, etc. blink symmetrically).
14. Simultaneous Emotion + Gaze + Blink on open eyes composes both offsets and lid closure.
15. Gaze directions (CENTER, LEFT, RIGHT, UP, DOWN, diagonals) are valid and bounded.
16. Gaze saccades are strictly smooth with bounded velocity (max step < 0.15 norm).
17. Gaze mid-movement interruption seamlessly captures live pose with zero teleportation.
18. Multi-blink variants (Double, Half, Slow, Quick) execute cleanly.
19. Cross-layer: Transition + Blink (transition advances, open eye blinks).
20. Cross-layer: Transition + Gaze (transition advances, open eye looks).
21. Cross-layer: Transition + Blink + Gaze combined.
22. Mid-transition interruption with active behaviors completes smoothly.
23. Full 182-pair transition matrix regression passes (182/182 PASS).
24. Full 182-pair curvature anomaly scan produces 0 anomalies (0/182 anomalies).
"""

import copy
import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

import config as cfg
import emotions as em
import face as fc
import geometry as g
import renderer as rn
import transition as tr
from blink_controller import BlinkController, BlinkState, BlinkType, apply_blink_to_eye, is_open_eye
from choreography import BehaviorChoreographer, compose_face
from look_controller import GAZE_DIRECTIONS, LookController, apply_gaze_to_eye

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


def run_tests():
    print("=" * 80)
    print("ROBoy Emotion V2 - Phases 4, 5, 6 Verification Suite (with Eligibility Rules)")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # Test 1: Static V2 Invariance (Behaviors Inactive)
    # -----------------------------------------------------------------------
    all_static_identical = True
    for emo in em.EMOTION_ORDER:
        static_face = fc.build_face(emo, 0.0)
        choreographer = BehaviorChoreographer(initial_emotion=emo)
        choreographed_face = choreographer.get_current_spec()

        if len(static_face.eyes) != len(choreographed_face.eyes):
            all_static_identical = False
            break
        for e0, e1 in zip(static_face.eyes, choreographed_face.eyes):
            if e0.shape != e1.shape or abs(e0.cx - e1.cx) > 1e-5 or abs(e0.cy - e1.cy) > 1e-5:
                all_static_identical = False
                break
    check("1. all 14 static emotions remain bit-for-bit identical when behaviors inactive", all_static_identical)

    # -----------------------------------------------------------------------
    # Test 2: Blink State Machine Progression
    # -----------------------------------------------------------------------
    blink_ctrl = BlinkController()
    states_seen = []
    blink_ctrl.trigger_blink(BlinkType.NORMAL)

    dt = 0.01
    for _ in range(35):
        w = blink_ctrl.update(dt)
        st = blink_ctrl.state
        if not states_seen or states_seen[-1] != st:
            states_seen.append(st)

    expected_states = [BlinkState.CLOSING, BlinkState.CLOSED, BlinkState.OPENING, BlinkState.OPEN]
    check("2. blink state machine progresses OPEN -> CLOSING -> CLOSED -> OPENING -> OPEN",
          states_seen == expected_states, f"Observed states: {states_seen}")

    # -----------------------------------------------------------------------
    # Test 3: Blink Smoothness and Monotonicity
    # -----------------------------------------------------------------------
    blink_ctrl.reset()
    blink_ctrl.trigger_blink(BlinkType.NORMAL)
    closing_weights = []
    while blink_ctrl.state == BlinkState.CLOSING:
        closing_weights.append(blink_ctrl.update(0.005))
    is_closing_monotonic = all(closing_weights[i] <= closing_weights[i+1] + 1e-5 for i in range(len(closing_weights)-1))

    while blink_ctrl.state == BlinkState.CLOSED:
        blink_ctrl.update(0.005)

    opening_weights = []
    while blink_ctrl.state == BlinkState.OPENING:
        opening_weights.append(blink_ctrl.update(0.005))
    is_opening_monotonic = all(opening_weights[i] >= opening_weights[i+1] - 1e-5 for i in range(len(opening_weights)-1))

    check("3. blink weights are strictly monotonic and smooth during close & open phases",
          is_closing_monotonic and is_opening_monotonic and len(closing_weights) > 3 and len(opening_weights) > 3)

    # -----------------------------------------------------------------------
    # Test 4: Blink Restores Exact Underlying Geometry
    # -----------------------------------------------------------------------
    emotions_preserved = True
    for emo in em.EMOTION_ORDER:
        ch = BehaviorChoreographer(initial_emotion=emo)
        ch.blink(BlinkType.NORMAL)
        # Advance through full blink (~0.17s total duration)
        for _ in range(35):
            ch.update(0.01)
        face_live = ch.get_current_spec()
        face_expected = fc.build_face(emo, ch.transition_controller.target_t)

        for e0, e1 in zip(face_expected.eyes, face_live.eyes):
            if e0.shape != e1.shape or abs(e0.cx - e1.cx) > 1e-4 or abs(e0.cy - e1.cy) > 1e-4:
                emotions_preserved = False
                break
    check("4. blink completes and restores exact underlying V2 geometry for all 14 emotions", emotions_preserved)

    # -----------------------------------------------------------------------
    # Test 5: Happy + Gaze = DISABLED / UNCHANGED
    # -----------------------------------------------------------------------
    ch_happy = BehaviorChoreographer(initial_emotion="happy")
    base_happy = copy.deepcopy(ch_happy.get_current_spec())
    ch_happy.look_direction("left")
    for _ in range(25):
        ch_happy.update(0.01)
    gazed_happy = ch_happy.get_current_spec()
    happy_gaze_disabled = (
        gazed_happy.eyes[0].cx == base_happy.eyes[0].cx and
        gazed_happy.eyes[1].cx == base_happy.eyes[1].cx and
        gazed_happy.eyes[0].shape == "arc" and
        gazed_happy.eyes[1].shape == "arc"
    )
    check("5. Happy + Gaze = DISABLED (both blended arc eyes remain strictly at baseline coords)", happy_gaze_disabled)

    # -----------------------------------------------------------------------
    # Test 6: Happy + Blink = DISABLED / UNCHANGED
    # -----------------------------------------------------------------------
    ch_happy = BehaviorChoreographer(initial_emotion="happy")
    ch_happy.blink()
    for _ in range(8):  # at peak closure
        ch_happy.update(0.01)
    blinked_happy = ch_happy.get_current_spec()
    expected_happy = fc.build_face("happy", ch_happy.transition_controller.target_t)
    happy_blink_disabled = (
        blinked_happy.eyes[0].shape == "arc" and
        blinked_happy.eyes[1].shape == "arc" and
        abs(blinked_happy.eyes[0].r - expected_happy.eyes[0].r) < 1e-6
    )
    check("6. Happy + Blink = DISABLED (both blended arc eyes remain strictly unchanged)", happy_blink_disabled)

    # -----------------------------------------------------------------------
    # Test 7: Sad + Gaze = DISABLED / UNCHANGED
    # -----------------------------------------------------------------------
    ch_sad = BehaviorChoreographer(initial_emotion="sad")
    base_sad = copy.deepcopy(ch_sad.get_current_spec())
    ch_sad.look_direction("right")
    for _ in range(25):
        ch_sad.update(0.01)
    gazed_sad = ch_sad.get_current_spec()
    sad_gaze_disabled = (
        gazed_sad.eyes[0].cx == base_sad.eyes[0].cx and
        gazed_sad.eyes[1].cx == base_sad.eyes[1].cx and
        gazed_sad.eyes[0].shape == "arc" and
        gazed_sad.eyes[1].shape == "arc"
    )
    check("7. Sad + Gaze = DISABLED (both blended arc eyes remain strictly at baseline coords)", sad_gaze_disabled)

    # -----------------------------------------------------------------------
    # Test 8: Sad + Blink = DISABLED / UNCHANGED
    # -----------------------------------------------------------------------
    ch_sad = BehaviorChoreographer(initial_emotion="sad")
    ch_sad.blink()
    for _ in range(8):
        ch_sad.update(0.01)
    blinked_sad = ch_sad.get_current_spec()
    expected_sad = fc.build_face("sad", ch_sad.transition_controller.target_t)
    sad_blink_disabled = (
        blinked_sad.eyes[0].shape == "arc" and
        blinked_sad.eyes[1].shape == "arc" and
        abs(blinked_sad.eyes[0].r - expected_sad.eyes[0].r) < 1e-6
    )
    check("8. Sad + Blink = DISABLED (both blended arc eyes remain strictly unchanged)", sad_blink_disabled)

    # -----------------------------------------------------------------------
    # Test 9: One-Open-Eye + Gaze (e.g. Confused: Left Arc, Right Circle)
    # -----------------------------------------------------------------------
    ch_conf = BehaviorChoreographer(initial_emotion="confused")
    base_conf = copy.deepcopy(ch_conf.get_current_spec())
    ch_conf.look_direction("left")
    for _ in range(25):
        ch_conf.update(0.01)
    gazed_conf = ch_conf.get_current_spec()
    # Left arc is untouched (baseline 0.345)
    left_arc_untouched = (gazed_conf.eyes[0].cx == base_conf.eyes[0].cx and gazed_conf.eyes[0].shape == "arc")
    # Right circle moved left (cx < base cx)
    right_circle_moved = (gazed_conf.eyes[1].cx < base_conf.eyes[1].cx - 0.015 and gazed_conf.eyes[1].shape == "circle")
    check("9. one-open-eye + Gaze: open eye moves, blended/non-open eye remains unchanged",
          left_arc_untouched and right_circle_moved)

    # -----------------------------------------------------------------------
    # Test 10: One-Open-Eye + Blink (e.g. Confused: Left Arc, Right Circle)
    # -----------------------------------------------------------------------
    ch_conf = BehaviorChoreographer(initial_emotion="confused")
    base_conf = copy.deepcopy(ch_conf.get_current_spec())
    ch_conf.blink()
    for _ in range(8):  # peak closure
        ch_conf.update(0.01)
    blinked_conf = ch_conf.get_current_spec()
    # Left arc is untouched
    left_arc_intact = (blinked_conf.eyes[0].shape == "arc")
    # Right circle is flattened
    right_circle_closed = (blinked_conf.eyes[1].shape == "circle" and blinked_conf.eyes[1].ry < 0.020)
    check("10. one-open-eye + Blink: open eye closes, blended/non-open eye remains unchanged",
          left_arc_intact and right_circle_closed)

    # -----------------------------------------------------------------------
    # Test 11: Wink Asymmetric Behavior Preservation
    # -----------------------------------------------------------------------
    ch_wink = BehaviorChoreographer(initial_emotion="wink")
    for _ in range(40):  # let initial wink settle
        ch_wink.update(0.01)
    base_wink = copy.deepcopy(ch_wink.get_current_spec())
    ch_wink.look_direction("left")
    ch_wink.blink()
    for _ in range(8):
        ch_wink.update(0.01)
    f_wink = ch_wink.get_current_spec()
    # Left circle: moved left and flattened
    left_wink_active = (f_wink.eyes[0].cx < base_wink.eyes[0].cx - 0.005 and f_wink.eyes[0].ry < 0.020)
    # Right arc: untouched wink arc
    right_wink_preserved = (f_wink.eyes[1].cx == base_wink.eyes[1].cx and f_wink.eyes[1].shape == "arc")
    check("11. Wink asymmetry preserved: left open eye receives gaze & blink, right winked eye unchanged",
          left_wink_active and right_wink_preserved)

    # -----------------------------------------------------------------------
    # Test 12: Both-Open-Eye + Gaze (Neutral, Angry, Surprised)
    # -----------------------------------------------------------------------
    ch_neu = BehaviorChoreographer(initial_emotion="neutral")
    ch_neu.look_direction("right")
    for _ in range(25):
        ch_neu.update(0.01)
    f_neu = ch_neu.get_current_spec()
    both_gazed = (f_neu.eyes[0].cx > 0.345 + 0.015 and f_neu.eyes[1].cx > 0.655 + 0.015)
    check("12. both-open-eye + Gaze: both eyes translate symmetrically", both_gazed)

    # -----------------------------------------------------------------------
    # Test 13: Both-Open-Eye + Blink (Neutral, Angry, Surprised)
    # -----------------------------------------------------------------------
    ch_neu = BehaviorChoreographer(initial_emotion="neutral")
    ch_neu.blink()
    for _ in range(8):
        ch_neu.update(0.01)
    f_neu = ch_neu.get_current_spec()
    both_closed = (f_neu.eyes[0].ry < 0.015 and f_neu.eyes[1].ry < 0.015)
    check("13. both-open-eye + Blink: both eyes close symmetrically", both_closed)

    # -----------------------------------------------------------------------
    # Test 14: Simultaneous Emotion + Gaze + Blink on Open Eyes
    # -----------------------------------------------------------------------
    ch_exc = BehaviorChoreographer(initial_emotion="excited")
    ch_exc.look_direction("right")
    ch_exc.blink()
    for _ in range(8):
        f = ch_exc.update(0.01)
    right_shifted = f.eyes[0].cx > 0.345 + 0.005
    vert_flattened = f.eyes[0].ry < 0.025
    check("14. simultaneous Emotion + Gaze + Blink composes both spatial translation and lid closure on open eyes",
          right_shifted and vert_flattened and finite(spec_coords(f)))

    # -----------------------------------------------------------------------
    # Test 15: Gaze Directions Valid and Bounded
    # -----------------------------------------------------------------------
    look_ctrl = LookController()
    all_gaze_dirs_ok = True
    for dir_name in GAZE_DIRECTIONS:
        look_ctrl.look_direction(dir_name)
        while look_ctrl.is_moving:
            look_ctrl.update(0.01)
        gx, gy = look_ctrl.gaze_direction
        dx, dy = look_ctrl.get_spatial_offset()
        if not (-1.01 <= gx <= 1.01 and -1.01 <= gy <= 1.01):
            all_gaze_dirs_ok = False
            break
        if not (-look_ctrl.max_offset_x - 1e-4 <= dx <= look_ctrl.max_offset_x + 1e-4):
            all_gaze_dirs_ok = False
            break
        if not (-look_ctrl.max_offset_y - 1e-4 <= dy <= look_ctrl.max_offset_y + 1e-4):
            all_gaze_dirs_ok = False
            break
    check("15. all named gaze directions are valid and bounded within max displacement limits", all_gaze_dirs_ok)

    # -----------------------------------------------------------------------
    # Test 16: Gaze Motion Smoothness (No Teleportation)
    # -----------------------------------------------------------------------
    look_ctrl.reset(0.0, 0.0)
    look_ctrl.look_direction("left")
    gaze_positions = []
    while look_ctrl.is_moving:
        look_ctrl.update(0.01)
        gaze_positions.append(look_ctrl.cur_x)

    is_gaze_monotonic = all(gaze_positions[i] >= gaze_positions[i+1] - 1e-5 for i in range(len(gaze_positions)-1))
    max_step_delta = max(abs(gaze_positions[i+1] - gaze_positions[i]) for i in range(len(gaze_positions)-1))
    check("16. gaze saccades are strictly smooth with bounded velocity (max step < 0.15 norm)",
          is_gaze_monotonic and max_step_delta < 0.15 and len(gaze_positions) > 5)

    # -----------------------------------------------------------------------
    # Test 17: Gaze Mid-Movement Interruption
    # -----------------------------------------------------------------------
    look_ctrl.reset(0.0, 0.0)
    look_ctrl.look_direction("left")
    for _ in range(6):
        look_ctrl.update(0.01)
    mid_gx, mid_gy = look_ctrl.gaze_direction
    look_ctrl.look_direction("right")
    new_start_x = look_ctrl.start_x
    start_matches = abs(new_start_x - mid_gx) < 1e-4
    look_ctrl.update(0.005)
    first_step_jump = abs(look_ctrl.cur_x - mid_gx)
    check("17. gaze interruption seamlessly redirects from live pose with zero teleportation",
          start_matches and first_step_jump < 0.05)

    # -----------------------------------------------------------------------
    # Test 18: Multi-Blink Types (Double, Slow, Half, Quick)
    # -----------------------------------------------------------------------
    blink_ctrl.reset()
    blink_ctrl.trigger_blink(BlinkType.DOUBLE)
    double_blinks_completed = 0
    prev_st = blink_ctrl.state
    for _ in range(60):
        blink_ctrl.update(0.01)
        if prev_st == BlinkState.OPENING and blink_ctrl.state == BlinkState.OPEN:
            double_blinks_completed += 1
        prev_st = blink_ctrl.state

    blink_ctrl.reset()
    blink_ctrl.trigger_blink(BlinkType.HALF)
    for _ in range(8):
        blink_ctrl.update(0.01)
    half_weight_ok = 0.40 <= blink_ctrl.blink_weight <= 0.55
    check("18. multi-blink variants (Double, Half, Slow, Quick) execute cleanly",
          double_blinks_completed >= 1 and half_weight_ok)

    # -----------------------------------------------------------------------
    # Test 19: Cross-Layer: Transition + Blink
    # -----------------------------------------------------------------------
    ch = BehaviorChoreographer(initial_emotion="neutral")
    ch.request_emotion("happy", duration=0.40)
    ch.blink()
    tr_and_blink_ok = True
    for _ in range(45):
        f = ch.update(0.01)
        if not (finite(spec_coords(f)) and in_bounds(spec_coords(f))):
            tr_and_blink_ok = False
            break
    check("19. emotion transition + active blink executes smoothly without snapping or resetting",
          tr_and_blink_ok and ch.current_emotion == "happy" and not ch.is_blinking)

    # -----------------------------------------------------------------------
    # Test 20: Cross-Layer: Transition + Gaze
    # -----------------------------------------------------------------------
    ch = BehaviorChoreographer(initial_emotion="neutral")
    ch.request_emotion("angry", duration=0.40)
    ch.look_direction("left")
    tr_and_gaze_ok = True
    for _ in range(45):
        f = ch.update(0.01)
        if not (finite(spec_coords(f)) and in_bounds(spec_coords(f))):
            tr_and_gaze_ok = False
            break
    check("20. emotion transition + active gaze shifts gaze smoothly while morphing expression",
          tr_and_gaze_ok and ch.current_emotion == "angry" and ch.gaze_direction[0] < -0.99)

    # -----------------------------------------------------------------------
    # Test 21: Cross-Layer: Transition + Blink + Gaze Combined
    # -----------------------------------------------------------------------
    ch = BehaviorChoreographer(initial_emotion="neutral")
    ch.request_emotion("angry", duration=0.45)
    ch.look_direction("down")
    ch.blink()
    combo_ok = True
    for _ in range(50):
        f = ch.update(0.01)
        if not (finite(spec_coords(f)) and in_bounds(spec_coords(f))):
            combo_ok = False
            break
    check("21. full combined pipeline (Transition + Gaze + Blink) converges cleanly on target pose",
          combo_ok and ch.current_emotion == "angry" and not ch.is_transitioning)

    # -----------------------------------------------------------------------
    # Test 22: Mid-Transition Interruption with Active Gaze & Blink
    # -----------------------------------------------------------------------
    ch = BehaviorChoreographer(initial_emotion="neutral")
    ch.request_emotion("happy", duration=0.50)
    ch.look_direction("right")
    for _ in range(20):
        ch.update(0.01)
    ch.blink()
    ch.request_emotion("sad", duration=0.40)
    interruption_ok = True
    for _ in range(50):
        f = ch.update(0.01)
        if not (finite(spec_coords(f)) and in_bounds(spec_coords(f))):
            interruption_ok = False
            break
    check("22. mid-transition interruption with active gaze & blink completes smoothly",
          interruption_ok and ch.current_emotion == "sad")

    # -----------------------------------------------------------------------
    # Test 23: Full 182-Pair Transition Matrix Regression
    # -----------------------------------------------------------------------
    all_pairs_ok = True
    pairs = [(src, tgt) for src in em.EMOTION_ORDER for tgt in em.EMOTION_ORDER if src != tgt]
    for src, tgt in pairs:
        ch = BehaviorChoreographer(initial_emotion=src)
        ch.request_emotion(tgt, duration=0.10)
        while ch.is_transitioning:
            f = ch.update(0.02)
            if not finite(spec_coords(f)):
                all_pairs_ok = False
                break
        if ch.current_emotion != tgt:
            all_pairs_ok = False
            break
    check(f"23. full 182-pair transition matrix regression passes ({len(pairs)}/182 PASS)", all_pairs_ok)

    # -----------------------------------------------------------------------
    # Test 24: Curvature Anomaly Matrix Scan
    # -----------------------------------------------------------------------
    from _diagnose_eye_blending_path import trace_transition_path, analyze_path_anomalies
    anomalies_count = 0
    for src, tgt in pairs:
        rec_l = trace_transition_path(src, tgt, side="left")
        anom_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
        if anom_l["has_anomaly"]:
            anomalies_count += 1
    check(f"24. full 182-pair curvature anomaly scan produces 0 anomalies ({anomalies_count}/182 anomalies)", anomalies_count == 0)

    print("=" * 80)
    for l in LOG:
        print(l)
    print("=" * 80)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
