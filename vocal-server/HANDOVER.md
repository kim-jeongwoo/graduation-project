# vocal-server HANDOVER (GPT 이관용)

작성: 2026-05-12 · 마지막 commit: `647c8e1`

> **GPT 측 추천 view 순서**:
> 1. 이 문서 (HANDOVER.md) — 워크스페이스 전체 컨텍스트
> 2. `CLAUDE.md` — #반복하지말것 9개 (실수 방지)
> 3. `PROGRESS.md` — 마일스톤 + 백로그
> 4. `docs/api.md` — endpoint 상세 명세 (앱 개발자용 통합 문서)
> 5. `docs/admin_reference.md` — admin 전용 핸드북 (Phase B 시작 시)

---

## 1. 프로젝트 개요

졸업작품 보컬 발성 분석 시스템의 백엔드 FastAPI 서버.

- **9개 항목 발성 평가** (성대접촉/호흡/공명 등) + **음정 분석** + **노래방 (14곡)** + **TrainingScreen 사후 측정** + **admin 대시보드**
- 협업 페이지: `vocal-app` (Expo 앱), `dml-server` (AI 모델 서버 GPU)
- 모노레포 `graduation-project/` 안에 `vocal-server/` 서브폴더로 위치 (다른 페이지 코드는 직접 수정 금지)

---

## 2. 인프라

| 항목 | 상태 |
|------|------|
| 호스트 | Mac Studio M1 (연구실) |
| 로컬 | `http://localhost:8000` (uvicorn 단일 worker) |
| 외부 (앱) | `https://api.vocal-fit.com` (Cloudflare Tunnel) |
| 외부 (admin) | `https://admin.vocal-fit.com` (같은 Tunnel, 같은 vocal-server) |
| dml-server 호출 base | `https://dml.vocal-fit.com` |
| DB | PostgreSQL 17 — `vocal_db` (localhost:5432) |
| Python | venv `vocalserver/` (3.14.2 symlink **고정** — brew 3.14.4 dylib 호환성 회피) |
| cloudflared | launchd 서비스 (root, 영구) — vocal-server와 별개 |
| vocal-server 자체 | **launchd 미등록** — Mac 재부팅 시 정우가 직접 `bash scripts/restart_server.sh` |

---

## 3. 핵심 아키텍처 결정 (변경 금지)

- **`result_json` 통째 저장 패턴**: dml-server 응답을 화이트리스트 없이 dict 그대로 DB JSONB에 저장. v2 등 신규 필드 자동 호환. (5/12 `/analyze-chunk`도 같은 패턴으로 통일)
- **사용자 wav 영구 보관**: `app/storage/users/{user_id}/sessions/{session_id}/{filename}`
- **14곡 자유곡 한정 + 자유녹음 별도**: `Session.song_id` 있으면 노래방, 없으면 자유녹음. 즐겨찾기는 노래방만 가능 (자유녹음은 400)
- **JWT 7일 유효기간** (`JWT_EXPIRE_DAYS=7`)
- **admin 비밀번호 인증** (환경변수 `ADMIN_PASSWORD`) + **IP rate limit 5분 5회 → 5분 차단** (메모리)
- **활동 추적 미들웨어** — 인증된 사용자 요청을 5분 throttle로 `users.last_seen_at`/`last_endpoint`에 기록 (admin/health/docs 제외)
- **DB 10 테이블**: `users, sessions, session_files, analysis_runs, analysis_results, reference_profiles, reference_metrics, songs, training_attempts, training_favorites`
- **alembic만 schema 변경** (`Base.metadata.create_all` 금지)

---

## 4. 진행 이력 (시간순)

