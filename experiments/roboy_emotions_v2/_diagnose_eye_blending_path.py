"""ROBoy Emotion V2 - Diagnostic script for eye blending curvature path analysis.
Analysis only - does not modify any production code.
"""

import os
import sys
import math
import copy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

import config as cfg
import geometry as g
import face as fc
import renderer as rn
import emotions as em
import transition as tr


def sample_eye_curve_points(e: fc.EyeSpec, side: str = "left", n: int = 48):
    """Sample points along the centerline of any EyeSpec primitive.
    
    Returns list of (x, y) normalized coordinates, left_pt, right_pt, mid_pt.
    """
    if e.shape == "circle":
        cx, cy = e.cx, e.cy
        rx = getattr(e, "rx", None) or cfg.EYE_R
        ry = getattr(e, "ry", None) or rx
        lid = getattr(e, "lid", 0.0) or 0.0
        pts = [(cx - rx + (2 * rx * i / n), cy) for i in range(n + 1)]
        return pts, (cx - rx, cy), (cx + rx, cy), (cx, cy)

    elif e.shape == "arc":
        cx, cy = e.cx, e.cy
        r = getattr(e, "r", None) or cfg.EYE_R
        a0 = getattr(e, "a0", 0.0) or 0.0
        a1 = getattr(e, "a1", math.pi) or math.pi
        span = a1 - a0
        if span < 0:
            span += 2 * math.pi
        pts = []
        for i in range(n + 1):
            a = a0 + (i / n) * span
            x = cx + r * math.cos(a)
            y = cy - r * math.sin(a)
            pts.append((x, y))
        p_start = pts[0]
        p_end = pts[-1]
        if p_start[0] <= p_end[0]:
            left_pt, right_pt = p_start, p_end
        else:
            left_pt, right_pt = p_end, p_start
        mid_pt = pts[n // 2]
        return pts, left_pt, right_pt, mid_pt

    elif e.shape == "sleepy_u" or e.shape == "quad_curve":
        cx, cy = e.cx, e.cy
        s = cfg.EYE_R * 1.00
        p0 = getattr(e, "p0", (cx - s, cy - 0.14 * s))
        p1 = getattr(e, "p1", (cx, cy + 0.50 * s))
        p2 = getattr(e, "p2", (cx + s, cy - 0.14 * s))
        pts = []
        for i in range(n + 1):
            u = i / n
            mu = 1.0 - u
            x = mu * mu * p0[0] + 2.0 * mu * u * p1[0] + u * u * p2[0]
            y = mu * mu * p0[1] + 2.0 * mu * u * p1[1] + u * u * p2[1]
            pts.append((x, y))
        if p0[0] <= p2[0]:
            left_pt, right_pt = p0, p2
        else:
            left_pt, right_pt = p2, p0
        mid_pt = pts[n // 2]
        return pts, left_pt, right_pt, mid_pt

    elif e.shape == "angry":
        a = e.curve_a
        b = e.curve_b
        t = e.curve_t
        u = e.curve_u
        if a[0] <= b[0]:
            left_pt, right_pt = a, b
        else:
            left_pt, right_pt = b, a
        pts = []
        for i in range(n + 1):
            param = i / n
            mu = 1.0 - param
            xt = mu * mu * a[0] + 2.0 * mu * param * t[0] + param * param * b[0]
            yt = mu * mu * a[1] + 2.0 * mu * param * t[1] + param * param * b[1]
            xb = mu * mu * b[0] + 2.0 * mu * param * u[0] + param * param * a[0]
            yb = mu * mu * b[1] + 2.0 * mu * param * u[1] + param * param * a[1]
            pts.append(((xt + xb) / 2.0, (yt + yb) / 2.0))
        mid_pt = pts[n // 2]
        return pts, left_pt, right_pt, mid_pt

    elif e.shape == "heart":
        cx, cy = e.cx, e.cy
        hs = getattr(e, "heart_scale", cfg.EYE_R * cfg.HEART_SCALE)
        left_pt = (cx - hs, cy)
        right_pt = (cx + hs, cy)
        mid_pt = (cx, cy)
        pts = [(cx - hs + 2 * hs * i / n, cy) for i in range(n + 1)]
        return pts, left_pt, right_pt, mid_pt

    else:
        cx, cy = e.cx, e.cy
        r = cfg.EYE_R
        left_pt = (cx - r, cy)
        right_pt = (cx + r, cy)
        mid_pt = (cx, cy)
        pts = [(cx - r + 2 * r * i / n, cy) for i in range(n + 1)]
        return pts, left_pt, right_pt, mid_pt


def compute_eye_metrics(e: fc.EyeSpec, side: str = "left"):
    """Compute geometric metrics for an eye."""
    pts, left_pt, right_pt, mid_pt = sample_eye_curve_points(e, side)
    
    # Baseline chord
    base_x = (left_pt[0] + right_pt[0]) / 2.0
    base_y = (left_pt[1] + right_pt[1]) / 2.0
    
    # Screen y-displacement: positive = sag downwards (U/smile), negative = arch upwards (frown/arch)
    dy_screen = mid_pt[1] - base_y
    
    # Semantic upward curvature: positive = arch upward (towards forehead, y < base_y), negative = sag downward (U/smile, y > base_y)
    bend_up = base_y - mid_pt[1]
    
    # Curvature sagitta magnitude
    bend_mag = abs(dy_screen)
    
    # Eye width and height
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    width = max(xs) - min(xs) if xs else 0.0
    height = max(ys) - min(ys) if ys else 0.0
    thick = getattr(e, "thickness", None) or cfg.EYE_THICK
    
    return {
        "shape": e.shape,
        "left_pt": left_pt,
        "right_pt": right_pt,
        "mid_pt": mid_pt,
        "base_pt": (base_x, base_y),
        "dy_screen": dy_screen,
        "bend_up": bend_up,
        "bend_mag": bend_mag,
        "width": width,
        "height": height,
        "thickness": thick,
    }


def classify_curvature(dy: float, tol: float = 0.002) -> str:
    if abs(dy) < tol:
        return "FLAT (0)"
    elif dy > 0:
        return "DOWNWARD (U/smile)"
    else:
        return "UPWARD (arch/frown)"


def trace_transition_path(src_emo: str, tgt_emo: str, u_steps=None, side="left"):
    """Sample and record transition metrics across u in [0, 1]."""
    if u_steps is None:
        u_steps = [i / 20.0 for i in range(21)]  # 0.00, 0.05, ..., 1.00
        
    src_spec = fc.build_face(src_emo, 0.0)
    tgt_spec = fc.build_face(tgt_emo, 0.0)
    
    records = []
    eye_idx = 0 if side == "left" else 1
    
    for u in u_steps:
        eased_u = tr.smootherstep(u)
        interp_spec = tr.interpolate_face(src_spec, tgt_spec, eased_u)
        eye = interp_spec.eyes[eye_idx]
        m = compute_eye_metrics(eye, side)
        
        # Extract internal control details if available
        ctrl_info = {}
        if eye.shape == "sleepy_u" or eye.shape == "quad_curve":
            ctrl_info["p0"] = getattr(eye, "p0", None)
            ctrl_info["p1"] = getattr(eye, "p1", None)
            ctrl_info["p2"] = getattr(eye, "p2", None)
        elif eye.shape == "angry":
            ctrl_info["curve_a"] = eye.curve_a
            ctrl_info["curve_t"] = eye.curve_t
            ctrl_info["curve_b"] = eye.curve_b
            ctrl_info["curve_u"] = eye.curve_u
        elif eye.shape == "arc":
            ctrl_info["r"] = eye.r
            ctrl_info["a0"] = eye.a0
            ctrl_info["a1"] = eye.a1
        elif eye.shape == "circle":
            ctrl_info["rx"] = eye.rx
            ctrl_info["ry"] = eye.ry
            ctrl_info["lid"] = getattr(eye, "lid", 0.0)
            
        rec = {
            "u": u,
            "eased_u": eased_u,
            "shape": eye.shape,
            "left_pt": m["left_pt"],
            "right_pt": m["right_pt"],
            "mid_pt": m["mid_pt"],
            "base_pt": m["base_pt"],
            "dy_screen": m["dy_screen"],
            "bend_up": m["bend_up"],
            "bend_mag": m["bend_mag"],
            "width": m["width"],
            "height": m["height"],
            "thickness": m["thickness"],
            "classification": classify_curvature(m["dy_screen"]),
            "ctrl_info": ctrl_info,
        }
        records.append(rec)
        
    return records


def analyze_path_anomalies(records, src_emo, tgt_emo, side="left"):
    """Detect wrong-direction curvature, unexpected sign reversals, overshoots."""
    dy_start = records[0]["dy_screen"]
    dy_end = records[-1]["dy_screen"]
    
    anomalies = []
    
    # 1. Monotonicity / Wrong Direction check:
    # If source is flat (0) and target is positive (downward), any negative (upward) deflection is wrong-direction.
    # If source is flat (0) and target is negative (upward), any positive (downward) deflection is wrong-direction.
    # If source and target have SAME sign (e.g. both downward, or both upward), any deflection with OPPOSITE sign is wrong-direction.
    # If source and target have OPPOSITE signs (e.g. happy downward -> sad upward), curvature should change sign at most once.
    
    tol = 0.003
    
    first_wrong_frame = None
    sign_changes = 0
    prev_sign = 0
    if abs(dy_start) >= tol:
        prev_sign = 1 if dy_start > 0 else -1
        
    wrong_direction_intervals = []
    current_wrong_start = None
    
    for i, r in enumerate(records):
        dy = r["dy_screen"]
        cur_sign = 0
        if abs(dy) >= tol:
            cur_sign = 1 if dy > 0 else -1
            
        if cur_sign != 0 and prev_sign != 0 and cur_sign != prev_sign:
            sign_changes += 1
        if cur_sign != 0:
            prev_sign = cur_sign
            
        # Check if dy moves in wrong direction
        is_wrong = False
        if abs(dy_start) < tol and abs(dy_end) >= tol:
            # From flat to curved
            target_sign = 1 if dy_end > 0 else -1
            if cur_sign != 0 and cur_sign != target_sign:
                is_wrong = True
        elif abs(dy_end) < tol and abs(dy_start) >= tol:
            # From curved to flat
            start_sign = 1 if dy_start > 0 else -1
            if cur_sign != 0 and cur_sign != start_sign:
                is_wrong = True
        elif (dy_start > tol and dy_end > tol) or (dy_start < -tol and dy_end < -tol):
            # Same sign at both ends
            expected_sign = 1 if dy_start > 0 else -1
            if cur_sign != 0 and cur_sign != expected_sign:
                is_wrong = True
                
        if is_wrong:
            if first_wrong_frame is None:
                first_wrong_frame = r["u"]
            if current_wrong_start is None:
                current_wrong_start = r["u"]
        else:
            if current_wrong_start is not None:
                wrong_direction_intervals.append((current_wrong_start, records[i-1]["u"]))
                current_wrong_start = None
                
    if current_wrong_start is not None:
        wrong_direction_intervals.append((current_wrong_start, records[-1]["u"]))
        
    # Check excessive sign changes (e.g. > 1 for opposite sign transitions, or > 0 for same sign)
    excessive_flips = False
    if (dy_start * dy_end > 0 and sign_changes > 0) or (abs(dy_start) < tol and sign_changes > 0) or (abs(dy_end) < tol and sign_changes > 0) or (sign_changes > 1):
        excessive_flips = True
        
    has_anomaly = (first_wrong_frame is not None) or excessive_flips
    
    # Calculate max divergence
    max_divergence = 0.0
    for r in records:
        dy = r["dy_screen"]
        if dy_start >= 0 and dy_end >= 0 and dy < 0:
            max_divergence = max(max_divergence, abs(dy))
        elif dy_start <= 0 and dy_end <= 0 and dy > 0:
            max_divergence = max(max_divergence, abs(dy))
            
    return {
        "has_anomaly": has_anomaly,
        "first_wrong_frame": first_wrong_frame,
        "sign_changes": sign_changes,
        "wrong_intervals": wrong_direction_intervals,
        "max_divergence": max_divergence,
        "dy_start": dy_start,
        "dy_end": dy_end,
    }


def print_table_for_transition(src_emo: str, tgt_emo: str, side="left"):
    records = trace_transition_path(src_emo, tgt_emo, side=side)
    anomaly = analyze_path_anomalies(records, src_emo, tgt_emo, side=side)
    
    print("=" * 95)
    print(f"TRANSITION: {src_emo} -> {tgt_emo} (Eye: {side})")
    print(f"Start dy: {anomaly['dy_start']:+.4f} ({classify_curvature(anomaly['dy_start'])}) -> End dy: {anomaly['dy_end']:+.4f} ({classify_curvature(anomaly['dy_end'])})")
    print(f"Anomaly: {anomaly['has_anomaly']} | First wrong frame u: {anomaly['first_wrong_frame']} | Sign changes: {anomaly['sign_changes']} | Max divergence: {anomaly['max_divergence']:.4f}")
    if anomaly['wrong_intervals']:
        print(f"Wrong direction intervals (u): {anomaly['wrong_intervals']}")
    print("-" * 95)
    print(f"{'u':<5} | {'eased_u':<7} | {'shape':<9} | {'left_pt':<16} | {'right_pt':<16} | {'mid_pt':<16} | {'dy_screen':<10} | {'Classification'}")
    print("-" * 95)
    for r in records:
        l_s = f"({r['left_pt'][0]:.3f},{r['left_pt'][1]:.3f})"
        r_s = f"({r['right_pt'][0]:.3f},{r['right_pt'][1]:.3f})"
        m_s = f"({r['mid_pt'][0]:.3f},{r['mid_pt'][1]:.3f})"
        print(f"{r['u']:<5.2f} | {r['eased_u']:<7.4f} | {r['shape']:<9} | {l_s:<16} | {r_s:<16} | {m_s:<16} | {r['dy_screen']:<+10.4f} | {r['classification']}")
    print()
    return records, anomaly


def run_full_182_matrix_diagnosis():
    print("=" * 80)
    print("FULL 182 TRANSITION MATRIX WRONG-CURVATURE FORENSIC SCAN")
    print("=" * 80)
    
    all_pairs = []
    for src in em.EMOTION_ORDER:
        for tgt in em.EMOTION_ORDER:
            if src != tgt:
                all_pairs.append((src, tgt))
                
    total_pairs = len(all_pairs)
    anomalous_left = []
    anomalous_right = []
    
    for src, tgt in all_pairs:
        rec_l = trace_transition_path(src, tgt, side="left")
        anom_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
        if anom_l["has_anomaly"]:
            anomalous_left.append((src, tgt, anom_l))
            
        rec_r = trace_transition_path(src, tgt, side="right")
        anom_r = analyze_path_anomalies(rec_r, src, tgt, side="right")
        if anom_r["has_anomaly"]:
            anomalous_right.append((src, tgt, anom_r))
            
    print(f"Total directed transitions scanned: {total_pairs}")
    print(f"Left eye anomalies detected:  {len(anomalous_left)} / {total_pairs} ({len(anomalous_left)/total_pairs*100:.1f}%)")
    print(f"Right eye anomalies detected: {len(anomalous_right)} / {total_pairs} ({len(anomalous_right)/total_pairs*100:.1f}%)")
    print()
    
    print("ANOMALOUS TRANSITION PAIRS BREAKDOWN (Left Eye):")
    print(f"{'Pair':<24} | {'Start -> End Shape':<24} | {'Start dy -> End dy':<22} | {'First Wrong u':<14} | {'Max Div':<8} | {'Intervals'}")
    print("-" * 115)
    for src, tgt, anom in anomalous_left:
        src_spec = fc.build_face(src, 0.0)
        tgt_spec = fc.build_face(tgt, 0.0)
        shape_pair = f"{src_spec.eyes[0].shape} -> {tgt_spec.eyes[0].shape}"
        dy_pair = f"{anom['dy_start']:+.3f} -> {anom['dy_end']:+.3f}"
        u_str = f"u={anom['first_wrong_frame']:.2f}" if anom['first_wrong_frame'] is not None else "SignFlip"
        int_str = str(anom['wrong_intervals'])
        print(f"{src + ' -> ' + tgt:<24} | {shape_pair:<24} | {dy_pair:<22} | {u_str:<14} | {anom['max_divergence']:<8.4f} | {int_str}")
    print()
    return anomalous_left, anomalous_right


def generate_diagnostic_contact_sheet(pairs_to_render):
    """Render frame-by-frame PNG contact sheets for selected transitions."""
    pygame.init()
    surf_size = 300
    tf = g.Transform(0, 0, surf_size)
    
    out_dir = os.path.join(os.path.dirname(__file__), "_diagnose_frames")
    os.makedirs(out_dir, exist_ok=True)
    
    u_steps = [i / 20.0 for i in range(21)]  # 21 frames: 0%, 5%, ..., 100%
    
    for src, tgt in pairs_to_render:
        src_spec = fc.build_face(src, 0.0)
        tgt_spec = fc.build_face(tgt, 0.0)
        
        # Create a contact sheet surface: 21 columns x 1 row (or 7 cols x 3 rows)
        cols = 7
        rows = 3
        cell_w = 160
        cell_h = 180
        sheet = pygame.Surface((cols * cell_w, rows * cell_h))
        sheet.fill((20, 20, 25))
        font = pygame.font.Font(pygame.font.get_default_font(), 12)
        
        for idx, u in enumerate(u_steps):
            col = idx % cols
            row = idx // cols
            x_off = col * cell_w
            y_off = row * cell_h
            
            eased_u = tr.smootherstep(u)
            interp_spec = tr.interpolate_face(src_spec, tgt_spec, eased_u)
            
            # Sub-surface for face
            sub_surf = pygame.Surface((cell_w, cell_w))
            sub_surf.fill(cfg.BG_COLOR)
            sub_tf = g.Transform(0, 0, cell_w)
            rn.render(sub_surf, interp_spec, sub_tf)
            
            sheet.blit(sub_surf, (x_off, y_off))
            
            # Compute metrics for left eye
            m_l = compute_eye_metrics(interp_spec.eyes[0], "left")
            dy = m_l["dy_screen"]
            
            # Label
            lbl1 = font.render(f"u={u:.2f} ({int(u*100)}%)", True, (200, 200, 200))
            lbl2 = font.render(f"{interp_spec.eyes[0].shape} dy={dy:+.3f}", True, (255, 200, 50) if abs(dy)>0.002 else (150, 150, 150))
            sheet.blit(lbl1, (x_off + 5, y_off + cell_w + 2))
            sheet.blit(lbl2, (x_off + 5, y_off + cell_w + 16))
            
        out_path = os.path.join(out_dir, f"{src}_to_{tgt}_path.png")
        pygame.image.save(sheet, out_path)
        print(f"Saved diagnostic contact sheet: {out_path}")
    print()


if __name__ == "__main__":
    # 1. Key transitions deep dive
    key_pairs = [
        ("neutral", "happy"),
        ("happy", "neutral"),
        ("neutral", "sad"),
        ("sad", "neutral"),
        ("neutral", "sleepy"),
        ("sleepy", "neutral"),
        ("neutral", "angry"),
        ("angry", "neutral"),
        ("neutral", "disgusted"),
        ("disgusted", "neutral"),
        ("happy", "sad"),
        ("sad", "happy"),
        ("happy", "sleepy"),
        ("sleepy", "happy"),
        ("happy", "angry"),
        ("angry", "happy"),
        ("happy", "disgusted"),
        ("disgusted", "happy"),
        ("happy", "excited"),
        ("excited", "happy"),
        ("happy", "surprised"),
        ("surprised", "happy"),
        ("happy", "thinking"),
        ("thinking", "happy"),
        ("happy", "confused"),
        ("confused", "happy"),
    ]
    
    print("=" * 80)
    print("KEY PAIRS DETAILED TRACES")
    print("=" * 80)
    for src, tgt in key_pairs:
        print_table_for_transition(src, tgt, side="left")
        
    # 2. Run full 182 matrix scan
    anom_l, anom_r = run_full_182_matrix_diagnosis()
    
    # 3. Generate contact sheets for representative pairs
    render_pairs = [
        ("neutral", "happy"),
        ("happy", "neutral"),
        ("happy", "sad"),
        ("sad", "happy"),
        ("sleepy", "happy"),
        ("happy", "angry"),
        ("happy", "disgusted"),
    ]
    generate_diagnostic_contact_sheet(render_pairs)
