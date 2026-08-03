"""
Demo mode for ELO eye animation engine.

Automatically cycles through all 10 registered states every 3 seconds.
State transitions blend smoothly over ~350ms via the AnimationMixer.

Usage:
    python demo.py

Press ESC to exit.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eyes import EyeEngine


STATE_ORDER: list[str] = [
    "calm",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "caring",
    "sad",
    "sleepy",
    "surprised",
    "focus",
]

CYCLE_SECONDS: float = 3.0


def render_state_label(surface: pygame.Surface, state: str, elapsed: float) -> None:
    w, h = surface.get_size()
    try:
        font = pygame.font.SysFont("consolas,monospace,courier", 20)
    except Exception:
        font = pygame.font.Font(None, 20)
    text = f"STATE: {state.upper()}   [{elapsed:5.1f}s]"
    label = font.render(text, True, (80, 80, 80), (0, 0, 0))
    surface.blit(label, (12, h - label.get_height() - 10))

    states_text = "  |  ".join(
        (s.upper() if s == state else s) for s in STATE_ORDER
    )
    small = pygame.font.SysFont("consolas,monospace,courier", 13)
    try:
        small = pygame.font.SysFont("consolas,monospace,courier", 13)
    except Exception:
        small = pygame.font.Font(None, 16)
    bar = small.render(states_text, True, (55, 55, 55), (0, 0, 0))
    surface.blit(bar, (10, 8))


def auto_cycle_look(t: float, engine: EyeEngine) -> None:
    lx = 0.5 + 0.35 * math.sin(t * 2.0 * math.pi / 11.0)
    ly = 0.5 + 0.30 * math.sin(t * 2.0 * math.pi / 7.0 + 0.7)
    engine.look_at(lx, ly)


def main() -> int:
    engine = EyeEngine()
    cfg = engine._engine.config
    engine._engine.init_video(windowed=True)

    clock = pygame.time.Clock()
    fps = cfg.display.fps
    cycle_ms = CYCLE_SECONDS * 1000.0

    state_idx = 0
    in_cycle_ms = 0.0
    elapsed_total = 0.0
    running = True

    print(f"ELO Eyes Demo — {len(STATE_ORDER)} states, {CYCLE_SECONDS:.1f}s each, {fps} FPS target")
    print("Press ESC to quit.")
    print(f"States: {STATE_ORDER}")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    engine.blink()

        dt_ms = clock.tick(fps)
        dt_ms = min(dt_ms, 66.0)
        dt_s = dt_ms / 1000.0

        elapsed_total += dt_s
        in_cycle_ms += dt_ms

        if in_cycle_ms >= cycle_ms:
            in_cycle_ms = 0.0
            state_idx = (state_idx + 1) % len(STATE_ORDER)
            next_state = STATE_ORDER[state_idx]
            engine.set_state(next_state)
            print(f"  -> {next_state:12s}  @ {elapsed_total:6.2f}s")

        auto_cycle_look(elapsed_total, engine)
        engine._engine.step(dt_ms)

        screen = pygame.display.get_surface()
        engine._engine._renderer.render_to_surface(screen, engine._engine.current_pose)
        render_state_label(screen, engine.current_state, in_cycle_ms / 1000.0)
        pygame.display.flip()

    pygame.quit()
    print("Demo stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
