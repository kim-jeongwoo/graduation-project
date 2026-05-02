"""
Stage 2: 가수 음정 곡선 추출
  1. Demucs 보컬 분리 (htdemucs, --two-stems=vocals)
  2. CREPE F0 추출 (step_size=10ms, viterbi=True)
  3. no_vocals vs MR cross-correlation 시간 정렬
  4. pitch_guide/{id}.json 출력
  5. 시각화 PNG 저장

사용법:
  python extract_pitch_guide.py --song 004
  python extract_pitch_guide.py --all
"""

import os, sys, re, json, time, shutil, argparse, subprocess
from pathlib import Path
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
from matplotlib.ticker import MultipleLocator

_NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_NOTO).exists():
    fm.fontManager.addfont(_NOTO)
    matplotlib.rcParams["font.family"] = fm.FontProperties(fname=_NOTO).get_name()

BASE       = Path(__file__).resolve().parents[3] / "data" / "songs"
MASTER_DIR = BASE / "audio" / "master"
MR_DIR     = BASE / "audio" / "mr"
STEMS_DIR  = BASE / "stems"
LRC_PARSED = BASE / "lrc" / "parsed"
PITCH_DIR  = BASE / "pitch_guide"
VIZ_DIR    = BASE / "pitch_guide"   # PNG도 같은 폴더
META_PATH  = BASE / "meta" / "songs.json"

SONGS = {
    "001": ("한로로",  "시간을달리네"),
    "002": ("윤하",   "기다리다"),
    "003": ("보보",   "늦은후회"),
    "004": ("김범수", "보고싶다"),
    "005": ("이적",   "다행이다"),
    "006": ("폴킴",   "모든날모든순간"),
    "007": ("지아",   "물론"),
    "008": ("이하이", "한숨"),
    "009": ("거미",   "친구라도될걸그랬어"),
    "010": ("나윤권", "나였으면"),
    "011": ("양다일", "요즘"),
    "012": ("조성모", "슬픈영혼식"),
    "013": ("케이윌", "LoveBlossom"),
    "014": ("성시경", "너의모든순간"),
}

MANUAL_LRC = {"001", "007", "011"}   # LRC 없는 곡


# ── 0. 경로 헬퍼 ────────────────────────────────────────────────

def master_path(sid):
    artist, title = SONGS[sid]
    return MASTER_DIR / f"{sid}_{artist}_{title}.mp3"

def mr_path(sid):
    artist, title = SONGS[sid]
    return MR_DIR / f"{sid}_{artist}_{title}_MR.mp3"

def stems_dir(sid):
    return STEMS_DIR / sid

def fmt(sec):
    return f"{int(sec//60)}:{int(sec%60):02d}"


# ── 1. Demucs ───────────────────────────────────────────────────

def run_demucs(sid: str) -> tuple[Path, Path]:
    """
    반환: (vocals_path, no_vocals_path)
    """
    artist, title = SONGS[sid]
    stem_out = stems_dir(sid)

    vocals_dst    = stem_out / "vocals.wav"
    no_vocals_dst = stem_out / "no_vocals.wav"

    if vocals_dst.exists() and no_vocals_dst.exists():
        print(f"  [Demucs] 캐시 사용: {stem_out}")
        return vocals_dst, no_vocals_dst

    stem_out.mkdir(parents=True, exist_ok=True)
    src = master_path(sid)
    print(f"  [Demucs] 시작: {src.name}")
    t0 = time.time()

    # demucs는 {out}/{model}/{track_name_without_ext}/ 에 출력
    tmp_out = STEMS_DIR / "_tmp"
    tmp_out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["conda", "run", "-n", "EGGDML",
         "demucs", "--two-stems=vocals",
         "-o", str(tmp_out),
         str(src)],
        capture_output=False, text=True
    )
    elapsed = time.time() - t0
    if result.returncode != 0:
        raise RuntimeError("Demucs 실패")

    # 출력 파일 탐색: htdemucs/{track_name}/vocals.wav
    track_name = src.stem
    found_vocals = list(tmp_out.rglob(f"{track_name}/vocals.wav"))
    found_novoc  = list(tmp_out.rglob(f"{track_name}/no_vocals.wav"))
    if not found_vocals:
        raise RuntimeError(f"Demucs 출력 vocals.wav 없음: {tmp_out}")
    
    model_used = found_vocals[0].parent.parent.name  # htdemucs / mdx_extra etc.
    shutil.move(str(found_vocals[0]),  str(vocals_dst))
    shutil.move(str(found_novoc[0]),   str(no_vocals_dst))
    shutil.rmtree(tmp_out, ignore_errors=True)

    print(f"  [Demucs] 완료 ({elapsed:.1f}s) — 모델: {model_used}")
    return vocals_dst, no_vocals_dst, model_used, elapsed