| 날짜 | 마일스톤 |
|------|---------|
| 4월말~5/2 | DB 학습 + 9 테이블 설계 |
| 5/2~5/3 | 서버 코어, 인증, 노래방 모델 + sync, 노래방 API 4개 |
| 5/3 | 모노레포 정리 (`vocal-server/` 서브폴더로 이동), CLAUDE.md Karpathy 4원칙 |
| 5/3~5/4 | song_id forward, no_voice status, ETag 캐싱, training-analyze 신규 (화이트리스트 패턴) |
| 5/9 | Cloudflare Tunnel 배포 (`api.vocal-fit.com`), JWT 7일 환경변수화 |
| 5/9 | dml-server base URL → `https://dml.vocal-fit.com` |
| 5/9 | Phase 7: training_attempts/training_favorites 테이블 + endpoint 4개 |
| 5/9 | admin 라우터 외부 노출 보안 사고 진단 → 임시 lock |
| 5/10 | admin Phase A-2~A-5-e: 비밀번호+rate limit, 사용자 리스트, 상세, 활동 추적, 폴링 로그 |
| 5/10 | `restart_server.sh`/`signup_toggle.sh` 작성, `SIGNUP_ENABLED` 토글 |
| 5/11 | dml-server score_mapper v2 자동 통과 검증 (코드 수정 0) |
| 5/11 | `_ANALYZE_TIMEOUT` 120s → 180s, Cloudflare 100s 한계 발견 |
| 5/12 | Admin Phase B 핸드북 (`docs/admin_reference.md`) 작성 |
| 5/12 | dml-server StreamingResponse 자동 통과 P1-2 검증 (TTFB 우회 확정) |
| 5/12 | `training-analyze` 화이트리스트 → 통째 통과 전환 (v2 5필드 누락 사례) |
| 5/12 | dml-server Phase 2 (/analyze StreamingResponse) 사후 검증: 218초 wav 통과 |
| 5/12 | **GPT 이관 — 이 문서 작성** |

---

## 5. 미해결 이슈 / 백로그

### 단기 (5/14 학원 실험 직후)
- admin Phase A-6 (옵션 2): 검색/페이지네이션, 비밀번호 reset + 강제 로그아웃, CSV export, 일별 활동 차트, 개인 실력 추이 (10개 항목 토글), 사용자 간 실력 비교
- vocal-admin-server 새 워크스페이스 시작 (이미 `docs/admin_reference.md` 작성됨)

### 중기 (6/15 시연 전)
- WebSocket vocal-server proxy 전환 (현재 vocal-app → dml-server 직접)
- 잠재 위험: dml-server가 새 `status="invalid"`/`"failed"` 반환 시 `analysis_service.py` 분기 추가 (현재 `no_voice`/`failed` 외 else 절로 빠져 알 수 없는 status 저장 가능)

### 장기 (시연 후)
- 이메일 인증
- launchd plist로 vocal-server 자동 기동 (현재 수동)

---

## 6. 협업 흐름 (페이지 간 의존성)

```
vocal-app (Expo)
    │
    ├─ HTTPS Bearer JWT ──→ vocal-server (api.vocal-fit.com)
    │                            │
    │                            └─ dml-server forward (dml.vocal-fit.com)
    │
    └─ WebSocket ──────────→ dml-server 직접 (현재, 향후 proxy 전환 예정)

admin (정우 모바일)
    └─ HTTPS Session Cookie ──→ vocal-server (admin.vocal-fit.com)
```

- vocal-server는 dml-server 응답을 **forward** (가공 없이 통째 저장/통과)
- **§15-3 운영 규칙**: dml-server 응답 schema 변경 시 사전 공유 필수 (이전에 user_f0 옵션 C, score_mapper_v2, training-analyze v2 누락 등 위반 사례 있음)
- vocal-app은 vocal-server를 통해서만 dml-server 결과 받음 (WebSocket 예외)

---

## 7. 알려진 한계

- **Cloudflare Tunnel 무료/Pro origin timeout 125s** (Enterprise만 6,000s, 비현실) — dml-server StreamingResponse(TTFB 우회)로 5/12 해소
- **메모리 기반 IP rate limit** — 단일 인스턴스 한정, 서버 재시작 시 카운터 초기화
- **메모리 기반 SIGNUP_ENABLED 토글** — admin 페이지 토글은 즉시 반영, 서버 재시작 시 `.env` 값으로 reset
- **활동 추적 throttle 메모리 캐시** — 분산 환경 비호환
- **admin 이벤트 deque 50개** — 메모리, 재시작 시 초기화. 영구 보관 필요 시 `event_logs` 테이블 추가 필요
- **CORS `allow_origins=["*"]` + `allow_credentials=True` 조합 비호환** — vocal-admin-server는 same-origin (vocal-server가 정적 파일 서빙) 권장 (`docs/admin_reference.md` 9번 참조)

