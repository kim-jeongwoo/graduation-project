# HANDOVER_TO_CLAUDE.md

작성 기준: 2026-07-06, repository `/Users/kimjeongwoo/vocal-server`.

주의:
- 이 문서는 저장소를 직접 읽어 확인한 코드 상태만 기록한다.
- `.env` 값, DB 백업의 이메일/해시 값, Cloudflare credential/token 값은 기록하지 않는다.
- `vocal-server` 구현 문서이지만, dmlserver 연동 확인을 위해 `dml-server/model_server/server.py`는 읽기 전용으로 확인했다.

## 1. 저장소 구조 + 각 디렉토리 역할

Git top-level은 `/Users/kimjeongwoo/vocal-server`이고, 현재는 monorepo 형태다.

| 경로 | 역할 |
|---|---|
| `vocal-server/` | FastAPI 백엔드 운영 코드. 실제 앱 root는 `vocal-server/app`, 실행 기준 디렉토리는 `vocal-server/` 내부다. |
| `vocal-server/app/` | FastAPI 앱, 라우터, DB 모델, 스키마, 미들웨어, 템플릿, storage root. |
| `vocal-server/alembic/` | PostgreSQL schema migration. `Base.metadata.create_all()`은 쓰지 않고 Alembic이 schema 관리. |
| `vocal-server/scripts/` | 서버 재시작, signup 토글, song sync, StreamingResponse 검증 스크립트. |
| `vocal-server/docs/` | 백엔드 API/admin/audit 문서. |
| `dml-server/` | AI 모델 및 추론 서버 코드. 현재 checkout의 `model_server/server.py`에는 `/health`, `/predict`, `/analyze`만 있다. |
| `vocal-app/` | Expo 앱. 이번 문서 생성 범위에서는 수정하지 않음. |
| `app/storage/demo_responses/` | 루트 쪽 demo response JSON. 앱 mock/demo 데이터로 보이는 정적 JSON. |
| `docs/` | monorepo 공통 문서. 이 파일도 여기에 위치한다. |
| `backups/` | SQL 백업 파일 위치. 개인정보/비밀번호 해시 포함 가능성이 있어 `.gitignore`에서 `backups/*.sql` 제외. |

## 2. FastAPI 앱 구조: 라우터 목록, 미들웨어, 의존성 주입 구조

앱 entrypoint:
- `vocal-server/app/main.py`: `app = FastAPI(title="Vocal Server", version="0.1.0")`
- `vocal-server/main.py`: `uvicorn main:app`용 루트 entrypoint.

등록 라우터 순서:
1. `auth.router`
2. `sessions.router`
3. `files.router`
4. `analysis.router`
5. `admin.router`
6. `songs.router`
7. `training.router`

라우터 파일:
- `app/routers/auth.py`: `/auth/signup`, `/auth/login`
- `app/routers/sessions.py`: `/sessions`, `/sessions/{session_id}`, `/sessions/{session_id}/training-analyze`
- `app/routers/files.py`: `/sessions/{session_id}/files`
- `app/routers/analysis.py`: `/sessions/{session_id}/analyze`, `/analysis/{run_id}`, `/analysis/{run_id}/results`, `/analysis/{run_id}/comparison`
- `app/routers/admin.py`: `/admin/*`
- `app/routers/songs.py`: `/songs`, `/songs/{song_id}/lrc`, `/songs/{song_id}/pitch-guide`, `/songs/{song_id}/mr`
- `app/routers/training.py`: `/users/me/training-attempts`, `/users/me/favorites`

