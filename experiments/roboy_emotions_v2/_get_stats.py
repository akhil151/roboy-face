"""Get exact summary stats for the 182 transitions.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import emotions as em
import face as fc
import transition as tr
from _diagnose_eye_blending_path import trace_transition_path, analyze_path_anomalies

all_pairs = []
for src in em.EMOTION_ORDER:
    for tgt in em.EMOTION_ORDER:
        if src != tgt:
            all_pairs.append((src, tgt))

anom_l = []
anom_r = []

for src, tgt in all_pairs:
    rec_l = trace_transition_path(src, tgt, side="left")
    a_l = analyze_path_anomalies(rec_l, src, tgt, side="left")
    if a_l["has_anomaly"]:
        anom_l.append((src, tgt, a_l))
        
    rec_r = trace_transition_path(src, tgt, side="right")
    a_r = analyze_path_anomalies(rec_r, src, tgt, side="right")
    if a_r["has_anomaly"]:
        anom_r.append((src, tgt, a_r))

print(f"Total pairs: {len(all_pairs)}")
print(f"Left eye anomalies: {len(anom_l)} / {len(all_pairs)} ({len(anom_l)/len(all_pairs)*100:.1f}%)")
print(f"Right eye anomalies: {len(anom_r)} / {len(all_pairs)} ({len(anom_r)/len(all_pairs)*100:.1f}%)")

# Categorize anomalous pairs by eye shapes
shape_categories = {}
for src, tgt, a in anom_l:
    s0 = fc.build_face(src, 0.0).eyes[0].shape
    s1 = fc.build_face(tgt, 0.0).eyes[0].shape
    cat = f"{s0} -> {s1}"
    shape_categories[cat] = shape_categories.get(cat, 0) + 1

print("\nShape pair breakdown for left eye anomalies:")
for k, v in sorted(shape_categories.items(), key=lambda x: -x[1]):
    print(f"  {k:<20}: {v} transitions")