---

## 8. 운영 권고

- **single uvicorn worker** (현재). 다중 worker로 가면 위 메모리 기반 캐시들 부정확해짐
- **재시작**: `bash scripts/restart_server.sh` (graceful SIGTERM → 10s 대기 → SIGKILL fallback → `/admin/health` 200 대기, 약 4~5초 다운타임)
- **SIGNUP_ENABLED 토글**: 모바일 admin 페이지에서 즉시 (재시작 없이), 또는 `bash scripts/signup_toggle.sh on|off` (재시작 포함)
- **DB 백업**: `pg_dump vocal_db > ~/vocal-server/backups/users_backup_YYYY-MM-DD.sql`
- **Mac 재부팅 시**: 수동 기동 필요 (cloudflared는 자동 기동)

---

## 9. 환경변수 (`.env`, gitignored — 값 절대 출력 금지)

```
DATABASE_URL          # postgresql://...
SECRET_KEY            # JWT 서명 키
ALGORITHM             # HS256
JWT_EXPIRE_DAYS       # 7
MODEL_SERVER_URL      # https://dml.vocal-fit.com
ADMIN_PASSWORD        # admin 로그인 비밀번호
ADMIN_SESSION_SECRET  # secrets.token_urlsafe(48)
SIGNUP_ENABLED        # true / false
```

`.env` 위치: `/Users/kimjeongwoo/vocal-server/.env` (`vocal-server/` 서브폴더 한 단계 위 — `python-dotenv`가 자동 검색)

---

## 10. 반복 실수 리스트 (#반복하지말것)

CLAUDE.md 9개 항목 요약:

1. [2026-05-03] uvicorn 재시작 시 "Address already in use" → `pkill -f "uvicorn app.main"` 후 재시작
2. [2026-05-02] alembic 도입 후 `Base.metadata.create_all()` 사용 금지
3. [2026-05-02] alembic NOT NULL 칼럼 추가 시 `server_default` 수동 필요 (autogenerate가 안 채움)
4. [2026-05-02] `lrc/parsed/{id}_aligned.json` 변종 dml 측 존재 — 현재 `{id}.json`만 sync
5. [2026-05-03] 모노레포 — 서버 실행/테스트는 `cd vocal-server/vocal-server/` 후 진행
6. [2026-05-04] dml-server `status='success'` vs vocal-server `'completed'` 매핑 — 분기 시 둘 다 고려 (캐싱 조건에서 누락 사례 있었음)
7. [2026-05-09] `cloudflared service install`이 plist에 `tunnel run` 인자 자동 미적용 — 수동 plist 작성
8. [2026-05-11] Cloudflare Tunnel 무료/Pro origin timeout 100~125s 고정 (5/12 StreamingResponse로 해소)
9. [2026-05-12] dml-server forward endpoint를 화이트리스트로 구현 시 신규 필드 자동 누락 — `/analyze`처럼 통째 통과 패턴 권장

전체 원문은 `CLAUDE.md` 마지막 섹션 참조.

---

## 11. 운영 명령어 모음

