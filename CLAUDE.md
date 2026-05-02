# vocal-server CLAUDE.md

## 프로젝트 한 줄 요약
FastAPI + PostgreSQL 기반 보컬 분석 서버 — 회원 인증, 녹음 세션, AI 분석, 곡 피치 추출 및 비교 기능 제공.

---

## 환경

| 항목 | 값 |
|------|-----|
| 언어 | Python 3.14 |
| 프레임워크 | FastAPI 0.133 + uvicorn |
| DB | PostgreSQL 17 (`vocal_db`, localhost:5432) |
| ORM | SQLAlchemy 2.0 |
| 인증 | bcrypt + python-jose JWT (HS256) |
| 오디오 | librosa 0.11 / soundfile / pydub |
| 가상환경 | `vocalserver/` (Python 3.14) |

```bash
# 서버 실행
cd /Users/kimjeongwoo/vocal-server
source vocalserver/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# ⚠️ 시작 시 피치 추출로 약 50초 소요 (이미 추출된 경우 즉시 시작)

# psql
/opt/homebrew/Cellar/postgresql@17/17.8/bin/psql vocal_db
```

---

## 현재 상태

**라우터 및 주요 엔드포인트:**
- `POST /auth/signup`, `POST /auth/login`
- `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`
- `POST /sessions/{id}/files` (m4a/wav/mp3 업로드)
- `POST /sessions/{id}/analyze` → 모델 서버 `114.71.220.144:8001`
- `GET /analysis/{run_id}`, `/results`, `/comparison`
- `GET /songs`, `GET /songs/{id}`, `/pitch`, `/lyrics`, `/audio` (인증 불필요)
- `POST /songs/register` (인증 필요)
- `POST /sessions/{id}/compare-pitch`
- `GET /admin/dashboard`, `/users`, `/events/stream` (SSE)

**파일 구조:**
```
app/
  main.py          # 라우터 등록 + 시작 시 곡 스캔/피치 추출
  models/models.py # ORM: User, Session, SessionFile, AnalysisRun, AnalysisResult, Song
  routers/         # auth, sessions, files, analysis, admin, vocal, songs
  services/        # analysis_service.py, pitch_service.py
  deps.py          # get_current_user (JWT)
songs/             # MP3, vocals.wav, final.json, pitch.json
```

**등록된 곡:** 잔나비 - 주저하는 연인들을 위해 (id: `efe04b77-532d-458a-8713-5f3b70c83465`)

---

## 에이전트 행동 규칙

### 토큰 효율
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.

### 실수 방지
- 파일 수정 전 뭘 바꿀 건지 먼저 설명.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.
- 되돌릴 수 있는 작업은 물어보지 말고 바로 진행. 삭제·전송 같은 비가역 작업만 확인.
- 추측 금지. 불명확하면 궁금한 것들을 한 번에 묶어 질문.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.
- 터미널 멀티라인 주의 — Python 코드는 `.py` 파일로 만들어 실행. `-c` 인라인 멀티라인은 쉘 오염을 일으킨다.
- 서버 재시작 후 최소 55초 대기 (startup 피치 추출 포함).
- pycache 클리어 — reload가 반영 안 될 때 `find app -name __pycache__ -exec rm -rf {} +` 후 재시작.
- 인증 불필요 엔드포인트 — songs의 list/get/audio/lyrics/pitch는 인증 없음. register만 인증 필요.
- songs/ 파일 경로는 `PROJECT_ROOT / rel_path` 패턴으로 접근.

---

## 절대 규칙

- DB 테이블 DROP, 데이터 DELETE는 반드시 사용자 확인 후 실행
- `git push`, `git reset --hard` 실행 전 확인
- `songs/` 디렉토리 파일 삭제 금지 (원곡 MP3, 보컬 WAV, 피치 JSON)
- `.env` 파일 내용 출력/로그 금지 (SECRET_KEY 포함)

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

<!-- 형식: [날짜] [카테고리] 실수 / 원인 / 대신 어떻게 -->
<!-- 최신이 위. 기존 항목은 절대 지우지 말고 누적만. -->
<!-- 에이전트가 실수했을 때 즉시 추가 -->

- [2026-05-02] [데이터 동기화] lrc/parsed/{id}_aligned.json 변종이 dmlserver에 존재.
  모델 페이지 산출물 확정 후 sync 패턴 재검토 필요.
  현재는 {id}.json만 동기화.

- [2026-05-02] [Alembic] alembic 도입 후에는 Base.metadata.create_all() 사용 금지.
  스키마 변경은 무조건 alembic revision + upgrade로만.
  이중 관리 시 환경 간 스키마 불일치 발생.

- [2026-04-29] [DB 마이그레이션] NOT NULL 칼럼을 기존 데이터 있는 테이블에 추가할 때는
  alembic autogenerate가 server_default를 자동 생성하지 않으므로
  마이그레이션 파일에 server_default를 수동 추가해야 함.

- [2026-05-03] [서버 재시작] uvicorn 재시작 시 "Address already in use" 발생하면
  이전 프로세스가 살아있는 것. --reload가 켜져 있어도 코드 변경이 반영 안 될 수 있음.
  해결: `pkill -f "uvicorn app.main"` 후 재시작.
  또는 `lsof -i :8000`으로 PID 확인 후 kill.