# ── 2. CREPE F0 추출 ────────────────────────────────────────────

def run_crepe(vocals_path: Path, cache_dir: Path, sr_target=16000) -> tuple:
    """
    반환: (time_arr, freq_arr, conf_arr, voiced_arr, midi_arr, elapsed_sec)
    cache_dir/crepe_cache.npz 에 결과 캐싱 — 재실행 시 즉시 로드.
    """
    cache_path = cache_dir / "crepe_cache.npz"
    elapsed = 0.0

    if cache_path.exists():
        print(f"  [CREPE] 캐시 로드: {cache_path.name}")
        d = np.load(cache_path)
        time_arr, freq_arr, conf_arr = d["time"], d["freq"], d["conf"]
    else:
        import crepe
        print(f"  [CREPE] 로드: {vocals_path.name}")
        audio, sr = librosa.load(str(vocals_path), sr=sr_target, mono=True)
        print(f"  [CREPE] 추출 시작 (duration={len(audio)/sr:.1f}s, CPU)...")
        t0 = time.time()
        time_arr, freq_arr, conf_arr, _ = crepe.predict(
            audio, sr, viterbi=True, step_size=10, verbose=1
        )
        elapsed = time.time() - t0
        print(f"  [CREPE] 완료 ({elapsed:.1f}s) → 캐시 저장")
        np.savez(cache_path, time=time_arr, freq=freq_arr, conf=conf_arr)

    voiced = conf_arr >= 0.5
    midi_arr = np.where(
        voiced,
        12 * np.log2(np.maximum(freq_arr, 1e-6) / 440) + 69,
        np.nan
    )
    return time_arr, freq_arr, conf_arr, voiced, midi_arr, elapsed


# ── 3. review_segments ──────────────────────────────────────────

def find_review_segments(time_arr, conf_arr, min_dur_sec=5.0) -> list[dict]:
    """
    confidence < 0.5가 min_dur_sec 이상 연속되는 구간 탐지.
    인접 구간(간격 1초 이내)은 병합.
    """
    unvoiced = (conf_arr < 0.5).astype(int)
    dt = time_arr[1] - time_arr[0]  # ~0.01s

    segs = []
    in_seg = False
    s = 0
    for i, v in enumerate(unvoiced):
        if v and not in_seg:
            s = i
            in_seg = True
        elif not v and in_seg:
            dur = (i - s) * dt
            if dur >= min_dur_sec:
                segs.append({"start": float(time_arr[s]), "end": float(time_arr[i]), "dur": dur})
            in_seg = False
    if in_seg:
        dur = (len(unvoiced) - s) * dt
        if dur >= min_dur_sec:
            segs.append({"start": float(time_arr[s]), "end": float(time_arr[-1]), "dur": dur})

    # 병합: 간격 1초 이내
    merged = []
    for seg in segs:
        if merged and seg["start"] - merged[-1]["end"] <= 1.0:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)

    return [{"start": round(s["start"],2), "end": round(s["end"],2),
             "reason": "low_confidence_drift"} for s in merged]


# ── 4. cross-correlation 정렬 ────────────────────────────────────

def compute_offset(ref_path: Path, target_path: Path, sr=16000) -> float:
    """
    ref (no_vocals.wav) vs target (MR.mp3) 시간 오프셋.
    양수: target이 ref보다 늦게 시작.
    처음 30초만 비교.
    """
    ref,    _ = librosa.load(str(ref_path),    sr=sr, mono=True)
    target, _ = librosa.load(str(target_path), sr=sr, mono=True)
    ref    = ref   [:30*sr]
    target = target[:30*sr]
    # 짧은 쪽 zero-pad
    n = max(len(ref), len(target))
    ref    = np.pad(ref,    (0, n - len(ref)))
    target = np.pad(target, (0, n - len(target)))
    correlation = np.correlate(target, ref, mode="full")
    lag = np.argmax(correlation) - len(ref) + 1
    return round(float(lag / sr), 3)


# ── 5. JSON 저장 ────────────────────────────────────────────────

