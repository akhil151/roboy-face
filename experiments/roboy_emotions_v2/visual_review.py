"""ROBoy Emotion V2 - visual review sheet (inspection only, not production).

Renders all 14 emotions in a grid using the SAME V2 renderer. Each cell shows
the face for that emotion. Press SPACE to toggle between:

    STATIC    - frozen at t = 0 (pure geometry inspection)
    ANIMATED  - live time, shows the real animation

This is a human-review tool. It imports nothing from the production engine.
"""

import sys

import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em


def make_cell_transform(cell_x, cell_y, cell_w, cell_h):
    pad = 0.10
    size = min(cell_w, cell_h) * (1.0 - 2 * pad)
    ox = cell_x + (cell_w - size) / 2.0
    oy = cell_y + (cell_h - size) / 2.0 - cell_h * 0.04
    return g.Transform(ox, oy, size)


def main():
    cols, rows = 4, 4
    W, H = 1200, 820
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ROBoy Emotion V2 - visual review")
    clock = pygame.time.Clock()
    font = pygame.font.Font(pygame.font.get_default_font(), 18)

    t = 0.0
    animated = False
    show_labels = True
    order = em.EMOTION_ORDER

    print("ROBoy Emotion V2 - visual review sheet")
    print(" SPACE : toggle STATIC / ANIMATED")
    print(" H     : toggle labels")
    print(" ESC   : exit")

    running = True
    while running:
        dt = clock.get_time() / 1000.0
        if animated:
            t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    animated = not animated
                    if not animated:
                        t = 0.0
                elif event.key == pygame.K_h:
                    show_labels = not show_labels

        screen.fill(cfg.BG_COLOR)
        cell_w = W / cols
        cell_h = H / rows
        for idx, name in enumerate(order):
            r = idx // cols
            c = idx % cols
            cx0 = c * cell_w
            cy0 = r * cell_h
            tf = make_cell_transform(cx0, cy0, cell_w, cell_h)
            spec = fc.build_face(name, t if animated else 0.0)
            rn.render(screen, spec, tf)
            if show_labels:
                label = f"{idx + 1:2d} {name}"
                img = font.render(label, True, (150, 150, 150))
                screen.blit(img, (cx0 + 10, cy0 + cell_h - 26))

        # mode banner
        banner = "ANIMATED" if animated else "STATIC"
        img = font.render(f"mode: {banner}   (SPACE toggle, H labels, ESC exit)",
                          True, (120, 120, 120))
        screen.blit(img, (12, 8))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    sys.exit(main())
