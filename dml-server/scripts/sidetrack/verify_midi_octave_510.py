"""
verify_midi_octave_510.py — 5/10 외부 MIDI 6곡 옥타브 검증

각 외부 MIDI 파일과 매칭되는 자체 F0(pitch_guide)을 비교해
+12 또는 -12 semitone 어긋남이 있는지 판정.

매핑:
    김범수 - 보고싶다(T64)        → song 04
    성시경 - 너의 모든 순간(T70)   → song 14
    윤하 - 기다리다(T68)           → song 02
    지아 - 물론(T79)               → song 07
    폴킴 - 모든날모든순간(T67)     → song 06
    허각 - 물론(T79)               → 14곡 외 (보컬 wav 없음, 기록만)

판정:
    |diff| < 6  → 옥타브 정상 → 외부 MIDI 사용 가능
    |diff| ≈ 12 → 옥타브 어긋남 → 자체 F0 사용 결정
    그 외      → 수동 검토
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pretty_midi

ROOT       = Path("/home/dmlserver/projects/egg_prediction")
MIDI_DIR   = ROOT / "data" / "vocal_academy" / "midi_510"
PITCH_DIR  = ROOT / "data" / "songs" / "pitch_guide"
OUT_DIR    = ROOT / "data" / "vocal_academy" / "results" / "sidetrack"

# 외부 MIDI 파일명 → 14곡 song_id 매핑
MAPPING = [
    ("김범수 - 보고싶다(T64).mid",       "004", "김범수 - 보고싶다"),
    ("성시경 - 너의 모든 순간(T70).mid",  "014", "성시경 - 너의 모든 순간"),
    ("윤하 - 기다리다(T68).mid",          "002", "윤하 - 기다리다"),
    ("지아 - 물론(T79).mid",              "007", "지아 - 물론"),
    ("폴킴 - 모든날모든순간(T67).mid",    "006", "폴킴 - 모든날모든순간"),
    ("허각 - 물론(T79).mid",              None,  "허각 - 물론 (14곡 외)"),
]


def midi_pitch_stats(midi_path: Path) -> dict:
    """모든 instrument의 노트 pitch 평균/중앙값/min/max."""
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    pitches: list[int] = []
    n_instruments = 0
    for inst in pm.instruments:
        # 보컬 트랙은 보통 program 0~7(piano), 41(viola), 53(voice ooh) 등 다양
        # 트랙명에 voice/vocal/melody 있으면 우선 사용
        notes = [n.pitch for n in inst.notes]
        if not notes:
            continue
        n_instruments += 1
        pitches.extend(notes)
    if not pitches:
        return {"n_notes": 0}
    arr = np.array(pitches)
    return {
        "n_notes":  len(pitches),
        "n_inst":   n_instruments,
        "mean":     float(arr.mean()),
        "median":   float(np.median(arr)),
        "min":      int(arr.min()),
        "max":      int(arr.max()),
    }


def f0_pitch_stats(song_id: str) -> dict | None:
    """pitch_guide.points의 voiced midi 평균/중앙값/min/max."""
    p = PITCH_DIR / f"{song_id}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    midis = [pt["midi"] for pt in data.get("points", [])
             if pt.get("voiced") and pt.get("midi") is not None]
    if not midis:
        return None
    arr = np.array(midis)
    return {
        "n_frames": len(midis),
        "mean":     float(arr.mean()),
        "median":   float(np.median(arr)),
        "min":      float(arr.min()),
        "max":      float(arr.max()),
    }


def classify(diff: float) -> str:
    """평균 차이 → 판정."""
    a = abs(diff)
    if a < 3:
        return "✓ 외부 MIDI 사용 가능 (차이<3 semitone)"
    if 9 <= a <= 15:
        return "⚠ 옥타브 어긋남 (≈±12) → 자체 F0 사용"
    if a < 6:
        return "△ 약간 어긋남 (3~6) → 수동 검토"
    return "? 큰 차이 (>6) → 수동 검토"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines: list[str] = []
    report_lines.append("# 5/10 외부 MIDI 옥타브 검증 보고서\n")
    report_lines.append("| 외부 MIDI | 매칭 song | MIDI 평균 | 자체 F0 평균 | 차이 | 판정 |")
    report_lines.append("|---|---|---:|---:|---:|---|")

    print(f"\n{'='*80}")
    print(f"{'외부 MIDI':35s}  {'song':5s}  {'MIDI':>8s}  {'F0':>8s}  {'diff':>8s}  판정")
    print(f"{'='*80}")

    for fname, song_id, label in MAPPING:
        midi_path = MIDI_DIR / fname
        if not midi_path.exists():
            print(f"  [{fname}] 파일 없음")
            continue

        m = midi_pitch_stats(midi_path)
        if m["n_notes"] == 0:
            verdict = "❌ 노트 없음"
            print(f"  {fname:35s}  ?       n=0       -         -      {verdict}")
            report_lines.append(f"| {label} | {song_id or '-'} | n=0 | - | - | {verdict} |")
            continue

        if song_id is None:
            verdict = "× 14곡 외 (비교 불가)"
            print(f"  {fname:35s}  -      {m['mean']:>7.1f}     -        -      {verdict}")
            report_lines.append(
                f"| {label} | - | {m['mean']:.1f} | (보컬 wav 없음) | - | {verdict} |"
            )
            continue

        f = f0_pitch_stats(song_id)
        if f is None:
            verdict = "× pitch_guide 없음"
            print(f"  {fname:35s}  {song_id}   {m['mean']:>7.1f}     -        -      {verdict}")
            report_lines.append(f"| {label} | {song_id} | {m['mean']:.1f} | - | - | {verdict} |")
            continue

        diff = m["mean"] - f["mean"]
        verdict = classify(diff)
        print(f"  {fname:35s}  {song_id:5s}  {m['mean']:>7.1f}  {f['mean']:>7.1f}  "
              f"{diff:>+7.2f}   {verdict}")

        report_lines.append(
            f"| {label} | {song_id} | "
            f"{m['mean']:.1f} (n={m['n_notes']}) | "
            f"{f['mean']:.1f} (n={f['n_frames']}) | "
            f"{diff:+.2f} | {verdict} |"
        )

    print(f"{'='*80}\n")

    out_md = OUT_DIR / "midi_octave_check_510.md"
    out_md.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"보고서: {out_md}")


if __name__ == "__main__":
    main()
