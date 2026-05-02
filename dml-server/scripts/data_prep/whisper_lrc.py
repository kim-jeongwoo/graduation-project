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
MAX_CORRECTION_S  = 0.5   # cross-corr 보정 최대값 (±s)

SR = 16000


def load_songs_meta() -> dict:
    with open(SONGS_JSON, encoding="utf-8") as f:
        songs = json.load(f)
    return {s["id"]: s for s in songs}


# ── 타임스탬프 보정: RMS vs Whisper activity cross-correlation ──────
def compute_timing_correction(audio: np.ndarray, segments: list) -> float:
    """
    vocals.wav의 RMS 에너지 포락선과 Whisper 활성 구간을 cross-correlation하여
    Whisper 타임스탬프의 전역 오프셋(초)을 추정한다.
    반환값: positive → Whisper가 앞섬(timestamps += correction), negative → 뒤섬
    """
    hop = int(SR * 0.01)  # 10ms 단위
    n_frames = len(audio) // hop
    duration = len(audio) / SR

    # RMS 에너지 포락선
    rms = librosa.feature.rms(y=audio, frame_length=hop * 2, hop_length=hop)[0]
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
        return 0.0

    # cross-correlation (검색 범위 ±MAX_CORRECTION_S)
    max_lag = int(MAX_CORRECTION_S * SR / hop)
    min_len = min(len(rms), len(activity))
    rms_c = rms[:min_len] - rms[:min_len].mean()
    act_c = activity[:min_len] - activity[:min_len].mean()

    corr = np.correlate(rms_c, act_c, mode="full")
    center = len(corr) // 2
    search_corr = corr[center - max_lag: center + max_lag + 1]
    lag_idx = np.argmax(search_corr) - max_lag  # frames
    correction = lag_idx * hop / SR  # 초

    return float(np.clip(correction, -MAX_CORRECTION_S, MAX_CORRECTION_S))


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


# ── 처리 ──────────────────────────────────────────────────────────
def process_song(song: dict, model: whisper.Whisper) -> dict:
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
    correction = compute_timing_correction(audio, segments)
    print(f"  cross-corr 보정: {correction:+.3f}s")

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

    return {
        "id": sid,
        "status": "ok",
        "n_lines": len(parsed),
        "n_mr_lines": len(mr_lines),
        "avg_confidence": round(avg_conf, 3),
        "low_conf_lines": low_conf_lines,
        "correction_s": round(correction, 3),
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
        print(f"  [{r['id']}] {r['n_lines']}줄 (MR: {r['n_mr_lines']}줄) "
              f"| avg_conf={r['avg_confidence']:.2f} "
              f"| 저신뢰={r['low_conf_lines']}줄 "
              f"| corr보정={r['correction_s']:+.3f}s{flag}")
    print("─" * 60)
    print("출력: lrc/raw/{id}_whisper.lrc, lrc/parsed/{id}.json/aligned/mr")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs", default=",".join(SONGS_WITHOUT_LRC),
                    help="처리할 곡 ID (쉼표 구분)")
    ap.add_argument("--model", default="large-v3",
                    help="Whisper 모델 (large-v3 | large-v3-turbo)")
    args = ap.parse_args()

    target_ids = [s.strip() for s in args.songs.split(",")]
    songs_meta = load_songs_meta()

    for sid in target_ids:
        if sid not in songs_meta:
            print(f"[{sid}] songs.json에 없음. 건너뜀.")
            target_ids.remove(sid)

    print(f"Whisper {args.model} 모델 로드 중...")
    model = whisper.load_model(args.model)
    print("로드 완료.")

    results = []
    for sid in target_ids:
        r = process_song(songs_meta[sid], model)
        results.append(r)

    print_report(results)


if __name__ == "__main__":
    main()