미들웨어:
- `ActivityTrackerMiddleware`: 일반 사용자 Bearer JWT를 best-effort로 파싱해 `users.last_seen_at`, `users.last_endpoint` 업데이트. `/admin`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/static` 제외. 같은 user + endpoint는 5분 throttle.
- `SessionMiddleware`: admin cookie `admin_session`, `max_age=24*60*60`, `https_only=True`, `same_site="lax"`. secret은 `ADMIN_SESSION_SECRET`, fallback 문자열은 코드에 있음.
- `CORSMiddleware`: `allow_origins=["*"]`, `allow_credentials=True`, 모든 method/header 허용, range 관련 header expose.
- global exception handler: 처리되지 않은 예외를 500 JSON `{"detail": str(exc)}`로 반환하고 traceback 로그.

의존성 주입:
- DB: `app.database.get_db()`가 SQLAlchemy `SessionLocal()`을 요청 단위로 yield/close.
- 일반 사용자 인증: `app.deps.get_current_user()`가 `HTTPBearer` token을 `SECRET_KEY`/`ALGORITHM`으로 decode하고 `sub` UUID로 `User` 조회.
- token 생성: `create_access_token(user_id)`가 `JWT_EXPIRE_DAYS` 기준 exp를 넣어 JWT 생성.
- admin 인증: `app.routers.admin.require_admin_auth(request)`가 `request.session["admin_authenticated"]` 확인. 일반 user `role`과 별도 체계.

## 3. 전체 엔드포인트 명세 (코드 기준)

FastAPI OpenAPI와 `app.routes`를 기준으로 확인했다. `include_in_schema=False` admin 경로도 포함한다.

### 3.1 공개 OpenAPI 포함 엔드포인트

| Method | Path | 인증 | 요청 | 응답 |
|---|---|---|---|---|
| POST | `/auth/signup` | 없음 | JSON `SignupRequest` | 201 `AuthResponse` |
| POST | `/auth/login` | 없음 | JSON `LoginRequest` | 200 `AuthResponse` |
| POST | `/sessions` | Bearer JWT | JSON `SessionCreateRequest` | 201 `SessionCreateResponse` |
| GET | `/sessions` | Bearer JWT | 없음 | 200 `list[SessionBrief]` |
| GET | `/sessions/{session_id}` | Bearer JWT | path `session_id: uuid` | 200 `SessionDetail` |
| POST | `/sessions/{session_id}/training-analyze` | Bearer JWT | multipart `audio`, optional form `chunk_meta` | 200 free-form JSON passthrough |
| POST | `/sessions/{session_id}/files` | Bearer JWT | path `session_id: uuid`, query `file_type=audio`, multipart `file` | 201 `FileUploadResponse` |
| POST | `/sessions/{session_id}/analyze` | Bearer JWT | path `session_id: uuid` | 201 `AnalyzeResponse` |
| GET | `/analysis/{run_id}` | Bearer JWT | path `run_id: uuid` | 200 `AnalysisRunDetail` |
| GET | `/analysis/{run_id}/results` | Bearer JWT | path `run_id: uuid` | 200 `AnalysisResultsResponse` |
| GET | `/analysis/{run_id}/comparison` | Bearer JWT | path `run_id: uuid` | 200 `ComparisonResponse` |
| GET | `/admin/users/{user_id}/sessions` | admin session dependency | path `user_id: uuid` | 200 `list[SessionBrief]` |
| GET | `/admin/events` | admin session dependency | 없음 | 200 free-form event list |
| GET | `/admin/dashboard` | admin session dependency | 없음 | 200 HTML |
| GET | `/songs` | Bearer JWT | 없음 | 200 `list[SongSummary]` |
| GET | `/songs/{song_id}/lrc` | Bearer JWT | path `song_id: ^\d{3}$` | 200 free-form JSON file content |
| GET | `/songs/{song_id}/pitch-guide` | Bearer JWT | path `song_id: ^\d{3}$` | 200 free-form JSON file content |
| GET | `/songs/{song_id}/mr` | Bearer JWT | path `song_id: ^\d{3}$` | 200 `FileResponse` audio/mpeg |
| GET | `/users/me/training-attempts` | Bearer JWT | query `indicator_key?`, `song_id?`, `original_run_id?`, `cursor?`, `limit=50` range 1..200 | 200 `AttemptListResponse` |
| GET | `/users/me/favorites` | Bearer JWT | query `indicator_key?`, `song_id?` | 200 `FavoriteListResponse` |
| POST | `/users/me/favorites` | Bearer JWT | JSON `FavoriteCreateRequest` | 201 `FavoriteItem` |
| DELETE | `/users/me/favorites/{favorite_id}` | Bearer JWT | path `favorite_id: uuid` | 204 no body |
| GET | `/health` | 없음 | 없음 | 200 `{"status": "ok"}` |

### 3.2 OpenAPI 제외 admin/system 엔드포인트

| Method | Path | 인증 | 동작 |
|---|---|---|---|
| GET | `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` | 없음 | FastAPI docs. |
| GET | `/admin` | 없음 | `/admin/login`으로 302 redirect. |
| GET | `/admin/health` | 없음 | `{"admin": "ok"}`. 재시작 스크립트 health check가 사용. |
| GET | `/admin/login` | 없음 | login HTML. |
| POST | `/admin/login` | 없음, password form | `ADMIN_PASSWORD` 비교, 성공 시 session cookie 설정. IP별 5회/5분 실패 시 5분 차단. |
| POST | `/admin/logout` | 없음 | session clear 후 login으로 redirect. |
| GET | `/admin/api/users` | admin session | `list[AdminUserResponse]`. dashboard JS용. |
| GET | `/admin/users` | admin session | 사용자 목록 HTML. query `q`, `show_test`, `limit`, `cursor`. |
| POST | `/admin/signup-toggle` | admin session | 메모리 `app_state.signup_enabled` 토글. 재시작 시 `.env` 기준으로 reset. |
| GET | `/admin/users/{user_id}` | admin session | 사용자 상세 HTML. 세션/즐겨찾기/누적 시도 표시. |
| GET | `/admin/logs` | admin session | 5초 polling 로그 HTML. |
| GET | `/admin/api/events` | admin session | query `limit`, `since`; 최근 event JSON. |
| GET | `/admin/api/online-users` | admin session | 5분 이내 활동 사용자 JSON. |
| GET | `/admin/events/stream` | admin session | deprecated. 항상 410 반환. |

### 3.3 Pydantic 모델 필드

`*`는 required. `anyOf`는 nullable 또는 union이다.

| 모델 | 필드 |
|---|---|
| `SignupRequest` | `email*: EmailStr`, `password*: str(min_length=1)`, `nickname*: str(min_length=1)` |
| `LoginRequest` | `email*: EmailStr`, `password*: str` |
| `AuthResponse` | `user_id*: uuid.UUID`, `email*: str`, `nickname*: str`, `token*: str` |
| `AdminUserResponse` | `user_id*: uuid.UUID`, `email*: str`, `nickname*: str`, `created_at*: datetime` |
| `SongInSession` | `id*: Optional[str]`, `artist*: Optional[str]`, `title*: Optional[str]` |
| `SessionCreateRequest` | `song_id: Optional[str] = None`, `song_title: Optional[str] = None` |
| `SessionCreateResponse` | `session_id*: uuid.UUID`, `status*: str`, `created_at*: datetime` |
| `FileInfo` | `file_id*: uuid.UUID`, `file_type*: str`, `storage_uri*: str`, `format*: Optional[str]`, `sample_rate_hz*: Optional[int]`, `duration_ms*: Optional[int]`, `file_size_bytes*: Optional[int]`, `uploaded_at*: datetime` |
| `MetricItem` | `key*: str`, `value*: float`, `unit*: Optional[str]` |
| `AnalysisRunBrief` | `run_id*: uuid.UUID`, `model_name*: str`, `model_version*: str`, `status*: str`, `requested_at*: datetime`, `finished_at*: Optional[datetime]`, `metrics: list[MetricItem] = []` |
| `LatestAnalysis` | `run_id*: uuid.UUID`, `status*: str`, `requested_at*: datetime`, `finished_at*: Optional[datetime]`, `result_json: Optional[dict] = None`, `metrics: list[MetricItem] = []` |
| `SessionBrief` | `session_id*: uuid.UUID`, `song_title*: Optional[str]`, `song: Optional[SongInSession] = None`, `status*: str`, `analysis_status*: str`, `started_at*: Optional[datetime]`, `created_at*: datetime` |
| `SessionDetail` | `session_id*: uuid.UUID`, `user_id*: uuid.UUID`, `song_title*: Optional[str]`, `song: Optional[SongInSession] = None`, `status*: str`, `started_at*: Optional[datetime]`, `ended_at*: Optional[datetime]`, `created_at*: datetime`, `files: list[FileInfo] = []`, `latest_analysis: Optional[LatestAnalysis] = None` |
| `FileUploadResponse` | `file_id*: uuid.UUID`, `file_type*: str`, `storage_uri*: str`, `duration_ms*: Optional[int]` |
| `AnalyzeResponse` | `run_id*: uuid.UUID`, `status*: str` |
| `AnalysisRunDetail` | `run_id*: uuid.UUID`, `session_id*: uuid.UUID`, `model_name*: str`, `model_version*: str`, `status*: str`, `requested_at*: datetime`, `finished_at*: Optional[datetime]` |
| `AnalysisResultsResponse` | `run_id*: uuid.UUID`, `session_id*: uuid.UUID`, `user_id*: uuid.UUID`, `metrics*: list[MetricItem]`, `result_json: Optional[dict] = None` |
| `ComparisonItem` | `key*: str`, `user_value*: float`, `reference_mean*: float`, `z_score*: Optional[float]`, `percentile*: Optional[float]` |
| `ComparisonResponse` | `run_id*: uuid.UUID`, `reference_name*: Optional[str]`, `comparisons*: list[ComparisonItem]` |
| `SongSummary` | `id*: str`, `artist*: str`, `title*: str`, `master_duration_sec: Optional[float] = None`, `mr_duration_sec: Optional[float] = None`, `has_lrc*: bool`, `has_pitch_guide*: bool` |
| `AttemptItem` | `attempt_id*: uuid.UUID`, `session_id*: Optional[uuid.UUID]`, `original_run_id*: Optional[uuid.UUID]`, `chunk_index*: int`, `chunk_start_sec*: float`, `chunk_end_sec*: float`, `indicator_key*: str`, `before_ai_score*: Optional[float]`, `before_rounded_score*: Optional[int]`, `before_zone*: Optional[str]`, `after_ai_score*: float`, `after_rounded_score*: int`, `after_zone*: str`, `improvement*: Optional[float]`, `attempted_at*: datetime` |
| `AttemptListResponse` | `items*: list[AttemptItem]`, `next_cursor*: Optional[str]`, `has_more*: bool` |
| `FavoriteItem` | `favorite_id*: uuid.UUID`, `song_id*: str`, `song_title*: str`, `song_artist*: str`, `original_run_id*: Optional[uuid.UUID]`, `chunk_index*: int`, `chunk_start_sec*: float`, `chunk_end_sec*: float`, `chunk_lrc_text*: Optional[str]`, `indicator_key*: str`, `created_at*: datetime` |
| `FavoriteListResponse` | `items*: list[FavoriteItem]` |
| `FavoriteCreateRequest` | `original_run_id*: uuid.UUID`, `chunk_index*: int`, `indicator_key*: str` |
| multipart upload body | `file*: binary` for `/sessions/{session_id}/files` |
| multipart training body | `audio*: binary`, `chunk_meta: Optional[str]` for `/sessions/{session_id}/training-analyze` |

## 4. dmlserver 프록시/호출부

Full analyze:
- 위치: `vocal-server/app/services/analysis_service.py`
- 호출 URL: `f"{MODEL_SERVER_URL}/analyze"`
- 요청 변환:
  - DB `SessionFile.storage_uri`에서 audio file path를 읽음.
  - multipart field는 `file`.
  - query param `run_id`는 vocal-server `AnalysisRun.run_id`.
  - `session.song_id`가 있으면 query param `song_id` 추가.
  - timeout `_ANALYZE_TIMEOUT = 180.0`.
- 응답 처리:
  - `response.json()` 파싱 성공 + HTTP success면 DML JSON 전체를 `analysis_runs.result_json`에 저장.
  - `audio_info.voiced_ratio`, `processing_time_ms`, `audio_info.duration_s|duration_sec`만 별도 `analysis_results` rows로 저장.
  - `data["status"]`를 `AnalysisRun.status`로 사용. `no_voice`면 session은 `completed`, `failed`면 session도 `failed`, 그 외 session status는 server status 그대로.
  - HTTP 실패나 JSON 파싱 실패는 `result_json = {"error": True, "http_status": ..., "raw_response": ...}` 형태로 저장.

Training chunk analyze:
- 위치: `vocal-server/app/routers/sessions.py`
- 호출 URL: `f"{MODEL_SERVER_URL}/analyze-chunk"`
- 요청 변환:
  - 클라이언트 request field는 `audio`.
  - dml-server 전송 field는 `file`.
  - optional form `chunk_meta`는 문자열 그대로 `data["chunk_meta"]`로 전달.
  - `chunk_meta`는 best-effort JSON parse해서 응답 echo와 training attempt 저장에만 사용.
  - timeout `_TRAINING_TIMEOUT = 25.0`.
- 응답 처리:
  - 400은 DML detail을 400으로 전달.
  - 5xx는 502, timeout/request error는 504.
  - success JSON은 `dict(body)`로 복사 후 `run_id`만 제거, `session_id`, parsed `chunk_meta`를 추가해서 반환.
  - `body.status == "success"`이고 `chunk_meta.original_run_id`, `chunk_meta.chunk_index`, `body.scores`가 있으면 `training_attempts`를 best-effort 저장한다. 저장 실패는 rollback/log만 하고 응답에는 영향 없음.

StreamingResponse keepalive:
- 현재 `vocal-server/app` 코드에는 `StreamingResponse` import/사용이 없다.
- `vocal-server/scripts/verify_streaming.py`는 `https://dml.vocal-fit.com/_test_stream?duration=130`을 `httpx.get(..., timeout=180.0)`으로 호출해 leading whitespace keepalive + 최종 JSON을 `response.json()`이 파싱 가능한지 검증하는 스크립트다.
- 현재 checkout의 `dml-server/model_server/server.py`에도 `StreamingResponse`, `/_test_stream`, `/analyze-chunk` 구현은 없다. 있는 endpoint는 `/health`, `/predict`, `/analyze`뿐이다. 따라서 문서/운영 서버와 현재 dml-server 소스 사이에는 불일치가 있다.

