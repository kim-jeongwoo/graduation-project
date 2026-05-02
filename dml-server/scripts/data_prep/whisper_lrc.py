#!/usr/bin/env python3
"""
whisper_lrc.py — Whisper ASR로 LRC 미확보 3곡 자동 생성

대상: 001 한로로, 007 지아, 011 양다일
입력: data/songs/stems/{id}/vocals.wav  (Demucs 결과, master 기준 시간)
출력:
  data/songs/lrc/raw/{id}_whisper.lrc
  data/songs/lrc/parsed/{id}.json        (master 기준)
  data/songs/lrc/parsed/{id}_aligned.json (lrc_offset_sec 적용)
  data/songs/lrc/parsed/{id}_mr.json     (MR 기준, t_mr 변환)

실행:
  conda activate EGGDML
  cd ~/projects/egg_prediction
  python dml-server/scripts/data_prep/whisper_lrc.py [--songs 001,007,011] [--model large-v3]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import librosa
import whisper

BASE = Path(__file__).resolve().parents[3]
SONGS_JSON = BASE / "data" / "songs" / "meta" / "songs.json"
STEMS_DIR  = BASE / "data" / "songs" / "stems"
LRC_DIR    = BASE / "data" / "songs" / "lrc"
MR_DIR     = BASE / "data" / "songs" / "mr"  # MR 음원 경로 (cross-corr용)

SONGS_WITHOUT_LRC = ["001", "007", "011"]
CONFIDENCE_WARN   = 0.5   # 이 미만 → manual_review 표시
DEFAULT_MAX_CORRECTION_S = 0.5  # cross-corr 보정 기본 클램프 (±s)
SNR_WARN          = 1.5   # 이 미만 → alignment_status에 _low_snr 접미사

PITCH_GUIDE_DIR = BASE / "data" / "songs" / "pitch_guide"

SR = 16000


def load_songs_meta() -> dict:
    with open(SONGS_JSON, encoding="utf-8") as f:
        songs = json.load(f)
    return {s["id"]: s for s in songs}


# ── 타임스탬프 보정: RMS vs Whisper activity cross-correlation ──────
def compute_timing_correction(audio: np.ndarray, segments: list,
                               max_correction_s: float,
                               verbose: bool = False) -> tuple[float, float, float]:
    """
    vocals.wav의 RMS 에너지 포락선과 Whisper 활성 구간을 cross-correlation하여
    Whisper 타임스탬프의 전역 오프셋(초)을 추정한다.

    반환: (raw_lag_s, clamped_correction_s, snr)
      raw_lag_s: 클램프 전 실제 추정값
      clamped:   ±max_correction_s 클램프 후 적용값
      snr:       peak / zero-lag 비율 (신뢰도 지표)
    positive → Whisper가 앞섬(timestamps += correction → 뒤로 이동)
    """
    hop = int(SR * 0.01)  # 10ms 단위
    n_frames = len(audio) // hop

    # RMS 에너지 포락선 (vocal 활성 구간의 대리 신호)
    rms = librosa.feature.rms(y=audio, frame_length=hop * 4, hop_length=hop)[0]
    rms = rms[:n_frames]
    rms = rms / (rms.max() + 1e-8)

    # Whisper 활성 신호 (구간 안 = 1, 밖 = 0)
    activity = np.zeros(n_frames, dtype=np.float32)
    for seg in segments:
        s = int(seg["start"] * SR / hop)
        e = int(seg["end"]   * SR / hop)
        s = max(0, min(s, n_frames))
        e = max(0, min(e, n_frames))
        if e > s:
            activity[s:e] = 1.0

    if activity.sum() == 0 or rms.sum() == 0:
        return 0.0, 0.0, 0.0

    # ±max_correction_s 범위 전체를 탐색
    max_lag = int(max_correction_s * SR / hop)
    min_len = min(len(rms), len(activity))
    rms_c = rms[:min_len] - rms[:min_len].mean()
    act_c = activity[:min_len] - activity[:min_len].mean()

    corr = np.correlate(rms_c, act_c, mode="full")
    center = len(corr) // 2

    # 클램프 전: 전체 범위 피크
    search_corr = corr[center - max_lag: center + max_lag + 1]
    lag_idx = int(np.argmax(search_corr)) - max_lag  # frames
    raw_lag_s = lag_idx * hop / SR

    peak_val = float(search_corr[lag_idx + max_lag])
    zero_val = float(corr[center])
    snr      = peak_val / (abs(zero_val) + 1e-8)

    if verbose:
        print(f"    corr peak={peak_val:.4f} @ lag={raw_lag_s:+.3f}s  "
              f"zero={zero_val:.4f}  SNR={snr:.2f}")

    clamped = float(np.clip(raw_lag_s, -max_correction_s, max_correction_s))
    return raw_lag_s, clamped, snr


# ── LRC 포맷 ──────────────────────────────────────────────────────
def sec_to_lrc_time(sec: float) -> str:
    sec = max(0.0, sec)
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:05.2f}"


def segments_to_lrc(segments: list, correction: float) -> str:
    lines = ["[00:00.00]"]
    for seg in segments:
        t = max(0.0, seg["start"] + correction)
        text = seg["text"].strip()
        if not text:
            continue
        lines.append(f"[{sec_to_lrc_time(t)}]{text}")
    return "\n".join(lines)


def segments_to_parsed(segments: list, correction: float,
                       confidence_warn: float) -> list:
    result = []
    for seg in segments:
        t_start = max(0.0, seg["start"] + correction)
        t_end   = max(t_start, seg["end"] + correction)
        text    = seg["text"].strip()
        if not text:
            continue
        avg_conf = float(np.mean([w.get("probability", 1.0)
                                  for w in seg.get("words", [{"probability": 1.0}])]))
        entry = {
            "time_start": round(t_start, 3),
            "time_end":   round(t_end,   3),
            "text":       text,
        }
        if avg_conf < confidence_warn:
            entry["manual_review"] = True
            entry["confidence"]    = round(avg_conf, 3)
        result.append(entry)
    return result


# ── 메타 갱신 ──────────────────────────────────────────────────────
def update_meta(sid: str, alignment_status: str,
                whisper_correction_s: float, whisper_snr: float) -> None:
    """songs.json + pitch_guide/{sid}.json 에 Whisper 보정 결과 기록."""
    # songs.json
    with open(SONGS_JSON, encoding="utf-8") as f:
        songs = json.load(f)
    for s in songs:
        if s["id"] == sid:
            s["alignment_status"]   = alignment_status
            s["has_lrc"]            = True
            s["whisper_correction_s"] = round(whisper_correction_s, 3)
            s["whisper_snr"]        = round(whisper_snr, 3)
            break
    with open(SONGS_JSON, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)

    # pitch_guide/{sid}.json (있을 때만)
    pg_path = PITCH_GUIDE_DIR / f"{sid}.json"
    if pg_path.exists():
        with open(pg_path, encoding="utf-8") as f:
            pg = json.load(f)
        pg["alignment_status"] = alignment_status
        pg["whisper_snr"]      = round(whisper_snr, 3)
        with open(pg_path, "w", encoding="utf-8") as f:
            json.dump(pg, f, ensure_ascii=False, indent=2)


# ── 처리 ──────────────────────────────────────────────────────────
def process_song(song: dict, model: whisper.Whisper,
                 max_correction_s: float = DEFAULT_MAX_CORRECTION_S,
                 verbose: bool = False) -> dict:
    sid = song["id"]
    lrc_offset = song["lrc_offset_sec"]
    mr_dur     = song["mr_duration_sec"]

    vocals_path = STEMS_DIR / sid / "vocals.wav"
    if not vocals_path.exists():
        return {"id": sid, "status": "error", "msg": "vocals.wav 없음"}

    print(f"\n[{sid}] Whisper 추론 중... ({vocals_path})")
    audio, _ = librosa.load(str(vocals_path), sr=SR, mono=True)

    result = model.transcribe(
        str(vocals_path),
        language="ko",
        word_timestamps=True,
        verbose=False,
        task="transcribe",
        condition_on_previous_text=False,
    )
    segments = result["segments"]
    if not segments:
        return {"id": sid, "status": "error", "msg": "전사 결과 없음"}

    # 타임스탬프 보정 (cross-correlation)
    raw_lag, correction, snr = compute_timing_correction(
        audio, segments, max_correction_s, verbose=verbose)
    clamped_flag = " [CLAMPED]" if abs(raw_lag) > max_correction_s - 0.01 else ""
    snr_flag = " ⚠LOW_SNR" if snr < SNR_WARN else ""
    print(f"  cross-corr raw={raw_lag:+.3f}s → clamped={correction:+.3f}s{clamped_flag}  SNR={snr:.2f}{snr_flag}")

    alignment_status = "whisper_auto" + ("_low_snr" if snr < SNR_WARN else "")

    # 라인별 통계
    low_conf_lines = sum(
        1 for seg in segments
        if float(np.mean([w.get("probability", 1.0)
                          for w in seg.get("words", [{"probability": 1.0}])])) < CONFIDENCE_WARN
    )
    avg_conf = float(np.mean([
        float(np.mean([w.get("probability", 1.0) for w in seg.get("words", [{"probability": 1.0}])]))
        for seg in segments
    ]))

    # 출력 파일 생성
    (LRC_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (LRC_DIR / "parsed").mkdir(parents=True, exist_ok=True)

    # 1. LRC raw (master 기준 + 보정)
    lrc_text = segments_to_lrc(segments, correction)
    lrc_path = LRC_DIR / "raw" / f"{sid}_whisper.lrc"
    lrc_path.write_text(lrc_text, encoding="utf-8")

    # 2. parsed/{id}.json (master 기준 + 보정)
    parsed = segments_to_parsed(segments, correction, CONFIDENCE_WARN)
    parsed_path = LRC_DIR / "parsed" / f"{sid}.json"
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    # 3. parsed/{id}_aligned.json (MR 기준)
    aligned = []
    for line in parsed:
        ts = line["time_start"] - lrc_offset
        te = line["time_end"]   - lrc_offset
        if te <= 0 or ts >= mr_dur:
            continue
        aligned.append({**line, "time_start": round(ts, 3), "time_end": round(te, 3)})
    aligned_path = LRC_DIR / "parsed" / f"{sid}_aligned.json"
    with open(aligned_path, "w", encoding="utf-8") as f:
        json.dump(aligned, f, ensure_ascii=False, indent=2)

    # 4. parsed/{id}_mr.json (기존 convert_to_mr_timeline 형식과 동일)
    mr_lines = []
    for line in parsed:
        ts_mr = round(line["time_start"] - lrc_offset, 6)
        te_mr = round(line["time_end"]   - lrc_offset, 6)
        if te_mr <= 0 or ts_mr >= mr_dur:
            continue
        mr_lines.append({**line, "time_start_mr": ts_mr, "time_end_mr": te_mr})
    mr_path = LRC_DIR / "parsed" / f"{sid}_mr.json"
    with open(mr_path, "w", encoding="utf-8") as f:
        json.dump(mr_lines, f, ensure_ascii=False, indent=2)

    # songs.json + pitch_guide 메타 갱신
    update_meta(sid, alignment_status, correction, snr)

    return {
        "id": sid,
        "status": "ok",
        "n_lines": len(parsed),
        "n_mr_lines": len(mr_lines),
        "avg_confidence": round(avg_conf, 3),
        "low_conf_lines": low_conf_lines,
        "raw_lag_s": round(raw_lag, 3),
        "correction_s": round(correction, 3),
        "clamped": abs(raw_lag) > max_correction_s - 0.01,
        "snr": round(snr, 3),
        "alignment_status": alignment_status,
        "lrc_offset_s": lrc_offset,
    }


def print_report(results: list) -> None:
    print("\n" + "─" * 60)
    print(" Whisper ASR 결과")
    print("─" * 60)
    for r in results:
        if r["status"] == "error":
            print(f"  [{r['id']}] ERROR: {r['msg']}")
            continue
        flag = " ⚠ manual_review 필요" if r["low_conf_lines"] > 0 else ""
        clamp_flag = " [CLAMPED]" if r.get("clamped") else ""
        print(f"  [{r['id']}] {r['n_lines']}줄 (MR: {r['n_mr_lines']}줄) "
              f"| avg_conf={r['avg_confidence']:.2f} "
              f"| 저신뢰={r['low_conf_lines']}줄 "
              f"| raw={r['raw_lag_s']:+.3f}s→corr={r['correction_s']:+.3f}s{clamp_flag} "
              f"| SNR={r['snr']:.2f} | {r['alignment_status']}{flag}")
    print("─" * 60)
    print("출력: lrc/raw/{id}_whisper.lrc, lrc/parsed/{id}.json/aligned/mr")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs", default=",".join(SONGS_WITHOUT_LRC),
                    help="처리할 곡 ID (쉼표 구분)")
    ap.add_argument("--model", default="large-v3",
                    help="Whisper 모델 (large-v3 | large-v3-turbo)")
    ap.add_argument("--max-correction", type=float, default=DEFAULT_MAX_CORRECTION_S,
                    help="cross-corr 클램프 범위 (±초, 기본 0.5)")
    ap.add_argument("--verbose", action="store_true",
                    help="cross-corr 진단 출력 활성화")
    args = ap.parse_args()

    target_ids = [s.strip() for s in args.songs.split(",")]
    songs_meta = load_songs_meta()

    target_ids = [sid for sid in target_ids if sid in songs_meta or
                  not print(f"[{sid}] songs.json에 없음. 건너뜀.")]

    print(f"Whisper {args.model} 모델 로드 중... (max_correction=±{args.max_correction}s)")
    model = whisper.load_model(args.model)
    print("로드 완료.")

    results = []
    for sid in target_ids:
        r = process_song(songs_meta[sid], model,
                         max_correction_s=args.max_correction,
                         verbose=args.verbose)
        results.append(r)

    print_report(results)


if __name__ == "__main__":
    main()
