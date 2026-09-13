"""Interactive showcase and entry point for ELO Face V3.

Controls:
    LEFT / RIGHT / UP / DOWN : Look in direction
    C                        : Center gaze
    SPACE                    : Trigger natural blink
    O                        : Toggle full circle <-> closed pill morph
    1, 2, 3, 4               : Set open state (1.0, 0.6, 0.25, 0.0)
    S                        : Trigger surprise scale bump (1.3x)
    + / =                    : Increase eye scale
    -                        : Decrease eye scale
    A                        : Toggle auto-idle / demo mode
    B                        : Toggle breathing pulse
    R                        : Reset to default state
    H                        : Toggle debug HUD
    ESC / Q                  : Exit
"""

import os
import sys
import time
import argparse
import pygame

from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    TARGET_FPS,
    MAX_LOOK_OFFSET_X,
    MAX_LOOK_OFFSET_Y,
    DEFAULT_SCALE,
)
from eye import EyePair
from renderer import Renderer
from animation import FaceController


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ELO Face V3 Showcase")
    parser.add_argument("--headless", action="store_true", help="Run in headless off-screen mode")
    parser.add_argument("--demo", action="store_true", help="Start immediately in auto-idle demo mode")
    parser.add_argument("--fps", type=int, default=TARGET_FPS, help="Target frames per second")
    parser.add_argument("--duration", type=float, default=None, help="Run for N seconds and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.display.set_caption("ELO Face V3 — Foundation Engine")

    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Consolas", 15) if pygame.font.get_init() else None

    eye_pair = EyePair()
    controller = FaceController(eye_pair)
    renderer = Renderer(WINDOW_WIDTH, WINDOW_HEIGHT)

    if args.demo:
        controller.auto_idle = True

    show_hud: bool = False
    running: bool = True
    start_time = time.perf_counter()
    last_time = start_time
    morph_toggle_state = True

    print("=" * 60)
    print("  ELO Face V3 — Foundation Engine Started")
    print("  Resolution: 800x480 | Target FPS:", args.fps)
    print("  Press 'H' for on-screen HUD | 'A' for Auto-Demo | 'ESC' to Quit")
    print("=" * 60)

    try:
        while running:
            current_time = time.perf_counter()
            dt = min(current_time - last_time, 0.1)  # Clamp dt to prevent teleporting on lag spikes
            last_time = current_time

            # Check optional duration limit
            if args.duration is not None and (current_time - start_time) >= args.duration:
                print(f"Reached duration limit of {args.duration}s. Exiting.")
                break

            # Handle Pygame Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_h:
                        show_hud = not show_hud
                    elif event.key == pygame.K_a:
                        controller.auto_idle = not controller.auto_idle
                        print(f"Auto-idle mode: {'ON' if controller.auto_idle else 'OFF'}")
                    elif event.key == pygame.K_b:
                        controller.breathing_enabled = not controller.breathing_enabled
                        print(f"Breathing: {'ON' if controller.breathing_enabled else 'OFF'}")
                    elif event.key == pygame.K_SPACE:
                        controller.trigger_blink()
                    elif event.key == pygame.K_o:
                        morph_toggle_state = not morph_toggle_state
                        target_o = 1.0 if morph_toggle_state else 0.0
                        controller.set_target_open(target_o)
                        print(f"Morphing open_amount -> {target_o:.2f}")
                    elif event.key == pygame.K_1:
                        controller.set_target_open(1.0)
                        morph_toggle_state = True
                    elif event.key == pygame.K_2:
                        controller.set_target_open(0.60)
                    elif event.key == pygame.K_3:
                        controller.set_target_open(0.25)
                    elif event.key == pygame.K_4:
                        controller.set_target_open(0.0)
                        morph_toggle_state = False
                    elif event.key == pygame.K_s:
                        controller.set_target_scale(1.30)
                        print("Scale -> 1.30 (Surprise)")
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        new_s = controller.target_scale + 0.1
                        controller.set_target_scale(new_s)
                        print(f"Scale increased -> {controller.target_scale:.2f}")
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        new_s = controller.target_scale - 0.1
                        controller.set_target_scale(new_s)
                        print(f"Scale decreased -> {controller.target_scale:.2f}")
                    elif event.key == pygame.K_LEFT:
                        controller.look_at("left")
                    elif event.key == pygame.K_RIGHT:
                        controller.look_at("right")
                    elif event.key == pygame.K_UP:
                        controller.look_at("up")
                    elif event.key == pygame.K_DOWN:
                        controller.look_at("down")
                    elif event.key == pygame.K_c:
                        controller.look_at("center")
                    elif event.key == pygame.K_r:
                        controller.set_target_open(1.0)
                        controller.set_target_look(0.0, 0.0)
                        controller.set_target_scale(DEFAULT_SCALE)
                        morph_toggle_state = True
                        print("Reset to default state.")

            # Update animation controller
            controller.update(dt)

            # Render frame
            renderer.render_frame(eye_pair, target_surface=screen)

            # Optional HUD
            if show_hud and font:
                auto_str = "Auto-Idle: ON" if controller.auto_idle else "Auto-Idle: OFF"
                renderer.render_hud(
                    surface=screen,
                    font=font,
                    eye_pair=eye_pair,
                    fps=clock.get_fps(),
                    extra_info=f"Mode: {auto_str} | Press 1-4 for Open Morph, S for Surprise, Arrow Keys to Look",
                )

            pygame.display.flip()
            clock.tick(args.fps)

    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
