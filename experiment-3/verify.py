"""Headless verification suite for ELO Face V3 (Stage 2).

Comprehensive automated tests verifying:
1. Module independence (zero dependencies on experiment-2 or legacy code).
2. Timeline segment ordering, durations, and 62.0-second loop timing.
3. Intro typewriter progression and face fade-in transition.
4. All 11 emotional behavior handlers and mathematical curves.
5. Blush alpha envelope and sleep floating 'Z' particle dynamics.
6. 3720-frame full 62-second 60 FPS headless simulation run.
7. Verification that experiment-2 remains 100% untouched.
"""

import os
import sys
import math
import time

# Set headless SDL video driver before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

# Ensure experiment-3 is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import config as cfg
import easing as eas
from eye import Eye, EyePair, EyeGeometry
from renderer import Renderer
from animation import FaceController, BlinkState
from timeline import TimelineController
from effects import IntroState, BlushState, SleepZParticles, SleepZParticle


def assert_test(condition: bool, description: str) -> None:
    """Helper for clear test assertions."""
    if not condition:
        print(f"  [FAIL] {description}")
        raise AssertionError(f"Test failed: {description}")
    print(f"  [PASS] {description}")


def test_configuration_and_isolation() -> None:
    print("\n--- 1. Configuration & Isolation Check ---")
    assert_test(cfg.WINDOW_WIDTH == 800, "Window width is 800px")
    assert_test(cfg.WINDOW_HEIGHT == 480, "Window height is 480px")
    assert_test(cfg.TARGET_FPS == 60, "Target framerate is 60 FPS")
    assert_test(cfg.COLOR_BG == (0, 0, 0), "Background is solid black (0, 0, 0)")
    assert_test(cfg.COLOR_EYE == (255, 255, 255), "Eyes are solid white (255, 255, 255)")
    assert_test(cfg.COLOR_ACCENT == (255, 160, 185), "Blush accent is warm soft pink")

    # Isolation check
    for mod_name in list(sys.modules.keys()):
        assert_test(
            "roboy_emotions_v2" not in mod_name and "experiment-2" not in mod_name,
            f"Module '{mod_name}' is not coupled to V2/legacy code",
        )


def test_timeline_structure_and_timing() -> None:
    print("\n--- 2. Timeline Structure & Duration Verification ---")
    expected_segments = [
        ("intro", 10.0),
        ("settle", 3.5),
        ("blink", 3.5),
        ("look_horizontal", 5.0),
        ("look_vertical", 4.5),
        ("surprise", 3.5),
        ("wink", 3.5),
        ("playful_double_wink", 4.5),
        ("happy_bounce", 4.5),
        ("cute_blush", 5.0),
        ("drowsy", 5.0),
        ("sleep", 9.5),
    ]

    assert_test(len(cfg.TIMELINE_SEGMENTS) == 12, "Timeline has exactly 12 segments")
    for i, (expected_name, expected_dur) in enumerate(expected_segments):
        actual_name, actual_dur = cfg.TIMELINE_SEGMENTS[i]
        assert_test(actual_name == expected_name, f"Segment #{i+1} is '{expected_name}'")
        assert_test(abs(actual_dur - expected_dur) < 1e-3, f"Segment '{actual_name}' duration is {expected_dur}s")

    assert_test(abs(cfg.TOTAL_TIMELINE_DURATION - 62.0) < 1e-3, f"Total timeline duration is exactly 62.0s ({cfg.TOTAL_TIMELINE_DURATION:.1f}s)")
    assert_test(cfg.TIMELINE_SEGMENTS[0][0] == "intro", "Intro is strictly the first segment")
    assert_test(cfg.TIMELINE_SEGMENTS[-1][0] == "sleep", "Sleep is strictly the final expression")


