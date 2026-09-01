"""ROBoy Emotion V2 - Behavior Showcase (Phases 4, 5, 6).

Interactive and automated 60 FPS showcase demonstrating:
- Phase 4: Eyelid Blinks (Normal, Quick, Slow, Double, Half)
- Phase 5: Gaze Saccades (Center, Left, Right, Up, Down, Diagonals)
- Phase 6: Layered Composition & Choreographed Sequences

Controls:
    1-9, 0, -, =    : Request emotions (Neutral, Happy, Sad, Angry, Sleepy, Surprised, etc.)
    B               : Normal Blink
    D               : Double Blink
    S               : Slow Blink
    H               : Half Blink
    Arrow Keys      : Look Left / Right / Up / Down
    C               : Center Gaze
    W               : Wink
    SPACE           : Toggle Auto-Tour / Choreography Demo
    ESC / Q         : Quit
"""

from __future__ import annotations

import os
import sys
import time

import pygame

import config as cfg
import emotions as em
import face as fc
import geometry as g
import renderer as rn
from blink_controller import BlinkType
from choreography import BehaviorChoreographer


def make_transform():
    size = min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE
    ox = (cfg.WINDOW_W - size) / 2.0
    oy = (cfg.WINDOW_H - size) / 2.0
    return g.Transform(ox, oy, size)


def run_showcase(headless: bool = False, max_frames: int = 1200):
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    pygame.font.init()

    win_w = cfg.WINDOW_W
    win_h = cfg.WINDOW_H
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("ROBoy V2 - Behavior Showcase (Phases 4, 5, 6)")
    clock = pygame.time.Clock()
    tf = make_transform()

    font_large = pygame.font.SysFont("monospace", 18, bold=True)
    font_small = pygame.font.SysFont("monospace", 14)

    choreographer = BehaviorChoreographer(initial_emotion="neutral")

    # Scripted automated choreo tour
    tour_script = [
        (0.0, lambda: choreographer.request_emotion("neutral")),
        (1.0, lambda: choreographer.look_direction("left")),
        (1.5, lambda: choreographer.blink(BlinkType.NORMAL)),
        (2.3, lambda: choreographer.request_emotion("happy", duration=0.45)),
        (2.6, lambda: choreographer.look_direction("right")),
        (3.5, lambda: choreographer.blink(BlinkType.DOUBLE)),
        (4.4, lambda: choreographer.request_emotion("sad", duration=0.50)),
        (4.7, lambda: choreographer.look_direction("down")),
        (5.5, lambda: choreographer.blink(BlinkType.SLOW)),
        (6.8, lambda: choreographer.request_emotion("angry", duration=0.45)),
        (7.1, lambda: choreographer.look_direction("up_right")),
        (8.2, lambda: choreographer.request_emotion("sleepy", duration=0.55)),
        (8.5, lambda: choreographer.look_direction("down")),
        (9.8, lambda: choreographer.request_emotion("confused", duration=0.45)),
        (10.1, lambda: choreographer.look_direction("left")),
        (11.2, lambda: choreographer.wink()),
        (12.5, lambda: choreographer.center_gaze()),
        (13.2, lambda: choreographer.request_emotion("neutral", duration=0.40)),
    ]
    tour_duration = 14.5
    auto_tour = True
    tour_time = 0.0
    script_idx = 0

    emotion_keys = {
        pygame.K_1: "neutral",
        pygame.K_2: "happy",
        pygame.K_3: "excited",
        pygame.K_4: "sad",
        pygame.K_5: "surprised",
        pygame.K_6: "thinking",
        pygame.K_7: "confused",
        pygame.K_8: "wink",
        pygame.K_9: "love",
        pygame.K_0: "tired",
        pygame.K_MINUS: "sleepy",
        pygame.K_EQUALS: "angry",
    }

    running = True
    frame_count = 0

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(0.05, max(0.001, dt))  # clamp dt against hitching

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    auto_tour = not auto_tour
                    if auto_tour:
                        tour_time = 0.0
                        script_idx = 0
                elif event.key in emotion_keys:
                    auto_tour = False
                    choreographer.request_emotion(emotion_keys[event.key])
                elif event.key == pygame.K_b:
                    choreographer.blink(BlinkType.NORMAL)
                elif event.key == pygame.K_d:
                    choreographer.blink(BlinkType.DOUBLE)
                elif event.key == pygame.K_s:
                    choreographer.blink(BlinkType.SLOW)
                elif event.key == pygame.K_h:
                    choreographer.blink(BlinkType.HALF)
                elif event.key == pygame.K_w:
                    choreographer.wink()
                elif event.key == pygame.K_c:
                    choreographer.center_gaze()
                elif event.key == pygame.K_LEFT:
                    auto_tour = False
                    choreographer.look_direction("left")
                elif event.key == pygame.K_RIGHT:
                    auto_tour = False
                    choreographer.look_direction("right")
                elif event.key == pygame.K_UP:
                    auto_tour = False
                    choreographer.look_direction("up")
                elif event.key == pygame.K_DOWN:
                    auto_tour = False
                    choreographer.look_direction("down")

        # Advance Auto-Tour script if active
        if auto_tour:
            tour_time += dt
            while script_idx < len(tour_script) and tour_time >= tour_script[script_idx][0]:
                tour_script[script_idx][1]()
                script_idx += 1
            if tour_time >= tour_duration:
                tour_time = 0.0
                script_idx = 0

        # Advance Choreographer (Transition + Gaze + Blink)
        composed_spec = choreographer.update(dt)

        # Clear background and render composed FaceSpec using authoritative V2 renderer
        screen.fill(cfg.BG_COLOR)
        rn.render(screen, composed_spec, tf)

        # UI Diagnostics Overlay
        if not headless:
            st = choreographer.get_status()
            emo_txt = font_large.render(f"EMOTION: {st['emotion'].upper()}", True, (255, 255, 255))
            screen.blit(emo_txt, (20, 20))

            if st["is_transitioning"]:
                tr_txt = font_small.render(f"TRANSITION: -> {st['target_emotion']} ({st['transition_progress']*100:.0f}%)", True, (120, 220, 255))
                screen.blit(tr_txt, (20, 48))

            gaze_txt = font_small.render(f"GAZE: ({st['gaze_x']:+.2f}, {st['gaze_y']:+.2f}) {'[MOVING]' if st['is_looking'] else '[SETTLED]'}", True, (160, 255, 160))
            screen.blit(gaze_txt, (20, 68))

            blink_txt = font_small.render(f"BLINK: {st['blink_state'].upper()} (weight: {st['blink_weight']:.2f})", True, (255, 220, 120))
            screen.blit(blink_txt, (20, 88))

            mode_txt = font_small.render(f"MODE: {'AUTO-TOUR [SPACE to pause]' if auto_tour else 'MANUAL [1-0=emo, Arrows=gaze, B=blink]'}", True, (200, 200, 200))
            screen.blit(mode_txt, (20, 110))

            fps_txt = font_small.render(f"FPS: {clock.get_fps():.1f}", True, (150, 150, 150))
            screen.blit(fps_txt, (win_w - 110, 20))

        pygame.display.flip()

        frame_count += 1
        if headless and frame_count >= max_frames:
            running = False

    pygame.quit()
    print(f"Showcase ran successfully for {frame_count} frames.")


if __name__ == "__main__":
    is_headless = "--headless" in sys.argv
    run_showcase(headless=is_headless, max_frames=300 if is_headless else 1000000)
