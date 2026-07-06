"""
f0_to_midi_segments.py — pitch_guide F0 → 직선 MIDI 세그먼트 변환
=====================================================================
CREPE 추출 F0(pitch_guide JSON의 points[])를 연속 음표 구간으로 변환.
외부 MIDI 없이 가수의 실제 보컬에서 자체 추출.

사용법:
    python f0_to_midi_segments.py --song 004
    python f0_to_midi_segments.py --song 004 --dry-run        # JSON 수정 없이 비교만
    python f0_to_midi_segments.py --song 004 --smoothing median
    python f0_to_midi_segments.py --song 004 --midi-threshold 0.3
    python f0_to_midi_segments.py --all
"""
import argparse
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

_NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_NOTO).exists():
    fm.fontManager.addfont(_NOTO)
    matplotlib.rcParams["font.family"] = fm.FontProperties(fname=_NOTO).get_name()

BASE      = Path(__file__).resolve().parents[3] / "data" / "songs"
PITCH_DIR = BASE / "pitch_guide"
LRC_DIR   = BASE / "lrc" / "parsed"
META_PATH = BASE / "meta" / "songs.json"
VIZ_DIR   = Path(__file__).resolve().parents[3] / "dml-server" / "results" / "sidetrack"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SONGS = {
    "001": "한로로",  "002": "윤하",   "003": "보보",   "004": "김범수",
    "005": "이적",    "006": "폴킴",   "007": "지아",   "008": "이하이",
    "009": "거미",    "010": "나윤권", "011": "양다일", "012": "조성모",
    "013": "케이윌",  "014": "성시경",
}