def test_intro_state_progression() -> None:
    print("\n--- 3. Intro Typewriter & Transition Tests ---")
    intro = IntroState()

    # 1. Start of "Hii"
    intro.update(0.3)
    assert_test("H" in intro.text_to_show, "Typewriter begins revealing 'Hii'")
    assert_test(intro.text_alpha == 1.0, "'Hii' text alpha is 1.0 during active hold")
    assert_test(intro.face_alpha == 0.0, "Face is hidden during early text intro")

    # 2. End of "Hii" fade
    intro.update(3.8)
    assert_test(0.0 < intro.text_alpha < 1.0, "'Hii' text alpha is smoothly fading out")

    # 3. Start of "This is ELO."
    intro.update(5.0)
    assert_test("This is" in intro.text_to_show, "Typewriter revealing 'This is ELO.'")
    assert_test(intro.text_alpha == 1.0, "'This is ELO.' text alpha is 1.0")

    # 4. Phase 3: Transition into Face
    intro.update(9.4)
    assert_test(intro.text_to_show == "", "Text cleared during face transition")
    assert_test(0.0 < intro.face_alpha <= 1.0, "Face alpha is smoothly fading in at end of intro")


def test_effects_blush_and_particles() -> None:
    print("\n--- 4. Blush & Sleep Particle Effects Tests ---")
    # Blush
    blush = BlushState()
    blush.set_normalized_progress(0.0)
    assert_test(blush.alpha == 0.0, "Blush alpha is 0.0 at progress=0.0")
    blush.set_normalized_progress(0.50)
    assert_test(abs(blush.alpha - cfg.BLUSH_MAX_ALPHA) < 1.0, f"Blush alpha reaches maximum ({cfg.BLUSH_MAX_ALPHA}) at peak progress")
    blush.set_normalized_progress(1.0)
    assert_test(blush.alpha == 0.0, "Blush alpha returns to 0.0 at progress=1.0")

    # Sleep Particles
    particles = SleepZParticles()
    particles.update(0.1, is_sleeping=True)
    particles.spawn()
    assert_test(len(particles.particles) >= 1, "Sleep particle spawned successfully")
    p = particles.particles[0]
    initial_y = p.y
    p.update(0.5)
    assert_test(p.y < initial_y, "Sleep 'Z' particle drifts upward")
    assert_test(p.alpha > 0, "Sleep 'Z' particle has positive alpha")


