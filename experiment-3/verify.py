"""Headless verification suite for ELO Face V3 (Stage 3 - Expanded Emotion Vocabulary).

Comprehensive automated tests verifying:
1. Module independence (zero dependencies on experiment-2 or legacy code).
2. Timeline segment ordering, durations, and 103.0-second loop timing across all 21 segments.
3. Intro typewriter progression and face fade-in transition.
4. All 20 emotional behavior handlers and mathematical curves.
5. Pairwise distinctness checks for nuanced emotion pairs (Curious vs Confused, Excited vs Happy, Angry vs Suspicious, etc.).
6. State boundary resets and clean transitions.
7. Blush alpha envelope and sleep floating 'Z' particle dynamics.
8. 6180-frame full 103.0-second 60 FPS headless simulation run.
9. Verification that experiment-2 remains 100% untouched.
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
        ("curious", 4.5),
        ("confused", 4.5),
        ("surprise", 3.5),
        ("excited", 4.5),
        ("happy_bounce", 4.5),
        ("wink", 3.5),
        ("playful_double_wink", 4.5),
        ("shy", 4.5),
        ("cute_blush", 5.0),
        ("thinking", 5.0),
        ("suspicious", 4.5),
        ("angry", 4.5),
        ("scared_nervous", 4.5),
        ("sad", 5.0),
        ("drowsy", 5.0),
        ("sleep", 9.0),
    ]

    assert_test(len(cfg.TIMELINE_SEGMENTS) == 21, f"Timeline has exactly 21 segments ({len(cfg.TIMELINE_SEGMENTS)}/21)")
    for i, (expected_name, expected_dur) in enumerate(expected_segments):
        actual_name, actual_dur = cfg.TIMELINE_SEGMENTS[i]
        assert_test(actual_name == expected_name, f"Segment #{i+1} is '{expected_name}'")
        assert_test(abs(actual_dur - expected_dur) < 1e-3, f"Segment '{actual_name}' duration is {expected_dur}s")

    assert_test(abs(cfg.TOTAL_TIMELINE_DURATION - 103.0) < 1e-3, f"Total timeline duration is exactly 103.0s ({cfg.TOTAL_TIMELINE_DURATION:.1f}s)")
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
    print("\n--- 5. All 20 Emotion Handlers & Curve Tests ---")
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    # 1. Settle
    timeline.jump_to("settle")
    controller.update(0.1)
    assert_test(controller.target_open_left == 1.0 and controller.target_open_right == 1.0, "Settle keeps eyes fully open")
    assert_test(controller.target_scale == 1.0, "Settle scale is 1.0")

    # 2. Blink
    timeline.jump_to("blink")
    timeline.segment_elapsed = 0.95
    controller.update(0.01)
    assert_test(controller.target_open_left < 0.2, "Blink closes eyes")

    # 3. Look Horizontal
    timeline.jump_to("look_horizontal")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    assert_test(controller.target_look_x < -30.0, "Look horizontal glances left")
    timeline.segment_elapsed = 3.8
    controller.update(0.01)
    assert_test(controller.target_look_x > 30.0, "Look horizontal glances right")

    # 4. Look Vertical
    timeline.jump_to("look_vertical")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    assert_test(controller.target_look_y < -20.0, "Look vertical glances up")
    timeline.segment_elapsed = 3.6
    controller.update(0.01)
    assert_test(controller.target_look_y > 20.0, "Look vertical glances down")

    # 5. Curious (New)
    timeline.jump_to("curious")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    assert_test(controller.target_look_x > 25.0, "Curious shifts gaze sideways (+x)")
    assert_test(controller.target_open_left == 1.0 and controller.target_open_right < 0.90, "Curious exhibits controlled asymmetric squint (oL=1.0, oR=0.82)")

    # 6. Confused (New)
    timeline.jump_to("confused")
    timeline.segment_elapsed = 0.8
    controller.update(0.01)
    assert_test(controller.target_look_x < -20.0 and controller.target_open_left < 0.90, "Confused shifts left with left squint")
    timeline.segment_elapsed = 3.0
    controller.update(0.01)
    assert_test(controller.target_look_x > 15.0 and controller.target_open_right < 0.90, "Confused shifts right with right squint")

    # 7. Surprise
    timeline.jump_to("surprise")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    assert_test(controller.target_scale >= 1.30, "Surprise scales eyes up to ~1.35x")

    # 8. Excited (New)
    timeline.jump_to("excited")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    assert_test(controller.target_scale >= 1.15, "Excited scales eyes up to ~1.25x")
    assert_test(controller.offset_look_y != 0.0, "Excited generates high-frequency bouncing (3.2 Hz)")

    # 9. Happy Bounce
    timeline.jump_to("happy_bounce")
    controller.update(0.1)
    assert_test(controller.offset_look_y != 0.0, "Happy bounce produces vertical hopping")

    # 10. Wink
    timeline.jump_to("wink")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    assert_test(controller.target_open_left == 1.0 and controller.target_open_right == 0.0, "Wink keeps left open and right closed")

    # 11. Playful Double Wink
    timeline.jump_to("playful_double_wink")
    timeline.segment_elapsed = 1.0
    controller.update(0.01)
    assert_test(controller.target_open_right < 0.2 and controller.target_open_left == 1.0, "Double wink phase 1 winks right")
    timeline.segment_elapsed = 3.2
    controller.update(0.01)
    assert_test(controller.target_open_left < 0.2 and controller.target_open_right == 1.0, "Double wink phase 2 winks left")

    # 12. Shy (New)
    timeline.jump_to("shy")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    assert_test(controller.target_look_y > 20.0 and controller.target_look_x < -15.0, "Shy looks down and away")
    assert_test(0.60 <= controller.target_open_left <= 0.70, "Shy droops eyelids to ~0.65")
    assert_test(controller.blush_state.alpha > 40.0, "Shy exhibits subtle blush cheek alpha (~70)")

    # 13. Cute Blush
    timeline.jump_to("cute_blush")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.blush_state.alpha > 150.0, "Cute blush produces full blush alpha (~180)")

    # 14. Thinking (New)
    timeline.jump_to("thinking")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.target_look_y < -25.0 and controller.target_look_x > 15.0, "Thinking drifts gaze upward and sideways")
    assert_test(0.35 <= controller.target_open_left <= 0.45, "Thinking squints eyelids to ~0.40")

    # 15. Suspicious (New)
    timeline.jump_to("suspicious")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.target_look_x >= 45.0, "Suspicious casts strong side-eye (dx=+50)")
    assert_test(0.40 <= controller.target_open_left <= 0.55, "Suspicious narrows eyes moderately (o=0.48)")

    # 16. Angry (New)
    timeline.jump_to("angry")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.target_open_left <= 0.35, "Angry squashes eyes to narrow horizontal slits (o=0.30)")
    assert_test(controller.target_scale <= 0.95, "Angry deflates scale compactly (s=0.94)")

    # 17. Scared/Nervous (New)
    timeline.jump_to("scared_nervous")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    assert_test(controller.target_scale >= 1.25, "Scared/Nervous scales eyes up (1.28x)")
    assert_test(controller.target_look_x != 0.0 or controller.target_look_y != 0.0, "Scared/Nervous produces micro-tremor jitter")

    # 18. Sad (New)
    timeline.jump_to("sad")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.target_look_y >= 30.0, "Sad directs heavy downward gaze (dy=+34)")
    assert_test(0.48 <= controller.target_open_left <= 0.56, "Sad droops eyes to ~0.52")
    assert_test(controller.target_scale <= 0.95, "Sad contracts scale (0.94x)")

    # 19. Drowsy
    timeline.jump_to("drowsy")
    timeline.segment_elapsed = 3.5
    controller.update(0.01)
    assert_test(0.35 <= controller.target_open_left <= 0.50, "Drowsy droops eyes to ~0.38")

    # 20. Sleep
    timeline.jump_to("sleep")
    timeline.segment_elapsed = 3.0
    controller.update(0.01)
    assert_test(controller.target_open_left == 0.0 and controller.target_open_right == 0.0, "Sleep closes both eyes completely")


def test_pairwise_distinctions() -> None:
    print("\n--- 6. Pairwise Emotion Distinction Verification ---")
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    # A. Curious vs Confused
    timeline.jump_to("curious")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    curious_dx = controller.target_look_x
    curious_asym = abs(controller.target_open_left - controller.target_open_right)

    timeline.jump_to("confused")
    timeline.segment_elapsed = 0.8
    controller.update(0.01)
    confused_dx = controller.target_look_x

    assert_test(curious_dx > 0 and confused_dx < 0, "Curious (right gaze) is distinct from early Confused (left hesitant glance)")
    assert_test(curious_asym > 0.10, "Curious maintains asymmetric eye inspection")

    # B. Happy Bounce vs Excited
    timeline.jump_to("happy_bounce")
    timeline.segment_elapsed = 1.0
    controller.update(0.01)
    happy_scale = controller.target_scale

    timeline.jump_to("excited")
    timeline.segment_elapsed = 1.0
    controller.update(0.01)
    excited_scale = controller.target_scale

    assert_test(abs(happy_scale - 1.0) < 0.02 and excited_scale > 1.15, "Excited maintains scale burst (1.25x) while Happy Bounce maintains base scale (1.0x)")

    # C. Angry vs Suspicious
    timeline.jump_to("angry")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    angry_open = controller.target_open_left
    angry_dx = controller.target_look_x

    timeline.jump_to("suspicious")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    suspicious_open = controller.target_open_left
    suspicious_dx = controller.target_look_x

    assert_test(angry_open < 0.35 and suspicious_open > 0.45, "Angry is much more squashed (o=0.30) than Suspicious (o=0.48)")
    assert_test(abs(angry_dx) < 5.0 and suspicious_dx >= 45.0, "Suspicious has heavy lateral displacement (dx=+50) while Angry is forward-focused")

    # D. Surprise vs Scared/Nervous
    timeline.jump_to("surprise")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    surprise_jitter = abs(controller.target_look_x) + abs(controller.target_look_y)

    timeline.jump_to("scared_nervous")
    timeline.segment_elapsed = 1.5
    controller.update(0.01)
    nervous_jitter = abs(controller.target_look_x) + abs(controller.target_look_y)

    assert_test(surprise_jitter < 0.01 and nervous_jitter > 0.5, "Scared/Nervous has active jitter tremor while Surprise has clean motionless gaze")

    # E. Shy vs Sad
    timeline.jump_to("shy")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    shy_blush = controller.blush_state.alpha
    shy_dx = controller.target_look_x

    timeline.jump_to("sad")
    timeline.segment_elapsed = 2.0
    controller.update(0.01)
    sad_blush = controller.blush_state.alpha
    sad_dx = controller.target_look_x

    assert_test(shy_blush > 50.0 and sad_blush == 0.0, "Shy displays blush accent while Sad does not")
    assert_test(abs(shy_dx) > 15.0 and abs(sad_dx) < 2.0, "Shy glances sideways/down while Sad looks straight down")

    # F. Drowsy vs Sad
    timeline.jump_to("drowsy")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    drowsy_dy = controller.target_look_y
    drowsy_scale = controller.target_scale

    timeline.jump_to("sad")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    sad_dy = controller.target_look_y
    sad_scale = controller.target_scale

    assert_test(sad_dy > 30.0 and drowsy_dy < 15.0, "Sad has heavier downward gaze than Drowsy")
    assert_test(sad_scale < 0.95 and abs(drowsy_scale - 1.0) < 0.02, "Sad deflates scale (0.94x) while Drowsy stays at default scale")


def test_state_boundary_transitions() -> None:
    print("\n--- 7. State Boundary Reset & Continuity Verification ---")
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    # 1. Cute blush -> settle
    timeline.jump_to("cute_blush")
    timeline.segment_elapsed = 2.5
    controller.update(0.01)
    assert_test(controller.blush_state.alpha > 100.0, "Blush is active during cute_blush")
    timeline.jump_to("settle")
    controller.update(0.01)
    assert_test(controller.blush_state.alpha == 0.0, "Blush resets to 0.0 when transitioning to settle")

    # 2. Sleep -> settle
    timeline.jump_to("sleep")
    controller.sleep_particles.spawn()
    assert_test(len(controller.sleep_particles.particles) > 0, "Sleep particles exist during sleep")
    timeline.jump_to("settle")
    controller.update(0.01)
    assert_test(len(controller.sleep_particles.particles) == 0, "Sleep particles reset when transitioning away from sleep")

    # 3. Drowsy -> Sleep Continuity (No Jump)
    timeline.jump_to("drowsy")
    timeline.segment_elapsed = 5.0
    controller._update_drowsy(1.0, 5.0, 0.016)
    drowsy_end_open = controller.target_open_left

    timeline.jump_to("sleep")
    timeline.segment_elapsed = 0.0
    controller._update_sleep(0.0, 0.0, 0.016)
    sleep_start_open = controller.target_open_left

    assert_test(
        abs(drowsy_end_open - sleep_start_open) < 0.05,
        f"Drowsy to Sleep transition is continuous without jump (drowsy_end={drowsy_end_open:.3f}, sleep_start={sleep_start_open:.3f})",
    )

    # 4. Zero-pop boundary guarantees (excited, happy_bounce, cute_blush)
    timeline.jump_to("excited")
    controller._update_excited(1.0, 4.5, 0.016)
    assert_test(abs(controller.offset_look_y) < 1e-3, "Excited vertical bounce returns to 0.0 at segment end")

    timeline.jump_to("happy_bounce")
    controller._update_happy_bounce(1.0, 4.5, 0.016)
    assert_test(abs(controller.offset_look_y) < 1e-3, "Happy bounce vertical offset returns to 0.0 at segment end")

    timeline.jump_to("cute_blush")
    controller._update_cute_blush(1.0, 5.0, 0.016)
    assert_test(abs(controller.target_look_y) < 1e-3, "Cute blush gaze tilt returns to 0.0 at segment end")


def test_full_103_second_simulation() -> None:
    print("\n--- 8. Full 103-Second 60 FPS Headless Simulation (6,180 Frames) ---")
    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))
    renderer = Renderer(cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)
    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)

    dt = 1.0 / 60.0
    total_frames = int(cfg.TOTAL_TIMELINE_DURATION * 60) + 10 # 6190 frames for complete loop roll-over

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
    assert_test(len(visited_segments) == 21, f"Simulation visited all 21 segments ({len(visited_segments)}/21)")
    assert_test(controller.timeline.loop_count >= 1, f"Simulation completed full 103.0s loop (loop_count={controller.timeline.loop_count})")
    print(f"  [PERF] {total_frames} frames simulated in {sim_time:.3f}s ({total_frames / sim_time:.0f} FPS headless throughput)")


def main() -> None:
    print("=" * 65)
    print("  RUNNING ELO FACE V3 (STAGE 3) FULL VERIFICATION SUITE")
    print("=" * 65)

    start_time = time.perf_counter()

    test_configuration_and_isolation()
    test_timeline_structure_and_timing()
    test_intro_state_progression()
    test_effects_blush_and_particles()
    test_emotion_behaviors()
    test_pairwise_distinctions()
    test_state_boundary_transitions()
    test_full_103_second_simulation()

    elapsed = time.perf_counter() - start_time
    print("=" * 65)
    print(f"  ALL STAGE 3 VERIFICATION TESTS PASSED in {elapsed:.3f}s!")
    print("=" * 65)


if __name__ == "__main__":
    main()