```bash
# 서버 재시작 (안전, ~5초)
bash /Users/kimjeongwoo/vocal-server/vocal-server/scripts/restart_server.sh

# 회원가입 토글 (재시작 포함)
bash /Users/kimjeongwoo/vocal-server/vocal-server/scripts/signup_toggle.sh on
bash /Users/kimjeongwoo/vocal-server/vocal-server/scripts/signup_toggle.sh off

# DB 접속
/opt/homebrew/Cellar/postgresql@17/17.8/bin/psql vocal_db

# DB 백업
/opt/homebrew/Cellar/postgresql@17/17.8/bin/pg_dump vocal_db > ~/vocal-server/backups/$(date +%Y-%m-%d).sql

# 마이그레이션 (vocal-server/vocal-server/ 에서)
/Users/kimjeongwoo/vocal-server/vocalserver/bin/alembic revision --autogenerate -m "..."
/Users/kimjeongwoo/vocal-server/vocalserver/bin/alembic upgrade head
/Users/kimjeongwoo/vocal-server/vocalserver/bin/alembic current

# 노래방 데이터 동기화 + 시드
bash scripts/sync_songs.sh
/Users/kimjeongwoo/vocal-server/vocalserver/bin/python scripts/seed_songs.py

# StreamingResponse 검증 (P1-2 재현)
/Users/kimjeongwoo/vocal-server/vocalserver/bin/python scripts/verify_streaming.py

# cloudflared 재시작 (sudo 필요)
sudo launchctl kickstart -k system/com.cloudflare.cloudflared

# pycache 클리어 (코드 변경 미반영 시)
find /Users/kimjeongwoo/vocal-server/vocal-server/app -name __pycache__ -exec rm -rf {} +
```

---

## 12. API endpoint 전체 (상세는 `docs/api.md`)

**일반 사용자 (Bearer JWT):**
- `POST /auth/signup`, `POST /auth/login`
- `POST /sessions`, `GET /sessions`, `GET /sessions/{id}`
- `POST /sessions/{id}/files`, `POST /sessions/{id}/analyze`, `POST /sessions/{id}/training-analyze`
- `GET /analysis/{run_id}`, `/results`, `/comparison`, `/user_f0`
- `GET /songs`, `/songs/{id}/lrc`, `/pitch-guide`, `/mr`
- `GET /users/me/training-attempts`, `GET/POST /users/me/favorites`, `DELETE /users/me/favorites/{id}`

**Admin (세션 쿠키, `admin.vocal-fit.com`):**
- `GET/POST /admin/login`, `POST /admin/logout`
- `GET /admin/users` (HTML, `?show_test=`), `GET /admin/users/{id}` (HTML, 3-탭)
- `GET /admin/api/users`, `/admin/api/online-users`, `/admin/api/events?limit=&since=`
- `POST /admin/signup-toggle`
- `GET /admin/dashboard` (구 SSE, 사용 비권장), `/admin/logs` (5초 폴링)
- `GET /admin/events/stream` → **410 Gone** (SSE 폐기)

---

## 13. dml-server 응답 forward 명세 (핵심)

### `POST /analyze` (정식 분석)
- **통째 저장 패턴**: `analysis_service.py` `run.result_json = data` (run_id 포함, top-level ~14필드 + v2 4필드)
- v2 필드 자동 통과: `score_mapper_version, scores_v2, scores_meta, academic_analysis_scores, reliability.{shown_v2, shown_v2_tiers, academic_only_v2, deferred_v2}`
- StreamingResponse 호환: httpx 동기 `response.json()`이 leading whitespace keepalive 자동 허용 (RFC 7159)

### `POST /sessions/{id}/training-analyze` (사후 측정, 휘발)
- **통째 통과 + 가공**: `dict(body) - run_id + session_id + chunk_meta` (12필드 — dml 11 - run_id + 2)
- `/analyze-chunk`엔 `academic_analysis_scores`, `reliability`, `timeline_scores`, `timeline_metadata`, `user_f0`, `feedback`, `registers`, `audio_info`, `register_boundaries` **없음** (정식 `/analyze`와 차이)
- 자동 누적 저장: `success` + `chunk_meta`에 `original_run_id`+`chunk_index` 있으면 `training_attempts` INSERT (best-effort)

---

## 14. GPT 환경 작업 규칙 (Karpathy 4원칙 — `CLAUDE.md` 전체 참조)

1. **Think Before Coding**: 추측 금지. 불확실하면 질문. 코드 작업 전 접근 방법 3~5줄 요약 → OK 후 진행
2. **Simplicity First**: 요청한 것만 구현. 추측성 기능/유연성 추가 금지
3. **Surgical Changes**: 수정해야 할 곳만. 무관한 코드 리팩토링 금지. 모든 수정 라인이 사용자 요청과 직접 연결되는가?
4. **Goal-Driven Execution**: 명령형 → 검증 가능한 목표로. 분석만 하고 멈추지 말 것 (구현→검증→설명까지). 새 endpoint는 '정상 + 에러 테스트 통과'까지가 완료

