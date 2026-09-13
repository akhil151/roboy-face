"""Interactive showcase for ELO Face V3 (Stage 3 - Expanded Emotion Vocabulary).

Runs the complete 103-second automated timeline experience (21 segments):
    Intro (10.0s) -> Settle (3.5s) -> Blink (3.5s) -> Look Horizontal (5.0s) ->
    Look Vertical (4.5s) -> Curious (4.5s) -> Confused (4.5s) -> Surprise (3.5s) ->
    Excited (4.5s) -> Happy Bounce (4.5s) -> Wink (3.5s) -> Playful Double Wink (4.5s) ->
    Shy (4.5s) -> Cute Blush (5.0s) -> Thinking (5.0s) -> Suspicious (4.5s) ->
    Angry (4.5s) -> Scared/Nervous (4.5s) -> Sad (5.0s) -> Drowsy (5.0s) ->
    Sleep (9.5s) -> Loop

Controls:
    1 - 9             : Jump to segments 1-9 (Intro .. Excited)
    0                 : Jump to segment 10 (Happy Bounce)
    - / =             : Jump to Drowsy / Sleep
    RIGHT / N         : Next timeline segment
    LEFT / P          : Previous timeline segment
    SPACE             : Toggle Pause / Resume
    R                 : Restart from beginning (Intro)
    H                 : Toggle on-screen debug HUD
    ESC / Q           : Exit
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
    TIMELINE_SEGMENTS,
    TOTAL_TIMELINE_DURATION,
)
from eye import EyePair
from renderer import Renderer
from animation import FaceController
from timeline import TimelineController


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ELO Face V3 Showcase (Stage 2)")
    parser.add_argument("--headless", action="store_true", help="Run in headless off-screen mode")
    parser.add_argument("--demo", action="store_true", help="Run in full automated demo mode")
    parser.add_argument("--start-at", type=str, default=None, help="Start at specific segment (e.g. sleep, cute_blush)")
    parser.add_argument("--fps", type=int, default=TARGET_FPS, help="Target frames per second")
    parser.add_argument("--duration", type=float, default=None, help="Run for N seconds and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.display.set_caption("ELO Face V3 — Expression Timeline Showcase")

    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Consolas", 14) if pygame.font.get_init() else None

    eye_pair = EyePair()
    timeline = TimelineController()
    controller = FaceController(eye_pair, timeline=timeline)
    renderer = Renderer(WINDOW_WIDTH, WINDOW_HEIGHT)

    if args.start_at:
        try:
            controller.timeline.jump_to(args.start_at)
            print(f"Starting at segment: {args.start_at}")
        except ValueError as e:
            print(f"Warning: {e}. Starting from beginning.")

    show_hud: bool = False
    running: bool = True
    start_time = time.perf_counter()
    last_time = start_time

    # Key to segment index mapping (quick jumps)
    segment_keys = {
        pygame.K_1: 0,  # intro
        pygame.K_2: 1,  # settle
        pygame.K_3: 2,  # blink
        pygame.K_4: 3,  # look_horizontal
        pygame.K_5: 4,  # look_vertical
        pygame.K_6: 5,  # curious
        pygame.K_7: 6,  # confused
        pygame.K_8: 7,  # surprise
        pygame.K_9: 8,  # excited
        pygame.K_0: 9,  # happy_bounce
        pygame.K_MINUS: 19, # drowsy
        pygame.K_EQUALS: 20, # sleep
    }

    print("=" * 65)
    print("  ELO Face V3 — Stage 3 Expression Timeline Showcase")
    print(f"  Resolution: 800x480 | Target FPS: {args.fps} | Total Loop: {TOTAL_TIMELINE_DURATION:.1f}s")
    print(f"  Total Segments: {len(TIMELINE_SEGMENTS)} expressions in sequence")
    print("  Keys 1-9, 0, -, = to Jump | N/P (or Left/Right) for Prev/Next | SPACE: Pause | H: HUD")
    print("=" * 65)

    try:
        while running:
            current_time = time.perf_counter()
            dt = min(current_time - last_time, 0.1)
            last_time = current_time

            # Duration check
            if args.duration is not None and (current_time - start_time) >= args.duration:
                print(f"Reached duration limit of {args.duration}s. Exiting.")
                break

            # Pygame Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_h:
                        show_hud = not show_hud
                    elif event.key == pygame.K_SPACE:
                        controller.timeline.toggle_pause()
                        status = "PAUSED" if controller.timeline.is_paused else "RESUMED"
                        print(f"Timeline {status}")
                    elif event.key == pygame.K_r:
                        controller.timeline.reset()
                        print("Timeline reset to Intro.")
                    elif event.key in (pygame.K_RIGHT, pygame.K_n):
                        controller.timeline.next_segment()
                        print(f"Advanced to: {controller.timeline.current_name}")
                    elif event.key in (pygame.K_LEFT, pygame.K_p):
                        controller.timeline.prev_segment()
                        print(f"Jumped back to: {controller.timeline.current_name}")
                    elif event.key in segment_keys:
                        seg_idx = segment_keys[event.key]
                        controller.timeline.jump_to(seg_idx)
                        print(f"Jumped to segment [{seg_idx + 1}/12]: {controller.timeline.current_name}")

            # Update controller & timeline
            controller.update(dt)

            # Render complete layered frame
            renderer.render_frame(
                eye_pair=eye_pair,
                target_surface=screen,
                face_alpha=controller.face_alpha,
                blush_state=controller.blush_state,
                sleep_particles=controller.sleep_particles,
                intro_state=controller.intro_state if controller.timeline.current_name == "intro" else None,
            )

            # Render HUD if enabled
            if show_hud and font:
                tl = controller.timeline
                renderer.render_hud(
                    surface=screen,
                    font=font,
                    eye_pair=eye_pair,
                    fps=clock.get_fps(),
                    segment_name=tl.current_name,
                    segment_progress=tl.progress,
                    segment_elapsed=tl.segment_elapsed,
                    segment_duration=tl.current_duration,
                    total_elapsed=tl.total_elapsed,
                    total_duration=tl.total_duration,
                    is_paused=tl.is_paused,
                )

            pygame.display.flip()
            clock.tick(args.fps)

    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
