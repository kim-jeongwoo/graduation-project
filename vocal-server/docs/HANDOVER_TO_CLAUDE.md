# HANDOVER_TO_CLAUDE.md

작성 기준: `/Users/kimjeongwoo/vocal-server/vocal-server`

작성 목적: Claude 작업공간 이전용 Phase A admin 코드 상태 문서. 이 문서는 저장소를 직접 읽어 확인한 사실만 기록한다. 확인하지 못한 내용은 `[불확실]`로 표기한다.

주의:
- secret/env 값은 기록하지 않는다. 환경 변수는 key 이름만 적는다.
- DB update, production deploy/restart, Cloudflare/DNS/Tunnel 변경은 수행하지 않았다.
- 이 문서 작성 전 확인한 admin 관련 미커밋 diff는 없었다.

## 1. 저장소 구조 + 기술 스택

### 기준 구조

git 루트는 `/Users/kimjeongwoo/vocal-server`이고, 실제 FastAPI 백엔드 기준 경로는 `/Users/kimjeongwoo/vocal-server/vocal-server`이다.

기준 경로의 주요 파일:

```text
vocal-server/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── event_store.py
│   ├── state.py
│   ├── middleware/activity_tracker.py
│   ├── models/models.py
│   ├── routers/admin.py
│   ├── routers/auth.py
│   ├── routers/sessions.py
│   ├── routers/analysis.py
│   ├── routers/training.py
│   └── templates/admin/
│       ├── login.html
│       ├── users.html
│       ├── user_detail.html
│       └── logs.html
├── docs/
│   ├── admin_reference.md
│   ├── api.md
│   └── vocal_server_code_audit_2026-06-16.md
├── scripts/
│   ├── restart_server.sh
│   └── signup_toggle.sh
└── requirements.txt
```

admin 관련 백업 파일도 존재한다.

- `app/routers/admin.py.bak-20260524-003229`
- `app/templates/admin/users.html.bak-20260524-003229`

이 백업 파일들은 현재 라우터 등록 대상이 아니다.

### 프레임워크

- FastAPI 앱: `app/main.py`의 `app = FastAPI(title="Vocal Server", version="0.1.0")`
- admin 라우터: `app/routers/admin.py`의 `router = APIRouter(prefix="/admin", tags=["admin"])`
- 템플릿 렌더링: `Jinja2Templates(directory="app/templates")`
- DB ORM: SQLAlchemy
- DB 마이그레이션 도구: Alembic 파일 존재
- 세션 쿠키: Starlette `SessionMiddleware`
- HTML UI: Bootstrap CDN을 템플릿에서 참조

### 주요 라이브러리

`requirements.txt` 기준 패키지명:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `psycopg2-binary`
- `python-dotenv`
- `alembic`
- `bcrypt`
- `python-jose[cryptography]`
- `python-multipart`
- `pydantic[email]`
- `httpx`
- `itsdangerous`
- `jinja2`

### 확인 가능한 버전

- 애플리케이션 버전: `0.1.0` (`app/main.py`)
- 패키지 버전: `requirements.txt`에는 pinning된 버전이 없다.
- `CLAUDE.md`에는 FastAPI와 uvicorn 버전 설명이 있으나, lockfile 또는 requirements pin으로 재확인되지는 않았다. `[불확실]`

## 2. 페이지/기능 목록

admin 라우트는 모두 `app/routers/admin.py`에 있다.

