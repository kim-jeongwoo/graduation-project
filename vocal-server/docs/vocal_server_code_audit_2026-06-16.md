# vocal-server 실제 코드 감사 보고서

작성일: 2026-06-16  
대상 repo: `/Users/kimjeongwoo/vocal-server`  
실제 백엔드 코드 위치: `/Users/kimjeongwoo/vocal-server/vocal-server`  
목적: 졸업작품 최종 설계서 작성을 위한 vocal-server 실제 구현 확인

## 0. 감사 범위와 원칙

이번 감사는 read-only 코드 감사 요청에 따라 진행했다.

- 파일 수정, DB 변경, 서버 재시작, Cloudflare 설정 변경, git fetch/pull/reset/stash/delete는 수행하지 않았다.
- secret/token/password/env 실제 값은 출력하지 않았다.
- env 변수명과 역할만 확인했다.
- `app/storage`는 파일 목록과 구조만 확인했고, 녹음/음원 파일 내용은 열지 않았다.
- 저장소 안에 `dml-server/`도 존재하지만, 작업 범위는 `vocal-server/`였으므로 dml-server 코드는 감사하지 않았다.

이 문서는 실제 코드 기준 요약이다. 특히 dirty worktree 상태의 변경 사항도 현재 코드 상태로 반영했다.

## 1. Repo 상태

| 항목 | 값 |
|---|---|
| path | `/Users/kimjeongwoo/vocal-server` |
| git top-level | `/Users/kimjeongwoo/vocal-server` |
| 실제 백엔드 코드 | `/Users/kimjeongwoo/vocal-server/vocal-server` |
| branch | `main` |
| HEAD | `16a11e0` |
| git diff check | 문제 없음 |
| read-only 여부 | 감사 중 파일 수정, DB 변경, 서버 재시작, Cloudflare 설정 변경, git fetch/pull/reset/stash/delete 없음 |

현재 dirty 상태:

```text
 M vocal-server/PROGRESS.md
 M vocal-server/app/routers/admin.py
 M vocal-server/app/routers/analysis.py
 M vocal-server/app/routers/sessions.py
 M vocal-server/app/services/analysis_service.py
 M vocal-server/app/templates/admin/users.html
 M vocal-server/docs/api.md
?? .codex/
?? AGENTS.md
?? app/
?? backups/
?? vocal-server/app/routers/admin.py.bak-20260524-003229
?? vocal-server/app/templates/admin/users.html.bak-20260524-003229
```

요청서에 적힌 dirty 목록보다 실제 dirty가 더 많다. 특히 `admin.py`, `users.html`, 백업 파일, 루트 untracked 항목도 존재한다.

## 2. 기술 스택과 dependency

`vocal-server/requirements.txt`에는 버전 pin이 없다. 아래 버전은 현재 venv의 `pip freeze` 기준이다.

| 항목 | 확인 결과 |
|---|---|
| Python | 3.14.2 |
| FastAPI | 0.133.0 |
| Uvicorn | 0.41.0 |
| SQLAlchemy | 2.0.47 |
| Alembic | 1.18.4 |
| Pydantic | 2.12.5 |
| httpx | 0.28.1 |
| bcrypt | 5.0.0 |
| passlib | 1.7.4 |
| JWT library | python-jose 3.5.0 |
| python-multipart | 0.0.22 |
| PostgreSQL driver | psycopg2-binary 2.9.11 |
| Jinja2 | 3.1.6 |
| 기타 설치 확인 | itsdangerous 2.2.0, python-dotenv 1.2.1, starlette 0.52.1 |

추가 확인:

- `pyproject.toml`, `poetry.lock`, `setup.py`, `setup.cfg`, `Dockerfile`, `docker-compose*.yml`, `Procfile`은 확인되지 않았다.
- deployment/script 관련 파일은 `vocal-server/scripts/` 아래에 있다.

## 3. 주요 파일 트리

중요 파일:

```text
vocal-server/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── event_store.py
│   ├── main.py
│   ├── state.py
│   ├── middleware/
│   │   └── activity_tracker.py
│   ├── models/
│   │   └── models.py
│   ├── routers/
│   │   ├── admin.py
│   │   ├── analysis.py
│   │   ├── auth.py
│   │   ├── files.py
│   │   ├── sessions.py
│   │   ├── songs.py
│   │   └── training.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── services/
│   │   └── analysis_service.py
│   ├── storage/
│   │   ├── .gitignore
│   │   ├── songs/
│   │   └── users/
│   └── templates/
│       └── admin/
│           ├── login.html
│           ├── logs.html
│           ├── user_detail.html
│           └── users.html
├── alembic/
│   ├── env.py
│   └── versions/
├── docs/
│   ├── admin_reference.md
│   └── api.md
├── scripts/
│   ├── restart_server.sh
│   ├── seed_songs.py
│   ├── signup_toggle.sh
│   ├── sync_songs.sh
│   └── verify_streaming.py
├── requirements.txt
└── test_integration.py
```

확인되지 않거나 없음:

- `tests/` 디렉토리 없음
- Docker 관련 파일 없음
- pyproject/poetry/setup 관련 파일 없음

`app/storage/.gitignore`는 `*` 및 `!.gitignore` 구조라 storage 내용은 기본적으로 git 추적 대상이 아니다.

## 4. FastAPI app 구성

`app/main.py`에서 FastAPI app을 생성한다.

- app title: `Vocal Server`
- app version: `0.1.0`
- middleware:
  - `ActivityTrackerMiddleware`
  - `SessionMiddleware` for admin session
  - `CORSMiddleware`
- 등록 router:
  - `auth.router`
  - `sessions.router`
  - `files.router`
  - `analysis.router`
  - `admin.router`
  - `songs.router`
  - `training.router`
- startup:
  - `SIGNUP_ENABLED` env를 읽어 `app_state.signup_enabled` 초기화
- health:
  - `GET /health` returns `{"status": "ok"}`

주의점:

- 전역 exception handler가 `detail=str(exc)`를 반환한다. 운영 환경에서는 내부 예외 문자열 노출 가능성이 있다.
- `SessionMiddleware`는 `ADMIN_SESSION_SECRET` env를 사용하고, fallback 문자열이 코드에 있다. 실제 secret 값은 출력하지 않았다.

## 5. Endpoint 전체 목록

아래 표는 실제 FastAPI route 등록 기준이다.

