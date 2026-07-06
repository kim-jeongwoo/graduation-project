# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 모노레포 구조

순천향대학교 졸업작품: 딥러닝 EGG 추정 기반 가창 발성 평가 시스템.

| 서브프로젝트 | 머신 | 포트 | 역할 |
|---|---|---|---|
| `vocal-server/` | Mac Studio | 8000 | FastAPI 백엔드 (인증, 세션, DB) |
| `dml-server/` | dmlserver GPU | 8001 | AI 추론 서버 + 모델 학습 |
| `app/` | — | — | Expo 앱 |

**각 서브프로젝트의 상세 운영 지침은 해당 `CLAUDE.md`/`AGENTS.md`를 반드시 먼저 읽을 것.**

---

## 시스템 흐름

```
[스마트폰 앱]
  ↓ 녹음 + 업로드 (m4a/wav)
[vocal-server :8000]  ← FastAPI, PostgreSQL, SQLAlchemy 2.0, Python 3.14
  ↓ POST /analyze (WAV + song_id)
[dml-server/model_server :8001]  ← FastAPI, PyTorch, Python 3.11, Conda: EGGDML
  ↓ EGG 추정 + 음향 지표 (CPP, CQ, F0) + 9항목 점수 + 피드백
[vocal-server에 결과 저장 → 앱 시각화]
```

실외/LTE 접근: Cloudflare named tunnel → `https://dml.vocal-fit.com` (dml-server 전용, 비표준 포트 우회).

---

## 서브프로젝트별 진입점

**dml-server** (이 머신, GPU 서버):
```bash
cd ~/projects/egg_prediction && conda activate EGGDML
# 서비스 상태
systemctl status dml-server.service
# 로그 확인
tail -n 80 /var/log/dml-server.log
# 로컬 health check
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health', timeout=8).read().decode())"
# 스크립트 실행 (repo root 기준)
python dml-server/scripts/data_prep/run_all.py
```

**vocal-server** (Mac Studio — 이 머신에서 직접 실행 불가):
```bash
cd /Users/kimjeongwoo/vocal-server/vocal-server
source ../vocalserver/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# psql
/opt/homebrew/Cellar/postgresql@17/17.8/bin/psql vocal_db
```

---

## dml-server 핵심 아키텍처

- **모델**: EfficientEGGNet (non-causal dilated CNN, 5.99M params). 체크포인트: `checkpoints/exp20_progressive/best_model.pt` (disk-only, gitignored).
- **엔드포인트**:
  - `POST /analyze` — 전곡 분석 (StreamingResponse + leading whitespace keepalive, Cloudflare 125s timeout 우회)
  - `POST /analyze-chunk` — 단구간 통합 점수
  - `GET /ws/realtime` — WebSocket 실시간 (200ms 음정 + 5s 호흡)
  - `POST /predict` — EGG wav 반환
  - `GET /health`
- **서비스 모듈** (`model_server/services/`): `timeline_analysis.py`, `realtime.py`, `chunk_analysis.py`
- **production**: `dml-server.service` (systemd). 수동 nohup은 비상 rollback 전용.

## vocal-server 핵심 아키텍처

- FastAPI + SQLAlchemy 2.0 + Alembic 마이그레이션. 스키마 변경은 `alembic revision + upgrade`만.
- ORM 모델: `User`, `Session`, `Song`, `SessionFile`, `AnalysisRun`, `AnalysisResult` (`app/models/models.py`)
- 노래방 파일 (`app/storage/songs/`): MR 음원, LRC, 피치 가이드 — 삭제 금지.
- `/songs/*` 엔드포인트는 인증 필요하지만 user_id 검증 없음.

---

## 에이전트 공통 규칙

- **서브폴더 분리**: `vocal-server/`와 `dml-server/`는 서로 손대지 않음. 작업 범위 CLAUDE.md 먼저 읽을 것.
- `dml-server` 작업 시: `AGENTS.md`가 primary 운영 지침. `CLAUDE.md`는 pitfall/이력 보조.
- **force push 금지**. DB DROP/DELETE는 사용자 확인 후 실행.
- **schema 변경 시** 영향받는 모든 endpoint 명시 (`/analyze`, `/analyze-chunk`, `/ws/realtime`, `/predict`, `/health`).
- `/analyze`는 HTTP 200 streaming 고정. 오류도 body `status` 필드로 반환 (`"invalid"` / `"failed"`).
- 스크립트 root 계산: `dml-server/scripts/` 직하위 → `parents[2]`, `scripts/data_prep/` 내부 → `parents[3]`.
- Python `-c` 인라인 멀티라인 금지 — `.py` 파일로 만들어 실행.
- macOS 업로드 파일명 NFC 정규화 필수: `unicodedata.normalize('NFC', name)`.
