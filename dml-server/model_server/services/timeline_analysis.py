"""
timeline_analysis.py — LRC 라인 단위 시간축 분석 (F4: 4항목 확장)
==================================================
LRC 세그먼트 경계로 오디오를 청킹해 4 항목 chunk 단위 점수 산출.
  - 3_vocal_fold_contact   (tier=high)
  - 4_breathiness          (tier=high_star)
  - 6_soft_palate          (tier=high_star)
  - 8_tongue_tension       (tier=high_star)

chunk loop에서 pipeline.v2.score_from_audio()를 직접 호출 (EGG+v1 산출 생략).
chunk_duration < LOW_CONF_THRESHOLD_S 시 low_confidence_items에
high_star 3항목 표시 (접촉강도 제외 — chunk 길이 영향 작음).

주요 함수:
  build_chunks(lrc_segments)  → List[chunk_dict]
  analyze_with_timeline(audio_bytes, lrc_segments, pipeline)
                              → (timeline_scores, timeline_metadata)
"""
from __future__ import annotations

import io
import time
from typing import Any, Optional

import numpy as np
import soundfile as sf
import librosa

# 타임라인 활성 4 항목 (v2 mapper 표시 항목)
TIMELINE_ITEMS = [
    "3_vocal_fold_contact",
    "4_breathiness",
    "6_soft_palate",
    "8_tongue_tension",
]
TIMELINE_TIERS = {
    "3_vocal_fold_contact": "high",
    "4_breathiness":        "high_star",
    "6_soft_palate":        "high_star",
    "8_tongue_tension":     "high_star",
}

# chunk < LOW_CONF_THRESHOLD_S 시 표시될 low-confidence 항목
# (접촉강도는 cq_p90 mid_band 기반으로 짧은 chunk에서도 비교적 안정)
LOW_CONF_THRESHOLD_S       = 5.0
LOW_CONF_ITEMS_WHEN_SHORT  = ["4_breathiness", "6_soft_palate", "8_tongue_tension"]

# v2 점수 키 한국어 → 영문 매핑
KOR_TO_KEY = {
    "비강사용":  "1_nasal_oral_ratio",
    "흉성두성":  "2_chest_head_voice",
    "접촉강도":  "3_vocal_fold_contact",
    "호흡식별":  "4_breathiness",
    "전방공명":  "5_forward_resonance",
    "연구개위치": "6_soft_palate",
    "공명개방":  "7_larynx_tongue_root",
    "혀경직도":  "8_tongue_tension",
    "상압하압":  "9_pressure_balance",
}

# v2 mapper deferred (chunk 단위 산출 X) — 메타 표시용
DEFERRED_ITEMS   = ["2_chest_head_voice", "7_larynx_tongue_root", "9_pressure_balance"]
DEFERRED_REASON  = "v2_mapper_deferred_tier_no_chunk_aggregation"
DEFERRED_REVISIT = "2026-05-24_post_b_group_data"

# chunk 단위 최소 voiced 시간 (silent guard용, 호환 유지)
CHUNK_MIN_VOICED_S = 2.0

TARGET_SR   = 16000
MIN_DUR     = 2.0    # 이 미만 세그먼트는 다음과 병합
MAX_DUR     = 15.0   # 이 초과 세그먼트는 균등 분할


# ── 청크 빌더 ────────────────────────────────────────────────────────

def build_chunks(
    lrc_segments: list[dict],
    min_dur: float = MIN_DUR,
    max_dur: float = MAX_DUR,
) -> list[dict]:
    """
    LRC 세그먼트 → 분석 단위 청크 리스트.
    - <min_dur 세그먼트: 다음 세그먼트와 병합
    - >max_dur 청크: 균등 분할

    반환 형식:
      [{"start_sec": float, "end_sec": float,
        "lrc_indices": [int,...], "lrc_text": str}, ...]
    """
    if not lrc_segments:
        return []

    # ── 1단계: 짧은 세그먼트 병합 ──────────────────────────────────
    buf_start: Optional[float] = None
    buf_end:   Optional[float] = None
    buf_idx:   list[int] = []
    buf_text:  list[str] = []
    chunks: list[dict] = []

    for i, seg in enumerate(lrc_segments):
        s    = float(seg["time_start"])
        e    = float(seg["time_end"]) if seg.get("time_end") else s + 5.0
        text = seg.get("text", "")

        if buf_start is None:
            buf_start, buf_end, buf_idx, buf_text = s, e, [i], [text]
        elif (buf_end - buf_start) < min_dur:
            # 이전 버퍼가 너무 짧음 → 현재 세그먼트와 병합
            buf_end = e
            buf_idx.append(i)
            buf_text.append(text)
        else:
            chunks.append({
                "start_sec":   buf_start,
                "end_sec":     buf_end,
                "lrc_indices": buf_idx,
                "lrc_text":    " / ".join(buf_text),
            })
            buf_start, buf_end, buf_idx, buf_text = s, e, [i], [text]

    if buf_start is not None:
        chunks.append({
            "start_sec":   buf_start,
            "end_sec":     buf_end,
            "lrc_indices": buf_idx,
            "lrc_text":    " / ".join(buf_text),
        })

    # ── 2단계: 긴 청크 균등 분할 ───────────────────────────────────
    final: list[dict] = []
    for chunk in chunks:
        dur = chunk["end_sec"] - chunk["start_sec"]
        if dur > max_dur:
            n = int(np.ceil(dur / max_dur))
            seg_dur = dur / n
            for j in range(n):
                final.append({
                    "start_sec":   round(chunk["start_sec"] + j * seg_dur, 3),
                    "end_sec":     round(chunk["start_sec"] + (j + 1) * seg_dur, 3),
                    "lrc_indices": chunk["lrc_indices"],
                    "lrc_text":    chunk["lrc_text"],
                })
        else:
            chunk["start_sec"] = round(chunk["start_sec"], 3)
            chunk["end_sec"]   = round(chunk["end_sec"],   3)
            final.append(chunk)

    return final


