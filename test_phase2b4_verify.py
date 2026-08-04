"""
Phase 2B-4 Final Character Polish & Eye Engine v1.0 Verification Suite.

Validates:
1. Resolution-independent safe region and soft spring/damping boundary constraints.
2. Eye size reduction (~16.7% reduction to 75px base radius for negative space).
3. 10 official state silhouettes & character performance expressiveness.
4. Transient thinking asymmetry & non-scaling intelligent motion sequence.
5. Subtle scaling, friendly focus posture, and conservative happy compression.
6. Transition safety (intermediate poses never breach screen canvas bounds).
7. Emotional Readability Review Mode in showcase studio.
8. Eye Engine v1.0 version freeze.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eyes
from eyes import EyeEngine, VALID_STATES
from eyes.engine.config import EngineConfig
from eyes.engine.eye_pair import EyePair
from eyes.engine.eye import EyeParams
from eyes.showcase import AnimationStudioShowcase

PASS = 0
FAIL = 0


def test(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        print(f"  [OK]   {msg}")
        PASS += 1
    else:
        print(f"  [FAIL] {msg}")
        FAIL += 1


def main() -> None:
    print("=" * 70)
    print("T1: Eye Engine Version 1.0 Freeze")
    print("=" * 70)

    test(hasattr(eyes, "__version__") and eyes.__version__ == "1.0.0", "Eye Engine version is 1.0.0")
    test(getattr(eyes, "__frozen__", False) is True, "Eye Engine core is frozen")

    print("\n" + "=" * 70)
    print("T2: Resolution-Independent Safe Region & Soft Damping Constraints")
    print("=" * 70)

    cfg = EngineConfig()
    test(cfg.layout.eye_radius == 75.0, "Base eye_radius reduced to 75.0 (16.7% size reduction)")

    # Test 800x480 resolution limits
    pair_800 = EyePair()
    pair_800.configure(cfg)
    pair_800.left.look_offset_x = -500.0  # Extreme breach
    pair_800.clamp_safe(display_width=800.0, display_height=480.0)
    
    # Verify soft restoration pulls it back inside margin (margin = 480 * 0.025 = 12px)
    left_cx = pair_800.left.pos_x + pair_800.left.look_offset_x
    eff_rx = pair_800.left.radius * pair_800.left.scale_x
    test(left_cx - eff_rx >= 10.0, "Left eye geometry contained within 800x480 screen canvas")

    # Test 1920x1080 resolution limits (Resolution independence)
    pair_1080 = EyePair()
    pair_1080.configure(cfg)
    pair_1080.right.look_offset_x = 2000.0  # Extreme breach right
    pair_1080.clamp_safe(display_width=1920.0, display_height=1080.0)
    
    right_cx = pair_1080.right.pos_x + pair_1080.right.look_offset_x
    eff_rx_r = pair_1080.right.radius * pair_1080.right.scale_x
    test(right_cx + eff_rx_r <= 1920.0 - 20.0, "Right eye geometry contained within 1920x1080 screen canvas")

    print("\n" + "=" * 70)
    print("T3: 10 Official States Silhouette Expressiveness & Refinements")
    print("=" * 70)

    engine = EyeEngine(cfg)
    valid_states = engine.valid_states
    test(len(valid_states) == 10, "10 official states loaded")

    poses = {}
    for st in valid_states:
        engine.set_state(st)
        p = engine._engine.step(500.0)
        poses[st] = p.copy()

    happy_p = poses["happy"]
    sleepy_p = poses["sleepy"]
    surprised_p = poses["surprised"]
    focus_p = poses["focus"]
    thinking_p = poses["thinking"]
    caring_p = poses["caring"]
    sad_p = poses["sad"]
    listening_p = poses["listening"]
    speaking_p = poses["speaking"]
    calm_p = poses["calm"]

    # Refinement 6 & Silhouette: Happy smiling inverted lower lid arc
    test(happy_p.left.lower_lid_curvature <= -0.30, "Happy has distinct smiling lower lid arc")
    test(happy_p.left.squash <= 0.10, "Happy compression is conservative (squash <= 0.10)")

    # Silhouette: Sleepy heavy upper lid droop
    test(sleepy_p.left.lid_openness <= 0.45, "Sleepy has heavy upper lid droop")

    # Refinement 4: Surprised favors eyelid openness over large radius increases
    test(surprised_p.left.lid_openness >= 1.10, "Surprised favors wide eyelid openness (>= 1.10)")
    test(surprised_p.left.radius <= cfg.layout.eye_radius * 1.10, "Surprised radius increase is subtle (<= 1.10x)")

    # Refinement 5: Focus friendly concentration
    test(0.55 <= focus_p.left.scale_y <= 0.64, "Focus compression is friendly (0.55 <= scale_y <= 0.64)")
    test(focus_p.left.squash <= 0.12, "Focus squash is friendly (squash <= 0.12)")

    # Refinement 2 & Task 5: Thinking baseline symmetric target pose
    st_thinking = engine._engine.state_machine._states["thinking"]
    target_p = st_thinking.target_pose
    test(target_p.left.rotation == 0.0 and target_p.right.rotation == 0.0, "Thinking base target pose is symmetric")
    
    # Transient thinking asymmetry check during loop execution
    p_think_loop = engine._engine.step(1000.0)
    test(abs(p_think_loop.left.look_offset_x) > 2.0, "Thinking executes slow look scan in loop")

    # Silhouette: Sad drooping upper lids and downcast gaze
    test(sad_p.left.upper_lid_curvature > 0.15, "Sad has drooping upper lid curvature")
    test(sad_p.left.look_offset_y > 2.0, "Sad has downcast gaze")

    # Silhouette: Listening inward lean & widened eyes
    test(listening_p.left.lid_openness >= 1.04, "Listening has widened attentive eyes")
    test(listening_p.left.pos_x > engine._engine._base_pose.left.pos_x, "Listening has inward lean posture")

    # Silhouette: Caring soft rounded eyelids & inner tilt
    test(caring_p.left.upper_lid_curvature < 0.0, "Caring has soft rounded upper lid curvature")
    test(caring_p.left.rotation > 0.0, "Caring has gentle inner tilt")

    # Silhouette: Calm clean relaxed geometry
    test(abs(calm_p.left.scale_x - 1.0) <= 0.05 and abs(calm_p.left.scale_y - 1.0) <= 0.05, "Calm has clean relaxed neutral geometry")

    # Silhouette: Speaking active posture
    test(speaking_p.left.lid_openness >= 1.02, "Speaking has active expressive posture")

    print("\n" + "=" * 70)
    print("T4: Transition Canvas Safety Verification")
    print("=" * 70)

    # Test rapid transitions across all canonical state pairs
    state_pairs = [
        ("calm", "listening"),
        ("listening", "thinking"),
        ("thinking", "speaking"),
        ("speaking", "happy"),
        ("happy", "caring"),
        ("caring", "calm"),
        ("surprised", "happy"),
        ("focus", "speaking"),
    ]

    all_transitions_safe = True
    for src, dst in state_pairs:
        engine.set_state(src)
        engine._engine.step(300.0)
        engine.set_state(dst)
        for _ in range(20):
            step_pose = engine._engine.step(20.0)
            for eye in (step_pose.left, step_pose.right):
                cx = eye.pos_x + eye.look_offset_x + eye.micro_offset_x + eye.bounce_offset_x
                cy = eye.pos_y + eye.look_offset_y + eye.micro_offset_y + eye.bounce_offset_y
                rx = eye.radius * (eye.scale_x + eye.stretch)
                ry = eye.radius * (eye.scale_y + eye.squash)
                r_eff = max(rx, ry)
                if cx - r_eff < 0 or cx + r_eff > 800 or cy - r_eff < 0 or cy + r_eff > 480:
                    all_transitions_safe = False

    test(all_transitions_safe, "All transition intermediate frames remain strictly inside 800x480 canvas")

    print("\n" + "=" * 70)
    print("T5: Emotional Readability Review Mode Verification")
    print("=" * 70)

    try:
        import pygame
        pygame.init()
        showcase = AnimationStudioShowcase()
        test(hasattr(showcase, "readability_review_mode"), "Showcase supports readability_review_mode")
        showcase.handle_key_down(pygame.K_e)
        test(showcase.readability_review_mode is True, "K_e toggles Emotional Readability Review Mode ON")
        showcase.handle_key_down(pygame.K_e)
        test(showcase.readability_review_mode is False, "K_e toggles Emotional Readability Review Mode OFF")
    except Exception as ex:
        test(False, f"Showcase review mode test failed: {ex}")

    print("\n" + "=" * 70)
    print(f"RESULTS: PASS = {PASS}   FAIL = {FAIL}")
    print("=" * 70)

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