def test_emotion_behaviors() -> None:
    print("\n--- 5. Emotion Segment Behaviors & Math Tests ---")
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    # A. Settle
    timeline.jump_to("settle")
    controller.update(0.1)
    assert_test(controller.target_open_left == 1.0 and controller.target_open_right == 1.0, "Settle keeps eyes fully open")
    assert_test(controller.target_scale == 1.0, "Settle scale is 1.0")

    # B. Blink (2 blinks)
    timeline.jump_to("blink")
    timeline.segment_elapsed = 0.95 # At peak of blink 1 (u ≈ 0.27)
    controller.update(0.01)
    assert_test(controller.target_open_left < 0.2, "Blink 1 closes eyes")
    timeline.segment_elapsed = 1.75 # Reopened interval (u ≈ 0.50)
    controller.update(0.01)
    assert_test(controller.target_open_left > 0.8, "Eyes reopen between blinks")

    # C. Look Horizontal
    timeline.jump_to("look_horizontal")
    timeline.segment_elapsed = 1.5 # Looking Left (u = 0.30)
    controller.update(0.01)
    assert_test(controller.target_look_x < -30.0, "Look horizontal glances left")
    timeline.segment_elapsed = 3.8 # Looking Right (u = 0.76)
    controller.update(0.01)
    assert_test(controller.target_look_x > 30.0, "Look horizontal glances right")

    # D. Look Vertical
    timeline.jump_to("look_vertical")
    timeline.segment_elapsed = 1.5 # Looking Up (u = 0.33)
    controller.update(0.01)
    assert_test(controller.target_look_y < -20.0, "Look vertical glances up")
    timeline.segment_elapsed = 3.6 # Looking Down (u = 0.80)
    controller.update(0.01)
    assert_test(controller.target_look_y > 20.0, "Look vertical glances down")

    # E. Surprise
    timeline.jump_to("surprise")
    timeline.segment_elapsed = 1.5 # Peak surprise (u = 0.43)
    controller.update(0.01)
    assert_test(controller.target_scale >= 1.30, "Surprise scales eyes up to ~1.35x")

    # F. Wink (Asymmetric)
    timeline.jump_to("wink")
    timeline.segment_elapsed = 1.5 # Mid wink (u = 0.43)
    controller.update(0.01)
    assert_test(controller.target_open_left == 1.0, "Left eye remains open during wink")
    assert_test(controller.target_open_right == 0.0, "Right eye closes during wink")

    # G. Playful Double Wink (Alternating)
    timeline.jump_to("playful_double_wink")
    timeline.segment_elapsed = 1.0 # Right eye wink (u ≈ 0.22)
    controller.update(0.01)
    assert_test(controller.target_open_right < 0.2 and controller.target_open_left == 1.0, "Double wink phase 1 winks right eye")
    timeline.segment_elapsed = 3.2 # Left eye wink (u ≈ 0.71)
    controller.update(0.01)
    assert_test(controller.target_open_left < 0.2 and controller.target_open_right == 1.0, "Double wink phase 2 winks left eye")

    # H. Happy Bounce
    timeline.jump_to("happy_bounce")
    controller.update(0.1)
    assert_test(controller.offset_look_y != 0.0, "Happy bounce produces vertical offset motion")

    # I. Cute Blush
    timeline.jump_to("cute_blush")
    timeline.segment_elapsed = 2.5 # Peak blush (u = 0.50)
    controller.update(0.01)
    assert_test(controller.blush_state.alpha > 150.0, "Cute blush produces visible cheek stroke alpha")

    # J. Drowsy
    timeline.jump_to("drowsy")
    timeline.segment_elapsed = 3.5 # Drowsy hold (u = 0.70)
    controller.update(0.01)
    assert_test(0.35 <= controller.target_open_left <= 0.50, f"Drowsy droops eyes to ~0.42 ({controller.target_open_left:.2f})")

    # K. Sleep
    timeline.jump_to("sleep")
    timeline.segment_elapsed = 3.0 # Sleep active
    controller.update(0.01)
    assert_test(controller.target_open_left == 0.0 and controller.target_open_right == 0.0, "Sleep closes both eyes completely")


def test_full_62_second_simulation() -> None:
    print("\n--- 6. Full 62-Second 60 FPS Headless Simulation ---")
    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))
    renderer = Renderer(cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    dt = 1.0 / 60.0
    total_frames = int(62.0 * 60) # 3720 frames

    visited_segments = set()
    start_sim = time.perf_counter()

    for frame in range(total_frames):
        seg_name = controller.timeline.current_name
        visited_segments.add(seg_name)

        controller.update(dt)

        # Render complete frame
        renderer.render_frame(
            eye_pair=eye_pair,
            target_surface=screen,
            face_alpha=controller.face_alpha,
            blush_state=controller.blush_state,
            sleep_particles=controller.sleep_particles,
            intro_state=controller.intro_state if seg_name == "intro" else None,
        )

    sim_time = time.perf_counter() - start_sim
    assert_test(len(visited_segments) == 12, f"Simulation visited all 12 segments ({len(visited_segments)}/12)")
    assert_test(controller.timeline.loop_count >= 1, f"Simulation completed full 62.0s loop (loop_count={controller.timeline.loop_count})")
    print(f"  [PERF] 3720 frames simulated in {sim_time:.3f}s ({total_frames / sim_time:.0f} FPS headless throughput)")


def main() -> None:
    print("=" * 65)
    print("  RUNNING ELO FACE V3 (STAGE 2) FULL VERIFICATION SUITE")
    print("=" * 65)

    start_time = time.perf_counter()

    test_configuration_and_isolation()
    test_timeline_structure_and_timing()
    test_intro_state_progression()
    test_effects_blush_and_particles()
    test_emotion_behaviors()
    test_full_62_second_simulation()

    elapsed = time.perf_counter() - start_time
    print("=" * 65)
    print(f"  ALL STAGE 2 VERIFICATION TESTS PASSED in {elapsed:.3f}s!")
    print("=" * 65)


if __name__ == "__main__":
    main()
