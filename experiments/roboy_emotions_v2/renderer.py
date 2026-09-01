"""ROBoy Emotion V2 - renderer.

Draws a :class:`face.FaceSpec` (normalized coordinates) onto a pygame surface
using the supplied :class:`geometry.Transform`. No production code is touched;
this is a fully isolated prototype renderer.
"""

import config as cfg
import geometry as g
from face import EyeSpec, MouthSpec


def _eye_color(e):
    return e.color if e.color is not None else cfg.FACE_COLOR


def _mouth_color(m):
    return m.color if m.color is not None else cfg.FACE_COLOR


def draw_eye(surf, tf, e: EyeSpec):
    color = _eye_color(e)
    if e.shape == "circle":
        g.fill_circle(surf, tf, e.cx, e.cy, e.rx, e.ry, color)
        if e.lid > 0.0:
            # heavy eyelid: paint the top fraction black (matches bg)
            px, py = tf.pt(e.cx, e.cy)
            rxp = tf.s(e.rx)
            ryp = tf.s(e.ry)
            x = int(px - rxp)
            y = int(py - ryp)
            h = int(ryp * 2 * e.lid)
            w = int(rxp * 2)
            pygame_draw_rect(surf, x, y, w, h)
    elif e.shape == "arc":
        g.thick_arc(surf, tf, e.cx, e.cy, e.r, e.a0, e.a1, e.thickness, color)
    elif e.shape == "sleepy_u":
        g.quad_curve(surf, tf, e.p0, e.p1, e.p2, e.thickness, color)
    elif e.shape == "angry":
        g.fill_curve_shape(surf, tf, e.curve_a, e.curve_t, e.curve_b,
                           e.curve_u, color)
    elif e.shape == "heart":
        pts = g.heart_points(e.cx, e.cy, e.heart_scale)
        g.poly_fill(surf, tf, pts, color)
    elif e.shape in ("polygon", "poly"):
        g.poly_fill(surf, tf, e.points, color)
    elif e.shape == "quad_curve":
        g.quad_curve(surf, tf, e.p0, e.p1, e.p2, e.thickness, color)
    else:
        raise ValueError(f"unknown eye shape: {e.shape}")


def pygame_draw_rect(surf, x, y, w, h):
    import pygame
    pygame.draw.rect(surf, cfg.BG_COLOR, (x, y, w, h))


def draw_mouth(surf, tf, m: MouthSpec):
    color = _mouth_color(m)
    cx, cy, w = m.cx, m.cy, m.w
    if m.shape == "line" or m.shape == "capsule":
        # smooth short mouth: a rounded capsule stroke with circular endcaps
        g.thick_line(surf, tf, (cx - w / 2.0, cy), (cx + w / 2.0, cy), m.thickness, color)
    elif m.shape == "smile":
        g.quad_curve(surf, tf, (cx - w / 2.0, cy), (cx, cy + m.h), (cx + w / 2.0, cy),
                     m.thickness, color)
    elif m.shape == "frown":
        g.quad_curve(surf, tf, (cx - w / 2.0, cy), (cx, cy - m.h), (cx + w / 2.0, cy),
                     m.thickness, color)
    elif m.shape == "open":
        g.fill_ellipse(surf, tf, cx, cy, w / 2.0, m.h / 2.0, color)
    elif m.shape == "open_smile":
        # open happy smile bowl: flat/subtle top, smooth deep rounded bowl bottom
        p0 = (cx - w / 2.0, cy)
        p1 = (cx, cy - m.h * 0.05)
        p2 = (cx + w / 2.0, cy)
        top = g.quad_points(p0, p1, p2, 24)
        p3 = (cx, cy + m.h * 1.85)
        bot = g.quad_points(p2, p3, p0, 24)[1:]
        g.poly_fill(surf, tf, top + bot, color)
    elif m.shape == "wavy" or m.shape == "curl":
        g.wavy_line(surf, tf, cx, cy, w, m.amp, m.waves, m.phase, m.thickness, color)
    elif m.shape in ("polygon", "poly"):
        g.poly_fill(surf, tf, m.points, color)
    elif m.shape == "quad_curve":
        p0 = getattr(m, "p0", (cx - w / 2.0, cy))
        p1 = getattr(m, "p1", (cx, cy + m.h))
        p2 = getattr(m, "p2", (cx + w / 2.0, cy))
        g.quad_curve(surf, tf, p0, p1, p2, m.thickness, color)
    else:
        raise ValueError(f"unknown mouth shape: {m.shape}")



def draw_overlay(surf, tf, o):
    color = o.color if o.color is not None else cfg.FACE_COLOR
    g.draw_text(surf, tf, o.text, o.cx, o.cy, o.size_norm, color, o.alpha)


def render(surf, spec, tf):
    """Render a full face spec."""
    for e in spec.eyes:
        draw_eye(surf, tf, e)
    draw_mouth(surf, tf, spec.mouth)
    for o in spec.overlays:
        draw_overlay(surf, tf, o)
