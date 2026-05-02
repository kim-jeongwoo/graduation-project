#!/usr/bin/env python3
"""
MR 기준 타임라인 변환 스크립트.

입력:
  data/songs/meta/songs.json
  data/songs/pitch_guide/{id}.json          (14곡)
  data/songs/lrc/parsed/{id}_aligned.json   (11곡, LRC 있는 곡만)

출력:
  data/songs/pitch_guide/{id}_mr.json       (14곡)
  data/songs/lrc/parsed/{id}_mr.json        (11곡)

변환 규칙:
  t_mr = time - lrc_offset_sec
  pitch_guide: t_mr < 0 또는 t_mr > mr_duration_sec 이면 drop
  LRC:         time_end_mr <= 0 또는 time_start_mr >= mr_duration_sec 이면 drop
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3] / "data" / "songs"
META_PATH = BASE / "meta" / "songs.json"
PG_DIR = BASE / "pitch_guide"
LRC_DIR = BASE / "lrc" / "parsed"

WARN_DROP_RATIO = 0.05


def load_songs() -> dict:
    with open(META_PATH) as f:
        songs = json.load(f)
    return {s["id"]: s for s in songs}


def convert_pitch_guide(song: dict) -> dict:
    sid = song["id"]
    offset = song["lrc_offset_sec"]
    mr_dur = song["mr_duration_sec"]

    src = PG_DIR / f"{sid}.json"
    with open(src) as f:
        pg = json.load(f)

    original_points = pg["points"]
    converted = []
    for pt in original_points:
        t_mr = round(pt["time"] - offset, 6)
        if t_mr < 0 or t_mr > mr_dur:
            continue
        converted.append({**pt, "time": t_mr})

    n_orig = len(original_points)
    n_drop = n_orig - len(converted)

    out = {
        **pg,
        "duration_sec": mr_dur,
        "lrc_offset_sec": offset,
        "points": converted,
    }
    dst = PG_DIR / f"{sid}_mr.json"
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    return {"song_id": sid, "orig": n_orig, "drop": n_drop}


def convert_lrc(song: dict) -> dict | None:
    sid = song["id"]
    offset = song["lrc_offset_sec"]
    mr_dur = song["mr_duration_sec"]

    src = LRC_DIR / f"{sid}_aligned.json"
    if not src.exists():
        return None

    with open(src) as f:
        lines = json.load(f)

    converted = []
    dropped = 0
    for line in lines:
        ts_mr = round(line["time_start"] - offset, 6)
        te_mr = round(line["time_end"] - offset, 6)
        if te_mr <= 0 or ts_mr >= mr_dur:
            dropped += 1
            continue
        converted.append({**line, "time_start_mr": ts_mr, "time_end_mr": te_mr})

    dst = LRC_DIR / f"{sid}_mr.json"
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    return {"song_id": sid, "orig": len(lines), "drop": dropped}


def print_stats(label: str, results: list[dict | None]) -> None:
    print(f"\n{'─'*55}")
    print(f" {label}")
    print(f"{'─'*55}")
    print(f"{'ID':>3}  {'orig':>6}  {'drop':>5}  {'ratio':>6}  {'!'}")
    print(f"{'─'*55}")
    warnings = []
    for r in results:
        if r is None:
            continue
        ratio = r["drop"] / r["orig"] if r["orig"] else 0
        flag = "⚠" if ratio > WARN_DROP_RATIO else " "
        print(f"{r['song_id']:>3}  {r['orig']:>6}  {r['drop']:>5}  {ratio:>5.1%}  {flag}")
        if ratio > WARN_DROP_RATIO:
            warnings.append(r)
    print(f"{'─'*55}")
    if warnings:
        print(f"\n[경고] drop 비율 {WARN_DROP_RATIO:.0%} 초과:")
        for w in warnings:
            ratio = w["drop"] / w["orig"]
            print(f"  {w['song_id']}: {w['drop']}/{w['orig']} ({ratio:.1%}) 프레임/라인 drop")


def main() -> None:
    songs = load_songs()
    pg_results = []
    lrc_results = []

    for sid in sorted(songs):
        song = songs[sid]
        pg_results.append(convert_pitch_guide(song))
        lrc_results.append(convert_lrc(song))

    print_stats("pitch_guide t_mr 변환 결과", pg_results)
    print_stats("LRC t_mr 변환 결과 (LRC 있는 11곡)", [r for r in lrc_results if r])

    pg_out = list(PG_DIR.glob("*_mr.json"))
    lrc_out = list(LRC_DIR.glob("*_mr.json"))
    print(f"\n출력: pitch_guide {len(pg_out)}개, lrc {len(lrc_out)}개")


if __name__ == "__main__":
    main()
