"""ROBoy Emotion V2 - interactive showcase.

Launches a real pygame window showing the V2 face for the selected emotion.
The canvas is a clean black background with cyan robot-expression geometry
only - no chassis, border, or HUD (unless toggled).

Controls
--------
  1-9         emotion selection (neutral .. love)
  0           tired
  A           sleepy
  S           angry
  D           fearful
  F           disgusted
  SPACE       replay current emotion (reset animation time)
  R           reset
  P           toggle PAUSED / STATIC (freeze base geometry)
  H           toggle HUD (OFF by default)
  ESC         exit

CLI
---
  --emotion NAME     launch directly into an emotion
  --static           start in the PAUSED / STATIC comparison mode
"""

import sys
import math

import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em


def make_transform():
    size = min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE
    ox = (cfg.WINDOW_W - size) / 2.0
    oy = (cfg.WINDOW_H - size) / 2.0
    return g.Transform(ox, oy, size)


def compute_phase(emotion, t):
    if emotion == "thinking":
        return "cue: ? (perimeter)"
    if emotion == "sleepy":
        # count visible Z's by rebuilding the overlay lifecycle
        from overlays import build_zzz
        eye = (0.5 + cfg.EYE_DX, cfg.EYE_CY)
        zs = build_zzz(eye, t)
        return f"ZZZ x{len(zs)} (drifting)"
    if emotion in ("neutral", "happy", "excited"):
        return "breathing"
    if emotion == "surprised":
        return "open reaction" if t < 0.6 else "settled"
    return "steady"


def print_banner(emotion):
    print("=" * 56)
    print(" ROBoy Emotion V2 - isolated prototype showcase")
    print("=" * 56)
    print("Emotion mapping:")
    for line in em.mapping_lines():
        print(line)
    print("-" * 56)
    print(f" Active emotion: {emotion}")
    print(" HUD is OFF by default. Press H to toggle.")
    print(" Press ESC to quit.")
    print("=" * 56)


def main():
    emotion = "neutral"
    static = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--emotion" and i + 1 < len(args):
            i += 1
            if args[i] in em.EMOTION_ORDER:
                emotion = args[i]
        elif a == "--static":
            static = True
        i += 1

    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_W, cfg.WINDOW_H))
    pygame.display.set_caption("ROBoy Emotion V2")
    clock = pygame.time.Clock()
    font = pygame.font.Font(pygame.font.get_default_font(), 20)

    tf = make_transform()
    t = 0.0
    paused = static
    hud = False
    current = emotion

    print_banner(current)

    running = True
    while running:
        dt = clock.get_time() / 1000.0
        if not paused:
            t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    t = 0.0
                elif event.key == pygame.K_r:
                    t = 0.0
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_h:
                    hud = not hud
                else:
                    key = event.unicode
                    new_e = em.emotion_for_key(key)
                    if new_e is not None:
                        current = new_e
                        t = 0.0

        spec = fc.build_face(current, t)

        screen.fill(cfg.BG_COLOR)
        rn.render(screen, spec, tf)

        if hud:
            lines = [
                f"emotion : {current}",
                f"time    : {t:6.2f}s",
                f"phase   : {compute_phase(current, t)}",
                f"mode    : {'STATIC' if paused else 'NORMAL'}",
            ]
            for idx, line in enumerate(lines):
                img = font.render(line, True, (180, 180, 180))
                screen.blit(img, (14, 12 + idx * 24))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
