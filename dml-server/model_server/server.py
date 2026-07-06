"""
EGG Prediction FastAPI Server
==============================
POST /predict  — WAV 파일을 받아 EGG wav 반환
POST /analyze  — WAV 파일을 받아 종합 발성 분석 JSON 반환 (StreamingResponse, Cloudflare 125s 우회)
GET  /health   — 모델 로드 상태 + GPU 확인
"""
import asyncio
import json
import os
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse

from predictor import EGGPredictor
from analysis_pipeline import AnalysisPipeline, SilentInputError
from services.timeline_analysis import analyze_with_timeline
from services.realtime import realtime_handler
from services.chunk_analysis import prepare_chunk, ChunkTooShortError

# ── 환경변수 로드 ──────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CHECKPOINT_PATH = os.getenv(
    "CHECKPOINT_PATH",
    os.path.expanduser(
        "~/projects/egg_prediction/checkpoints/exp20_progressive/best_model.pt"
    ),
)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRITERIA_PATH = os.path.join(
    _PROJECT_ROOT, "data", "vocal_academy", "evaluation_criteria.json"
)
MAPPINGS_PATH = os.path.join(
    _PROJECT_ROOT, "data", "vocal_academy", "results", "ai_scores.json"
)

OUTPUTS_DIR  = os.path.join(os.path.dirname(__file__), "outputs")
LRC_PARSED_DIR  = os.path.join(_PROJECT_ROOT, "data", "songs", "lrc", "parsed")
PITCH_GUIDE_DIR = os.path.join(_PROJECT_ROOT, "data", "songs", "pitch_guide")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ── FastAPI 앱 ─────────────────────────────────────────────
app = FastAPI(
    title="EGG Prediction & Vocal Analysis Server",
    version="2.0.0",
    description="POST /predict → EGG wav | POST /analyze → JSON analysis",
)

# 서버 시작 시 모델 한 번만 로드
predictor: EGGPredictor | None = None
pipeline: AnalysisPipeline | None = None


@app.on_event("startup")
def _load_model():
    global predictor, pipeline
    predictor = EGGPredictor(CHECKPOINT_PATH)
    pipeline = AnalysisPipeline(CHECKPOINT_PATH, CRITERIA_PATH, MAPPINGS_PATH)


# ── 엔드포인트 ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": predictor is not None,
        "gpu_available": torch.cuda.is_available(),
        "device": str(predictor.device) if predictor else None,
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    run_id: str = Query(default=None, description="추적용 run_id (없으면 자동 생성)"),
):
    if run_id is None:
        run_id = uuid.uuid4().hex[:12]

    try:
        # 업로드 파일을 임시 저장
        suffix = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            shutil.copyfileobj(file.file, tmp)
            tmp.close()

            # 출력 디렉토리
            run_dir = os.path.join(OUTPUTS_DIR, run_id)
            os.makedirs(run_dir, exist_ok=True)
            output_path = os.path.join(run_dir, "egg_estimated.wav")

            # 추론
            result = predictor.predict(tmp.name, output_path)
        finally:
            os.unlink(tmp.name)

        # 상대 경로로 변환
        rel_uri = os.path.relpath(result["egg_signal_uri"], os.path.dirname(__file__))

        return {
            "run_id": run_id,
            "status": "success",
            "egg_signal_uri": rel_uri,
            "duration_ms": result["duration_ms"],
            "processing_time_ms": result["processing_time_ms"],
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
            },
        )


def _load_lrc_segments(song_id: str) -> list | None:
    """LRC 파싱 파일 로드. 없으면 None 반환."""
    lrc_path = Path(LRC_PARSED_DIR) / f"{song_id}_aligned.json"
    if not lrc_path.exists():
        lrc_path = Path(LRC_PARSED_DIR) / f"{song_id}.json"
    if not lrc_path.exists():
        return None
    with open(lrc_path, encoding="utf-8") as f:
        return json.load(f)


def _analyze_sync(audio_bytes: bytes, song_id: Optional[str], run_id: str) -> dict:
    """Blocking /analyze 분석. StreamingResponse handler에서 thread pool 실행.

    예외는 모두 catch → status 필드 명시한 dict 반환 (status 200 통일).
    streaming 시작 후 HTTP status code 변경 불가하므로 body status로 통일."""
    try:
        result = pipeline.analyze(audio_bytes)
    except SilentInputError as e:
        return {
            "run_id": run_id, "status": "no_voice",
            "reason": e.reason, "processing_time_ms": e.elapsed_ms,
            "audio_info": e.audio_info,
            "scores": None, "feedback": None, "reliability": None,
            "registers": None, "register_boundaries": None, "indicators": None,
            "timeline_scores": None, "timeline_metadata": None, "user_f0": None,
        }
    except ValueError as e:
        return {"run_id": run_id, "status": "invalid", "error": str(e)}
    except Exception as e:
        return {"run_id": run_id, "status": "failed", "error": str(e)}

    # 타임라인 분석 (song_id 제공 시)
    timeline_scores   = None
    timeline_metadata = None
    if song_id is not None:
        lrc_segments = _load_lrc_segments(song_id)
        if lrc_segments:
            try:
                timeline_scores, timeline_metadata = analyze_with_timeline(
                    audio_bytes, lrc_segments, pipeline,
                )
            except Exception as e:
                timeline_metadata = {"error": str(e)}

    return {
        "run_id": run_id, "status": "success", **result,
        "timeline_scores":   timeline_scores,
        "timeline_metadata": timeline_metadata,
    }


