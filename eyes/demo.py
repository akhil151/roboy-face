"""
Demo mode for ELO eye animation engine.

Supports two interaction modes, toggled with TAB:

    * Auto-cycle (default): rotates through all 10 states every N seconds
      with an automatic sinusoidal look target sweep.
    * Manual: keyboard selects the state, mouse drives look_at().

Keyboard:
    1  Calm         2  Listening    3  Thinking     4  Speaking     5  Happy
    6  Caring       7  Sad          8  Sleepy       9  Surprised    0  Focus
    SPACE   Force blink
    TAB     Toggle auto-cycle
    ESC     Exit

Mouse:
    Movement drives look_at() when auto-cycle is off.  Click also snaps
    the look target to the click point for convenience.

Debug overlay (always on, bottom-left + top HUD):
    FPS | State | Blend % | Blink W | Look Target | Mouse Target | Eye Pos
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eyes import EyeEngine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

# Map from pygame key -> state name.  K_1..K_9 then K_0 for index 9.
KEY_STATE_MAP: Dict[int, str] = {
    pygame.K_1: "calm",
    pygame.K_2: "listening",
    pygame.K_3: "thinking",
    pygame.K_4: "speaking",
    pygame.K_5: "happy",
    pygame.K_6: "caring",
    pygame.K_7: "sad",
    pygame.K_8: "sleepy",
    pygame.K_9: "surprised",
    pygame.K_0: "focus",
}

CYCLE_SECONDS: float = 3.0


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _load_font(size: int, fallback: Optional[int] = None) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas,monospace,courier", size)
    except Exception:
        return pygame.font.Font(None, fallback or size)


# ---------------------------------------------------------------------------
# Rendering helpers: HUD state bar + debug overlay.
# ---------------------------------------------------------------------------

def render_state_bar(surface: pygame.Surface, active_state: str) -> None:
    w, _h = surface.get_size()
    try:
        font = _load_font(13, 16)
    except Exception:
        return
    states_text = "  |  ".join(
        (f"[{s.upper()}]" if s == active_state else f" {s} ")
        for s in STATE_ORDER
    )
    label = font.render(states_text, True, (70, 140, 90), (0, 0, 0))
    # Right half of HUD reserved for debug numbers; draw bar in top-left.
    max_x = w * 0.55
    if label.get_width() > max_x:
        # Trim with ellipsis if needed (unlikely at 800px).
        label = label.subsurface(pygame.Rect(0, 0, int(max_x), label.get_height()))
    surface.blit(label, (8, 6))


def render_debug_overlay(
    surface: pygame.Surface,
    *,
    fps: float,
    state: str,
    blend_pct: float,
    blink_weight: float,
    look_target: Tuple[float, float],
    mouse_target: Tuple[float, float],
    left_eye_pos: Tuple[float, float],
    right_eye_pos: Tuple[float, float],
    auto_cycle: bool,
    state_timer_s: float,
) -> None:
    _w, h = surface.get_size()
    try:
        font = _load_font(14, 16)
    except Exception:
        return

    lines: list[str] = [
        f"FPS:        {fps:6.1f}",
        f"State:      {state.upper()} [{state_timer_s:4.1f}s] {'(AUTO)' if auto_cycle else '(MANUAL)'}",
        f"Blend %:    {blend_pct * 100.0:6.2f}",
        f"Blink W:    {blink_weight:6.3f}",
        f"Look Trg:   ({look_target[0]:.3f}, {look_target[1]:.3f})",
        f"Mouse Trg:  ({mouse_target[0]:.3f}, {mouse_target[1]:.3f})",
        f"Eye Pos L:  ({left_eye_pos[0]:5.1f}, {left_eye_pos[1]:5.1f})",
        f"Eye Pos R:  ({right_eye_pos[0]:5.1f}, {right_eye_pos[1]:5.1f})",
    ]

    x = 10
    y = h - len(lines) * (font.get_linesize() + 1) - 8
    # Semi-transparent backing rect for contrast against white eyes.
    line_h = font.get_linesize()
    panel_w = 360
    panel_h = len(lines) * (line_h + 1) + 6
    back = pygame.Surface((panel_w, panel_h))
    back.set_alpha(200)
    back.fill((0, 0, 0))
    surface.blit(back, (x - 4, y - 4))

    text_color = (210, 210, 220)
    for i, line in enumerate(lines):
        surf = font.render(line, True, text_color, None)
        surface.blit(surf, (x, y + i * (line_h + 1)))

    # Short key-hint bar at the very bottom-right.
    hint_lines = [
        "1-9/0 State   SPACE Blink   TAB Auto   Mouse Look   ESC Quit",
    ]
    hint_font = _load_font(11, 14)
    hint_color = (95, 95, 110)
    for i, hl in enumerate(hint_lines):
        hs = hint_font.render(hl, True, hint_color, None)
        hx = surface.get_width() - hs.get_width() - 10
        hy = surface.get_height() - hs.get_height() - 6 - i * (hint_font.get_linesize() + 1)
        surface.blit(hs, (hx, hy))


def auto_cycle_look(t: float, engine: EyeEngine) -> None:
    lx = 0.5 + 0.35 * math.sin(t * 2.0 * math.pi / 11.0)
    ly = 0.5 + 0.30 * math.sin(t * 2.0 * math.pi / 7.0 + 0.7)
    engine.look_at(lx, ly)


def _norm_mouse(mx: int, my: int, w: int, h: int) -> Tuple[float, float]:
    return (max(0.0, min(1.0, mx / max(1, w))),
            max(0.0, min(1.0, my / max(1, h))))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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
    auto_cycle = True
    running = True

    # FPS smoothing: average over ~0.5s worth of frames.
    fps_smooth = float(fps)
    # Mouse target in normalized [0,1] coords (always tracked, even in auto mode
    # so the debug overlay shows the current live position).
    mouse_norm: Tuple[float, float] = (0.5, 0.5)

    screen = pygame.display.get_surface()
    assert screen is not None
    disp_w, disp_h = screen.get_size()

    print("ELO Eyes Demo")
    print("--------------------------------------------------------------")
    print(f"  States:       {STATE_ORDER}")
    print(f"  Cycle time:   {CYCLE_SECONDS:.1f}s (toggle with TAB)")
    print(f"  Target FPS:   {fps}")
    print("  Keys:         1-9/0 -> state | SPACE -> blink | TAB -> auto")
    print("  Mouse:        move -> look at (manual mode)")
    print("  Quit:         ESC or close window")
    print("--------------------------------------------------------------")

    while running:
        # --- Event dispatch
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break
                if event.key == pygame.K_SPACE:
                    engine.blink()
                    continue
                if event.key == pygame.K_TAB:
                    auto_cycle = not auto_cycle
                    if auto_cycle:
                        # Re-sync: start fresh from wherever we are in the list.
                        in_cycle_ms = 0.0
                    print(f"[demo] auto_cycle = {auto_cycle}")
                    continue
                state_name = KEY_STATE_MAP.get(event.key)
                if state_name is not None:
                    engine.set_state(state_name)
                    state_idx = STATE_ORDER.index(state_name)
                    in_cycle_ms = 0.0
                    continue

            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                mouse_norm = _norm_mouse(mx, my, disp_w, disp_h)
                if not auto_cycle:
                    engine.look_at(mouse_norm[0], mouse_norm[1])
            elif event.type == pygame.MOUSEBUTTONDOWN and not auto_cycle:
                mx, my = event.pos
                mouse_norm = _norm_mouse(mx, my, disp_w, disp_h)
                engine.look_at(mouse_norm[0], mouse_norm[1])

        if not running:
            break

        # --- Timing
        dt_ms = clock.tick(fps)
        dt_ms = min(dt_ms, 66.0)
        dt_s = dt_ms / 1000.0
        # EWMA-based FPS smoothing so the HUD number doesn't jitter badly.
        fps_meas = 1000.0 / max(1.0, dt_ms)
        fps_smooth += (fps_meas - fps_smooth) * 0.08
        fps_smooth = min(999.0, fps_smooth)

        elapsed_total += dt_s
        in_cycle_ms += dt_ms

        # --- Auto-cycle state transitions + auto look sweep
        if auto_cycle:
            if in_cycle_ms >= cycle_ms:
                in_cycle_ms = 0.0
                state_idx = (state_idx + 1) % len(STATE_ORDER)
                next_state = STATE_ORDER[state_idx]
                engine.set_state(next_state)
            auto_cycle_look(elapsed_total, engine)

        # --- Step engine + render (renderer draws to screen + flips internally
        #     via render_frame; we re-blit HUD on top then flip once more.)
        engine._engine.step(dt_ms)
        engine._engine._renderer.render_to_surface(screen, engine._engine.current_pose)

        # --- HUD / overlay
        render_state_bar(screen, engine.current_state)

        pose = engine._engine.current_pose
        look_norm = engine._engine.look_controller.current_normalized
        render_debug_overlay(
            screen,
            fps=fps_smooth,
            state=engine.current_state,
            blend_pct=engine._engine.mixer.blend_progress,
            blink_weight=engine._engine.blink_controller.blink_weight,
            look_target=look_norm,
            mouse_target=mouse_norm,
            left_eye_pos=(pose.left.pos_x + pose.left.look_offset_x + pose.left.micro_offset_x + pose.left.bounce_offset_x,
                          pose.left.pos_y + pose.left.look_offset_y + pose.left.micro_offset_y + pose.left.bounce_offset_y),
            right_eye_pos=(pose.right.pos_x + pose.right.look_offset_x + pose.right.micro_offset_x + pose.right.bounce_offset_x,
                           pose.right.pos_y + pose.right.look_offset_y + pose.right.micro_offset_y + pose.right.bounce_offset_y),
            auto_cycle=auto_cycle,
            state_timer_s=in_cycle_ms / 1000.0,
        )

        pygame.display.flip()

    pygame.quit()
    print("Demo stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