| Method | Path | 함수 | 유형 | 인증 | 역할 |
| --- | --- | --- | --- | --- | --- |
| GET | `/admin` | `admin_root` | Redirect | 없음 | `/admin/login`으로 이동 |
| GET | `/admin/health` | `admin_health` | JSON | 없음 | admin health check |
| GET | `/admin/login` | `login_page` | HTML | 없음 | 비밀번호 로그인 폼 |
| POST | `/admin/login` | `login_submit` | Redirect | 없음 | admin password 검증, 세션 생성, rate limit 처리 |
| POST | `/admin/logout` | `logout` | Redirect | 없음 | 현재 세션 clear 후 로그인으로 이동 |
| GET | `/admin/api/users` | `list_all_users_json` | JSON | `require_admin_auth` | 전체 사용자 목록 JSON, `AdminUserResponse` |
| GET | `/admin/users` | `list_all_users_page` | HTML | `require_admin_auth` | 사용자 목록, 검색, 테스트 계정 표시 토글, cursor pagination |
| POST | `/admin/signup-toggle` | `toggle_signup` | Redirect | `require_admin_auth` | 메모리 기반 회원가입 on/off 토글 |
| GET | `/admin/users/{user_id}` | `get_user_detail` | HTML | `require_admin_auth` | 사용자 상세, 세션/즐겨찾기/누적 시도 탭 |
| GET | `/admin/users/{user_id}/sessions` | `list_user_sessions` | JSON | `require_admin_auth` | 특정 사용자의 세션 목록 |
| GET | `/admin/events` | `list_events` | JSON | `require_admin_auth` | 이벤트 목록, legacy compatibility |
| GET | `/admin/logs` | `logs_page` | HTML | `require_admin_auth` | 5초 polling 로그 화면 |
| GET | `/admin/api/events` | `api_events` | JSON | `require_admin_auth` | `limit`, `since` 기반 이벤트 polling API |
| GET | `/admin/api/online-users` | `api_online_users` | JSON | `require_admin_auth` | 5분 이내 활동 사용자 목록 |
| GET | `/admin/events/stream` | `event_stream_deprecated` | JSON error | `require_admin_auth` | SSE 폐기. 410 Gone 반환 |
| GET | `/admin/dashboard` | `dashboard` | HTML 문자열 | `require_admin_auth` | legacy dashboard HTML |

HTML 페이지:

- `app/templates/admin/login.html`: admin password 입력 폼, rate limit/error 표시.
- `app/templates/admin/users.html`: 사용자 목록, 검색 입력 `q`, 페이지 크기 `limit`, 테스트 계정 표시 `show_test`, 다음 페이지 링크.
- `app/templates/admin/user_detail.html`: 사용자 정보, 분석 세션, 즐겨찾기, 누적 시도 탭.
- `app/templates/admin/logs.html`: 최근 signup/login 이벤트와 online users를 polling.
- `app/routers/admin.py`의 `_DASHBOARD_HTML`: legacy dashboard. 내부 JS는 `/admin/events/stream` SSE를 호출하지만 해당 endpoint는 410 Gone이다.

JSON endpoint:

- `/admin/health`
- `/admin/api/users`
- `/admin/users/{user_id}/sessions`
- `/admin/events`
- `/admin/api/events`
- `/admin/api/online-users`
- `/admin/events/stream`은 JSON error 성격의 410 endpoint

deprecated/410 endpoint:

- `GET /admin/events/stream`: 코드 주석과 docstring 기준 Cloudflare Tunnel long-lived connection 문제로 SSE를 폐기하고 `/admin/logs` + `/admin/api/events` polling으로 대체했다.

## 3. 인증/권한

### admin 로그인 방식

admin web 인증은 일반 사용자 계정과 별개다.

- `POST /admin/login`은 form field `password`를 받는다.
- 비교 대상은 환경 변수 key `ADMIN_PASSWORD`이다. 값은 기록하지 않는다.
- 성공 시 `request.session["admin_authenticated"] = True`와 `request.session["admin_logged_in_at"]`을 설정한다.
- 실패 시 IP별 메모리 rate limit 카운트를 기록하고 `/admin/login?error=invalid_password`로 redirect한다.
- 5분 윈도우에서 5회 이상 실패하면 5분 차단 로직이 작동한다.

### 세션 방식

`app/main.py`의 `SessionMiddleware` 설정:

- session cookie name: `admin_session`
- secret key env: `ADMIN_SESSION_SECRET`
- max age: 24시간
- `https_only=True`
- `same_site="lax"`

세션 secret의 fallback 문자열이 코드에 존재하지만, 이 문서에는 secret 값 또는 fallback 값을 기록하지 않는다.

### `require_admin_auth` 적용 범위

`require_admin_auth(request)`는 `request.session.get("admin_authenticated")`가 없으면 401과 `Location: /admin/login` 헤더를 반환한다.

