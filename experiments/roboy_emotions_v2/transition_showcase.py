"""ROBoy Emotion V2 - live transition matrix showcase.

Interactive showcase and test harness for observing and reviewing all 182 directed
emotion-to-emotion transitions (14 emotions x 13 targets).

Usage:
------
  py experiments/roboy_emotions_v2/transition_showcase.py
  py experiments/roboy_emotions_v2/transition_showcase.py --matrix
  py experiments/roboy_emotions_v2/transition_showcase.py --auto
  py experiments/roboy_emotions_v2/transition_showcase.py --from happy --to angry
  py experiments/roboy_emotions_v2/transition_showcase.py --duration 0.55 --hold 0.4

Controls:
---------
  Arrow Left / B    Previous transition pair
  Arrow Right / N   Next transition pair
  Arrow Up / Down   Cycle source / target emotion
  ENTER             Trigger transition for selected pair
  SPACE             Replay current transition
  M                 Toggle AUTOMATIC MATRIX MODE (cycles through all 182 pairs)
  P                 Toggle PAUSED
  H                 Toggle HUD (OFF by default)
  1-9, 0, A, S, D, F Direct emotion jump / interruption
  R                 Reset to neutral
  ESC               Exit
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


def build_matrix_pairs():
    """Build all 14 x 13 = 182 directed transition pairs in canonical order."""
    pairs = []
    for src in em.EMOTION_ORDER:
        for tgt in em.EMOTION_ORDER:
            if src != tgt:
                pairs.append((src, tgt))
    return pairs


MATRIX_PAIRS = build_matrix_pairs()


def make_transform():
    size = min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE
    ox = (cfg.WINDOW_W - size) / 2.0
    oy = (cfg.WINDOW_H - size) / 2.0
    return g.Transform(ox, oy, size)


def print_banner(mode_str, total_pairs):
    print("=" * 64)
    print(" ROBoy Emotion V2 — Live Transition Matrix Showcase")
    print("=" * 64)
    print(f" Mode               : {mode_str}")
    print(f" Total Pairs        : {total_pairs} directed transitions")
    print(f" Transition Duration: {cfg.TRANSITION_DURATION * 1000:.0f} ms ({cfg.TRANSITION_EASING})")
    print("-" * 64)
    print(" Navigation:")
    print("   N / Right Arrow  : Next pair")
    print("   B / Left  Arrow  : Previous pair")
    print("   ENTER            : Start transition")
    print("   SPACE            : Replay transition")
    print("   M                : Toggle Auto Matrix playback")
    print("   H                : Toggle HUD (OFF by default)")
    print("   1-9, 0, A-F      : Direct emotion jump")
    print("   ESC              : Exit")
    print("=" * 64)


def main():
    # CLI Arguments parsing
    auto_mode = False
    matrix_mode = False
    source_arg = None
    target_arg = None
    trans_duration = cfg.TRANSITION_DURATION
    hold_duration = 0.40  # seconds to hold source/target in auto mode

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--auto", "--all-transitions"):
            auto_mode = True
            matrix_mode = True
        elif a == "--matrix":
            matrix_mode = True
        elif a == "--from" and i + 1 < len(args):
            i += 1
            if args[i] in em.EMOTION_ORDER:
                source_arg = args[i]
        elif a == "--to" and i + 1 < len(args):
            i += 1
            if args[i] in em.EMOTION_ORDER:
                target_arg = args[i]
        elif a == "--duration" and i + 1 < len(args):
            i += 1
            try:
                trans_duration = float(args[i])
            except ValueError:
                pass
        elif a == "--hold" and i + 1 < len(args):
            i += 1
            try:
                hold_duration = float(args[i])
            except ValueError:
                pass
        i += 1

    # Initialize pair index
    pair_idx = 0
    if source_arg and target_arg and source_arg != target_arg:
        for idx, (s, t) in enumerate(MATRIX_PAIRS):
            if s == source_arg and t == target_arg:
                pair_idx = idx
                break
    elif source_arg:
        for idx, (s, t) in enumerate(MATRIX_PAIRS):
            if s == source_arg:
                pair_idx = idx
                break

    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_W, cfg.WINDOW_H))
    pygame.display.set_caption("ROBoy Emotion V2 — Transition Matrix Showcase")
    clock = pygame.time.Clock()
    font_large = pygame.font.Font(pygame.font.get_default_font(), 22)
    font_small = pygame.font.Font(pygame.font.get_default_font(), 17)

    tf = make_transform()
    hud = False
    paused = False

    # State machine for auto matrix playback
    # States: 'HOLD_SOURCE', 'TRANSITIONING', 'HOLD_TARGET'
    auto_state = "HOLD_SOURCE"
    auto_timer = 0.0

    cur_src, cur_tgt = MATRIX_PAIRS[pair_idx]
    controller = tr.TransitionController(initial_emotion=cur_src, duration=trans_duration)

    mode_label = "AUTO MATRIX" if auto_mode else ("MATRIX REVIEW" if matrix_mode else "INTERACTIVE")
    print_banner(mode_label, len(MATRIX_PAIRS))

    running = True
    while running:
        dt = clock.get_time() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_n):
                    # Next pair
                    pair_idx = (pair_idx + 1) % len(MATRIX_PAIRS)
                    cur_src, cur_tgt = MATRIX_PAIRS[pair_idx]
                    controller.reset(cur_src)
                    auto_state = "HOLD_SOURCE"
                    auto_timer = 0.0
                elif event.key in (pygame.K_LEFT, pygame.K_b):
                    # Previous pair
                    pair_idx = (pair_idx - 1) % len(MATRIX_PAIRS)
                    cur_src, cur_tgt = MATRIX_PAIRS[pair_idx]
                    controller.reset(cur_src)
                    auto_state = "HOLD_SOURCE"
                    auto_timer = 0.0
                elif event.key == pygame.K_RETURN:
                    # Trigger transition for current pair
                    controller.reset(cur_src)
                    controller.request_emotion(cur_tgt, duration=trans_duration)
                    auto_state = "TRANSITIONING"
                elif event.key == pygame.K_SPACE:
                    # Replay current pair transition
                    controller.reset(cur_src)
                    controller.request_emotion(cur_tgt, duration=trans_duration)
                    auto_state = "TRANSITIONING"
                elif event.key == pygame.K_m:
                    # Toggle auto matrix
                    auto_mode = not auto_mode
                    if auto_mode:
                        auto_state = "HOLD_SOURCE"
                        auto_timer = 0.0
                        controller.reset(cur_src)
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_h:
                    hud = not hud
                elif event.key == pygame.K_r:
                    controller.reset("neutral")
                    cur_src, cur_tgt = "neutral", "happy"
                else:
                    key = event.unicode
                    new_e = em.emotion_for_key(key)
                    if new_e is not None:
                        controller.request_emotion(new_e)

        # Automatic Matrix Playback Logic
        if auto_mode and not paused:
            if auto_state == "HOLD_SOURCE":
                auto_timer += dt
                if auto_timer >= hold_duration:
                    auto_state = "TRANSITIONING"
                    controller.request_emotion(cur_tgt, duration=trans_duration)
            elif auto_state == "TRANSITIONING":
                if not controller.is_transitioning():
                    auto_state = "HOLD_TARGET"
                    auto_timer = 0.0
            elif auto_state == "HOLD_TARGET":
                auto_timer += dt
                if auto_timer >= hold_duration:
                    # Advance to next pair
                    pair_idx = (pair_idx + 1) % len(MATRIX_PAIRS)
                    cur_src, cur_tgt = MATRIX_PAIRS[pair_idx]
                    controller.reset(cur_src)
                    auto_state = "HOLD_SOURCE"
                    auto_timer = 0.0

        if not paused:
            spec = controller.update(dt)
        else:
            spec = controller.get_current_spec()

        screen.fill(cfg.BG_COLOR)
        rn.render(screen, spec, tf)

        # Optional Diagnostic HUD (OFF by default, toggled with H)
        if hud:
            st = controller.get_status()
            cur = st["current"]
            tgt = st["target"]
            is_tr = st["is_transitioning"]
            prg = st["progress"]
            t_val = st["time"]

            # Pair index string: e.g. "002/182"
            idx_str = f"[{pair_idx + 1:03d}/{len(MATRIX_PAIRS):03d}]"
            pair_str = f"{cur_src.upper()} -> {cur_tgt.upper()}"
            status_str = f"TRANSITIONING ({int(prg * 100)}%)" if is_tr else ("HOLD_SRC" if auto_state == "HOLD_SOURCE" else "SETTLED")

            hud_lines = [
                f"PAIR   : {idx_str}  {pair_str}",
                f"STATUS : {status_str} | MODE: {'AUTO' if auto_mode else 'MANUAL'}",
                f"ACTIVE : {cur} (time: {t_val:5.2f}s)",
                f"TIMING : {trans_duration * 1000:.0f}ms transition, {hold_duration * 1000:.0f}ms hold",
                f"EASING : {cfg.TRANSITION_EASING}",
            ]

            # Render HUD background box
            hud_surf = pygame.Surface((440, len(hud_lines) * 24 + 16), pygame.SRCALPHA)
            hud_surf.fill((0, 0, 0, 180))
            screen.blit(hud_surf, (10, 10))

            for idx, line in enumerate(hud_lines):
                col = (255, 255, 255) if idx == 0 else (180, 200, 220)
                img = font_small.render(line, True, col)
                screen.blit(img, (18, 16 + idx * 24))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
