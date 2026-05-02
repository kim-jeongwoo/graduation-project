#!/usr/bin/env python3
"""
vad_intersect.py — (singer, song) 쌍별 oral/nasal/phone VAD 마스크 교집합 생성
저장: results/vad_masks/{singer}_{song}_intersect_vad.npy
"""
import os
import glob
import re
import numpy as np

VOCAL_DIR = '/home/dmlserver/projects/egg_prediction/data/vocal_academy'
MASK_DIR  = os.path.join(VOCAL_DIR, 'results', 'vad_masks')

# singer_01,04,22: no phone. 6-8: nearly silent.
NO_PHONE = {(1, None), (4, None), (22, None)}  # matched by singer only
KNOWN_BAD = {(6, 8)}  # nearly silent, mark for exclusion

print("F-1: Generating intersect VAD masks")
print("="*60)

# Discover all (singer, song) pairs from individual mask files
pattern = re.compile(r'^(\d+)_(\d+)_(oral|nasal|phone)_vad\.npy$')
groups = {}  # (singer, song) → {type: path}
for fname in sorted(os.listdir(MASK_DIR)):
    m = pattern.match(fname)
    if not m:
        continue
    singer, song, mic_type = int(m.group(1)), int(m.group(2)), m.group(3)
    key = (singer, song)
    if key not in groups:
        groups[key] = {}
    groups[key][mic_type] = os.path.join(MASK_DIR, fname)

results = []
for key in sorted(groups):
    singer, song = key
    types = groups[key]
    
    # Load available masks
    masks = {}
    for t in ['oral', 'nasal', 'phone']:
        if t in types:
            masks[t] = np.load(types[t])
    
    if not masks:
        continue
    
    # Trim to shortest length before AND
    min_len = min(len(m) for m in masks.values())
    trimmed = {t: m[:min_len] for t, m in masks.items()}
    
    # AND intersection
    intersect = np.ones(min_len, dtype=bool)
    for m in trimmed.values():
        intersect &= m
    
    out_name = f'{singer}_{song}_intersect_vad.npy'
    out_path = os.path.join(MASK_DIR, out_name)
    np.save(out_path, intersect)
    
    # Stats
    n_voiced_orig = {t: m.sum() for t, m in trimmed.items()}
    n_intersect = intersect.sum()
    ratio_orig = {t: v/min_len for t, v in n_voiced_orig.items()}
    ratio_inter = n_intersect / min_len if min_len > 0 else 0
    
    is_bad = key in KNOWN_BAD
    flag = ' ⚠️ NEARLY_SILENT' if is_bad else ''
    has_phone = 'phone' in types
    
    way = '2-way' if not has_phone else '3-way'
    ph_val = ratio_orig.get('phone', 0)
    phone_str = f'phone={ph_val:.1%}' if has_phone else 'phone=N/A'
    line = (f"  Singer {singer:2d} Song {song:2d}  "
            f"oral={ratio_orig.get('oral', 0):.1%} "
            f"nasal={ratio_orig.get('nasal', 0):.1%} "
            f"{phone_str:15s}"
            f"-> intersect={ratio_inter:.1%} ({way})" + flag)
    print(line)
    
    results.append({
        'singer': singer, 'song': song,
        'has_phone': has_phone,
        'mask_types': list(types.keys()),
        'n_frames': min_len,
        'voiced_intersect': int(n_intersect),
        'ratio_intersect': round(ratio_inter, 4),
        'ratio_oral': round(ratio_orig.get('oral', 0), 4),
        'ratio_nasal': round(ratio_orig.get('nasal', 0), 4),
        'ratio_phone': round(ratio_orig.get('phone', 0), 4) if has_phone else None,
        'exclude_bad': is_bad,
    })

print(f"\n✅ {len(results)} intersect masks saved to {MASK_DIR}")
voiced_ratios = [r['ratio_intersect'] for r in results if not r['exclude_bad']]
if voiced_ratios:
    print(f"   Intersect voiced: min={min(voiced_ratios):.1%} "
          f"mean={sum(voiced_ratios)/len(voiced_ratios):.1%} "
          f"max={max(voiced_ratios):.1%}")

# Save summary
import json
summary_path = os.path.join(MASK_DIR, 'intersect_summary.json')
with open(summary_path, 'w', encoding='utf-8') as f:
    json.dump({'n_pairs': len(results), 'pairs': results}, f, ensure_ascii=False, indent=2)
print(f"   Summary: {summary_path}")