적용된 endpoint:

- `/admin/api/users`
- `/admin/users`
- `/admin/signup-toggle`
- `/admin/users/{user_id}`
- `/admin/users/{user_id}/sessions`
- `/admin/events`
- `/admin/logs`
- `/admin/api/events`
- `/admin/api/online-users`
- `/admin/events/stream`
- `/admin/dashboard`

### 인증 제외 endpoint

- `GET /admin`
- `GET /admin/health`
- `GET /admin/login`
- `POST /admin/login`
- `POST /admin/logout`

`POST /admin/logout`은 dependency가 없고, 호출 시 session clear 후 `/admin/login`으로 redirect한다.

### 일반 사용자 계정 체계와의 연결

일반 사용자 인증:

- `POST /auth/signup`: `User` row 생성, bcrypt password hash 저장, JWT 발급.
- `POST /auth/login`: email/password 확인 후 JWT 발급.
- JWT 생성/검증은 `app/deps.py`에서 `SECRET_KEY`, `ALGORITHM`, `JWT_EXPIRE_DAYS` key를 사용한다.

admin web 로그인:

- `User` 테이블의 `role` 또는 `is_approved`를 검사하지 않는다.
- admin password는 `users` 테이블의 password와 연결되어 있지 않다.
- `User.role`에는 `user / trainer / admin` 주석이 있으나 admin web 권한 판단에는 사용되지 않는다.
- `User.is_approved` 필드는 존재하지만 `POST /auth/login` 또는 admin web auth에서 확인되지 않는다.

확인되지 않은 계정 체계:

- `User.role == "admin"`을 admin web 권한으로 사용하는 흐름은 admin 코드 기준 확인되지 않음.
- 별도 admin 사용자 테이블은 admin 코드 기준 확인되지 않음.

## 4. vocal-server API/DB 사용부

### admin이 직접 사용하는 내부 함수/상태

`app/routers/admin.py`:

- `get_db`: SQLAlchemy DB session dependency.
- `get_events`: 인메모리 이벤트 조회.
- `app_state.signup_enabled`: 회원가입 활성 상태.
- `_format_activity`: endpoint label 한글화.
- `_format_status`, `_status_badge_class`: session status 표시용.
- `_relative_time`, `_activity_status`: 활동 시각과 온라인 상태 표시.
- `_parse_admin_users_limit`: `limit` 파싱, 기본 50, 최대 100.
- `_encode_admin_users_cursor`, `_decode_admin_users_cursor`: 사용자 목록 keyset pagination cursor.
- `get_client_ip`, `check_rate_limit`, `record_failed_attempt`, `reset_attempts`: admin login rate limit.

### admin이 직접 사용하는 DB 모델

`app/routers/admin.py` import 기준:

- `User`
- `Session`
- `Song`
- `TrainingAttempt`
- `TrainingFavorite`
- `AnalysisRun`은 import되어 있지만 현재 admin route 본문에서 직접 query하는 흐름은 확인되지 않았다.

직접 query되는 주요 테이블:

- `users`
- `sessions`
- `songs`
- `training_attempts`
- `training_favorites`

### admin이 제공하는 endpoint 전체

admin route 전체는 2번 섹션의 표와 같다. admin 라우터는 외부 모델 서버를 직접 호출하지 않는다. 모델 서버 호출은 일반 사용자 API 쪽 `sessions.py`와 `analysis_service.py`에서 수행된다.

### 사용하는 `User` 필드

admin UI/API에서 직접 사용하는 필드:

- `user_id`
- `email`
- `nickname`
- `created_at`
- `last_seen_at`
- `last_endpoint`

모델에는 있으나 admin web auth에는 연결되지 않은 필드:

- `password_hash`
- `role`
- `is_approved`
- `updated_at`

### 활동 추적 필드

`app/middleware/activity_tracker.py`:

