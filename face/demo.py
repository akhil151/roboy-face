"""
Phase 4C Standalone Demo — Unified Face Engine (Eyes + Mouth + FX).

Demonstrates the complete character face with Eyes, Procedural Mouth,
Speech Sync, and Overlays driven synchronously by one unified emotional state machine.

Controls:
    1-9/0 : Select face state (Calm, Listening, Thinking, Speaking, Happy, Caring, Sad, Sleepy, Surprised, Focus)
    LEFT / RIGHT : Cycle states
    MOUSE : Move mouse to drive face gaze / look_at()
    S : Toggle auto speech simulator
    SPACE : Trigger blink
    ESC : Quit
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
import pygame

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from face import FaceEngine, VALID_STATES

STATE_ORDER = [
    "calm", "listening", "thinking", "speaking", "happy",
    "caring", "sad", "sleepy", "surprised", "focus"
]


def run_face_demo() -> None:
    face = FaceEngine()
    face.init_video(windowed=True)
    screen = face.composer._screen
    assert screen is not None

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 16, bold=True)
    font_small = pygame.font.SysFont("monospace", 12)

    current_idx = 0
    auto_speech = False
    speech_timer = 0.0
    running = True

    print("Starting Phase 4C Unified Face Engine Demo...")
    print("Controls: 1-0 or Left/Right: change state. Mouse: look. S: speech. SPACE: blink.")

    while running:
        dt_ms = clock.tick(60)
        dt_ms = min(dt_ms, 66.0)
        dt_s = dt_ms / 1000.0
        speech_timer += dt_s

        mx, my = pygame.mouse.get_pos()
        face.look_at(mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RIGHT:
                    current_idx = (current_idx + 1) % len(STATE_ORDER)
                    face.set_state(STATE_ORDER[current_idx])
                elif event.key == pygame.K_LEFT:
                    current_idx = (current_idx - 1) % len(STATE_ORDER)
                    face.set_state(STATE_ORDER[current_idx])
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(STATE_ORDER):
                        current_idx = idx
                        face.set_state(STATE_ORDER[current_idx])
                elif event.key == pygame.K_0:
                    current_idx = 9
                    face.set_state(STATE_ORDER[current_idx])
                elif event.key == pygame.K_s:
                    auto_speech = not auto_speech
                elif event.key == pygame.K_SPACE:
                    face.blink()

        # Compute speech pulse
        speech_pulse = 0.0
        if auto_speech or STATE_ORDER[current_idx] == "speaking":
            w1 = max(0.0, math.sin(speech_timer * 12.0))
            w2 = max(0.0, math.sin(speech_timer * 18.0 + 1.0))
            speech_pulse = min(1.0, w1 * 0.7 + w2 * 0.5)

        face.set_speech_pulse(speech_pulse)

        # Step and render
        eye_pose, mouth_params, ctx = face.step(dt_ms)
        face.composer.compose(screen, eye_pose, mouth_params, ctx)

        # HUD / Debug readout
        fps = clock.get_fps()
        state_txt = f"Face State: {face.current_state.upper()} ({current_idx + 1}/{len(STATE_ORDER)})"
        speech_txt = f"Speech: {'ON' if speech_pulse > 0.01 else 'OFF'} ({speech_pulse:.2f})"
        fps_txt = f"FPS: {fps:.1f}"

        surf_state = font.render(state_txt, True, (0, 230, 150))
        surf_speech = font.render(speech_txt, True, (255, 175, 40) if speech_pulse > 0.01 else (160, 172, 195))
        surf_fps = font.render(fps_txt, True, (0, 210, 255))

        screen.blit(surf_state, (20, 20))
        screen.blit(surf_speech, (20, 45))
        screen.blit(surf_fps, (700, 20))

        pygame.display.flip()

    pygame.quit()
    print("Face Engine demo finished.")


if __name__ == "__main__":
    run_face_demo()