## 5. 필드 처리 방식: whitelist vs passthrough

| 엔드포인트/흐름 | 패턴 | v2 필드 drop 위험 |
|---|---|---|
| `POST /auth/signup`, `POST /auth/login` | whitelist. `AuthResponse`만 반환. | DML v2와 무관. |
| `POST /sessions` | whitelist. `SessionCreateResponse`만 반환. | 무관. |
| `GET /sessions` | whitelist. `SessionBrief`를 직접 구성. `result_json` 없음. | 분석 결과 v2 필드는 의도적으로 목록에 없음. |
| `GET /sessions/{session_id}` | mixed. top-level은 `SessionDetail` whitelist, `latest_analysis.result_json`은 DB JSON passthrough. | `result_json` 내부 v2 필드는 보존. top-level 신규 DML 필드는 없음. |
| `POST /sessions/{session_id}/files` | whitelist. `FileUploadResponse`만 반환. | 무관. |
| `POST /sessions/{session_id}/analyze` | whitelist. `run_id`, `status`만 반환하고 실제 DML 결과는 background task 저장. | 즉시 응답에는 v2 필드 없음. 결과 조회에서 확인. |
| full analyze 저장 | passthrough 저장. DML `/analyze` JSON 전체를 `AnalysisRun.result_json`에 저장. | v2 필드 보존. 단 `AnalysisResult` table에는 3개 metric만 별도 저장되므로 comparison 계열은 v2를 쓰지 않음. |
| `GET /analysis/{run_id}` | whitelist. `AnalysisRunDetail`. | 결과 JSON 없음. |
| `GET /analysis/{run_id}/results` | mixed. top-level whitelist, `result_json` passthrough. | `result_json` 내부 v2 필드 보존. |
| `GET /analysis/{run_id}/comparison` | whitelist. `AnalysisResult` rows 기반 비교. | v2 `scores_v2` 등과 무관하며 drop/미사용. |
| `POST /sessions/{session_id}/training-analyze` | passthrough. DML JSON 전체에서 `run_id`만 제거하고 `session_id`, `chunk_meta` 추가. | 신규 v2 필드 자동 통과. `run_id`는 의도적으로 drop. |
| `GET /songs` | whitelist. `SongSummary`. | 무관. |
| `GET /songs/{song_id}/lrc`, `/pitch-guide` | file JSON passthrough. | 파일 JSON schema 변화는 그대로 반환. |
| `GET /songs/{song_id}/mr` | `FileResponse`. | 무관. |
| training attempts/favorites | whitelist. 내부 DB 모델 필드만 반환. | DML v2 result_json 직접 반환 아님. |
| admin JSON/HTML | mostly whitelist/manual dict/HTML. events는 in-memory event dict passthrough. | DML v2 직접 노출 아님. |

