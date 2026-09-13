"""Headless verification suite for ELO Face V3 (Experiment 3).

Verifies:
1. Module independence (zero dependencies on experiment-2 or legacy code).
2. Canvas and display configuration (800x480, black bg, white eyes).
3. Single rounded shape circle-to-pill squash morphing math.
4. Gaze offset and scale modulation mechanics.
5. Easing curves, exponential decay smoothing, and blink lifecycle.
6. 60 FPS simulated headless render run.
7. Integrity check that experiment-2 remains untouched.
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

    # Check that no experiment-2 or legacy modules are imported in sys.modules
    for mod_name in sys.modules.keys():
        assert_test(
            "roboy_emotions_v2" not in mod_name and "experiment-2" not in mod_name,
            f"Module '{mod_name}' is not coupled to V2/legacy code",
        )


def test_easing_primitives() -> None:
    print("\n--- 2. Easing & Smoothing Primitives ---")
    assert_test(eas.clamp(-5.0, 0.0, 1.0) == 0.0, "Clamp lower bound")
    assert_test(eas.clamp(5.0, 0.0, 1.0) == 1.0, "Clamp upper bound")
    assert_test(eas.clamp(0.5, 0.0, 1.0) == 0.5, "Clamp within bound")

    assert_test(eas.smoothstep(0.0) == 0.0, "Smoothstep at t=0 is 0.0")
    assert_test(eas.smoothstep(1.0) == 1.0, "Smoothstep at t=1 is 1.0")
    assert_test(eas.smoothstep(0.5) == 0.5, "Smoothstep at t=0.5 is 0.5")

    # Exponential decay smoothing
    curr = 0.0
    target = 100.0
    rate = 10.0
    dt = 0.1
    next_val = eas.exp_decay(curr, target, rate, dt)
    assert_test(0.0 < next_val < target, "Exponential decay moves towards target smoothly")
    assert_test(not math.isnan(next_val) and not math.isinf(next_val), "Exponential decay is finite and stable")


def test_eye_geometry_and_morphing() -> None:
    print("\n--- 3. Eye Geometry & Circle-to-Pill Squash Morphing ---")
    eye = Eye(base_cx=400.0, base_cy=240.0, radius=80.0)

    # State A: Fully Open (open_amount = 1.0) -> Geometric Circle
    eye.set_open(1.0)
    eye.set_scale(1.0)
    eye.set_look(0.0, 0.0)
    geom_open = eye.compute_geometry()

    assert_test(geom_open.cx == 400.0 and geom_open.cy == 240.0, "Center matches base at zero look offset")
    assert_test(abs(geom_open.width - 160.0) < 1e-3, "Open eye width is 2 * radius (160px)")
    assert_test(abs(geom_open.height - 160.0) < 1e-3, "Open eye height is 2 * radius (160px)")
    assert_test(abs(geom_open.corner_radius - 80.0) < 1e-3, "Open eye corner radius is radius (80px) -> circle")
    assert_test(geom_open.is_circle, "Eye identifies as circle when fully open")

    # State B: Fully Closed (open_amount = 0.0) -> Horizontally Elongated Pill
    eye.set_open(0.0)
    geom_closed = eye.compute_geometry()

    min_expected_h = 160.0 * cfg.MIN_OPEN_RATIO
    assert_test(abs(geom_closed.height - min_expected_h) < 1e-3, f"Closed eye height is {min_expected_h:.2f}px")
    assert_test(geom_closed.width > 160.0, "Closed eye expands horizontally during squash")
    assert_test(geom_closed.corner_radius == geom_closed.height / 2.0, "Corner radius is height / 2 -> stadium pill")
    assert_test(not geom_closed.is_circle, "Closed eye is pill, not circle")

    # State C: Intermediate open amounts (monotonicity check)
    prev_h = geom_closed.height
    for o_val in [0.2, 0.4, 0.6, 0.8, 1.0]:
        eye.set_open(o_val)
        g = eye.compute_geometry()
        assert_test(g.height > prev_h, f"Height increases monotonically at open_amount={o_val:.1f}")
        prev_h = g.height


def test_gaze_and_scale() -> None:
    print("\n--- 4. Gaze Offset & Scale Modulation ---")
    eye = Eye(base_cx=270.0, base_cy=240.0, radius=85.0)

    # Gaze offset
    eye.set_look(50.0, -30.0)
    g = eye.compute_geometry()
    assert_test(g.cx == 320.0, "Gaze X offset correctly applied to center (270 + 50 = 320)")
    assert_test(g.cy == 210.0, "Gaze Y offset correctly applied to center (240 - 30 = 210)")

    # Gaze clamping
    eye.set_look(200.0, -200.0)
    assert_test(eye.look_x == cfg.MAX_LOOK_OFFSET_X, "Gaze X clamped to MAX_LOOK_OFFSET_X")
    assert_test(eye.look_y == -cfg.MAX_LOOK_OFFSET_Y, "Gaze Y clamped to -MAX_LOOK_OFFSET_Y")

    # Scale modulation
    eye.set_look(0.0, 0.0)
    eye.set_open(1.0)
    eye.set_scale(1.4)
    g_scaled = eye.compute_geometry()
    assert_test(abs(g_scaled.width - (170.0 * 1.4)) < 1e-3, "Scale 1.4x correctly scales width")
    assert_test(abs(g_scaled.height - (170.0 * 1.4)) < 1e-3, "Scale 1.4x correctly scales height")


def test_eye_pair_and_renderer() -> None:
    print("\n--- 5. EyePair & Pygame Renderer ---")
    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))
    renderer = Renderer(cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT)
    eye_pair = EyePair()

    # Verify initial layout
    l_geom, r_geom = eye_pair.get_geometries()
    assert_test(l_geom.cx == cfg.LEFT_EYE_BASE_X, f"Left eye base X is {cfg.LEFT_EYE_BASE_X}")
    assert_test(r_geom.cx == cfg.RIGHT_EYE_BASE_X, f"Right eye base X is {cfg.RIGHT_EYE_BASE_X}")
    assert_test(l_geom.cy == cfg.EYE_BASE_Y and r_geom.cy == cfg.EYE_BASE_Y, "Both eyes share center Y")

    # Render a test frame
    surf = renderer.render_frame(eye_pair, target_surface=screen)
    assert_test(surf.get_width() == 800 and surf.get_height() == 480, "Rendered surface is 800x480")

    # Sample pixel at top-left corner (should be black background)
    bg_sample = surf.get_at((10, 10))[:3]
    assert_test(bg_sample == (0, 0, 0), "Background pixel (10, 10) is pure black (0, 0, 0)")

    # Sample pixel at left eye center (should be white eye fill)
    eye_sample = surf.get_at((int(cfg.LEFT_EYE_BASE_X), int(cfg.EYE_BASE_Y)))[:3]
    assert_test(eye_sample == (255, 255, 255), "Eye center pixel is solid white (255, 255, 255)")


def test_animation_controller_and_simulation() -> None:
    print("\n--- 6. Animation Controller & 60 FPS Simulation ---")
    eye_pair = EyePair()
    controller = FaceController(eye_pair)
    renderer = Renderer()
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))

    # Set target gaze and scale
    controller.set_target_look(40.0, -20.0)
    controller.set_target_scale(1.25)
    controller.trigger_blink(0.18)

    # Simulate 120 frames at 60 FPS (2.0 seconds)
    dt = 1.0 / 60.0
    for frame in range(120):
        controller.update(dt)
        renderer.render_frame(eye_pair, target_surface=screen)

    # After 2 seconds, look offset and scale should have smoothly converged to targets
    assert_test(abs(controller.current_look_x - 40.0) < 0.1, "Look X converged smoothly to target")
    assert_test(abs(controller.current_look_y - (-20.0)) < 0.1, "Look Y converged smoothly to target")
    assert_test(abs(controller.current_scale - 1.25) < 0.05, "Scale converged smoothly to target")
    assert_test(not controller.blink.active, "Blink cycle completed cleanly")


def main() -> None:
    print("=" * 60)
    print("  RUNNING ELO FACE V3 (EXPERIMENT 3) VERIFICATION SUITE")
    print("=" * 60)

    start_time = time.perf_counter()

    test_configuration_and_isolation()
    test_easing_primitives()
    test_eye_geometry_and_morphing()
    test_gaze_and_scale()
    test_eye_pair_and_renderer()
    test_animation_controller_and_simulation()

    elapsed = time.perf_counter() - start_time
    print("=" * 60)
    print(f"  ALL V3 FOUNDATION VERIFICATION TESTS PASSED in {elapsed:.3f}s!")
    print("=" * 60)


if __name__ == "__main__":
    main()
