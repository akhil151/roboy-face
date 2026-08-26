"""ROBoy Emotion V2 - geometry helpers.

Provides a normalized -> pixel transform and low-level drawing primitives that
operate in NORMALIZED face coordinates. Every primitive converts through a
:class:`Transform`, so the renderer never deals with raw pixel maths.

The visual output is a clean black canvas with cyan robot-expression geometry.
"""

import math

import pygame


class Transform:
    """Maps normalized face coordinates (0..1) to window pixels."""

    __slots__ = ("ox", "oy", "size")

    def __init__(self, origin_x: float, origin_y: float, size: float):
        self.ox = origin_x
        self.oy = origin_y
        self.size = size

    def pt(self, nx: float, ny: float):
        """Convert a normalized point to a pixel tuple (float)."""
        return (self.ox + nx * self.size, self.oy + ny * self.size)

    def s(self, n: float) -> float:
        """Convert a normalized length to pixels."""
        return n * self.size

    def thick(self, n: float) -> int:
        """Convert a normalized thickness to a clamped pixel width."""
        return max(1, int(n * self.size))


# ---------------------------------------------------------------------------
# Primitive drawing helpers (all take normalized coordinates)
# ---------------------------------------------------------------------------

def fill_circle(surf, tf: Transform, cx, cy, rx, ry, color):
    px, py = tf.pt(cx, cy)
    rxp = tf.s(rx)
    ryp = tf.s(ry)
    rect = pygame.Rect(int(px - rxp), int(py - ryp),
                       int(rxp * 2), int(ryp * 2))
    pygame.draw.ellipse(surf, color, rect)


def fill_ellipse(surf, tf: Transform, cx, cy, rx, ry, color):
    fill_circle(surf, tf, cx, cy, rx, ry, color)


def thick_line(surf, tf: Transform, p0, p1, thick, color):
    """Draw a straight line stroke with rounded endcaps."""
    a = tf.pt(*p0)
    b = tf.pt(*p1)
    t_px = tf.thick(thick)
    pygame.draw.line(surf, color, a, b, t_px)
    r = t_px / 2.0
    if r >= 1:
        pygame.draw.circle(surf, color, (int(a[0]), int(a[1])), int(r))
        pygame.draw.circle(surf, color, (int(b[0]), int(b[1])), int(r))


def thick_arc(surf, tf: Transform, cx, cy, r, a0, a1, thick, color, n=48):
    """Draw a smooth circular arc stroke centred at (cx, cy) with rounded endcaps."""
    span = a1 - a0
    if span < 0:
        span += 2 * math.pi
    pts = []
    for i in range(n + 1):
        a = a0 + (i / n) * span
        x = cx + r * math.cos(a)
        y = cy - r * math.sin(a)
        pts.append(tf.pt(x, y))
    t_px = tf.thick(thick)
    pygame.draw.lines(surf, color, False, pts, t_px)
    r_cap = t_px / 2.0
    if r_cap >= 1:
        pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), int(r_cap))
        pygame.draw.circle(surf, color, (int(pts[-1][0]), int(pts[-1][1])), int(r_cap))


def quad_curve(surf, tf: Transform, p0, p1, p2, thick, color, n=48):
    """Draw a quadratic Bezier as a smooth thick polyline with rounded endcaps."""
    pts = []
    for i in range(n + 1):
        u = i / n
        mu = 1.0 - u
        x = mu * mu * p0[0] + 2.0 * mu * u * p1[0] + u * u * p2[0]
        y = mu * mu * p0[1] + 2.0 * mu * u * p1[1] + u * u * p2[1]
        pts.append(tf.pt(x, y))
    t_px = tf.thick(thick)
    pygame.draw.lines(surf, color, False, pts, t_px)
    r_cap = t_px / 2.0
    if r_cap >= 1:
        pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), int(r_cap))
        pygame.draw.circle(surf, color, (int(pts[-1][0]), int(pts[-1][1])), int(r_cap))