@app.post("/analyze", summary="WAV → 종합 발성 분석 JSON (StreamingResponse)")
async def analyze(
    file: UploadFile = File(..., description="분석할 WAV 파일"),
    run_id: str = Query(default=None, description="추적용 run_id (없으면 자동 생성)"),
    song_id: Optional[str] = Query(
        default=None,
        description="곡 ID (e.g. '004'). 지정 시 LRC 기반 타임라인 분석 포함.",
    ),
):
    """
    WAV 파일을 받아 9개 항목 발성 분석 결과를 JSON으로 반환.

    응답은 StreamingResponse로 송신 (Cloudflare ~125s edge timeout 우회).
    - TTFB ~0s: 첫 byte (leading whitespace) 즉시 송신
    - 처리 중 5s마다 leading whitespace ping
    - 처리 완료: 최종 JSON body 송신
    - 표준 JSON parser는 leading whitespace 무시 (RFC 7159) → schema 변경 0

    - **audio_info**: 길이, voiced 비율, F0 통계
    - **registers**: 저/중/고 음역대별 지표
    - **indicators**: 전체 voiced 구간 지표
    - **scores**: v1 9 항목 (legacy)
    - **scores_v2 / scores_meta / academic_analysis_scores / score_mapper_version**: v2
    - **feedback**: 점수 + 평가표 기준 텍스트 + 피드백
    - **reliability**: high/medium/unavailable + shown_v2/shown_v2_tiers
    - **timeline_scores / timeline_metadata** *(song_id 지정 시)*

    응답 status 규칙 (streaming 시작 후 HTTP status code 변경 불가):
    - 정상           → 200 + body status='success'
    - 무음/잡음       → 200 + body status='no_voice'
    - 잘못된 음성     → 200 + body status='invalid' + error
    - 처리 중 예외    → 200 + body status='failed' + error
    - file 검증 실패 → 400 (streaming 시작 전 raise)
    - 모듈 미로드   → 503 (streaming 시작 전 raise)
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Analysis pipeline not loaded")

    if run_id is None:
        run_id = uuid.uuid4().hex[:12]

    # Read file into memory — no disk writes
    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read uploaded file: {e}")

    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid WAV")

    async def _stream():
        # 첫 byte 즉시 (Cloudflare TTFB ~0s → 524 우회)
        yield b" "
        task = asyncio.create_task(
            asyncio.to_thread(_analyze_sync, audio_bytes, song_id, run_id),
        )
        while True:
            try:
                result_dict = await asyncio.wait_for(
                    asyncio.shield(task), timeout=5.0,
                )
                yield json.dumps(result_dict, ensure_ascii=False).encode()
                return
            except asyncio.TimeoutError:
                yield b" "
            except Exception as e:
                # fallback: executor에서 못 잡은 예외
                err = {"run_id": run_id, "status": "failed", "error": str(e)}
                yield json.dumps(err, ensure_ascii=False).encode()
                return

    return StreamingResponse(_stream(), media_type="application/json")


# ── Phase 4: 단일 chunk 사후 분석 ──────────────────────────
@app.post("/analyze-chunk", summary="WAV chunk(3~10초) → 호흡/접촉 통합 점수")
async def analyze_chunk(
    file: UploadFile = File(..., description="분석할 chunk WAV (3~10초 권장)"),
    run_id: Optional[str] = Query(default=None),
    start_sec: Optional[float] = Query(default=None, description="원본 wav slice 시작(선택)"),
    end_sec: Optional[float] = Query(default=None, description="원본 wav slice 종료(선택)"),
    song_id: Optional[str] = Query(default=None, description="향후 음정 분석용(현재 미사용)"),
):
    """
    Phase 4 (TrainingScreen 사후 측정) 전용. 호흡식별 + 접촉강도만 반환.

    - duration < 3.0s → 400 chunk_too_short
    - voiced_s < duration × 0.4 → 200 no_voice (Guard A)
    - voiced_ratio > 0.95 + cpp_mean < 0.15 → 200 no_voice (Guard B)
    - 정상 → 200 success + scores(2 항목) + indicators
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Analysis pipeline not loaded")

    if run_id is None:
        run_id = uuid.uuid4().hex[:12]

    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read uploaded file: {e}")
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid WAV")

    # 1) 전처리: slice + duration 검증 + adaptive min_voiced_s
    try:
        wav_bytes, duration, min_voiced_s, confidence = prepare_chunk(
            audio_bytes, start_sec=start_sec, end_sec=end_sec,
        )
    except ChunkTooShortError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error":            "chunk_too_short",
                "reason":           "분석을 위해 최소 3초 이상 녹음이 필요합니다.",
                "duration_sec":     round(e.duration, 2),
                "min_required_sec": e.min_required,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot decode audio: {e}")

    # 2) pipeline 분석
    try:
        result = pipeline.analyze(wav_bytes, min_voiced_s=min_voiced_s)
    except SilentInputError as e:
        return {
            "run_id":              run_id,
            "status":              "no_voice",
            "reason":              e.reason,
            "duration_sec":        round(duration, 2),
            "chunk_duration_s":    round(duration, 3),
            "scores":              None,
            "scores_v2":           None,
            "scores_meta":         None,
            "low_confidence_items": None,
            "score_mapper_version": None,
            "indicators":          None,
            "processing_time_ms":  e.elapsed_ms,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"run_id": run_id, "status": "failed", "error": str(e)},
        )

    # 3) v1 scores (legacy 2항목) + v2 scores_v2 (4항목, F4-3) 산출
    V2_KEYS = ("3_vocal_fold_contact", "4_breathiness",
               "6_soft_palate",        "8_tongue_tension")
    V2_TIERS = {"3_vocal_fold_contact":"high","4_breathiness":"high_star",
                "6_soft_palate":"high_star","8_tongue_tension":"high_star"}

    def _zone(ai):
        if ai is None: return None
        s = round(ai)
        if s <= 1: return "insufficient"
        if s <= 3: return "appropriate"
        return "excessive"

    # legacy v1 scores (호환): 호흡식별 + 접촉강도
    scores_out: dict = {}
    for key in ("3_vocal_fold_contact", "4_breathiness"):
        s = (result.get("scores") or {}).get(key) or {}
        scores_out[key] = {
            "ai_score":      s.get("ai_score"),
            "rounded_score": s.get("rounded_score"),
            "zone":          s.get("zone"),
            "confidence":    confidence if s.get("ai_score") is not None else "unavailable",
        }

    # v2 scores_v2: 4항목 (v1+v2 혼합 — ai_score는 v2, zone은 v1 로직)
    v2_raw  = result.get("scores_v2")  or {}
    v2_meta = result.get("scores_meta") or {}
    scores_v2_out: dict = {}
    for key in V2_KEYS:
        ai = v2_raw.get(key)
        m  = v2_meta.get(key) or {}
        scores_v2_out[key] = {
            "ai_score":      ai,
            "rounded_score": m.get("rounded_score"),
            "zone":          _zone(ai),
            "confidence":    confidence if ai is not None else "unavailable",
            "tier":          m.get("tier") or V2_TIERS[key],
        }
    low_confidence_items = (
        ["4_breathiness", "6_soft_palate", "8_tongue_tension"]
        if duration < 5.0 else []
    )

    ind = result.get("indicators") or {}
    audio_info = result.get("audio_info") or {}
    indicators_out = {
        "voiced_ratio": audio_info.get("voiced_ratio"),
        "cpp_mean":     ind.get("cpp_mean"),
        "cq_p90":       ind.get("cq_peak"),  # _aggregate가 (mean, p90) 반환 → cq_peak == cq_p90
    }

    return {
        "run_id":              run_id,
        "status":              "success",
        "duration_sec":        round(duration, 2),
        "chunk_duration_s":    round(duration, 3),
        "scores":              scores_out,           # legacy v1 (2 항목)
        "scores_v2":           scores_v2_out,        # F4-3: 4 항목 v2 (권장 사용)
        "scores_meta":         v2_meta,
        "low_confidence_items": low_confidence_items,
        "score_mapper_version": result.get("score_mapper_version"),
        "indicators":          indicators_out,
        "processing_time_ms":  result.get("processing_time_ms"),
    }


# ── WebSocket 실시간 분석 ───────────────────────────────────
@app.websocket("/ws/realtime")
async def ws_realtime(
    websocket: WebSocket,
    song_id: Optional[str] = None,
):
    await realtime_handler(websocket, song_id, pipeline, PITCH_GUIDE_DIR)


# ── 직접 실행 ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
