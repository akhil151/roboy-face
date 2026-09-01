"""ROBoy Emotion V2 - Forensic Analysis Data Extraction.
Computes and formats all 32 required report points.
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
from _diagnose_eye_blending_path import (
    sample_eye_curve_points,
    compute_eye_metrics,
    classify_curvature,
    trace_transition_path,
    analyze_path_anomalies,
)


def print_key_paths():
    key_pairs = [
        ("neutral", "happy"),
        ("happy", "neutral"),
        ("happy", "sad"),
        ("sad", "happy"),
        ("happy", "sleepy"),
        ("sleepy", "happy"),
        ("happy", "angry"),
        ("angry", "happy"),
        ("happy", "disgusted"),
        ("disgusted", "happy"),
        ("neutral", "sad"),
        ("sad", "neutral"),
        ("neutral", "sleepy"),
        ("sleepy", "neutral"),
        ("neutral", "angry"),
        ("angry", "neutral"),
        ("neutral", "disgusted"),
        ("disgusted", "neutral"),
        ("happy", "excited"),
        ("excited", "happy"),
        ("happy", "surprised"),
        ("surprised", "happy"),
        ("happy", "thinking"),
        ("thinking", "happy"),
        ("happy", "confused"),
        ("confused", "happy"),
    ]

    print("================================================================================")
    print("DETAILED CURVATURE PATHS FOR KEY TRANSITIONS")
    print("================================================================================")
    
    for src, tgt in key_pairs:
        rec_l = trace_transition_path(src, tgt, side="left")
        rec_r = trace_transition_path(src, tgt, side="right")
        anom_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
        anom_r = analyze_path_anomalies(rec_r, src, tgt, side="right")
        
        print(f"\n>>> TRANSITION: {src.upper()} -> {tgt.upper()} <<<")
        print(f"Start dy: {anom_l['dy_start']:+.4f} ({classify_curvature(anom_l['dy_start'])}) -> Target dy: {anom_l['dy_end']:+.4f} ({classify_curvature(anom_l['dy_end'])})")
        print(f"Left Anomaly: {anom_l['has_anomaly']} (First wrong u: {anom_l['first_wrong_frame']}, Sign flips: {anom_l['sign_changes']}, Max div: {anom_l['max_divergence']:.4f})")
        print(f"Right Anomaly: {anom_r['has_anomaly']} (First wrong u: {anom_r['first_wrong_frame']}, Sign flips: {anom_r['sign_changes']}, Max div: {anom_r['max_divergence']:.4f})")
        
        # Print table for left eye
        print(f"{'u':<5} | {'eased_u':<7} | {'shape':<9} | {'left_pt':<16} | {'right_pt':<16} | {'mid_pt':<16} | {'dy_screen':<10} | {'bend_up':<10} | {'Classification'}")
        print("-" * 110)
        for r in rec_l:
            l_s = f"({r['left_pt'][0]:.3f},{r['left_pt'][1]:.3f})"
            r_s = f"({r['right_pt'][0]:.3f},{r['right_pt'][1]:.3f})"
            m_s = f"({r['mid_pt'][0]:.3f},{r['mid_pt'][1]:.3f})"
            print(f"{r['u']:<5.2f} | {r['eased_u']:<7.4f} | {r['shape']:<9} | {l_s:<16} | {r_s:<16} | {m_s:<16} | {r['dy_screen']:<+10.4f} | {r['bend_up']:<+10.4f} | {r['classification']}")
            
        # Curvature values at 0%, 10%, 25%, 50%, 75%, 100%
        key_pcts = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00]
        rec_pcts = trace_transition_path(src, tgt, u_steps=key_pcts, side="left")
        pct_str = ", ".join([f"{int(p*100)}%: {r['dy_screen']:+.4f}" for p, r in zip(key_pcts, rec_pcts)])
        print(f"Key Percentages dy_screen [ {pct_str} ]")


def print_canonical_vs_raw():
    print("\n================================================================================")
    print("RAW EYESPEC VS CANONICAL TRANSITION REPRESENTATION")
    print("================================================================================")
    for emo in ["neutral", "happy", "sad", "sleepy", "angry", "confused", "wink", "disgusted"]:
        face_spec = fc.build_face(emo, 0.0)
        print(f"\n--- Emotion: {emo.upper()} ---")
        for i, eye in enumerate(face_spec.eyes):
            side = "left" if i == 0 else "right"
            raw_dict = {k: v for k, v in vars(eye).items() if v is not None and not (isinstance(v, (int, float)) and v == 0.0 and k not in ('cx', 'cy'))}
            print(f"[{side.upper()} EYE] Raw EyeSpec: shape={eye.shape}, cx={eye.cx:.3f}, cy={eye.cy:.3f}")
            for k, v in raw_dict.items():
                if k not in ('shape', 'cx', 'cy'):
                    if isinstance(v, tuple):
                        print(f"    {k}: ({v[0]:.3f}, {v[1]:.3f})")
                    elif isinstance(v, float):
                        print(f"    {k}: {v:.4f}")
                    else:
                        print(f"    {k}: {v}")
            
            # Canonical anchors
            l_c, r_c, top_c, bot_c, p1_mid, is_up = tr.get_canonical_eye_anchors(eye, side)
            print(f"  Canonical Extracted:")
            print(f"    left_pt:   ({l_c[0]:.3f}, {l_c[1]:.3f})")
            print(f"    right_pt:  ({r_c[0]:.3f}, {r_c[1]:.3f})")
            print(f"    top_ctrl:  ({top_c[0]:.3f}, {top_c[1]:.3f})")
            print(f"    bot_ctrl:  ({bot_c[0]:.3f}, {bot_c[1]:.3f})")
            print(f"    p1_mid:    ({p1_mid[0]:.3f}, {p1_mid[1]:.3f})")
            print(f"    is_upward: {is_up}")
            
            # True geometric midpoint
            pts, l_pt, r_pt, m_pt = sample_eye_curve_points(eye, side)
            base_y = (l_pt[1] + r_pt[1]) / 2.0
            print(f"  Actual Geometric Curve:")
            print(f"    true_midpoint: ({m_pt[0]:.3f}, {m_pt[1]:.3f})")
            print(f"    true dy_screen: {m_pt[1] - base_y:+.4f}")
            print(f"    canonical p1 dy: {p1_mid[1] - base_y:+.4f} (DISCREPANCY: {'INVERTED' if (m_pt[1] - base_y) * (p1_mid[1] - base_y) < -0.0001 else 'MATCH'})")


if __name__ == "__main__":
    print_canonical_vs_raw()
    print_key_paths()