명시 위험:
- `GET /analysis/{run_id}/comparison`은 `analysis_results` table에 저장된 3개 metric만 대상으로 하므로 v2 score mapper 결과를 반영하지 않는다.
- `GET /admin/users/{user_id}/sessions`는 `response_model=list[SessionBrief]`인데 함수는 raw `Session` rows를 반환한다. `SessionBrief`에는 `analysis_status` required가 있어 response validation 실패 가능성이 있다.
- `training-analyze` 함수 description에는 “DB 저장 없이”라고 되어 있지만 현재 코드는 조건 충족 시 `training_attempts`를 저장한다.

## 6. score_mapper_v2 관련 코드

`vocal-server/app`에는 `score_mapper_v2`라는 함수/모듈은 없다.

현재 처리 흐름:
- full analyze는 dml-server `/analyze` 응답 JSON 전체를 `analysis_runs.result_json`에 저장한다. 따라서 DML 응답에 `score_mapper_version`, `scores_v2`, `scores_meta`, `academic_analysis_scores`, `reliability` 등이 들어오면 DB JSON과 `/analysis/{run_id}/results`, `/sessions/{session_id}`의 `latest_analysis.result_json`에서 보존된다.
- training analyze는 DML `/analyze-chunk` 응답을 `run_id`만 제거하고 거의 그대로 반환한다. v2 신규 필드도 자동 통과한다.
- 별도 DB table `analysis_results`에는 score_mapper_v2 전체가 분해 저장되지 않는다.

