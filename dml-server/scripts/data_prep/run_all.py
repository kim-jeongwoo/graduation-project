"""
Stage 3: 14곡 일괄 처리
  - extract_pitch_guide.process_song() 순차 호출
  - results_summary.json 누적 저장
  - 14곡 그리드 PNG 생성
  - 종합 보고

사용법:
  python run_all.py              # 전체 14곡
  python run_all.py --songs 002,003,005
"""

import sys, json, time, argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, str(Path(__file__).parent))
from extract_pitch_guide import process_song, SONGS, VIZ_DIR, BASE, PITCH_DIR, MANUAL_LRC

_NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_NOTO).exists():
    fm.fontManager.addfont(_NOTO)
    matplotlib.rcParams["font.family"] = fm.FontProperties(fname=_NOTO).get_name()

SUMMARY_PATH = BASE / "meta" / "results_summary.json"
GRID_PNG     = BASE / "pitch_guide" / "00_grid_all_songs.png"
NOTE_NAMES   = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]


# ── 그리드 PNG ──────────────────────────────────────────────────

def generate_grid_png(results: list):
    cols = 4
    rows = (len(SONGS) + cols - 1) // cols  # 14곡 → 4행
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5.5, rows * 3.2))
    axes_flat = axes.flatten()

    all_ids = list(SONGS.keys())
    for idx, sid in enumerate(all_ids):
        ax = axes_flat[idx]
        artist, title = SONGS[sid]

        pitch_path = PITCH_DIR / f"{sid}.json"
        if not pitch_path.exists():
            ax.text(0.5, 0.5, f"{sid}\n미처리", ha="center", va="center",
                    transform=ax.transAxes, fontsize=9, color="gray")
            ax.set_xticks([]); ax.set_yticks([])
            continue

        with open(pitch_path) as f:
            data = json.load(f)

        pts = data["points"]
        t_arr = np.array([p["time"] for p in pts])
        m_arr = np.array([p["midi"] if p["midi"] else np.nan for p in pts])
        c_arr = np.array([p["confidence"] for p in pts])
        v_arr = np.array([p["voiced"] for p in pts])
        dur   = data["duration_sec"]

        ax.scatter(t_arr[v_arr], m_arr[v_arr],
                   c=c_arr[v_arr], cmap="Blues", vmin=0.5, vmax=1.0, s=1, alpha=0.75)

        for seg in data["review_segments"]:
            ax.axvspan(seg["start"], seg["end"], alpha=0.3, color="orange")

        ax.set_xlim(0, dur)
        vm = m_arr[v_arr]
        if len(vm):
            lo = max(float(np.nanmin(vm)) - 2, 36)
            hi = min(float(np.nanmax(vm)) + 2, 96)
            ax.set_ylim(lo, hi)
            yticks = list(range(int(lo), int(hi)+1, 3))
            ax.set_yticks(yticks)
            ax.set_yticklabels([f"{NOTE_NAMES[m%12]}{m//12-1}" for m in yticks], fontsize=5)

        ax.tick_params(axis="x", labelsize=5)
        ax.grid(axis="y", alpha=0.2)
        ax.set_xlabel("Time (s)", fontsize=5)

        # 통계 from results
        r = next((x for x in results if x["song_id"] == sid), None)
        al_sym = "⚠" if r and r["alignment_status"] == "needs_review" else ""
        rv_sym = "★" if r and r["review_segments_count"] > 0 else ""
        cf_str = f"{r['confidence_avg']:.2f}" if r else "?"
        off_str = f"{r['offset_sec']:+.2f}s" if r else "?"
        no_lrc = " (no LRC)" if sid in MANUAL_LRC else ""

        ax.set_title(
            f"{sid} {artist} - {title}{no_lrc}\n"
            f"conf={cf_str}  off={off_str}  {al_sym}{rv_sym}",
            fontsize=6.5, pad=2
        )

    # 빈 칸 숨기기
    for j in range(len(all_ids), len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("전체 음정 곡선 요약 (14곡) — voiced 구간 · 파란색=고신뢰 · 주황=review", fontsize=12)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(GRID_PNG, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[GRID] 저장: {GRID_PNG}")


# ── 종합 보고 ───────────────────────────────────────────────────

def print_report(results: list, total_sec: float):
    ok       = [r for r in results if r["status"] == "ok"]
    failed   = [r for r in results if r["status"] != "ok"]
    nr       = [r for r in ok if r["alignment_status"] == "needs_review"]
    rev      = [r for r in ok if r["review_segments_count"] > 0]
    low_conf = [r for r in ok if r["confidence_avg"] < 0.7]

    print(f"\n{'='*65}")
    print(f"종합 보고  (총 소요: {total_sec/60:.1f}분  /  {total_sec:.0f}s)")
    print(f"{'='*65}")

    print(f"\n✓ 성공: {len(ok)}/{len(results)}")
    if failed:
        print(f"✗ 실패:")
        for r in failed:
            print(f"    [{r['song_id']}] {r.get('error','?')}")

    print()
    if nr:
        print(f"⚠ needs_review (|offset| > 5s):")
        for r in nr:
            print(f"    [{r['song_id']}] offset={r['offset_sec']:+.3f}s")
    else:
        print("✓ alignment: 전곡 auto")

    if rev:
        print(f"⚠ review_segments 발생:")
        for r in rev:
            print(f"    [{r['song_id']}] {r['review_segments_count']}개")
    else:
        print("✓ review_segments: 없음")

    if low_conf:
        print(f"⚠ confidence < 0.7 (보컬 분리 품질 의심):")
        for r in low_conf:
            print(f"    [{r['song_id']}] conf={r['confidence_avg']:.3f}")
    else:
        print("✓ confidence: 전곡 0.7 이상")

    print(f"\n{'─'*65}")
    h = f"{'ID':<5} {'가수':<7} {'voiced':>7} {'conf':>6} {'offset':>8} {'rev':>4} {'MB':>5}  상태"
    print(h)
    print("─" * len(h))
    for r in results:
        sym  = "✓" if r["status"] == "ok" else "✗"
        al   = "⚠NR" if r.get("alignment_status") == "needs_review" else "  ok"
        rv   = f"★{r['review_segments_count']}" if r.get("review_segments_count", 0) > 0 else "  -"
        lrc  = "" if r.get("has_lrc") else " (no LRC)"
        artist = SONGS[r["song_id"]][0]
        print(f"{r['song_id']:<5} {artist:<7} "
              f"{r.get('voiced_ratio',0):>7.1%} "
              f"{r.get('confidence_avg',0):>6.3f} "
              f"{r.get('offset_sec',0):>+8.3f} "
              f"{rv:>4} "
              f"{r.get('pitch_guide_size_mb',0):>5.2f}  "
              f"{sym} {al}{lrc}")


# ── 메인 ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--songs", metavar="IDS",
                        help="처리할 곡 ID (쉼표 구분, 예: 002,003). 생략 시 전체.")
    args = parser.parse_args()

    if args.songs:
        target_ids = [s.strip().zfill(3) for s in args.songs.split(",")]
    else:
        target_ids = list(SONGS.keys())

    total_start = time.time()
    results = []

    print(f"=== 일괄 Stage 2 처리 시작: {len(target_ids)}곡 ===")
    print(f"순서: {target_ids}\n")

    for i, sid in enumerate(target_ids, 1):
        elapsed = time.time() - total_start
        artist, title = SONGS[sid]
        print(f"\n{'━'*65}")
        print(f"[{i:02d}/{len(target_ids):02d}] {sid} {artist} - {title}"
              f"   누적: {elapsed:.0f}s ({elapsed/60:.1f}min)")
        print(f"{'━'*65}")

        try:
            r = process_song(sid)
            r["artist"] = artist
            r["title"]  = title
            r["status"] = "ok"
        except Exception as e:
            import traceback
            print(f"  ✗ 오류: {e}")
            traceback.print_exc()
            r = {
                "song_id": sid, "artist": artist, "title": title,
                "status": "error", "error": str(e),
                "demucs_sec": 0, "crepe_sec": 0,
                "voiced_ratio": 0, "confidence_avg": 0,
                "offset_sec": 0, "alignment_status": "error",
                "review_segments_count": 0, "pitch_guide_size_mb": 0,
                "has_lrc": False,
            }

        results.append(r)

        # 중간 저장
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        done_ok = sum(1 for x in results if x["status"] == "ok")
        print(f"  → {i}곡 완료 ({done_ok} 성공)  누적: {time.time()-total_start:.0f}s")

    total_sec = time.time() - total_start

    generate_grid_png(results)
    print_report(results, total_sec)

    print(f"\n결과 파일:")
    print(f"  summary: {SUMMARY_PATH}")
    print(f"  grid:    {GRID_PNG}")


if __name__ == "__main__":
    main()
