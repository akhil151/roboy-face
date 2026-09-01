"""ROBoy Emotion V2 - interactive showcase with live emotion transitions.

Launches a real pygame window showing the V2 face for the selected emotion,
featuring smooth geometric transitions between expressions.
The canvas is a clean black background with pure white robot-expression
geometry - no chassis, border, or HUD (unless toggled).

Controls
--------
  1-9         emotion selection (neutral .. love)
  0           tired
  A           sleepy
  S           angry
  D           fearful
  F           disgusted
  SPACE       replay active emotion
  R           reset to neutral
  P           toggle PAUSED / STATIC
  H           toggle HUD (OFF by default)
  ESC         exit

CLI
---
  --emotion NAME     launch directly into an emotion
  --static           start in the PAUSED / STATIC comparison mode
  --duration SECS    transition duration in seconds (default: 0.55s)
"""

import sys
import math

import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em
import transition as tr


def make_transform():
    size = min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE
    ox = (cfg.WINDOW_W - size) / 2.0
    oy = (cfg.WINDOW_H - size) / 2.0
    return g.Transform(ox, oy, size)


def compute_phase(emotion, t, is_trans=False, target_e=None, prog=1.0):
    if is_trans:
        return f"transition -> {target_e} ({int(prog * 100)}%)"
    if emotion == "thinking":
        return "cue: ? (perimeter)"
    if emotion == "sleepy":
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
    print(" ROBoy Emotion V2 - Live Emotion Transition Showcase")
    print("=" * 56)
    print("Emotion mapping:")
    for line in em.mapping_lines():
        print(line)
    print("-" * 56)
    print(f" Active emotion : {emotion}")
    print(f" Transition     : {cfg.TRANSITION_DURATION * 1000:.0f} ms ({cfg.TRANSITION_EASING})")
    print(" HUD is OFF by default. Press H to toggle.")
    print(" Press ESC to quit.")
    print("=" * 56)


def main():
    emotion = "neutral"
    static = False
    duration = cfg.TRANSITION_DURATION
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
        elif a == "--duration" and i + 1 < len(args):
            i += 1
            try:
                duration = float(args[i])
            except ValueError:
                pass
        i += 1

    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_W, cfg.WINDOW_H))
    pygame.display.set_caption("ROBoy Emotion V2 - Live Transitions")
    clock = pygame.time.Clock()
    font = pygame.font.Font(pygame.font.get_default_font(), 20)

    tf = make_transform()
    paused = static
    hud = False

    controller = tr.TransitionController(initial_emotion=emotion, duration=duration)

    print_banner(emotion)

    running = True
    while running:
        dt = clock.get_time() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    controller.request_emotion(controller.current_emotion, reset_time=True)
                elif event.key == pygame.K_r:
                    controller.reset("neutral")
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_h:
                    hud = not hud
                else:
                    key = event.unicode
                    new_e = em.emotion_for_key(key)
                    if new_e is not None:
                        controller.request_emotion(new_e)

        if not paused:
            spec = controller.update(dt)
        else:
            spec = controller.get_current_spec()

        screen.fill(cfg.BG_COLOR)
        rn.render(screen, spec, tf)

        if hud:
            st = controller.get_status()
            cur = st["current"]
            tgt = st["target"]
            is_tr = st["is_transitioning"]
            prg = st["progress"]
            t_val = st["time"]

            emo_str = f"{cur} -> {tgt} ({int(prg * 100)}%)" if is_tr else f"{cur}"
            lines = [
                f"emotion : {emo_str}",
                f"time    : {t_val:6.2f}s",
                f"phase   : {compute_phase(cur, t_val, is_tr, tgt, prg)}",
                f"mode    : {'STATIC' if paused else 'NORMAL'}",
                f"easing  : {cfg.TRANSITION_EASING} ({controller.duration * 1000:.0f}ms)",
            ]
            for idx, line in enumerate(lines):
                img = font.render(line, True, (180, 180, 180))
                screen.blit(img, (14, 12 + idx * 24))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()