추가:
- diff 중심 출력. 파일 전체 재출력 금지. 서론/마무리 금지
- 완료 보고 3줄 이내
- 비밀값 출력 금지 (`ADMIN_PASSWORD`, `SECRET_KEY`, `ADMIN_SESSION_SECRET` 등)
- 모델 선택 — 단순 매핑/진단/timeout: 작은 모델 / 복잡 설계·다중 의존성: 큰 모델
- DB DROP/DELETE는 사용자 확인 후. `git push`/`git reset --hard` 확인
- 통합 테스트 (`test_integration.py`)는 사용자 명시 요청 시만 실행 (테스트 계정 자동 생성됨)

---

## 15. 마지막 작업 + 다음 트리거

- **마지막 commit**: `647c8e1` Pass-through v2 fields in training-analyze response
- **방금 검증 완료**: dml-server Phase 2 (/analyze StreamingResponse) 사후 검증 — 짧은/긴/무음 wav 모두 자동 통과, 코드 수정 0
- **다음 트리거**:
  - 5/14 학원 실험 중 issue 발생 시 즉시 대응
  - 5/14+ admin Phase A-6 (옵션 2) 진행
  - vocal-admin-server 새 워크스페이스 시작 시 `docs/admin_reference.md` 활용
  - dml-server 추가 schema 변경 시 §15-3 사전 공유 후 통째 통과 패턴으로 자동 호환

---

## 16. 주요 파일 위치 (빠른 참조)

```
vocal-server/                      # 모노레포 루트 (graduation-project/)
├── .env                           # 환경변수 (gitignored, 값 출력 금지)
├── backups/                       # pg_dump 백업
├── vocalserver/                   # Python venv (3.14.2 symlink)
└── vocal-server/                  # ★ 코드 루트 (cd 여기서)
    ├── app/
    │   ├── main.py                # FastAPI 앱 + 미들웨어 (Session, ActivityTracker, CORS)
    │   ├── config.py              # 환경변수 노출
    │   ├── database.py            # SQLAlchemy engine + SessionLocal
    │   ├── deps.py                # JWT 인증 (get_current_user, create_access_token)
    │   ├── state.py               # AppState (signup_enabled 메모리)
    │   ├── event_store.py         # admin 이벤트 deque
    │   ├── middleware/
    │   │   └── activity_tracker.py  # 활동 추적 미들웨어
    │   ├── models/models.py       # ORM 10 테이블
    │   ├── schemas/schemas.py     # Pydantic
    │   ├── routers/               # auth, sessions, files, analysis, songs, training, admin
    │   ├── services/
    │   │   └── analysis_service.py  # dml-server forward
    │   ├── storage/               # 사용자 wav + 노래방 데이터 (gitignored)
    │   └── templates/admin/       # login.html, users.html, user_detail.html, logs.html
    ├── alembic/versions/          # 마이그레이션 (head: 9a253a587cb6)
    ├── scripts/
    │   ├── restart_server.sh      # ★ 안전 재시작
    │   ├── signup_toggle.sh       # SIGNUP_ENABLED on/off
    │   ├── verify_streaming.py    # dml-server StreamingResponse 검증
    │   ├── sync_songs.sh          # dml → 로컬 동기화
    │   └── seed_songs.py          # songs.json → DB upsert
    ├── docs/
    │   ├── api.md                 # ★ 앱 개발자용 API 통합 문서
    │   └── admin_reference.md     # vocal-admin-server (Phase B) 핸드북
    ├── HANDOVER.md                # ★ 이 문서 (GPT 이관용)
    ├── PROGRESS.md                # 마일스톤 + 백로그
    ├── CLAUDE.md                  # 에이전트 행동 규칙 + #반복하지말것 9개
    └── test_integration.py        # 30/30 통합 테스트 (사용자 명시 요청 시만)
```