현재 checkout의 `dml-server/model_server`에도 `score_mapper_v2`, `score_mapper_version`, `scores_v2` 문자열은 발견되지 않았다. `analysis_pipeline.py`에는 기존 `reliability.high_reliability`, `reliability.medium_reliability` 형태만 확인된다.

## 7. 실행/배포

실행 기준 디렉토리:

```bash
cd /Users/kimjeongwoo/vocal-server/vocal-server
../vocalserver/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

코드상 다른 실행:

```bash
cd /Users/kimjeongwoo/vocal-server/vocal-server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python main.py
```

재시작 스크립트:
- `vocal-server/scripts/restart_server.sh`
- `PROJECT_DIR="/Users/kimjeongwoo/vocal-server/vocal-server"`
- `VENV_BIN="/Users/kimjeongwoo/vocal-server/vocalserver/bin"`
- `LOG_FILE="/tmp/uvicorn_new.log"`
- `pkill -TERM -f "uvicorn app.main"` 후 최대 10초 대기, 이후 `pkill -9`, 새 uvicorn 실행, `/admin/health`를 30초까지 확인.

Cloudflare Tunnel:
- 코드 저장소 안에는 vocal-server용 Cloudflare `config.yml`이 없다.
- 문서상 설정 위치는 `~/.cloudflared/config.yml` 및 `/etc/cloudflared/config.yml`이 언급된다.
- 문서상 외부 도메인은 `https://api.vocal-fit.com`, `https://admin.vocal-fit.com`, dmlserver base는 `https://dml.vocal-fit.com`.
- Cloudflare credential/token/config 내용은 저장소에 기록하지 않는다.

