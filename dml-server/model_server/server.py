"""
EGG Prediction FastAPI Server
==============================
POST /predict  — WAV 파일을 받아 EGG wav 반환
POST /analyze  — WAV 파일을 받아 종합 발성 분석 JSON 반환
GET  /health   — 모델 로드 상태 + GPU 확인
"""
import os
import uuid
import shutil
import tempfile

import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from predictor import EGGPredictor
from analysis_pipeline import AnalysisPipeline

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

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
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


@app.post("/analyze", summary="WAV → 종합 발성 분석 JSON")
async def analyze(
    file: UploadFile = File(..., description="분석할 WAV 파일"),
    run_id: str = Query(default=None, description="추적용 run_id (없으면 자동 생성)"),
):
    """
    WAV 파일을 받아 9개 항목 발성 분석 결과를 JSON으로 반환.

    - **audio_info**: 길이, voiced 비율, F0 통계
    - **registers**: 저/중/고 음역대별 지표
    - **indicators**: 전체 voiced 구간 지표
    - **scores**: 항목별 AI 점수 (0~5)
    - **feedback**: 점수 + 평가표 기준 텍스트 + 피드백
    - **reliability**: high/medium/unavailable 신뢰도 분류

    오류 코드:
    - 400: 잘못된 파일 포맷
    - 422: 음성 너무 짧음 (voiced < 5초)
    - 503: 분석 모듈 미로드
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

    try:
        result = pipeline.analyze(audio_bytes)
    except ValueError as e:
        # voiced too short
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"run_id": run_id, "status": "failed", "error": str(e)},
        )

    return {
        "run_id": run_id,
        "status": "success",
        **result,
    }


# ── 직접 실행 ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
