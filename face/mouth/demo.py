"""
Phase 4B Standalone Demo — Procedural Mouth Engine & Speech Sync.

Tests standalone procedural mouth rendering, state presets, transitions, and
multi-parameter procedural speech sync across all 10 official character emotional states.

Controls:
    1-9/0 : Select mouth state (Calm, Happy, Caring, Speaking, Thinking, Sad, Surprised, Sleepy, Focus, Listening)
    LEFT / RIGHT : Cycle states
    S : Toggle auto speech pulse simulator
    SPACE (Hold/Tap) : Interactive speech pulse trigger
    ESC : Quit
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
import pygame

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from face.mouth.mouth_shapes import MOUTH_PRESETS
from face.mouth.mouth_renderer import MouthRenderer
from face.mouth.mouth_animation import MouthAnimationController

STATE_NAMES = list(MOUTH_PRESETS.keys())


def run_mouth_demo() -> None:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((800, 480))
    pygame.display.set_caption("ELO Robot Face - Phase 4B Mouth & Speech Sync Demo")
    clock = pygame.time.Clock()

    renderer = MouthRenderer(bg_color=(0, 0, 0))
    controller = MouthAnimationController()
    controller.initialize("calm")

    font = pygame.font.SysFont("monospace", 16, bold=True)
    font_small = pygame.font.SysFont("monospace", 12)

    current_idx = 0
    auto_speech = False
    speech_timer = 0.0
    running = True

    print("Starting Phase 4B Mouth & Speech Sync Demo...")
    print("Keys 1-0 or Left/Right: select state. S: toggle auto speech. SPACE: pulse speech.")

    while running:
        dt_ms = clock.tick(60)
        dt_ms = min(dt_ms, 66.0)
        dt_s = dt_ms / 1000.0
        speech_timer += dt_s

        manual_speech = False
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            manual_speech = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RIGHT:
                    current_idx = (current_idx + 1) % len(STATE_NAMES)
                    controller.set_state(STATE_NAMES[current_idx])
                elif event.key == pygame.K_LEFT:
                    current_idx = (current_idx - 1) % len(STATE_NAMES)
                    controller.set_state(STATE_NAMES[current_idx])
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(STATE_NAMES):
                        current_idx = idx
                        controller.set_state(STATE_NAMES[current_idx])
                elif event.key == pygame.K_0:
                    current_idx = 9
                    controller.set_state(STATE_NAMES[current_idx])
                elif event.key == pygame.K_s:
                    auto_speech = not auto_speech

        # Compute speech pulse
        speech_pulse = 0.0
        if manual_speech:
            speech_pulse = 0.95
        elif auto_speech:
            # Organic synthetic speech modulation wave
            wave1 = max(0.0, math.sin(speech_timer * 11.0))
            wave2 = max(0.0, math.sin(speech_timer * 17.0 + 1.2))
            speech_pulse = min(1.0, wave1 * 0.7 + wave2 * 0.5)

        # Step animation
        params = controller.step(dt_ms, speech_pulse=speech_pulse)

        # Render frame
        screen.fill((0, 0, 0))
        renderer.draw_mouth(screen, params)

        # Render HUD / Debug text
        fps = clock.get_fps()
        state_txt = f"State: {controller.current_state.upper()} ({current_idx + 1}/{len(STATE_NAMES)})"
        speech_status = f"Speech: {'AUTO' if auto_speech else ('MANUAL' if manual_speech else 'OFF')} (Pulse: {controller.speech_sync.current_pulse:.2f})"
        fps_txt = f"FPS: {fps:.1f}"

        surf_state = font.render(state_txt, True, (0, 230, 150))
        surf_speech = font.render(speech_status, True, (255, 175, 40) if speech_pulse > 0 else (160, 172, 195))
        surf_fps = font.render(fps_txt, True, (0, 210, 255))

        screen.blit(surf_state, (20, 20))
        screen.blit(surf_speech, (20, 45))
        screen.blit(surf_fps, (700, 20))

        # Parameter readout
        p_info = [
            f"width: {params.width:.1f}  height: {params.height:.1f}  opening: {params.opening:.2f}",
            f"up_curve: {params.upper_curvature:+.2f}  low_curve: {params.lower_curvature:+.2f}  smile: {params.smile_amount:+.2f}",
            f"roundness: {params.corner_roundness:.2f}  stretch/squash: ({params.stretch:+.2f}, {params.squash:+.2f})",
        ]
        for i, line in enumerate(p_info):
            surf_line = font_small.render(line, True, (160, 172, 195))
            screen.blit(surf_line, (20, 410 + i * 18))

        pygame.display.flip()

    pygame.quit()
    print("Mouth demo finished.")


if __name__ == "__main__":
    run_mouth_demo()