# ── 핵심 분석 함수 ──────────────────────────────────────────────────

def analyze_with_timeline(
    audio_bytes: bytes,
    lrc_segments: list[dict],
    pipeline: Any,
) -> tuple[list[dict], dict]:
    """
    오디오 bytes + LRC 세그먼트 → 타임라인 분석 (4 항목 chunk score).

    chunk 별로 pipeline.v2.score_from_audio(chunk_audio, 16000) 직접 호출.
    EGG inference / v1 score 산출 생략 (대응 1' 최적화).

    Returns:
        timeline_scores   : [
            {start_sec, end_sec, lrc_text, chunk_duration_s,
             scores: {key: {ai_score, rounded_score, tier} | None},
             low_confidence_items: [...]},
            ...
        ]
        timeline_metadata : {n_chunks, n_ok, n_skipped, processing_time_ms,
                             shown_indicators, shown_indicators_meta, ...}
    """
    t_wall = time.perf_counter()

    # 전체 오디오 한 번만 로드 (16kHz mono float32)
    audio, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR
    audio = audio.astype(np.float32, copy=False)

    chunks = build_chunks(lrc_segments)
    timeline_scores: list[dict] = []
    n_ok      = 0
    n_skipped = 0
    chunk_costs_s: list[float] = []

    v2_available = getattr(pipeline, "v2", None) is not None

    for chunk in chunks:
        s_smp = max(0,         int(chunk["start_sec"] * sr))
        e_smp = min(len(audio), int(chunk["end_sec"]  * sr))
        chunk_audio = audio[s_smp:e_smp]
        chunk_dur   = (e_smp - s_smp) / sr

        scores_out: dict = {k: None for k in TIMELINE_ITEMS}
        low_conf:   list[str] = []

        if not v2_available or chunk_dur < CHUNK_MIN_VOICED_S:
            # v2 미로드 또는 chunk 너무 짧음
            n_skipped += 1
            low_conf = list(TIMELINE_ITEMS)
        else:
            t_chunk = time.perf_counter()
            try:
                v2_raw = pipeline.v2.score_from_audio(chunk_audio, sr)
                for kor, item in v2_raw.items():
                    key = KOR_TO_KEY.get(kor, kor)
                    if key not in TIMELINE_ITEMS:
                        continue
                    ai = item.get("ai_score")
                    scores_out[key] = {
                        "ai_score":      ai,
                        "rounded_score": item.get("rounded_score"),
                        "tier":          TIMELINE_TIERS[key],
                    }
                # 누락 항목 None 유지
                missing = [k for k in TIMELINE_ITEMS if scores_out.get(k) is None]
                if missing:
                    low_conf.extend(missing)
                n_ok += 1
            except Exception:
                scores_out = {k: None for k in TIMELINE_ITEMS}
                low_conf   = list(TIMELINE_ITEMS)
                n_skipped += 1
            chunk_costs_s.append(time.perf_counter() - t_chunk)

        # 짧은 chunk → high_star 3항목을 low_confidence_items에 표시
        if chunk_dur < LOW_CONF_THRESHOLD_S:
            for k in LOW_CONF_ITEMS_WHEN_SHORT:
                if k not in low_conf:
                    low_conf.append(k)

        timeline_scores.append({
            "start_sec":            chunk["start_sec"],
            "end_sec":              chunk["end_sec"],
            "lrc_text":             chunk["lrc_text"],
            "chunk_duration_s":     round(chunk_dur, 3),
            "scores":               scores_out,
            "low_confidence_items": low_conf,
        })

    elapsed_ms = (time.perf_counter() - t_wall) * 1000

    shown_meta = {
        k: {
            "tier":         TIMELINE_TIERS[k],
            "display_mark": "asterisk" if TIMELINE_TIERS[k] == "high_star" else None,
        }
        for k in TIMELINE_ITEMS
    }

    timeline_metadata = {
        "n_chunks":                   len(chunks),
        "n_ok":                       n_ok,
        "n_skipped":                  n_skipped,
        "processing_time_ms":         round(elapsed_ms, 1),
        "items":                      TIMELINE_ITEMS,           # backward compat
        "shown_indicators":           TIMELINE_ITEMS,
        "shown_indicators_meta":      shown_meta,
        "shown_indicators_reason":    "v2_mapper_4items",
        "chunk_score_items":          TIMELINE_ITEMS,
        "deferred_indicators":        DEFERRED_ITEMS,
        "deferred_reason":            DEFERRED_REASON,
        "deferred_revisit_after":     DEFERRED_REVISIT,
        "chunk_min_voiced_s":         CHUNK_MIN_VOICED_S,
        "low_confidence_threshold_s": LOW_CONF_THRESHOLD_S,
        "max_chunk_sec":              MAX_DUR,
        "score_mapper_version":       "v2",
        "v2_chunk_cost_avg_ms": (
            round(float(np.mean(chunk_costs_s)) * 1000, 1) if chunk_costs_s else None
        ),
    }

    return timeline_scores, timeline_metadata
