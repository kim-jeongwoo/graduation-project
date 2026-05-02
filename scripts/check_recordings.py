#!/usr/bin/env python3
"""
check_recordings.py — 녹음 파일 품질 전수 검사
================================================
VAD 마스크 기반으로 모든 wav 파일의 실제 발성 구간을 분석하고,
문제 파일(무음 과다, 부분 녹음)을 식별함.

결과: data/vocal_academy/results/recording_quality.json
"""
import os
import json
import glob
import re

import numpy as np
import soundfile as sf

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAL_DIR = os.path.join(PROJECT_ROOT, "data", "vocal_academy")
RESULTS_DIR = os.path.join(VOCAL_DIR, "results")
MASK_DIR = os.path.join(RESULTS_DIR, "vad_masks")

TARGET_SR = 16000
HOP = 256
FRAME_DUR = HOP / TARGET_SR  # seconds per frame

# ── Song reference lengths (approximate, in seconds) ─────────────
SONG_LENGTHS = {
    1:  {"name": "한로로 - 시간을 달리네",       "approx_s": 252},
    2:  {"name": "윤하 - 기다리다",             "approx_s": 277},
    3:  {"name": "보보 - 늦은 후회",            "approx_s": 293},
    4:  {"name": "김범수 - 보고싶다",           "approx_s": 250},
    5:  {"name": "이적 - 다행이다",             "approx_s": 222},
    6:  {"name": "폴킴 - 모든 날, 모든 순간",    "approx_s": 209},
    7:  {"name": "지아 - 물론",                "approx_s": 237},
    8:  {"name": "이하이 - 한숨",              "approx_s": 286},
    9:  {"name": "거미 - 친구라도 될 걸 그랬어",  "approx_s": 134},
    10: {"name": "나윤권 - 나였으면",           "approx_s": 102},
    11: {"name": "양다일 - 요즘",              "approx_s": 113},
    12: {"name": "조성모 - 슬픈 영혼식",         "approx_s": 113},
    13: {"name": "케이윌 - Love Blossom",      "approx_s": 55},
}


def load_vad_mask(singer_id, song_id, mic_type):
    mask_name = f"{singer_id}_{song_id}_{mic_type}_vad.npy"
    mask_path = os.path.join(MASK_DIR, mask_name)
    if os.path.exists(mask_path):
        return np.load(mask_path)
    return None


def analyze_vad_mask(mask):
    """Analyze a VAD mask to get voiced statistics."""
    n = len(mask)
    n_voiced = int(mask.sum())
    voiced_dur = n_voiced * FRAME_DUR
    voiced_ratio = n_voiced / n if n > 0 else 0

    # Longest continuous voiced segment
    max_run = 0
    current_run = 0
    for v in mask:
        if v:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    longest_voiced = max_run * FRAME_DUR

    # Voiced range: first and last voiced frame
    voiced_indices = np.where(mask)[0]
    if len(voiced_indices) > 0:
        first_voiced = voiced_indices[0] * FRAME_DUR
        last_voiced = voiced_indices[-1] * FRAME_DUR
    else:
        first_voiced = 0
        last_voiced = 0

    return {
        "total_frames": n,
        "voiced_frames": n_voiced,
        "voiced_dur_s": round(voiced_dur, 1),
        "voiced_ratio": round(voiced_ratio, 4),
        "longest_continuous_s": round(longest_voiced, 1),
        "voiced_start_s": round(first_voiced, 1),
        "voiced_end_s": round(last_voiced, 1),
    }


def classify_quality(voiced_dur, voiced_ratio):
    """Classify recording quality into 3 grades."""
    if voiced_dur < 30 or voiced_ratio < 0.20:
        return "bad"
    elif voiced_dur < 60 or voiced_ratio < 0.40:
        return "partial"
    else:
        return "ok"