def save_pitch_guide(sid, time_arr, freq_arr, conf_arr, voiced, midi_arr,
                     offset_sec, alignment_status, review_segs, song_duration):
    points = []
    for t, f, c, v, m in zip(time_arr, freq_arr, conf_arr, voiced, midi_arr):
        points.append({
            "time":        round(float(t), 3),
            "midi":        round(float(m), 3) if v else None,
            "freq_hz":     round(float(f), 2) if v else None,
            "voiced":      bool(v),
            "confidence":  round(float(c), 3),
        })
    data = {
        "song_id":          sid,
        "duration_sec":     round(float(song_duration), 2),
        "frame_hz":         100,
        "alignment_status": alignment_status,
        "lrc_offset_sec":   offset_sec,
        "review_segments":  review_segs,
        "points":           points,
    }
    out = PITCH_DIR / f"{sid}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = out.stat().st_size / 1_048_576
    print(f"  [JSON] 저장: {out.name}  ({size_mb:.2f}MB, {len(points)} frames)")
    return out, size_mb


# ── 6. 시각화 ───────────────────────────────────────────────────

def visualize(sid, time_arr, midi_arr, conf_arr, voiced, review_segs,
              offset_sec, lrc_lines, song_duration, artist, title):

    fig, axes = plt.subplots(2, 1, figsize=(18, 10), sharex=False)
    fig.suptitle(f"{sid} {artist} - {title}  |  offset={offset_sec:+.3f}s", fontsize=13)

    def draw_panel(ax, lrc_times, panel_title):
        # review_segments 배경
        for seg in review_segs:
            ax.axvspan(seg["start"], seg["end"], alpha=0.2, color="orange",
                       label="_nolegend_")
        # 음정 곡선 (voiced)
        t_v = time_arr[voiced]
        m_v = midi_arr[voiced]
        ax.scatter(t_v, m_v, c=conf_arr[voiced], cmap="Blues",
                   vmin=0.5, vmax=1.0, s=2, alpha=0.8)
        # LRC 세로선
        for lrc_t in lrc_times:
            if 0 <= lrc_t <= song_duration:
                ax.axvline(lrc_t, color="green", alpha=0.35, linewidth=0.7)
        # 축 설정
        ax.set_ylabel("MIDI pitch")
        ax.set_xlabel("Time (s)")
        ax.set_xlim(0, song_duration)
        voiced_midi = midi_arr[voiced]
        if len(voiced_midi):
            lo = max(np.nanmin(voiced_midi) - 3, 36)
            hi = min(np.nanmax(voiced_midi) + 3, 96)
            ax.set_ylim(lo, hi)
        ax.yaxis.set_minor_locator(MultipleLocator(1))
        ax.grid(axis="y", which="major", alpha=0.3)
        ax.set_title(panel_title, fontsize=10)

        # MIDI → 음이름 y-tick
        yticks = range(int(ax.get_ylim()[0]), int(ax.get_ylim()[1])+1, 2)
        note_names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        ax.set_yticks(list(yticks))
        ax.set_yticklabels([f"{note_names[m%12]}{m//12-1}" for m in yticks], fontsize=7)

        # 범례
        patches = [
            mpatches.Patch(color="orange", alpha=0.4, label="review segment"),
            mpatches.Patch(color="green",  alpha=0.5, label="LRC line"),
        ]
        if review_segs:
            ax.legend(handles=patches, loc="upper right", fontsize=8)

    lrc_orig  = [l["time_start"] for l in lrc_lines] if lrc_lines else []
    lrc_corr  = [t - offset_sec  for t in lrc_orig]

    draw_panel(axes[0], lrc_orig, f"Before offset correction (LRC 원본)")
    draw_panel(axes[1], lrc_corr, f"After offset correction (LRC − {offset_sec:+.3f}s)")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = VIZ_DIR / f"{sid}_visualization.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  [VIZ] 저장: {out}")
    return out


# ── 7. 메인 처리 ────────────────────────────────────────────────