- 요청 인증 헤더의 JWT를 decode한다.
- `/admin`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/static` prefix는 추적 제외한다.
- 추적 대상이면 path의 UUID/hex/song id를 `{id}`로 정규화한다.
- 같은 user + 같은 endpoint는 5분 내 DB update를 skip한다.
- `users.last_seen_at`, `users.last_endpoint`를 update한다.
- 캐시는 메모리 기반이다.

admin 화면에서 이 필드는 다음에 사용된다.

- `/admin/users`: 상태 badge, 마지막 활동, 활동 label, 접속 중 count.
- `/admin/users/{user_id}`: 사용자 상세 상단 활동 정보.
- `/admin/api/online-users`: 5분 이내 활동한 사용자 목록.

### 이벤트/로그 저장 구조

`app/event_store.py`:

- `_events`: `deque(maxlen=50)` 메모리 저장소.
- event shape: `timestamp`, `event_type`, `nickname`, `email`.
- `event_type`은 코드상 `signup`, `login`이 사용된다.
- `add_event`는 `_events.appendleft(event)` 후 `_subscribers` queue에도 push를 시도한다.
- `get_events()`는 최신순 list를 반환한다.
- `subscribe`/`unsubscribe` 함수가 남아 있지만 현재 `/admin/events/stream`은 410 Gone이므로 실사용 SSE 흐름은 admin 코드 기준 확인되지 않는다.

이벤트 발생 위치:

- `app/routers/auth.py`의 `signup`: 가입 성공 후 `add_event("signup", ...)`.
- `app/routers/auth.py`의 `login`: 로그인 성공 후 `add_event("login", ...)`.

## 5. 평가자 채점 관련 기능

admin 코드 기준 수동 평가자 채점 저장 endpoint, 평가자 계정, 평가자 assignment, reviewer score table은 확인되지 않았다.

확인된 점수 관련 기능은 AI 분석/훈련 시도 기록 표시다.

### TrainingAttempt 저장 흐름

`POST /sessions/{session_id}/training-analyze` (`app/routers/sessions.py`)에서 확인된 흐름:

1. 일반 사용자 JWT 인증으로 현재 사용자를 확인한다.
2. 업로드된 chunk audio를 DML 서버 `/analyze-chunk`로 전달한다.
3. `chunk_meta`를 JSON으로 파싱한다.
4. DML 응답 `body.status == "success"`이고 `chunk_meta`에 `original_run_id`, `chunk_index`가 있으며 응답 `scores`가 있으면 best-effort로 누적 시도를 저장한다.
5. 원본 `AnalysisRun.result_json.timeline_scores[chunk_index].scores`에서 before score를 읽는다.
6. DML 응답 `scores`의 indicator별 after score를 순회하며 `TrainingAttempt` row를 생성한다.
7. 저장 실패 시 rollback하고 경고 로그만 남기며, API 응답 자체에는 영향을 주지 않는다.

저장 필드:

- `user_id`
- `session_id`
- `original_run_id`
- `chunk_index`
- `chunk_start_sec`
- `chunk_end_sec`
- `indicator_key`
- `before_ai_score`
- `before_rounded_score`
- `before_zone`
- `after_ai_score`
- `after_rounded_score`
- `after_zone`
- `attempted_at`

admin 표시 흐름:

- `/admin/users/{user_id}`는 `TrainingAttempt`를 `attempted_at desc` 기준 최근 100개 조회한다.
- `improvement = after_ai_score - before_ai_score`로 계산한다.
- `user_detail.html`의 "누적 시도" 탭에 시점, 구간, 항목, 전/후 점수, 변화량을 표시한다.

평가자 채점 관련 결론:

- "평가자 채점"이라는 별도 human/manual scoring 기능은 admin 코드 기준 확인되지 않음.
- `docs/admin_reference.md`에는 Phase B용 점수 추이/사용자 비교 endpoint 요청안이 있으나 현재 admin 라우터에는 해당 endpoint가 없다.

## 6. 빌드/배포

### admin.vocal-fit.com 배포 방식

저장소 문서 기준:

- `https://api.vocal-fit.com`과 `https://admin.vocal-fit.com`은 Cloudflare Tunnel을 통해 같은 vocal-server `localhost:8000`으로 연결된다.
- admin은 현재 별도 React 서버가 아니라 vocal-server가 `/admin/*` 라우트와 Jinja HTML을 직접 제공하는 구조다.
- `docs/admin_reference.md`는 Phase B에서 React build를 vocal-server 정적 파일로 서빙하는 same-origin 방식을 권장한다고 적고 있다. 현재 admin 코드 기준 React 정적 서빙 구현은 확인되지 않았다.