def poly_fill(surf, tf: Transform, points, color):
    px = [tf.pt(*p) for p in points]
    pygame.draw.polygon(surf, color, px)


def quad_points(p0, p1, p2, n=36):
    """Sample a quadratic Bezier into normalized points."""
    pts = []
    for i in range(n + 1):
        u = i / n
        mu = 1 - u
        x = mu * mu * p0[0] + 2 * mu * u * p1[0] + u * u * p2[0]
        y = mu * mu * p0[1] + 2 * mu * u * p1[1] + u * u * p2[1]
        pts.append((x, y))
    return pts


def fill_curve_shape(surf, tf: Transform, a, t, b, u, color, corner_soften=0.08):
    """Fill a closed shape bounded by two quadratic Beziers with softened corners.

    Top edge: a -> b via control t.  Bottom edge: b -> a via control u.
    Used for the angry filled slanted eye. Subtle corner filleting softens
    the sharp corner tips while preserving the exact wedge geometry.
    """
    if corner_soften > 0.0:
        f = corner_soften
        a_top = (a[0] + f * (t[0] - a[0]), a[1] + f * (t[1] - a[1]))
        a_bot = (a[0] + f * (u[0] - a[0]), a[1] + f * (u[1] - a[1]))
        b_top = (b[0] + f * (t[0] - b[0]), b[1] + f * (t[1] - b[1]))
        b_bot = (b[0] + f * (u[0] - b[0]), b[1] + f * (u[1] - b[1]))

        pts = []
        pts.extend(quad_points(a_top, t, b_top, 24))
        pts.extend(quad_points(b_top, b, b_bot, 8)[1:])
        pts.extend(quad_points(b_bot, u, a_bot, 24)[1:])
        pts.extend(quad_points(a_bot, a, a_top, 8)[1:])
        poly_fill(surf, tf, pts, color)
    else:
        top = quad_points(a, t, b)
        bot = quad_points(b, u, a)[1:]   # skip duplicate anchor at b
        poly_fill(surf, tf, top + bot, color)


def heart_points(cx, cy, scale):
    """Return normalized points outlining a heart centred at (cx, cy).

    ``scale`` is roughly the heart "radius". Uses the classic parametric
    heart curve. y is flipped so the point is at the bottom.
    """
    pts = []
    n = 40
    for i in range(n + 1):
        t = (i / n) * 2 * math.pi
        hx = 16 * (math.sin(t) ** 3)
        hy = (13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        x = cx + (hx / 17.0) * scale
        y = cy - (hy / 17.0) * scale
        pts.append((x, y))
    return pts


def wavy_line(surf, tf: Transform, cx, cy, w, amp, waves, phase, thick, color, n=60):
    """Draw a horizontal wavy line with rounded endcaps."""
    pts = []
    for i in range(n + 1):
        u = i / n
        x = cx - w / 2.0 + u * w
        y = cy + amp * math.sin(phase + u * math.pi * waves)
        pts.append(tf.pt(x, y))
    t_px = tf.thick(thick)
    pygame.draw.lines(surf, color, False, pts, t_px)
    r_cap = t_px / 2.0
    if r_cap >= 1:
        pygame.draw.circle(surf, color, (int(pts[0][0]), int(pts[0][1])), int(r_cap))
        pygame.draw.circle(surf, color, (int(pts[-1][0]), int(pts[-1][1])), int(r_cap))


def draw_text(surf, tf: Transform, text, cx, cy, size_norm, color, alpha=255):
    """Render a text glyph (used for "?" and "Z") centred at (cx, cy)."""
    size_px = max(6, int(tf.s(size_norm)))
    font = pygame.font.Font(pygame.font.get_default_font(), size_px)
    img = font.render(text, True, color)
    img.set_alpha(int(alpha))
    r = img.get_rect()
    px, py = tf.pt(cx, cy)
    surf.blit(img, (int(px - r.width / 2.0), int(py - r.height / 2.0)))