def process_song(sid: str):
    artist, title = SONGS[sid]
    print(f"\n{'='*60}")
    print(f"[{sid}] {artist} - {title}")
    print(f"{'='*60}")

    # songs.json에서 duration 읽기
    with open(META_PATH, encoding="utf-8") as f:
        meta = {s["id"]: s for s in json.load(f)}
    song_meta = meta[sid]
    song_duration = song_meta.get("master_duration_sec") or 240.0

    # 1. Demucs
    result = run_demucs(sid)
    if len(result) == 2:
        vocals_p, no_vocals_p = result
        demucs_model, demucs_time = "htdemucs(cached)", 0
    else:
        vocals_p, no_vocals_p, demucs_model, demucs_time = result

    # 2. CREPE
    time_arr, freq_arr, conf_arr, voiced, midi_arr, crepe_time = run_crepe(vocals_p, stems_dir(sid))
    voiced_ratio = voiced.sum() / len(voiced)
    conf_mean    = float(conf_arr[voiced].mean()) if voiced.any() else 0.0
    print(f"  voiced 비율: {voiced_ratio:.1%}  conf 평균(voiced): {conf_mean:.3f}")

    # 3. review_segments
    review_segs = find_review_segments(time_arr, conf_arr)
    if review_segs:
        print(f"  review_segments: {len(review_segs)}개")
        for seg in review_segs:
            print(f"    {seg['start']:.1f}s ~ {seg['end']:.1f}s ({seg['end']-seg['start']:.1f}s)")
    else:
        print(f"  review_segments: 없음")

    # 4. cross-correlation
    offset_sec = compute_offset(no_vocals_p, mr_path(sid))
    alignment_status = "auto" if abs(offset_sec) <= 5.0 else "needs_review"
    print(f"  offset_sec: {offset_sec:+.3f}s  → {alignment_status}")
    if alignment_status == "needs_review":
        print("  ⚠ offset > 5s: needs_review. 수동 확인 필요.")

    # 5. LRC 읽기
    lrc_path = LRC_PARSED / f"{sid}.json"
    lrc_lines = []
    if lrc_path.exists():
        with open(lrc_path, encoding="utf-8") as f:
            lrc_lines = json.load(f)
        # offset 적용 (in-place copy)
        lrc_corrected = [
            {**l, "time_start": round(l["time_start"] - offset_sec, 3),
                  "time_end":   round(l["time_end"] - offset_sec, 3) if l["time_end"] else None}
            for l in lrc_lines
        ]
        lrc_save = LRC_PARSED / f"{sid}_aligned.json"
        with open(lrc_save, "w", encoding="utf-8") as f:
            json.dump(lrc_corrected, f, ensure_ascii=False, indent=2)
        print(f"  [LRC] offset 적용본: {lrc_save.name}")
    else:
        lrc_corrected = []
        print(f"  [LRC] 없음 (MANUAL)")

    # 6. JSON 저장
    out_json, size_mb = save_pitch_guide(
        sid, time_arr, freq_arr, conf_arr, voiced, midi_arr,
        offset_sec, alignment_status, review_segs, song_duration
    )

    # 7. 시각화
    out_png = visualize(
        sid, time_arr, midi_arr, conf_arr, voiced,
        review_segs, offset_sec, lrc_lines, song_duration, artist, title
    )

    # 8. songs.json 업데이트
    song_meta["lrc_offset_sec"]   = offset_sec
    song_meta["alignment_status"] = alignment_status
    song_meta["has_pitch_guide"]  = True
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(list(meta.values()), f, ensure_ascii=False, indent=2)

    # 보고
    print(f"\n─── {sid} 완료 ───")
    print(f"  Demucs:  {demucs_model}, {demucs_time:.0f}s")
    print(f"  CREPE:   {crepe_time:.0f}s  voiced={voiced_ratio:.1%}  conf={conf_mean:.3f}")
    print(f"  Offset:  {offset_sec:+.3f}s ({alignment_status})")
    print(f"  JSON:    {size_mb:.2f}MB  {len(time_arr)} frames")
    print(f"  Review:  {len(review_segs)}개")
    print(f"  PNG:     {out_png}")

    return {
        "song_id":               sid,
        "demucs_model":          demucs_model,
        "demucs_sec":            round(demucs_time, 1),
        "crepe_sec":             round(crepe_time, 1),
        "voiced_ratio":          round(float(voiced_ratio), 4),
        "confidence_avg":        round(conf_mean, 4),
        "offset_sec":            offset_sec,
        "alignment_status":      alignment_status,
        "review_segments_count": len(review_segs),
        "pitch_guide_size_mb":   round(size_mb, 3),
        "frames":                len(time_arr),
        "has_lrc":               bool(lrc_lines),
        "png":                   str(out_png),
    }


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--song", metavar="ID")
    g.add_argument("--all",  action="store_true")
    args = parser.parse_args()

    ids = (
        [args.song.zfill(3)] if args.song
        else [s for s in SONGS if s not in {"001","007","011"}]   # LRC 없는 곡도 pitch는 추출
    )
    # --all이면 001, 007, 011도 포함 (LRC 없어도 음정 추출은 가능)
    if args.all:
        ids = list(SONGS.keys())

    for sid in ids:
        process_song(sid)


if __name__ == "__main__":
    main()