환경 변수 목록(값 제외):
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `ALGORITHM`
- `DATABASE_URL`
- `JWT_EXPIRE_DAYS`
- `MODEL_SERVER_URL`
- `SECRET_KEY`
- `SIGNUP_ENABLED`

## 8. 의존성과 버전

`vocal-server/requirements.txt`:

```text
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-dotenv
alembic
bcrypt
python-jose[cryptography]
python-multipart
pydantic[email]
httpx
itsdangerous
jinja2
```

현재 `vocalserver` venv에서 확인한 주요 설치 버전:

| package | version |
|---|---|
| fastapi | 0.133.0 |
| starlette | 0.52.1 |
| uvicorn | 0.41.0 |
| SQLAlchemy | 2.0.47 |
| alembic | 1.18.4 |
| psycopg2-binary | 2.9.11 |
| pydantic | 2.12.5 |
| email-validator | 2.3.0 |
| python-dotenv | 1.2.1 |
| python-jose | 3.5.0 |
| python-multipart | 0.0.22 |
| bcrypt | 5.0.0 |
| httpx | 0.28.1 |
| itsdangerous | 2.2.0 |
| Jinja2 | 3.1.6 |
| anyio | 4.12.1 |

## 9. git 이력: `647c8e1` 이후 전체 커밋 요약, 브랜치/태그

