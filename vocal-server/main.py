"""루트 진입점 – uvicorn main:app 또는 python main.py 로 실행 가능."""

from app.main import app  # noqa: F401  ← uvicorn main:app 에서 이 app 을 찾음

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)