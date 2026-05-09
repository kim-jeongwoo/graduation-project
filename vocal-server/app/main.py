import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import admin, analysis, auth, files, sessions, songs, training

# 모델 import — alembic이 스키마 관리. create_all 사용 금지.
import app.models.models  # noqa: F401

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Vocal Server", version="0.1.0")

# CORS 설정 (개발 단계 – 모든 origin 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외의 traceback을 로그에 출력합니다."""
    logger.error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# 라우터 등록
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(files.router)
app.include_router(analysis.router)
app.include_router(admin.router)
app.include_router(songs.router)
app.include_router(training.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