def main():
    all_wavs = sorted(glob.glob(os.path.join(VOCAL_DIR, "singer_*", "*.wav")))
    print(f"Found {len(all_wavs)} wav files\n")

    results = []
    grade_counts = {"ok": 0, "partial": 0, "bad": 0}

    # Table header
    hdr = f"{'Singer':>6} {'Song':>4} {'Type':>6} {'Total(s)':>9} {'Voiced(s)':>9} " \
          f"{'V%':>6} {'MaxRun(s)':>9} {'Range':>15} {'Grade':>7}"
    print(hdr)
    print("-" * len(hdr))

    for wav_path in all_wavs:
        fname = os.path.basename(wav_path)
        m = re.match(r'(\d+)-(\d+)_(\w+)\.wav', fname)
        if not m:
            continue
        singer_id = int(m.group(1))
        song_id = int(m.group(2))
        mic_type = m.group(3)

        # Get total duration
        info = sf.info(wav_path)
        total_dur = info.duration

        # Load VAD mask
        vad = load_vad_mask(singer_id, song_id, mic_type)
        if vad is None:
            print(f"  {fname}: VAD mask not found!")
            continue

        stats = analyze_vad_mask(vad)
        grade = classify_quality(stats["voiced_dur_s"], stats["voiced_ratio"])
        grade_counts[grade] += 1

        # Grade symbol
        sym = {"ok": "✅", "partial": "⚠️", "bad": "❌"}[grade]
        flag = "" if grade == "ok" else f" {sym}"

        range_str = f"{stats['voiced_start_s']:.0f}~{stats['voiced_end_s']:.0f}s"

        print(f"{singer_id:>6} {song_id:>4} {mic_type:>6} {total_dur:>9.1f} "
              f"{stats['voiced_dur_s']:>9.1f} {stats['voiced_ratio']:>5.1%} "
              f"{stats['longest_continuous_s']:>9.1f} {range_str:>15}{flag}")

        song_info = SONG_LENGTHS.get(song_id, {})
        results.append({
            "file": fname,
            "singer_id": singer_id,
            "song_id": song_id,
            "song_name": song_info.get("name", ""),
            "mic_type": mic_type,
            "total_dur_s": round(total_dur, 1),
            **stats,
            "grade": grade,
        })

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Total: {len(results)} files")
    print(f"  ✅ 정상:     {grade_counts['ok']}")
    print(f"  ⚠️ 부분녹음: {grade_counts['partial']}")
    print(f"  ❌ 불량:     {grade_counts['bad']}")

    # ── Singer consistency check ──────────────────────────────────
    print(f"\n{'='*60}")
    print("Singer consistency check (oral/nasal/phone for same song):")
    from collections import defaultdict
    singer_songs = defaultdict(lambda: defaultdict(dict))
    for r in results:
        singer_songs[r["singer_id"]][r["song_id"]][r["mic_type"]] = r["grade"]

    inconsistent = []
    for sid in sorted(singer_songs):
        for song in sorted(singer_songs[sid]):
            types = singer_songs[sid][song]
            grades = set(types.values())
            if len(grades) > 1:
                detail = ", ".join(f"{t}={g}" for t, g in sorted(types.items()))
                inconsistent.append((sid, song, detail))
                print(f"  ⚠️ Singer {sid}, Song {song}: {detail}")

    if not inconsistent:
        print("  ✅ All consistent")

    # ── Problem files list ────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Problem files:")
    bad_files = [r for r in results if r["grade"] == "bad"]
    partial_files = [r for r in results if r["grade"] == "partial"]

    if bad_files:
        print(f"\n  ❌ 불량 ({len(bad_files)}):")
        for r in bad_files:
            print(f"    {r['file']}: voiced={r['voiced_dur_s']}s ({r['voiced_ratio']:.1%})")
    if partial_files:
        print(f"\n  ⚠️ 부분녹음 ({len(partial_files)}):")
        for r in partial_files:
            print(f"    {r['file']}: voiced={r['voiced_dur_s']}s ({r['voiced_ratio']:.1%})")
    if not bad_files and not partial_files:
        print("  ✅ No problems found")

    # ── Save JSON ─────────────────────────────────────────────────
    output = {
        "description": "Recording quality check based on VAD analysis",
        "song_reference": SONG_LENGTHS,
        "summary": {
            "total_files": len(results),
            "ok": grade_counts["ok"],
            "partial": grade_counts["partial"],
            "bad": grade_counts["bad"],
            "inconsistent_singers": [(s, so, d) for s, so, d in inconsistent],
        },
        "files": results,
    }
    json_path = os.path.join(RESULTS_DIR, "recording_quality.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved: {json_path}")


if __name__ == "__main__":
    main()