현재 브랜치:
- `main`
- `origin/main`

태그:
- `v2.x-gpt-final` -> `8e939c0` 기준으로 생성/푸시 완료.

`647c8e1` 이후 커밋:

| commit | 요약 |
|---|---|
| `16a11e0` | Add HANDOVER.md for GPT migration |
| `f1168fb` | feat: add vocal-app project snapshot |
| `863c1b7` | docs: strengthen vocal-app project documentation |
| `a497946` | Merge PR #1 add vocal-app |
| `9ccd7e0` | feat: finalize vocal-app v2 closeout |
| `5e82e7e` | docs: remove raw handover changes from v2 closeout PR |
| `1606663` | Merge PR #2 v2 closeout |
| `5e18c84` | feat: apply vocal-app stability batch 1 |
| `7987881` | docs: expand vocal-fit project overview |
| `359c7b9` | Merge PR #3 batch1 |
| `67710f3` | feat: apply vocal-app stability batch 2 |
| `8407809` | Merge PR #4 batch2 |
| `5b4c38c` | feat: apply vocal-app stability batch 3 |
| `12c2e66` | Merge PR #5 batch3 |
| `c7d22a8` | feat: apply vocal-app feedback batch 4 |
| `315d088` | Merge PR #6 batch4 |
| `4836837` | feat: apply vocal-app training batch 5 |
| `7cfc851` | Merge PR #7 batch5 |
| `561aa34` | chore: prepare vocal-app release configuration |
| `4aebe54` | Merge PR #8 release prep |
| `f8532b4` | fix: apply vocal-app apk feedback hotfix |
| `beb0911` | Merge PR #9 apk feedback hotfix |
| `7905f4b` | fix: stabilize vocal-app audio focus flows |
| `4bd8fb3` | Merge PR #10 audio focus hotfix |
| `8e939c0` | chore: save current vocal-server workspace state |
| `HEAD` | docs: add Claude handover code state |

## 10. TODO/FIXME/HACK 주석 전수 수집

검색 범위: monorepo 전체, 단 `.git`, `vocalserver` venv, `vocal-app/node_modules`, `backups`, lock/json/sql 파일 제외. 이 문서 자체의 TODO 문자열은 제외했다.

| 파일:라인 | 주석 |
|---|---|
| `vocal-server/app/models/models.py:38` | `TODO: 상용화 시 default=False로 변경, 가입 승인 흐름 추가` |
| `vocal-server/app/routers/songs.py:98` | `TODO: 앱에서 부분 재생/탐색 필요 시 range request 구현` |
| `vocal-app/src/store/recordingStore.ts:3` | `TODO: Step B에서 실제 상태 정의` |
| `vocal-app/src/store/historyStore.ts:3` | `TODO: Step B에서 실제 상태 정의` |
| `vocal-app/src/screens/home/EvalResultScreen.tsx:27` | `TODO(Step E): 사용자 목표에서 가져오기` |

문서 내 회고성 TODO 언급:
- `vocal-server/docs/vocal_server_code_audit_2026-06-16.md:863`에 range request TODO가 문서화되어 있음.

## 11. 위험 지점: 하드코딩, 임시방편, 타임아웃 관련 설정값들

하드코딩/default:
- `app/config.py`: `DATABASE_URL` fallback `postgresql://localhost:5432/vocal_db`.
- `app/config.py`: `SECRET_KEY` fallback `change-me-in-production`.
- `app/config.py`: `MODEL_SERVER_URL` fallback `http://114.71.220.144:8001`.
- `app/main.py`: `ADMIN_SESSION_SECRET` fallback `dev-only-change-me`.
- `app/main.py`: CORS `allow_origins=["*"]` + credentials.
- `app/database.py`: `create_engine(..., echo=True)`로 SQL 로그가 켜져 있음.
- `app/routers/admin.py`: admin login rate limit이 process memory 기반.
- `app/state.py`: `signup_enabled`가 memory state. admin toggle은 재시작 시 `.env` 값으로 reset.
- `app/event_store.py`: events/subscribers가 memory store. multi-worker/재시작 시 유실.
- `app/middleware/activity_tracker.py`: throttle cache가 memory store. multi-worker에서 부정확.
- `app/routers/files.py`: 업로드 파일을 원본 filename 그대로 `app/storage/users/{user_id}/sessions/{session_id}/`에 저장.
- `app/routers/songs.py`: storage path가 `app/storage/songs/...`로 코드상 고정.
- `app/routers/admin.py`: `templates = Jinja2Templates(directory="app/templates")`라 실행 cwd가 `vocal-server/` 내부여야 안전.

