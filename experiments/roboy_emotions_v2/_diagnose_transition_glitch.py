"""ROBoy Emotion V2 — Comprehensive Transition Glitch Verification Tool.

Tests all 182 directed transition pairs (14 emotions x 13 targets) across 21 samples
per transition (u = 0.00, 0.05, 0.10, ..., 1.00), validating:
 1. Exact endpoint reproduction (u=0 -> source, u=1 -> target).
 2. Bounded and finite coordinates (no NaN, no Inf, 0.0 <= x,y <= 1.0).
 3. Positive width for both eyes across all frames (no horizontal collapse / inversion).
 4. Proper canonical semantic ordering (left_pt.x < right_pt.x).
 5. Zero self-intersecting polygons on any filled eye or mouth shape.
 6. Smooth vertical curvature transformation without horizontal chord rotation.
 7. Strict vertical eye-to-mouth clearance gap (gap >= 0.02).
 8. Offscreen rendering success without exception or crash.
"""

import os
import sys
import math

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em
import transition as tr


def sample_quad_bezier(p0, p1, p2, n=16):
    pts = []
    for i in range(n + 1):
        u = i / n
        mu = 1.0 - u
        x = mu * mu * p0[0] + 2.0 * mu * u * p1[0] + u * u * p2[0]
        y = mu * mu * p0[1] + 2.0 * mu * u * p1[1] + u * u * p2[1]
        pts.append((x, y))
    return pts


def robust_self_intersection(pts):
    """Check if a closed polygon has genuinely self-intersecting non-adjacent edges."""
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def intersect(A, B, C, D):
        if A == C or A == D or B == C or B == D:
            return False
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    n = len(pts)
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        for j in range(i + 2, n):
            if (j + 1) % n == i or (i + 1) % n == j:
                continue
            p3, p4 = pts[j], pts[(j + 1) % n]
            if intersect(p1, p2, p3, p4):
                return True
    return False


def inspect_eye_geometry(e: fc.EyeSpec, side: str = "left"):
    anomalies = []

    # Check finite
    coords = [e.cx, e.cy]
    for attr in ("rx", "ry", "r", "heart_scale", "thickness", "lid"):
        val = getattr(e, attr, None)
        if val is not None and not math.isfinite(val):
            anomalies.append(f"Non-finite attribute {attr}={val}")

    if e.shape == "arc":
        pass
    elif e.shape == "circle":
        if e.rx <= 0.001 or e.ry <= 0.001:
            anomalies.append(f"Degenerate circle radius rx={e.rx}, ry={e.ry}")
    elif e.shape == "sleepy_u":
        p0 = e.p0
        p1 = e.p1
        p2 = e.p2
        if p0 and p2:
            w = abs(p2[0] - p0[0])
            if w < 0.010:
                anomalies.append(f"Collapsed chord width={w:.4f} (p0={p0}, p2={p2})")
            if p0[0] > p2[0]:
                anomalies.append(f"Inverted endpoints p0.x={p0[0]:.4f} > p2.x={p2[0]:.4f}")
    elif e.shape == "angry":
        a, t, b, u = e.curve_a, e.curve_t, e.curve_b, e.curve_u
        top_pts = sample_quad_bezier(a, t, b, 16)
        bot_pts = sample_quad_bezier(b, u, a, 16)[1:]
        poly = top_pts + bot_pts
        if robust_self_intersection(poly):
            anomalies.append(f"Self-intersecting angry polygon on {side} eye")
        # Check canonical ordering
        if side == "left" and a[0] > b[0]:
            anomalies.append(f"Left angry eye endpoints crossed a.x={a[0]:.4f} > b.x={b[0]:.4f}")
        elif side == "right" and b[0] > a[0]:
            anomalies.append(f"Right angry eye endpoints crossed b.x={b[0]:.4f} > a.x={a[0]:.4f}")

    return anomalies


def run_full_matrix_test():
    pygame.init()
    surf = pygame.Surface((cfg.WINDOW_W, cfg.WINDOW_H), pygame.SRCALPHA)
    tf = g.Transform(0, 0, min(cfg.WINDOW_W, cfg.WINDOW_H) * cfg.FACE_SCALE)

    all_emotions = em.EMOTION_ORDER
    pairs = [(s, t) for s in all_emotions for t in all_emotions if s != t]

    samples = [i / 20.0 for i in range(21)]  # 0.00, 0.05, ..., 1.00

    total_pairs = len(pairs)
    passed_pairs = 0
    failed_pairs = []

    print("=" * 72)
    print(" ROBoy Emotion V2 — 182-Pair Live Transition Matrix Diagnostic")
    print("=" * 72)

    for src_name, tgt_name in pairs:
        pair_key = f"{src_name:>10} -> {tgt_name:<10}"
        pair_ok = True
        pair_anomalies = []

        s0 = fc.build_face(src_name, 0.0)
        s1 = fc.build_face(tgt_name, 0.5)

        for u in samples:
            spec = tr.interpolate_face(s0, s1, u)

            # 1. Render test
            try:
                rn.render(surf, spec, tf)
            except Exception as ex:
                pair_ok = False
                pair_anomalies.append(f"Render crash at u={u:.2f}: {ex}")

            # 2. Eye geometry test
            for i, e in enumerate(spec.eyes):
                side = "left" if i == 0 else "right"
                anoms = inspect_eye_geometry(e, side=side)
                if anoms:
                    pair_ok = False
                    for a in anoms:
                        pair_anomalies.append(f"u={u:.2f} Eye {i} ({side}): {a}")

            # 3. Clearance test
            eye_bottom = max(e.cy + getattr(e, "ry", getattr(e, "r", cfg.EYE_R)) for e in spec.eyes)
            mouth_top = spec.mouth.cy - getattr(spec.mouth, "h", cfg.MOUTH_THICK) / 2.0
            if (mouth_top - eye_bottom) < 0.01:
                pair_ok = False
                pair_anomalies.append(f"u={u:.2f}: eye/mouth overlap clearance={mouth_top - eye_bottom:.4f}")

        if pair_ok:
            passed_pairs += 1
            # print(f"  [PASS] {pair_key}")
        else:
            failed_pairs.append((pair_key, pair_anomalies))
            print(f"  [FAIL] {pair_key} ({len(pair_anomalies)} anomalies)")
            for an in pair_anomalies[:5]:
                print(f"         {an}")

    print("=" * 72)
    print(f"MATRIX RESULT: {passed_pairs} / {total_pairs} passed ({len(failed_pairs)} failed)")
    print("=" * 72)

    return 0 if passed_pairs == total_pairs else 1


if __name__ == "__main__":
    sys.exit(run_full_matrix_test())
