"""Extract exact numbers for key pairs and write to text file for reference.
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

def dump_all_data():
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
    
    with open("_forensics_dump.txt", "w") as f:
        f.write("KEY PAIRS DATA DUMP\n")
        f.write("===================\n\n")
        for src, tgt in key_pairs:
            rec_l = trace_transition_path(src, tgt, side="left")
            anom_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
            
            f.write(f"=== {src.upper()} -> {tgt.upper()} ===\n")
            f.write(f"Start dy: {anom_l['dy_start']:+.4f} ({classify_curvature(anom_l['dy_start'])}) -> Target dy: {anom_l['dy_end']:+.4f} ({classify_curvature(anom_l['dy_end'])})\n")
            f.write(f"Anomaly: {anom_l['has_anomaly']} | First wrong u: {anom_l['first_wrong_frame']} | Sign flips: {anom_l['sign_changes']} | Max div: {anom_l['max_divergence']:.4f}\n")
            f.write(f"Wrong intervals: {anom_l['wrong_intervals']}\n")
            
            key_pcts = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00]
            rec_pcts = trace_transition_path(src, tgt, u_steps=key_pcts, side="left")
            pct_str = ", ".join([f"{int(p*100)}%: {r['dy_screen']:+.4f}" for p, r in zip(key_pcts, rec_pcts)])
            f.write(f"Key Percentages dy_screen [ {pct_str} ]\n")
            
            f.write("Full Table (Left Eye):\n")
            f.write(f"{'u':<5} | {'eased_u':<7} | {'shape':<9} | {'left_pt':<16} | {'right_pt':<16} | {'mid_pt':<16} | {'dy_screen':<10} | {'bend_up':<10} | {'Classification'}\n")
            f.write("-" * 110 + "\n")
            for r in rec_l:
                l_s = f"({r['left_pt'][0]:.3f},{r['left_pt'][1]:.3f})"
                r_s = f"({r['right_pt'][0]:.3f},{r['right_pt'][1]:.3f})"
                m_s = f"({r['mid_pt'][0]:.3f},{r['mid_pt'][1]:.3f})"
                f.write(f"{r['u']:<5.2f} | {r['eased_u']:<7.4f} | {r['shape']:<9} | {l_s:<16} | {r_s:<16} | {m_s:<16} | {r['dy_screen']:<+10.4f} | {r['bend_up']:<+10.4f} | {r['classification']}\n")
            f.write("\n")

if __name__ == "__main__":
    dump_all_data()