타임아웃/제한값:
- `app/services/analysis_service.py`: `_ANALYZE_TIMEOUT = 180.0`.
- `app/routers/sessions.py`: `_TRAINING_TIMEOUT = 25.0`.
- `app/main.py`: admin session max age `24 * 60 * 60`.
- `app/routers/admin.py`: `_FAIL_LIMIT = 5`, `_BLOCK_DURATION = 5분`, `_FAIL_WINDOW = 5분`.
- `app/middleware/activity_tracker.py`: `_THROTTLE_WINDOW = 5분`.
- `app/event_store.py`: `MAX_EVENTS = 50`, subscriber queue maxsize `100`.
- `app/routers/training.py`: training attempts default limit `50`, max limit `200`.
- `app/routers/admin.py`: admin users default limit `50`, max limit `100`.
- `scripts/restart_server.sh`: graceful wait 10초, health wait 30초, curl max time 2초.
- `scripts/verify_streaming.py`: streaming verification timeout `180.0`.

구현 불일치/임시방편:
- `event_store.py`는 SSE 구독자 기능이 남아 있지만 `/admin/events/stream`은 410으로 폐기되어 현재 admin logs는 polling 방식이다.
- `vocal-server`는 `/sessions/{id}/training-analyze`에서 `MODEL_SERVER_URL/analyze-chunk`를 호출하지만 현재 checkout의 `dml-server/model_server/server.py`에는 `/analyze-chunk`가 없다.
- `StreamingResponse`는 운영/문서/검증 스크립트에 언급되지만 현재 checkout의 vocal-server/dml-server 코드에는 구현이 없다.
- SQL 백업 파일은 개인정보/비밀번호 해시를 포함할 수 있어 commit/push 대상에서 제외해야 한다.

## 12. 계정/권한 처리 코드 (16개 계정 체계 관련)

일반 사용자:
- `User` model fields: `user_id`, `email(unique)`, `password_hash`, `nickname`, `role`, `is_approved`, `created_at`, `updated_at`, `last_seen_at`, `last_endpoint`.
- `role` default는 `"user"`이고 주석상 `user / trainer / admin` 값이 가능하지만, 일반 API 권한 분기는 `role`을 사용하지 않는다.
- `is_approved` default는 `True`. TODO는 상용화 시 `False`로 바꾸고 승인 flow를 추가하라는 내용이다.
- `signup`은 `app_state.signup_enabled`가 false면 403, true면 이메일 중복 확인 후 bcrypt hash 저장 및 JWT 반환.
- `login`은 이메일 조회 + bcrypt 검증 후 JWT 반환. `is_approved` 검사는 현재 login에 없다.
- 일반 API 권한은 Bearer JWT의 `sub` UUID가 DB user와 일치하는지만 확인한다.

Admin:
- admin은 `User.role == "admin"` 기반이 아니다.
- `/admin/login` form password가 `ADMIN_PASSWORD`와 일치하면 `request.session["admin_authenticated"] = True`.
- admin session cookie 이름은 `admin_session`.
- admin 보호 endpoint는 `Depends(require_admin_auth)`로 세션만 확인한다.
- login 실패 rate limit은 IP 기준 memory dict다.

16개 계정 체계:
- 현재 코드에는 “16개 계정을 생성/고정 배정”하는 로직이 없다.
- 관련된 코드는 admin 사용자 목록에서 테스트 계정을 숨기기 위한 `_TEST_EMAIL_LIKE_PATTERNS`뿐이다.
- 현재 패턴: `test_a_%`, `test_b_%`, `hdrtest_%`, `tmtest_%`, `trtest_%`, `trtest2_%`, `raw_%`, `p7a_%`, `p7b_%`, `sigtest_%`, `sigtest_back_%`, `toggle_test_%`, `toggle_status_check%`, `signup_check%`.
- 따라서 student/evaluator/director/team 같은 계정 체계가 운영상 존재하더라도, 이 checkout의 FastAPI 코드에서는 별도 권한 체계로 구현되어 있지 않다.