def midi_to_note(m: int) -> str:
    return NOTE_NAMES[m % 12] + str(m // 12 - 1)


def _rolling_median(arr: np.ndarray, window: int = 5) -> np.ndarray:
    pad = window // 2
    padded = np.pad(arr, pad, mode="edge")
    return np.array([np.median(padded[i:i + window]) for i in range(len(arr))])


def extract_f0_segments(
    points: list,
    midi_threshold: float = 0.5,
    min_segment_ms: float = 100,
    voiced_gap_ms: float = 100,
    smoothing: str | None = None,
) -> list[dict]:
    """
    points[] → midi_segments[]

    Args:
        points:          pitch_guide JSON의 points 리스트
        midi_threshold:  이 이상 MIDI 변화 시 새 음표 시작 (semitone 단위)
        min_segment_ms:  이 미만 세그먼트 제거 (ms)
        voiced_gap_ms:   이 이상 무음 간격 시 새 음표 시작 (ms)
        smoothing:       None | "median" (50ms 중앙값 필터)
    """
    # 1. voiced 프레임 추출
    voiced_pairs = [
        (float(p["time"]), float(p["midi"]))
        for p in points
        if p.get("voiced") and p.get("midi") is not None
    ]
    if not voiced_pairs:
        return []

    times = np.array([t for t, _ in voiced_pairs])
    midis = np.array([m for _, m in voiced_pairs])

    # 2. 선택적 smoothing (50ms → window=5 at 10ms/frame)
    if smoothing == "median":
        midis = _rolling_median(midis, window=5)

    # 3. 세그먼트 경계 탐지
    raw_segments: list[tuple[float, float, np.ndarray]] = []
    seg_start = 0

    for i in range(1, len(times)):
        gap_ms      = (times[i] - times[i - 1]) * 1000
        midi_change = abs(midis[i] - midis[i - 1])

        new_seg = gap_ms >= voiced_gap_ms or midi_change >= midi_threshold

        if new_seg:
            raw_segments.append((float(times[seg_start]),
                                  float(times[i - 1]) + 0.01,
                                  midis[seg_start:i]))
            seg_start = i

    # 마지막 세그먼트
    raw_segments.append((float(times[seg_start]),
                          float(times[-1]) + 0.01,
                          midis[seg_start:]))

    # 4. 짧은 세그먼트 제거 + 정수 MIDI 산출
    segments: list[dict] = []
    for start, end, seg_midis in raw_segments:
        dur_ms = (end - start) * 1000
        if dur_ms < min_segment_ms:
            continue
        avg_midi = int(round(float(np.mean(seg_midis))))
        segments.append({
            "start":     round(start, 3),
            "end":       round(end, 3),
            "midi":      avg_midi,
            "note_name": midi_to_note(avg_midi),
        })

    # 5. 인접 동일 음표 병합 (gap < voiced_gap_ms)
    merged: list[dict] = []
    for seg in segments:
        if merged and seg["midi"] == merged[-1]["midi"]:
            gap_ms = (seg["start"] - merged[-1]["end"]) * 1000
            if gap_ms < voiced_gap_ms:
                merged[-1]["end"] = seg["end"]
                continue
        merged.append(dict(seg))

    return merged


# ── 비교 + 시각화 ─────────────────────────────────────────────────────

def compare_segments(ext_segs: list, f0_segs: list, sid: str, points: list) -> dict:
    """외부 MIDI vs 자체 F0 비교 통계 계산."""
    def stats(segs):
        if not segs:
            return dict(n=0, midi_min=None, midi_max=None, midi_mean=None,
                        first_start=None, first_10=None)
        midis = [s["midi"] for s in segs]
        return dict(
            n=len(segs),
            midi_min=min(midis),
            midi_max=max(midis),
            midi_mean=round(sum(midis) / len(midis), 1),
            first_start=segs[0]["start"],
            first_10=[s["midi"] for s in segs[:10]],
        )

    e, f = stats(ext_segs), stats(f0_segs)

    # 옥타브 차이 분석 (매칭 기준: 가장 가까운 외부 MIDI segment 기준)
    diffs = []
    for f_seg in f0_segs[:50]:
        f_mid  = (f_seg["start"] + f_seg["end"]) / 2
        # 같은 시간대의 외부 MIDI segment 찾기
        overlaps = [
            s["midi"] - f_seg["midi"]
            for s in ext_segs
            if s["start"] <= f_mid <= s["end"]
        ]
        diffs.extend(overlaps)

    if diffs:
        diff_arr  = np.array(diffs)
        oct_diag  = f"평균 차이={np.mean(diff_arr):+.1f}  중앙값={np.median(diff_arr):+.1f}  범위=[{diff_arr.min():+.0f}, {diff_arr.max():+.0f}]"
        if abs(np.median(diff_arr) - 12) < 2:
            oct_verdict = "외부 MIDI +1 옥타브 (Steinway 트랙 옥타브 높음)"
        elif abs(np.median(diff_arr) + 12) < 2:
            oct_verdict = "외부 MIDI -1 옥타브"
        elif abs(np.median(diff_arr)) < 2:
            oct_verdict = "옥타브 차이 없음 (다른 원인)"
        else:
            oct_verdict = f"불규칙 차이 (즉흥 옥타브 시프트 또는 다른 곡)"
    else:
        oct_diag    = "겹치는 구간 없음"
        oct_verdict = "분석 불가"

    return dict(ext=e, f0=f, oct_diag=oct_diag, oct_verdict=oct_verdict, diffs=diffs)


def print_comparison(cmp: dict, sid: str):
    e, f = cmp["ext"], cmp["f0"]

    def n2s(v): return f"{midi_to_note(v)} ({v})" if v is not None else "N/A"

    print(f"\n{'='*60}")
    print(f"  {sid} 비교: 외부 MIDI vs 자체 F0")
    print(f"{'='*60}")
    print(f"{'항목':<22} {'외부 MIDI (Steinway)':<22} {'자체 F0 (vocals)'}")
    print("-" * 60)
    print(f"{'segments 수':<22} {e['n']:<22} {f['n']}")
    print(f"{'음역대 min':<22} {n2s(e['midi_min']):<22} {n2s(f['midi_min'])}")
    print(f"{'음역대 max':<22} {n2s(e['midi_max']):<22} {n2s(f['midi_max'])}")
    print(f"{'평균 MIDI':<22} {str(e['midi_mean']):<22} {f['midi_mean']}")
    print(f"{'첫 segment start':<22} {str(e['first_start'])+'s':<22} {f['first_start']}s")
    print(f"{'첫 10개 MIDI':<22} {str(e['first_10']):<22} {f['first_10']}")
    print()
    print(f"  옥타브 차이 분석:  {cmp['oct_diag']}")
    print(f"  진단:              {cmp['oct_verdict']}")
    print(f"{'='*60}\n")


def visualize_comparison(ext_segs: list, f0_segs: list, points: list,
                         sid: str, lrc_times: list, window_sec: float = 60.0):
    """외부 MIDI vs 자체 F0 비교 PNG 생성."""
    fig, ax = plt.subplots(figsize=(16, 6))
    fig.suptitle(f"{sid} — 외부 MIDI vs 자체 F0 비교  (첫 {window_sec:.0f}초)", fontsize=13)

    # CREPE raw points (voiced) — gray background
    voiced_t = [p["time"] for p in points if p.get("voiced") and p.get("midi") is not None]
    voiced_m = [p["midi"]  for p in points if p.get("voiced") and p.get("midi") is not None]
    voiced_t = [t for t in voiced_t if t <= window_sec]
    voiced_m = voiced_m[:len(voiced_t)]
    ax.scatter(voiced_t, voiced_m, s=1, alpha=0.3, color="gray", label="CREPE raw")

    # 외부 MIDI segments — 빨간 직선
    for seg in ext_segs:
        if seg["start"] > window_sec:
            break
        e = min(seg["end"], window_sec)
        ax.hlines(seg["midi"], seg["start"], e, colors="red", linewidth=2, alpha=0.8)
    ax.hlines([], [], [], colors="red", linewidth=2, label="외부 MIDI")  # legend proxy

    # 자체 F0 segments — 파란 직선
    for seg in f0_segs:
        if seg["start"] > window_sec:
            break
        e = min(seg["end"], window_sec)
        ax.hlines(seg["midi"], seg["start"], e, colors="steelblue", linewidth=2, alpha=0.8)
    ax.hlines([], [], [], colors="steelblue", linewidth=2, label="자체 F0")  # legend proxy

    # LRC 세로선
    for lt in lrc_times:
        if 0 < lt <= window_sec:
            ax.axvline(lt, color="green", alpha=0.3, linewidth=0.8)
    ax.axvline(0, color="green", alpha=0.3, linewidth=0.8, label="LRC 라인")

    # 축
    all_midis = [s["midi"] for s in ext_segs + f0_segs]
    if all_midis:
        lo = max(min(all_midis) - 4, 36)
        hi = min(max(all_midis) + 4, 96)
    else:
        lo, hi = 48, 84
    ax.set_ylim(lo, hi)
    ax.set_xlim(0, window_sec)

    yticks = range(int(lo), int(hi) + 1, 2)
    ax.set_yticks(list(yticks))
    ax.set_yticklabels([f"{NOTE_NAMES[m%12]}{m//12-1}" for m in yticks], fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("MIDI pitch")
    ax.legend(loc="upper right", fontsize=9)

    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    out = VIZ_DIR / f"{sid}_midi_vs_f0_comparison.png"
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  [PNG] {out}")
    return out


# ── 메인 처리 ────────────────────────────────────────────────────────

def process_song(
    sid: str,
    midi_threshold: float = 0.5,
    min_segment_ms: float = 100,
    voiced_gap_ms: float = 100,
    smoothing: str | None = None,
    dry_run: bool = False,
    visualize: bool = True,
) -> dict:
    pitch_path = PITCH_DIR / f"{sid}.json"
    if not pitch_path.exists():
        print(f"  [SKIP] pitch_guide 없음: {pitch_path}")
        return {"song_id": sid, "status": "no_pitch_guide"}

    with open(pitch_path, encoding="utf-8") as f:
        pg = json.load(f)

    points = pg.get("points", [])
    if not points:
        print(f"  [SKIP] points 없음")
        return {"song_id": sid, "status": "no_points"}

    print(f"  [F0] {len(points)} frames → 추출 중 (threshold={midi_threshold}, "
          f"min={min_segment_ms}ms, gap={voiced_gap_ms}ms, smoothing={smoothing})")

    f0_segs = extract_f0_segments(
        points,
        midi_threshold=midi_threshold,
        min_segment_ms=min_segment_ms,
        voiced_gap_ms=voiced_gap_ms,
        smoothing=smoothing,
    )
    print(f"  [F0] 추출 완료: {len(f0_segs)} segments")

    # 비교 출력
    ext_segs = pg.get("midi_segments", [])
    cmp = compare_segments(ext_segs, f0_segs, sid, points)
    print_comparison(cmp, sid)

    # 시각화
    lrc_times = []
    lrc_path = LRC_DIR / f"{sid}_aligned.json"
    if lrc_path.exists():
        with open(lrc_path) as f2:
            lrc_times = [l["time_start"] for l in json.load(f2)]

    if visualize:
        visualize_comparison(ext_segs, f0_segs, points, sid, lrc_times, window_sec=60.0)

    if not dry_run:
        # 기존 외부 MIDI 백업 (없을 경우)
        bak = PITCH_DIR / f"{sid}_external_midi.json"
        if not bak.exists() and pg.get("guide_source") == "midi":
            shutil.copy(pitch_path, bak)
            print(f"  [BAK] {bak.name} 백업 생성")

        pg["guide_source"]  = "f0"
        pg["midi_segments"] = f0_segs
        pg.pop("midi_track_pm",   None)
        pg.pop("midi_track_name", None)
        with open(pitch_path, "w", encoding="utf-8") as f:
            json.dump(pg, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  [JSON] {pitch_path.name} 갱신 (guide_source=f0, {len(f0_segs)} segments)")
    else:
        print(f"  [DRY-RUN] JSON 수정 없음")

    return {
        "song_id":      sid,
        "status":       "dry-run" if dry_run else "ok",
        "n_f0_segs":    len(f0_segs),
        "n_ext_segs":   len(ext_segs),
        "oct_verdict":  cmp["oct_verdict"],
    }


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="F0 → MIDI segments 변환")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--song", metavar="ID")
    g.add_argument("--all", action="store_true")
    parser.add_argument("--midi-threshold",  type=float, default=0.5,
                        help="음표 경계 MIDI 변화 임계값 (기본 0.5 semitone)")
    parser.add_argument("--min-segment-ms",  type=float, default=100,
                        help="최소 세그먼트 길이 (기본 100ms)")
    parser.add_argument("--voiced-gap-ms",   type=float, default=100,
                        help="무음 간격 임계값 (기본 100ms)")
    parser.add_argument("--smoothing",       type=str,   default=None,
                        choices=[None, "median"],
                        help="smoothing 방식 (기본 none)")
    parser.add_argument("--dry-run",         action="store_true",
                        help="JSON 수정 없이 비교/시각화만 출력")
    parser.add_argument("--no-viz",          action="store_true",
                        help="시각화 PNG 생성 안 함")
    args = parser.parse_args()

    ids = [args.song.zfill(3)] if args.song else sorted(SONGS.keys())

    for sid in ids:
        print(f"\n{'='*55}\n[{sid}] {SONGS.get(sid, '')}\n{'='*55}")
        r = process_song(
            sid,
            midi_threshold=args.midi_threshold,
            min_segment_ms=args.min_segment_ms,
            voiced_gap_ms=args.voiced_gap_ms,
            smoothing=args.smoothing,
            dry_run=args.dry_run,
            visualize=not args.no_viz,
        )
        icon = "✓" if r.get("status") in ("ok", "dry-run") else "✗"
        print(f"  → {icon} {r.get('status')}  f0={r.get('n_f0_segs')}  ext={r.get('n_ext_segs')}")


if __name__ == "__main__":
    main()