| Method | Path | Source | Function | Auth | Request | Response | DML | 앱 사용 | 운영/Admin | 비고 |
|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/health` | `main.py` | `health_check` | 없음 | 없음 | `{"status":"ok"}` | 없음 | 가능 | health | 정상 route |
| POST | `/auth/signup` | `auth.py` | `signup` | 없음 | JSON `email`, `password`, `nickname` | `AuthResponse` | 없음 | 예 | 아니오 | signup toggle 영향 |
| POST | `/auth/login` | `auth.py` | `login` | 없음 | JSON `email`, `password` | `AuthResponse` | 없음 | 예 | 아니오 | JWT 발급 |
| POST | `/sessions` | `sessions.py` | `create_session` | Bearer JWT | JSON `song_id?`, `song_title?` | `SessionCreateResponse` | 없음 | 예 | 아니오 | 세션 생성 |
| GET | `/sessions` | `sessions.py` | `list_sessions` | Bearer JWT | 없음 | `list[SessionBrief]` | 없음 | 예 | 아니오 | `analysis_status` 계산 |
| GET | `/sessions/{session_id}` | `sessions.py` | `get_session` | Bearer JWT | path UUID | `SessionDetail` | 없음 | 예 | 아니오 | latest analysis 포함 |
| POST | `/sessions/{session_id}/files` | `files.py` | `upload_file` | Bearer JWT | multipart `file`, query `file_type=audio` | `FileUploadResponse` | 없음 | 예 | 아니오 | upload 후 session status=`uploaded` |
| POST | `/sessions/{session_id}/analyze` | `analysis.py` | `analyze_session` | Bearer JWT | path UUID | `AnalyzeResponse` | full analyze | 예 | 아니오 | async start + polling |
| GET | `/analysis/{run_id}` | `analysis.py` | `get_analysis_run` | Bearer JWT | path UUID | `AnalysisRunDetail` | 없음 | 예 | 아니오 | polling status |
| GET | `/analysis/{run_id}/results` | `analysis.py` | `get_analysis_results` | Bearer JWT | path UUID | `AnalysisResultsResponse` | 없음 | 예 | 아니오 | result_json 반환 |
| GET | `/analysis/{run_id}/comparison` | `analysis.py` | `get_analysis_comparison` | Bearer JWT | path UUID | `ComparisonResponse` | 없음 | 가능 | 아니오 | reference 없으면 빈 배열 |
| POST | `/sessions/{session_id}/training-analyze` | `sessions.py` | `training_analyze` | Bearer JWT | multipart `audio`, form `chunk_meta?` | raw dict | `/analyze-chunk` | 예 | 아니오 | TrainingScreen |
| GET | `/users/me/training-attempts` | `training.py` | `list_training_attempts` | Bearer JWT | query filters/cursor/limit | `AttemptListResponse` | 없음 | 예 | 아니오 | 훈련 이력 |
| GET | `/users/me/favorites` | `training.py` | `list_favorites` | Bearer JWT | query filters | `FavoriteListResponse` | 없음 | 예 | 아니오 | 즐겨찾기 |
| POST | `/users/me/favorites` | `training.py` | `create_favorite` | Bearer JWT | JSON `original_run_id`, `chunk_index`, `indicator_key` | `FavoriteItem` | 없음 | 예 | 아니오 | 노래방 세션만 |
| DELETE | `/users/me/favorites/{favorite_id}` | `training.py` | `delete_favorite` | Bearer JWT | path UUID | 204 | 없음 | 예 | 아니오 | 본인 것만 |
| GET | `/songs` | `songs.py` | `list_songs` | Bearer JWT | 없음 | `list[SongSummary]` | 없음 | 예 | 아니오 | DB source |
| GET | `/songs/{song_id}/lrc` | `songs.py` | `get_lrc` | Bearer JWT | 3-digit path | JSON file | 없음 | 예 | 아니오 | LRC parsed file |
| GET | `/songs/{song_id}/pitch-guide` | `songs.py` | `get_pitch_guide` | Bearer JWT | 3-digit path | JSON file | 없음 | 예 | 아니오 | pitch guide file |
| GET | `/songs/{song_id}/mr` | `songs.py` | `get_mr` | Bearer JWT | 3-digit path | `FileResponse audio/mpeg` | 없음 | 예 | 아니오 | range request 미구현 |
| GET | `/admin` | `admin.py` | `admin_root` | 없음 | 없음 | 302 | 없음 | 아니오 | 예 | `/admin/login` redirect |
| GET | `/admin/health` | `admin.py` | `admin_health` | 없음 | 없음 | JSON | 없음 | 아니오 | 예 | admin health |
| GET | `/admin/login` | `admin.py` | `login_page` | 없음 | query error/retry | HTML | 없음 | 아니오 | 예 | login page |
| POST | `/admin/login` | `admin.py` | `login_submit` | 없음 | form `password` | 302 또는 500 | 없음 | 아니오 | 예 | admin password |
| POST | `/admin/logout` | `admin.py` | `logout` | admin session | 없음 | 302 | 없음 | 아니오 | 예 | session clear |
| GET | `/admin/api/users` | `admin.py` | `list_all_users_json` | admin session | 없음 | `list[AdminUserResponse]` | 없음 | 아니오 | 예 | schema 제외 |
| GET | `/admin/users` | `admin.py` | `list_all_users_page` | admin session | `q`, `show_test`, `limit`, `cursor` | HTML | 없음 | 아니오 | 예 | 사용자 목록 |
| POST | `/admin/signup-toggle` | `admin.py` | `toggle_signup` | admin session | 없음 | 302 | 없음 | 아니오 | 예 | memory toggle |
| GET | `/admin/users/{user_id}` | `admin.py` | `get_user_detail` | admin session | path UUID | HTML | 없음 | 아니오 | 예 | 상세 화면 |
| GET | `/admin/users/{user_id}/sessions` | `admin.py` | `list_user_sessions` | admin session | path UUID | `list[SessionBrief]` | 없음 | 아니오 | 예 | OpenAPI 포함 |
| GET | `/admin/events` | `admin.py` | `list_events` | admin session | 없음 | JSON list | 없음 | 아니오 | 예 | legacy compatibility |
| GET | `/admin/logs` | `admin.py` | `logs_page` | admin session | 없음 | HTML | 없음 | 아니오 | 예 | 5초 polling UI |
| GET | `/admin/api/events` | `admin.py` | `api_events` | admin session | `limit`, `since` | JSON | 없음 | 아니오 | 예 | polling events |
| GET | `/admin/api/online-users` | `admin.py` | `api_online_users` | admin session | 없음 | JSON | 없음 | 아니오 | 예 | 5분 이내 활동 |
| GET | `/admin/events/stream` | `admin.py` | `event_stream_deprecated` | admin session | 없음 | 410 Gone | 없음 | 아니오 | deprecated | SSE 폐기 |
| GET | `/admin/dashboard` | `admin.py` | `dashboard` | admin session | 없음 | HTML | 없음 | 아니오 | 구 dashboard | SSE JS가 남아 있어 비권장 |

존재하지 않는 route:

- `/ws/realtime`: 실제 등록 없음
- `/analysis/{id}/user_f0`: admin label/docs 흔적만 있고 실제 route 없음
- `target_chunks`: 실제 route 없음

## 6. 인증과 보안 구조

### 6.1 일반 사용자 인증

관련 파일:

- `app/routers/auth.py`
- `app/deps.py`
- `app/config.py`
- `app/middleware/activity_tracker.py`

회원가입:

1. `POST /auth/signup`
2. `app_state.signup_enabled`가 false면 403
3. email 중복 검사
4. password를 bcrypt로 hash
5. `User` row 생성
6. JWT access token 발급
7. signup event 추가

로그인:

1. `POST /auth/login`
2. email로 user 조회
3. bcrypt로 password 검증
4. JWT access token 발급
5. login event 추가

JWT:

- `create_access_token(user_id)`가 `sub`와 `exp`를 넣어 JWT 발급
- `SECRET_KEY`, `ALGORITHM`, `JWT_EXPIRE_DAYS` env 사용
- `get_current_user()`는 `Authorization: Bearer <token>`에서 token을 꺼내고, `sub`를 UUID로 변환해 DB user를 찾는다.

401 처리:

- token payload에 `sub` 없음: 401
- JWT decode 실패: 401
- user 없음: 401
- login email/password 불일치: 401

### 6.2 Admin 인증

관련 파일:

- `app/main.py`
- `app/routers/admin.py`
- `app/templates/admin/login.html`

구조:

- `SessionMiddleware` 기반 admin session cookie
- cookie name: `admin_session`
- max age: 24시간
- `https_only=True`, `same_site="lax"`
- password는 `ADMIN_PASSWORD` env에서 읽음
- session secret은 `ADMIN_SESSION_SECRET` env에서 읽음

Admin login flow:

1. `GET /admin/login` HTML form 표시
2. `POST /admin/login` form `password` 제출
3. IP rate limit 검사
4. `ADMIN_PASSWORD`와 비교
5. 성공 시 `request.session["admin_authenticated"] = True`
6. `/admin/users`로 redirect

Admin auth dependency:

- `require_admin_auth(request)`
- `request.session.get("admin_authenticated")`가 없으면 401
- response header에 `Location: /admin/login`

Rate limit:

- 5분 window
- 실패 5회
- 5분 차단
- 메모리 기반이라 서버 재시작 시 초기화
- IP는 `X-Forwarded-For` 첫 번째 값을 우선 사용

보안상 caveat:

- 일반 user `role`과 admin web auth는 분리되어 있다.
- Admin password 비교는 단순 문자열 비교다.
- Admin session과 rate-limit 상태는 단일 프로세스 메모리 기반이다.
- 전역 exception handler가 exception 문자열을 response detail에 포함한다.

## 7. DML 서버 연동

관련 파일:

- `app/config.py`
- `app/routers/analysis.py`
- `app/services/analysis_service.py`
- `app/routers/sessions.py`

`MODEL_SERVER_URL` 사용 위치:

- `app/services/analysis_service.py`: full analyze에서 `MODEL_SERVER_URL/analyze`
- `app/routers/sessions.py`: training analyze에서 `MODEL_SERVER_URL/analyze-chunk`

### 7.1 Full analyze flow

Endpoint:

- `POST /sessions/{session_id}/analyze`

흐름:

1. JWT user 확인
2. session 존재 확인
3. session owner 확인
4. session status가 `uploaded`인지 확인
5. `AnalysisRun` 생성
   - `model_name="vocal-analysis"`
   - `model_version="0.1.0"`
   - `status="queued"`
6. DB commit 후 run_id 반환
7. FastAPI `BackgroundTasks`에 `run_analysis_by_ids(run_id, session_id)` 등록
8. background task가 새 DB session을 만들고 run/session을 다시 조회
9. `run_analysis(run, session, db)` 실행
10. `SessionFile` 중 `file_type="audio"` 파일을 찾아 `storage_uri`에서 파일 open
11. DML `/analyze`로 `file` multipart 전송
12. params:
    - `run_id`
    - `song_id`가 있으면 함께 전달
13. DML JSON response를 `analysis_runs.result_json`에 통째 저장
14. 일부 metric은 `analysis_results`에 row로 저장
15. `AnalysisRun.status`와 `Session.status` 업데이트

Full analyze timeout:

```python
_ANALYZE_TIMEOUT = 180.0
```

전송 구조:

- URL: `f"{MODEL_SERVER_URL}/analyze"`
- params: `{"run_id": str(run.run_id)}`, optional `song_id`
- files: `{"file": (file_path.name, file_object, "audio/wav")}`

Status policy:

- HTTP 비성공 또는 JSON parse 실패:
  - `run.status="failed"`
  - `session.status="failed"`
  - `run.result_json`에 error/http_status/raw_response/exception 형태 저장
- DML body parse 성공:
  - `run.result_json = data`
  - `server_status = data.get("status", "completed")`
  - `run.status = server_status`
  - `server_status == "no_voice"`이면 `session.status="completed"`
  - `server_status == "failed"`이면 `session.status="failed"`
  - 그 외에는 `session.status = server_status`

No voice:

- `AnalysisRun.status`: `no_voice`
- `Session.status`: `completed`
- reason은 `result_json` 안에 저장됨

BackgroundTask/run_id polling:

- POST analyze는 완료를 기다리지 않고 즉시 `{run_id, status:"queued"}`를 반환
- 앱은 `GET /analysis/{run_id}`로 상태를 polling
- terminal status 후 `GET /analysis/{run_id}/results` 조회

StreamingResponse:

- 현재 vocal-server app code에는 `StreamingResponse` 사용이 없다.
- Cloudflare 장시간 응답 회피는 StreamingResponse가 아니라 async start + polling 구조로 구현되어 있다.

### 7.2 Training analyze flow

Endpoint:

- `POST /sessions/{session_id}/training-analyze`

흐름:

1. JWT user 확인
2. session 존재 확인
3. session owner 확인
4. form field `chunk_meta`가 있으면 JSON parse 시도
5. multipart `audio` bytes를 메모리로 읽음
6. DML `/analyze-chunk`에 forwarding
7. DML response status code와 body status logging
8. DML body를 dict로 만들고 `run_id` 제거
9. response에 `session_id`, `chunk_meta` 추가
10. 반환

Training analyze timeout:

```python
_TRAINING_TIMEOUT = 25.0
```

전송 구조:

- URL: `f"{MODEL_SERVER_URL}/analyze-chunk"`
- client-facing field: `audio`
- DML-facing field: `file`
- files: `{"file": (audio.filename or "chunk.wav", audio_bytes, "audio/wav")}`
- data: optional `{"chunk_meta": chunk_meta}`

Crop/trim 여부:

- vocal-server 코드에는 audio crop/trim이 없다.
- 클라이언트가 보낸 chunk audio를 그대로 DML로 forwarding한다.

Error policy:

- DML 400:
  - DML JSON detail을 최대한 그대로 400으로 전달
- DML 500 이상:
  - 502 `분석 서버 오류`
- DML non-success 기타:
  - 502 `분석 서버 비정상 응답`
- timeout:
  - 504 `분석 서버 응답 시간 초과`
- request error:
  - 504 `분석 서버에 연결할 수 없음`
- JSON parse 실패:
  - 502 `분석 서버 응답 파싱 실패`

Training attempt 자동 저장:

- `body.get("status") == "success"`이고 `chunk_meta` parse에 성공했으며, `original_run_id`, `chunk_index`, `scores`가 있으면 `training_attempts`에 best-effort INSERT한다.
- 원본 run의 `result_json.timeline_scores[chunk_index].scores`에서 before score를 찾는다.
- DML after scores를 indicator별로 row 생성한다.
- 저장 실패 시 rollback하고 warning log만 남기며 응답 자체에는 영향 없음.

중요 caveat:

- 함수 description에는 “DB 저장 없이”라는 표현이 남아 있지만, 현재 dirty code에는 성공 시 `training_attempts` 자동 저장 로직이 있다. 설계서에는 현재 구현 기준으로 “응답은 pass-through지만 조건 충족 시 누적 시도는 best-effort 저장”이라고 쓰는 것이 정확하다.

## 8. Status와 polling 정책

### AnalysisRun status

모델 정의 주석에는 `queued / running / completed / failed`가 적혀 있지만, 실제 코드와 docs에서는 다음 값도 사용한다.

| status | 의미 |
|---|---|
| `queued` | 분석 접수됨, background task 대기 |
| `running` | background task가 DML 호출 중 |
| `success` | DML 정상 완료 |
| `completed` | 정상 완료 호환 값 |
| `no_voice` | 음성 없음/잡음 감지로 분석 스킵 |
| `failed` | 분석 실패 |
| `invalid` | docs에 언급됨. 코드상 별도 분기는 없고 DML body status가 그대로 저장될 수 있음 |
| `error` | docs에 언급됨. 코드상 별도 분기는 없고 DML body status가 그대로 저장될 수 있음 |

### Session status

| status | 의미 |
|---|---|
| `uploading` | 세션 생성 후 파일 업로드 전 |
| `uploaded` | 파일 업로드 완료 |
| `analyzing` | full analyze background task 진행 중 |
| `completed` | 세션 분석 완료 또는 no_voice 정상 처리 |
| `failed` | 세션 분석 실패 |
| `success` | DML status가 success일 때 session.status에도 들어갈 수 있음 |

### HTTP status와 body.status 구분

- HTTP status는 transport/API 성공 여부다.
- DML의 body `status`는 분석 의미 상태다.
- full analyze에서는 body `status`가 `AnalysisRun.status`로 저장된다.
- `GET /analysis/{run_id}/results`는 완료 전 호출해도 200을 반환할 수 있으나 `result_json`이 null일 수 있다.

설계서에 쓸 수 있는 정확한 문장:

> vocal-server는 정식 분석 요청을 즉시 처리 결과로 반환하지 않고, `AnalysisRun`을 `queued` 상태로 생성한 뒤 background task에서 DML 서버를 호출한다. 클라이언트는 `run_id`를 이용해 상태 endpoint를 polling하고, 분석이 terminal status에 도달한 뒤 결과 endpoint에서 `result_json`을 조회한다.

## 9. DB schema 상세

모든 model class는 `app/models/models.py`에 있다.

### 9.1 users

Class: `User`  
Table: `users`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `user_id` | UUID | false | `uuid.uuid4` | PK | 사용자 ID |
| `email` | String | false | 없음 | unique | 로그인 email |
| `password_hash` | String | false | 없음 | 없음 | bcrypt hash |
| `nickname` | String | false | 없음 | 없음 | 표시 이름 |
| `role` | String | false | `user` | 없음 | user/trainer/admin |
| `is_approved` | Boolean | false | true | 없음 | 승인 여부 |
| `created_at` | DateTime(tz) | false | `_utcnow` | 없음 | 생성 시각 |
| `updated_at` | DateTime(tz) | false | `_utcnow`, onupdate | 없음 | 수정 시각 |
| `last_seen_at` | DateTime(tz) | true | 없음 | 없음 | 마지막 활동 시각 |
| `last_endpoint` | String(100) | true | 없음 | 없음 | 마지막 활동 endpoint |

Relationship:

- `User.sessions`: `Session`, cascade all delete-orphan

### 9.2 sessions

Class: `Session`  
Table: `sessions`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `session_id` | UUID | false | `uuid.uuid4` | PK | 분석 세션 ID |
| `user_id` | UUID | false | 없음 | FK users.user_id ondelete CASCADE | 소유 사용자 |
| `song_id` | String(8) | true | 없음 | FK songs.id | 노래방 14곡 선택 |
| `song_title` | String | true | 없음 | 없음 | 자유 입력 곡명 |
| `status` | String | false | `uploading` | 없음 | 세션 상태 |
| `started_at` | DateTime(tz) | true | 없음 | 없음 | 시작 시각 |
| `ended_at` | DateTime(tz) | true | 없음 | 없음 | 종료 시각 |
| `created_at` | DateTime(tz) | false | `_utcnow` | 없음 | 생성 시각 |

Relationship:

- `user`: `User`
- `song`: `Song`
- `files`: `SessionFile`, cascade all delete-orphan
- `analysis_runs`: `AnalysisRun`, cascade all delete-orphan

### 9.3 session_files

Class: `SessionFile`  
Table: `session_files`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `file_id` | UUID | false | `uuid.uuid4` | PK | 파일 row ID |
| `session_id` | UUID | false | 없음 | FK sessions.session_id ondelete CASCADE | 소속 세션 |
| `file_type` | String | false | 없음 | 없음 | audio/piezo/accelerometer |
| `storage_uri` | String | false | 없음 | 없음 | 로컬 저장 경로 문자열 |
| `format` | String | true | 없음 | 없음 | wav/mp3/m4a 등 |
| `sample_rate_hz` | Integer | true | 없음 | 없음 | WAV sample rate |
| `duration_ms` | Integer | true | 없음 | 없음 | WAV duration |
| `file_size_bytes` | BigInteger | true | 없음 | 없음 | 파일 크기 |
| `uploaded_at` | DateTime(tz) | false | `_utcnow` | 없음 | 업로드 시각 |

Relationship:

- `session`: `Session`

### 9.4 analysis_runs

Class: `AnalysisRun`  
Table: `analysis_runs`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `run_id` | UUID | false | `uuid.uuid4` | PK | 분석 실행 ID |
| `session_id` | UUID | false | 없음 | FK sessions.session_id ondelete CASCADE | 소속 세션 |
| `model_name` | String | false | 없음 | 없음 | 모델 이름 |
| `model_version` | String | false | 없음 | 없음 | 모델 버전 |
| `status` | String | false | `queued` | 없음 | 분석 상태 |
| `requested_at` | DateTime(tz) | false | `_utcnow` | 없음 | 요청 시각 |
| `finished_at` | DateTime(tz) | true | 없음 | 없음 | 완료 시각 |
| `error_message` | Text | true | 없음 | 없음 | 실패 메시지 |
| `output_uri` | String | true | 없음 | 없음 | 출력 경로용 예비 필드 |
| `result_json` | JSONB | true | 없음 | 없음 | DML `/analyze` 응답 전체 |

Relationship:

- `session`: `Session`
- `results`: `AnalysisResult`, cascade all delete-orphan

### 9.5 analysis_results

Class: `AnalysisResult`  
Table: `analysis_results`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `result_id` | UUID | false | `uuid.uuid4` | PK | metric row ID |
| `run_id` | UUID | false | 없음 | FK analysis_runs.run_id ondelete CASCADE | 분석 실행 |
| `metric_key` | String | false | 없음 | 없음 | metric key |
| `metric_value` | Float | false | 없음 | 없음 | metric value |
| `unit` | String | true | 없음 | 없음 | 단위 |

Relationship:

- `analysis_run`: `AnalysisRun`

현재 full analyze가 저장하는 metric rows:

- `voiced_ratio`
- `processing_time_ms`
- `duration_sec`

### 9.6 reference_profiles

Class: `ReferenceProfile`  
Table: `reference_profiles`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `reference_id` | UUID | false | `uuid.uuid4` | PK | 기준 프로필 ID |
| `name` | String | false | 없음 | 없음 | 기준 이름 |
| `description` | Text | true | 없음 | 없음 | 설명 |
| `created_at` | DateTime(tz) | false | `_utcnow` | 없음 | 생성 시각 |
| `is_active` | Boolean | false | true | 없음 | 활성 기준 여부 |

Relationship:

- `metrics`: `ReferenceMetric`, cascade all delete-orphan

### 9.7 reference_metrics

Class: `ReferenceMetric`  
Table: `reference_metrics`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `reference_id` | UUID | false | 없음 | composite PK, FK reference_profiles.reference_id ondelete CASCADE | 기준 프로필 |
| `metric_key` | String | false | 없음 | composite PK | 지표 key |
| `mean_value` | Float | false | 없음 | 없음 | 기준 평균 |
| `std_value` | Float | false | 없음 | 없음 | 기준 표준편차 |

Relationship:

- `profile`: `ReferenceProfile`

### 9.8 songs

Class: `Song`  
Table: `songs`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `id` | String(8) | false | 없음 | PK | `"001"`~`"014"` 곡 ID |
| `artist` | String(255) | false | 없음 | 없음 | 가수 |
| `title` | String(255) | false | 없음 | 없음 | 곡명 |
| `master_filename` | String(255) | true | 없음 | 없음 | 원곡 filename |
| `mr_filename` | String(255) | true | 없음 | 없음 | MR filename |
| `master_duration_sec` | Float | true | 없음 | 없음 | 원곡 길이 |
| `mr_duration_sec` | Float | true | 없음 | 없음 | MR 길이 |
| `lrc_offset_sec` | Float | true | 없음 | 없음 | LRC offset |
| `alignment_status` | String(20) | true | 없음 | 없음 | alignment 상태 |
| `has_lrc` | Boolean | false | false | server_default false | LRC 준비 여부 |
| `has_pitch_guide` | Boolean | false | false | server_default false | pitch guide 준비 여부 |
| `created_at` | DateTime(tz) | false | `_utcnow` | 없음 | 생성 시각 |
| `updated_at` | DateTime(tz) | false | `_utcnow`, onupdate | 없음 | 수정 시각 |

Relationship:

- `sessions`: `Session`

### 9.9 training_attempts

Class: `TrainingAttempt`  
Table: `training_attempts`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `attempt_id` | UUID | false | `uuid.uuid4` | PK | 시도 ID |
| `user_id` | UUID | false | 없음 | FK users.user_id ondelete CASCADE | 사용자 |
| `session_id` | UUID | true | 없음 | FK sessions.session_id ondelete SET NULL | 세션 |
| `original_run_id` | UUID | true | 없음 | FK analysis_runs.run_id ondelete SET NULL | 원본 분석 |
| `chunk_index` | Integer | false | 없음 | 없음 | 청크 index |
| `chunk_start_sec` | Float | false | 없음 | 없음 | 청크 시작 초 |
| `chunk_end_sec` | Float | false | 없음 | 없음 | 청크 끝 초 |
| `indicator_key` | String(50) | false | 없음 | 없음 | 지표 key |
| `before_ai_score` | Float | true | 없음 | 없음 | 훈련 전 ai score |
| `before_rounded_score` | Integer | true | 없음 | 없음 | 훈련 전 rounded score |
| `before_zone` | String(20) | true | 없음 | 없음 | 훈련 전 zone |
| `after_ai_score` | Float | false | 없음 | 없음 | 훈련 후 ai score |
| `after_rounded_score` | Integer | false | 없음 | 없음 | 훈련 후 rounded score |
| `after_zone` | String(20) | false | 없음 | 없음 | 훈련 후 zone |
| `attempted_at` | DateTime(tz) | false | `_utcnow` | 없음 | 시도 시각 |

Indexes:

- `idx_training_attempts_user_attempted`
- `idx_training_attempts_user_indicator`
- `idx_training_attempts_user_original_run`

### 9.10 training_favorites

Class: `TrainingFavorite`  
Table: `training_favorites`

| field | type | nullable | default | key/constraint | 의미 |
|---|---|---|---|---|---|
| `favorite_id` | UUID | false | `uuid.uuid4` | PK | 즐겨찾기 ID |
| `user_id` | UUID | false | 없음 | FK users.user_id ondelete CASCADE | 사용자 |
| `song_id` | String(8) | false | 없음 | FK songs.id | 곡 ID |
| `original_run_id` | UUID | true | 없음 | FK analysis_runs.run_id ondelete SET NULL | 원본 분석 |
| `chunk_index` | Integer | false | 없음 | 없음 | 청크 index |
| `chunk_start_sec` | Float | false | 없음 | 없음 | 청크 시작 초 |
| `chunk_end_sec` | Float | false | 없음 | 없음 | 청크 끝 초 |
| `chunk_lrc_text` | Text | true | 없음 | 없음 | 청크 가사 |
| `indicator_key` | String(50) | false | 없음 | 없음 | 지표 key |
| `created_at` | DateTime(tz) | false | `_utcnow` | 없음 | 생성 시각 |

Constraints:

- unique: `user_id`, `song_id`, `chunk_index`, `indicator_key`

Indexes:

- `idx_training_favorites_user_created`

### 9.11 ERD 설명

설계서용 관계 요약:

```text
User 1 ── N Session
Session 1 ── N SessionFile
Session 1 ── N AnalysisRun
AnalysisRun 1 ── N AnalysisResult
Song 1 ── N Session
ReferenceProfile 1 ── N ReferenceMetric
User 1 ── N TrainingAttempt
User 1 ── N TrainingFavorite
Song 1 ── N TrainingFavorite
AnalysisRun 1 ── N TrainingAttempt / TrainingFavorite (nullable, SET NULL)
```

## 10. Migration 이력

Alembic 위치:

- `vocal-server/alembic/env.py`
- `vocal-server/alembic/versions/`

Migration files:

| Revision | 내용 |
|---|---|
| `3a6386a215ec` | `analysis_runs.result_json` JSONB 추가, `users.is_approved` 추가 |
| `a1b2c3d4e5f6` | 기존 songs table drop 후 새 songs table 생성, `sessions.song_id` FK 추가 |
| `fd55a51eef83` | `training_attempts`, `training_favorites` 생성 |
| `9a253a587cb6` | `users.last_seen_at`, `users.last_endpoint` 추가 |

주의:

- `alembic/env.py`는 `DATABASE_URL` env를 필수로 읽는다.
- 실제 env 값은 출력하지 않았다.

## 11. File/audio 처리

### UploadFile 저장

Endpoint:

- `POST /sessions/{session_id}/files`

저장 위치:

```text
app/storage/users/{user_id}/sessions/{session_id}/{filename}
```

처리:

1. session 존재/권한 확인
2. 저장 directory 생성
3. upload file bytes 읽기
4. 파일 write
5. 확장자 계산
6. WAV이면 `wave` module로 sample rate와 duration 계산 시도
7. `SessionFile` row 생성
8. session status를 `uploaded`로 변경

특징:

- WAV 파싱 실패해도 업로드는 진행한다.
- 파일 삭제/quarantine 로직은 확인되지 않았다.
- 저장된 `storage_uri`는 실제 로컬 path 문자열이다.

### Full analyze forwarding

- DB에 저장된 `SessionFile.storage_uri`를 다시 열어 DML `/analyze`에 전달한다.
- file field name은 `file`이다.

### Training analyze forwarding

- client field name은 `audio`다.
- vocal-server가 DML로 보낼 때 field name을 `file`로 바꾼다.
- 별도 저장 없이 bytes를 바로 DML `/analyze-chunk`에 보낸다.
- crop/trim은 하지 않는다.

## 12. Songs asset API와 storage 구조

관련 파일:

- `app/routers/songs.py`
- `app/storage/songs/meta/songs.json`
- `app/storage/songs/audio/mr/`
- `app/storage/songs/lrc/parsed/`
- `app/storage/songs/pitch_guide/`

### Endpoint별 source

| Endpoint | Source |
|---|---|
| `GET /songs` | DB `songs` table |
| `GET /songs/{id}/lrc` | `app/storage/songs/lrc/parsed/{id}.json` |
| `GET /songs/{id}/pitch-guide` | `app/storage/songs/pitch_guide/{id}.json` |
| `GET /songs/{id}/mr` | DB `Song.mr_filename` + `app/storage/songs/audio/mr/{filename}` |

`meta/songs.json`은 현재 API source가 아니다. seed/sync용 asset meta로 보는 것이 맞다.

### 5곡 상태 확인

`meta/songs.json` 기준 14곡이 존재한다. 요청된 5곡 상태:

| id | artist | title | has_lrc | has_pitch_guide | MR | LRC | Pitch |
|---|---|---|---|---|---|---|---|
| 002 | 윤하 | 기다리다 | true | true | 있음 | 있음 | 있음 |
| 004 | 김범수 | 보고싶다 | true | true | 있음 | 있음 | 있음 |
| 006 | 폴킴 | 모든 날 모든 순간 | true | true | 있음 | 있음 | 있음 |
| 007 | 지아 | 물론 | true | true | 있음 | 있음 | 있음 |
| 014 | 성시경 | 너의 모든 순간 | true | true | 있음 | 있음 | 있음 |

LRC shape:

- list
- 주요 key: `time_start`, `time_end`, `text`
- 일부 파일에는 `placeholder` key도 있다.

Pitch guide shape:

- object
- 주요 key:
  - `song_id`
  - `duration_sec`
  - `frame_hz`
  - `lrc_offset_sec`
  - `guide_source`
  - `production_status`
  - `midi_segments`
  - `points`
  - `meta`

MR:

- `FileResponse`
- media type: `audio/mpeg`
- range request는 TODO로 남아 있고 현재 직접 구현은 없다.

## 13. Admin 기능

관련 파일:

- `app/routers/admin.py`
- `app/templates/admin/login.html`
- `app/templates/admin/users.html`
- `app/templates/admin/user_detail.html`
- `app/templates/admin/logs.html`
- `app/middleware/activity_tracker.py`
- `app/event_store.py`
- `app/state.py`
- `docs/admin_reference.md`

### Phase A 구현 목록

- admin login/logout
- admin password auth
- IP rate limit
- users page
- user detail page
- signup toggle
- logs page
- events polling
- online users API
- ActivityTrackerMiddleware
- SSE endpoint deprecated

### Admin endpoint 요약

| Endpoint | 기능 | Auth |
|---|---|---|
| `GET /admin` | login redirect | 없음 |
| `GET /admin/health` | admin health | 없음 |
| `GET /admin/login` | login page | 없음 |
| `POST /admin/login` | password form submit | 없음, rate limit |
| `POST /admin/logout` | session clear | admin session |
| `GET /admin/users` | 사용자 목록 HTML | admin session |
| `GET /admin/users/{user_id}` | 사용자 상세 HTML | admin session |
| `GET /admin/api/users` | 전체 user JSON | admin session |
| `GET /admin/users/{user_id}/sessions` | 특정 user session JSON | admin session |
| `POST /admin/signup-toggle` | signup on/off toggle | admin session |
| `GET /admin/logs` | logs HTML | admin session |
| `GET /admin/api/events` | polling events JSON | admin session |
| `GET /admin/api/online-users` | online users JSON | admin session |
| `GET /admin/events/stream` | 410 Gone | admin session |
| `GET /admin/dashboard` | legacy dashboard | admin session |

### SSE에서 polling으로 전환

- `event_store.py`에는 SSE subscriber 함수가 남아 있다.
- 하지만 실제 route `/admin/events/stream`은 410 Gone을 반환한다.
- Cloudflare Tunnel에서 long-lived connection이 불안정해 polling으로 대체했다는 설명이 docs에 있다.
- 현재 권장 흐름은 `/admin/logs` page가 `/admin/api/events`를 polling하는 구조다.

### Activity tracking

Middleware:

- `ActivityTrackerMiddleware`

추적 대상:

- 인증된 일반 사용자 요청만
- JWT Bearer token에서 user_id를 추출

추적 제외:

- `/admin`
- `/health`
- `/docs`
- `/openapi.json`
- `/redoc`
- `/static`

Throttle:

- 같은 user + 같은 endpoint
- 5분 이내면 DB UPDATE skip
- 메모리 cache 기반

경로 정규화:

- UUID -> `{id}`
- 12자리 이상 hex -> `{id}`
- `/songs/\d{3}` -> `/songs/{id}`

저장 field:

- `users.last_seen_at`
- `users.last_endpoint`

### Known limitations

- Event store는 메모리 deque라 서버 재시작 시 초기화된다.
- Signup toggle도 메모리 상태라 서버 재시작 시 env 값으로 reset된다.
- Admin Phase B용 JSON endpoint가 일부 부족하다.
- `docs/admin_reference.md`는 Phase B에서 추가 필요 endpoint를 별도 요청 사항으로 정리해 두었다.

## 14. Dirty file diff 요약

현재 dirty 파일은 설계서에 반영할 필요가 있는 변경을 포함한다.

### 14.1 `vocal-server/PROGRESS.md`

Changed area:

- 2026-05-15 production `training-analyze` 504 계측/timeout 보정 기록 추가
- full analyze async start + polling 전환 기록 추가

Meaning:

- training analyze timeout이 10초에서 25초로 조정된 이유가 기록됨
- full analyze가 blocking에서 background task/polling 구조로 바뀐 배경이 기록됨

Design doc impact:

- 분석 흐름 설명에 async polling 구조를 반영해야 한다.
- timeout 정책에 full analyze 180초, training analyze 25초를 구분해야 한다.

Risk:

- 문서 변경이므로 직접 runtime risk는 낮다.

### 14.2 `vocal-server/app/routers/analysis.py`

Changed area:

- `BackgroundTasks` import 추가
- `run_analysis` 직접 호출 제거
- `run_analysis_by_ids` background task 등록
- endpoint description을 비동기/polling 설명으로 변경

Meaning:

- `POST /sessions/{session_id}/analyze`가 DML 완료를 기다리지 않고 즉시 `{run_id, status:"queued"}`를 반환한다.

Design doc impact:

- 반드시 반영해야 한다.
- 앱 흐름은 POST analyze 후 바로 결과 화면이 아니라 polling이다.

Risk:

- background task 실패는 즉시 POST response로 알 수 없다.
- app은 polling과 results 조회 흐름을 정확히 따라야 한다.

### 14.3 `vocal-server/app/services/analysis_service.py`

Changed area:

- `run_analysis_by_ids(run_id, session_id)` 추가
- background task에서 새 `SessionLocal()` DB session을 열어 run/session 재조회
- background task 실패 시 `AnalysisRun.status="failed"`, `result_json` error shape 저장 시도

Meaning:

- request DB session에 묶이지 않고 background task에서 독립적으로 분석을 수행한다.

Design doc impact:

- full analyze 저장/상태 전이 흐름에 포함해야 한다.

Risk:

- background task 자체는 process memory에서 실행되므로 서버 프로세스가 죽으면 job queue durability는 없다.
- 별도 queue 시스템은 아니다.

### 14.4 `vocal-server/app/routers/sessions.py`

Changed area:

- `_TRAINING_TIMEOUT = 10.0` -> `25.0`
- elapsed timing logging 추가
- timeout/request error/response/body status logging 추가

Meaning:

- production에서 약 11초 후 504가 나던 training-analyze timeout 문제를 완화한다.

Design doc impact:

- training analyze timeout은 25초로 작성해야 한다.

Risk:

- timeout이 늘어 app/network timeout과의 관계를 맞춰야 한다.
- retry는 여전히 없다.

### 14.5 `vocal-server/docs/api.md`

Changed area:

- training-analyze timeout 25초 설명 추가
- full analyze를 async start endpoint로 문서화
- polling 권장 flow 추가

Meaning:

- API 문서가 현재 코드 흐름을 따라가도록 수정 중이다.

Design doc impact:

- 설계서에는 async/polling 버전을 반영해야 한다.

Risk:

- 문서 내부에 아직 과거 문장 “현재 분석은 동기 처리”가 남아 있어 불일치가 있다.

### 14.6 `vocal-server/app/routers/admin.py`

Changed area:

- admin users page에 search, page limit, cursor pagination 지원 추가
- cursor encode/decode helper 추가
- `q`, `limit`, `cursor` query 처리 추가

Meaning:

- 운영자 사용자 목록이 전체 로딩에서 페이지 단위 조회로 개선되는 중이다.

Design doc impact:

- Admin 기능 설명에 검색/페이지네이션이 들어가도 된다. 단 dirty 상태이므로 최종 merge 전이면 “현재 작업 중 변경”으로 표시하는 것이 안전하다.

Risk:

- 아직 테스트 실행 결과는 확인하지 않았다.

### 14.7 `vocal-server/app/templates/admin/users.html`

Changed area:

- 검색 input
- page size select
- 다음 페이지 button
- responsive style 추가

Meaning:

- admin users UI가 검색/페이지네이션을 지원한다.

Design doc impact:

- Admin Phase A 기능 목록에 반영 가능하다.

Risk:

- UI 동작은 서버 실행 금지 조건 때문에 브라우저로 검증하지 않았다.

### 14.8 untracked `.bak-*`, root `app/`, `.codex/`, `backups/`

Meaning:

- 현재 worktree에 추적되지 않은 보조/백업/루트 파일이 있다.

Design doc impact:

- 일반 설계서에는 포함하지 않는 것이 좋다.

Risk:

- 커밋/배포 시 실수로 포함하지 않도록 주의가 필요하다.

## 15. Tests 확인

확인된 test file:

- `vocal-server/test_integration.py`

커버 범위:

- signup
- login
- session create
- WAV upload
- analyze request
- analysis run 조회
- analysis results 조회
- session list/detail
- cross-user 403
- 없는 session_id 404
- invalid token 401
- no token 401
- song_id session cases

누락 또는 약한 영역:

- pytest 구조 없음
- `tests/` directory 없음
- admin auth/page/API test 없음
- training-analyze `/analyze-chunk` test 없음
- training attempts/favorites test 없음
- async polling terminal transition test 없음
- no_voice/error status handling test 없음
- songs asset endpoints 직접 호출 test 부족

이번 감사에서는 server restart 금지 조건 때문에 테스트는 실행하지 않았다.

## 16. 문서와 코드 불일치/주의 사항

1. `docs/api.md`는 full analyze async 전환을 설명하지만, 뒤쪽 “폴링 가이드” 섹션에 아직 “현재 분석은 동기 처리” 문장이 남아 있다.
2. `sessions.py` training-analyze endpoint description에는 “DB 저장 없이”가 남아 있지만, 현재 코드에는 `training_attempts` best-effort 자동 저장이 있다.
3. `models.py`의 `AnalysisRun.status` 주석은 `queued/running/completed/failed`만 언급하지만, 실제 코드는 `success`, `no_voice` 등 DML body status를 그대로 저장할 수 있다.
4. `admin.py`의 activity label map에는 `GET /analysis/{id}/user_f0`가 있지만 실제 route는 없다.
5. `event_store.py`에는 SSE subscribe/unsubscribe 함수가 남아 있지만 실제 SSE endpoint는 410 Gone이다.
6. `/ws/realtime`은 실제 route가 없다.
7. `target_chunks` route는 실제 route가 없다.

## 17. 설계서에 넣을 추천 문장

### vocal-server 역할

vocal-server는 Expo 앱과 DML 추론 서버 사이의 FastAPI 백엔드로, 사용자 인증, 세션/파일 관리, 분석 요청 접수, 분석 결과 저장, 곡 asset 제공, 훈련 기록/즐겨찾기 및 운영자 관리 화면을 담당한다.

### 분석 흐름

앱은 세션 생성과 파일 업로드 후 `POST /sessions/{session_id}/analyze`로 분석을 접수하고, 서버는 즉시 `run_id`와 `status="queued"`를 반환한다. 실제 DML 분석은 FastAPI background task에서 수행되며, 앱은 `GET /analysis/{run_id}`로 상태를 polling하고 terminal status에서 `GET /analysis/{run_id}/results`를 호출해 결과 JSON을 조회한다.

### DML 연동

정식 full analyze는 저장된 업로드 파일을 DML 서버의 `/analyze` endpoint에 multipart file로 전달하며, `run_id`와 선택된 `song_id`를 함께 전달한다. TrainingScreen 사후 측정은 클라이언트가 보낸 청크 audio를 별도 저장 없이 DML 서버의 `/analyze-chunk` endpoint에 forwarding한다.

### DB 저장

DML full analyze 응답은 `analysis_runs.result_json` JSONB 컬럼에 원문 형태로 저장하고, `voiced_ratio`, `processing_time_ms`, `duration_sec` 같은 핵심 metric 일부는 `analysis_results`에 별도 row로 저장한다. TrainingScreen 사후 측정이 성공하고 `chunk_meta`에 원본 분석 run과 chunk 정보가 있으면 `training_attempts`에 best-effort로 누적 시도를 저장한다.

### 운영/배포

운영 노출은 Cloudflare Tunnel 뒤 FastAPI 서버 구조이며, 장시간 DML 분석 응답으로 인한 Cloudflare timeout을 피하기 위해 full analyze는 async start + polling 방식으로 구현되어 있다. Admin 기능은 별도 admin session cookie와 password form login을 사용하며, 사용자 활동 추적과 polling 기반 운영 로그 화면을 제공한다.

### 보안

일반 사용자 API는 Bearer JWT 인증을 사용하며, 비밀번호는 bcrypt hash로 저장한다. Admin 화면은 `ADMIN_PASSWORD`와 `ADMIN_SESSION_SECRET` 기반의 별도 세션 인증을 사용하고, login 실패에 대해 IP 기준 메모리 rate limit을 적용한다.

## 18. 최종 한계와 확인 필요 사항

설계서 작성 시 “구현됨”이라고 쓰면 안 되는 항목:

- `/ws/realtime`
- `target_chunks`
- `/analysis/{id}/user_f0`
- StreamingResponse 기반 full analyze 처리
- durable job queue
- 파일 삭제/quarantine 정책
- admin Phase B React용 상세 JSON endpoint 다수

추가 확인이 필요한 항목:

- 실제 production DB에 migration이 모두 적용되어 있는지
- dirty 변경이 최종 배포/커밋된 상태인지
- DML 서버의 `/analyze`, `/analyze-chunk` response schema 최신 버전
- 앱이 async polling flow를 이미 반영했는지
- training attempts 자동 저장이 product 요구사항과 일치하는지