### vocal-server와의 관계

- admin 라우터는 `app/main.py`에서 `app.include_router(admin.router)`로 등록된다.
- `SessionMiddleware`도 같은 FastAPI 앱에 등록된다.
- admin HTML과 JSON endpoint는 모두 같은 FastAPI process에서 동작한다.

### Cloudflare Tunnel 구조

문서 기준:

- Cloudflare Tunnel은 vocal-server와 별도 launchd 서비스로 운영된다고 기록되어 있다.
- vocal-server 자체는 launchd 미등록이고, Mac 재부팅 후 수동 기동이 필요하다고 문서에 기록되어 있다.
- `admin.vocal-fit.com`과 `api.vocal-fit.com`은 둘 다 vocal-server `:8000`을 향한다고 기록되어 있다.

Cloudflare/DNS/Tunnel credential 값은 기록하지 않는다.

### 실행/restart/deploy 명령어

저장소/문서에서 확인된 명령:

- 개발 실행: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- 재시작 스크립트: `bash scripts/restart_server.sh`
- 회원가입 상태 변경 스크립트: `bash scripts/signup_toggle.sh on|off`

`scripts/restart_server.sh`는 기존 `uvicorn app.main` process에 SIGTERM을 보내고, 필요 시 강제 종료 후 venv의 uvicorn으로 `app.main:app`을 `0.0.0.0:8000`에서 백그라운드 실행하고 `/admin/health` 200을 대기한다.

`scripts/signup_toggle.sh`는 `.env`의 `SIGNUP_ENABLED` 값을 수정하고 `restart_server.sh`를 호출한 뒤 signup endpoint로 검증한다. 이 스크립트는 DB에 검증용 signup을 발생시킬 수 있으므로 production에서 실행 전 주의가 필요하다.

이번 작업에서는 위 명령을 실행하지 않았다.

### 환경 변수 key 목록

코드와 문서에서 확인한 key:

- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `JWT_EXPIRE_DAYS`
- `MODEL_SERVER_URL`
- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`
- `SIGNUP_ENABLED`

값은 기록하지 않는다.

## 7. git 이력, 브랜치/태그

확인 시점: 2026-07-06 KST, 문서 작성 직전 로컬 상태.

- git root: `/Users/kimjeongwoo/vocal-server`
- branch: `main`
- 현재 HEAD: `cc652f63a2715c1099a0d4911a82ab2cc69c5fa5`
- 현재 HEAD 커밋 메시지: `docs: add Claude handover code state`
- remote: `origin` = GitHub SSH remote
- remote tracking 상태: `main...origin/main [ahead 1]`
- 기존 tag 목록 요약: `v2.x-gpt-final` 1개 확인
- `v2.x-gpt-final`이 가리키는 commit: `8e939c02a2fefea2aa494e47e40a903637e0ec91`
- 현재 HEAD에 tag는 붙어 있지 않다.
- 새 tag `v2.x-gpt-final` 생성 여부: 이번 작업에서는 생성하지 않음. 동일 이름 tag가 이미 존재한다.
- push 여부: 이번 작업에서는 push하지 않음.

주의:

- 요청 전제에는 dirty 항목이 많다고 되어 있었지만, 문서 작성 전 `git status --short`와 admin 파일 diff 확인 결과 출력은 없었다.
- `app/routers/admin.py`, `app/templates/admin/users.html`의 미커밋 diff도 확인되지 않았다.
- 루트 `docs/HANDOVER_TO_CLAUDE.md`는 이미 현재 HEAD 커밋에 포함되어 있었다. 이번 문서는 요청 기준 경로에 맞춰 `vocal-server/docs/HANDOVER_TO_CLAUDE.md`로 작성한다.

## 8. TODO/FIXME/HACK 주석 전수 수집

검색 명령 범위: `app`, `docs`, `scripts`, `main.py`, `HANDOVER.md`, `PROGRESS.md`, `CLAUDE.md`.

admin 관련 코드:

- `app/routers/admin.py`: TODO/FIXME/HACK 없음.
- `app/templates/admin/*.html`: TODO/FIXME/HACK 없음.

저장소 전체 검색 결과:

| 파일 | 라인 | 종류 | 내용 |
| --- | ---: | --- | --- |
| `app/models/models.py` | 38 | TODO | `User.is_approved`에 대해 상용화 시 default false와 가입 승인 흐름 추가 필요 주석 |
| `app/routers/songs.py` | 98 | TODO | 앱에서 부분 재생/탐색 필요 시 range request 구현 필요 주석 |
| `docs/vocal_server_code_audit_2026-06-16.md` | 863 | TODO 언급 | range request TODO가 남아 있고 직접 구현은 없다는 감사 기록 |

## 9. 위험 지점

### 하드코딩/설정 위험

- `app/config.py`에는 여러 환경 변수 fallback이 코드에 있다. 이 문서에는 fallback 값을 기록하지 않는다.
- `app/main.py`의 `ADMIN_SESSION_SECRET` fallback도 코드에 있다. production에서는 반드시 실제 env key가 설정되어야 한다.
- `app/database.py`는 `create_engine(..., echo=True)`로 SQL echo가 켜져 있다. production 로그 민감도와 성능 영향 확인 필요.
- admin login은 단일 `ADMIN_PASSWORD` 방식이고 사용자별 admin 계정/감사 trail이 없다.

### 임시방편/메모리 기반 상태

- admin login rate limit `_failed_attempts`는 메모리 기반이다.
- `app_state.signup_enabled`는 메모리 기반이며 서버 startup 시 env key `SIGNUP_ENABLED`로 초기화된다. admin 화면 토글은 재시작 후 env 기준으로 reset된다.
- `event_store._events`는 메모리 `deque(maxlen=50)`라 재시작 시 사라진다.
- ActivityTracker middleware의 throttle cache도 메모리 기반이다.
- 다중 worker/process 배포 시 위 메모리 상태들이 worker별로 달라질 수 있다.

### auth/session/cookie 위험

- `POST /admin/logout`은 auth dependency 없이 session clear를 수행한다.
- admin password가 단일 공유 비밀번호라 사용자별 권한/로그아웃/회수 모델이 없다.
- `require_admin_auth`는 401과 `Location` header를 주지만 HTML 브라우저 redirect response는 아니다.
- `CORSMiddleware`가 wildcard origin과 credentials 허용으로 설정되어 있다. admin Phase B에서 별도 origin React를 붙이면 쿠키/CORS 동작을 다시 검증해야 한다.

### 검색/페이지네이션 성능 위험

- `/admin/users`는 `User.nickname.ilike("%q%")`와 `User.email.ilike("%q%")`로 검색한다. 일반 btree index만으로는 leading wildcard 검색 성능을 기대하기 어렵다.
- `/admin/api/users`는 모든 사용자를 한 번에 반환한다. 사용자 수 증가 시 pagination이 없다.
- `/admin/users`는 count subquery와 keyset pagination을 사용하지만 total/test/op count는 매 요청 계산한다.
- `online_count`는 현재 페이지 rows 기준으로 계산된다. 전체 접속 중 수가 아니라 현재 page 내 접속 중 수다.

### production 배포 시 주의점

- `scripts/restart_server.sh`는 process 종료와 재기동을 수행한다. production에서 실행하면 짧은 다운타임이 생긴다.
- `scripts/signup_toggle.sh`는 `.env` 수정, 서버 재시작, signup 검증 요청을 수행한다. production DB에 검증용 가입 기록이 생길 수 있다.
- Cloudflare Tunnel 설정 변경, DNS 변경, deploy/restart는 이번 작업에서 수행하지 않았다.
- `/admin/dashboard`는 SSE endpoint를 호출하지만 실제 `/admin/events/stream`은 410 Gone이다. 운영 안내에서는 `/admin/logs` 사용이 맞다.
- `_ACTIVITY_KR`에는 `GET /analysis/{id}/user_f0` label이 있지만 현재 `app/routers/analysis.py`에는 해당 route가 확인되지 않는다.
