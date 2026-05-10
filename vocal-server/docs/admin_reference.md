# Admin Reference (Phase B 핸드북)

vocal-admin-server (React 프론트엔드)가 vocal-server admin API를 활용하기 위한 통합 문서.

> **이 문서를 처음 읽는 React 페이지 에이전트에게**: 이 문서 1개로 admin 작업 시작 가능. 추가 정보가 필요하면 vocal-server 페이지에 endpoint 추가 요청.

- vocal-server: FastAPI + PostgreSQL (Mac Studio M1, port 8000)
- 외부 노출: Cloudflare Tunnel
  - `https://api.vocal-fit.com` — 일반 사용자 API (앱)
  - `https://admin.vocal-fit.com` — admin (현재 vocal-server 직결, Phase B 전환 시 변경)
- admin 워크스페이스 별도: `vocal-admin-server/` (React, 신규)

---

## 1. 인증 흐름

### POST /admin/login

```http
POST /admin/login
Content-Type: application/x-www-form-urlencoded
```

**Request (form):**
```
password=<ADMIN_PASSWORD>
```

**성공 응답 (302):**
- `Location: /admin/users` (Phase A는 redirect)
- `Set-Cookie: admin_session=...; HttpOnly; Path=/; SameSite=lax; Secure; Max-Age=86400`

**실패 응답 (302):**
- `Location: /admin/login?error=invalid_password`
- 5분 윈도우 5회 실패 → `Location: /admin/login?error=rate_limited&retry=<seconds>`

> **React에서 사용 시 주의**: Phase A는 form + redirect 구조. React SPA에선 `fetch('/admin/login', {method:'POST', body:formData, credentials:'include', redirect:'manual'})` 후 응답 status로 분기. Location 헤더의 `?error=` 파라미터로 실패 사유 확인. 또는 vocal-server 페이지에 JSON 버전(`/admin/api/login`) 추가 요청.

### POST /admin/logout

```http
POST /admin/logout
Cookie: admin_session=...
```
세션 clear → 302 `/admin/login`.

### 인증 의존성 (모든 admin endpoint)

쿠키 누락/만료/잘못된 세션 → **401**:
```json
{ "detail": "Admin authentication required" }
```
응답 헤더 `Location: /admin/login`.

> React 인터셉터: 401 응답 → 로그인 페이지로 이동.

### Rate Limit (서버 메모리)

- 윈도우: 5분
- 실패 5회 → 5분 차단 (해당 IP)
- 차단 중 시도 → 즉시 `?error=rate_limited&retry=N` redirect
- IP 추출: `X-Forwarded-For` 첫 번째 (Cloudflare Tunnel 뒤)
- **단일 인스턴스 한정** — 서버 재시작 시 카운터 초기화

---

## 2. 사용자 관련 endpoint

### GET /admin/api/users (JSON)

```http
GET /admin/api/users
Cookie: admin_session=...
```

**Response 200:**
```json
[
  {
    "user_id": "9ef3c8af-b8ba-4bdc-b32c-9e993cad689a",
    "email": "vocal2026@test.com",
    "nickname": "테스트",
    "created_at": "2026-05-03T04:09:59.973472+09:00"
  }
]
```

**필드:** `user_id` (UUID), `email`, `nickname`, `created_at` (ISO datetime, KST). Pydantic `AdminUserResponse` 기반.

> **카운트는 미포함**. 세션수/즐겨찾기/시도수가 필요하면 별도 호출 또는 vocal-server에 `/admin/api/users-with-counts` 추가 요청.  
> **테스트 계정 필터 X**. show_test 필터는 HTML 페이지 전용. JSON은 항상 전체 반환.

### GET /admin/users/{user_id} (HTML, JSON 버전 없음)

현재 HTML 페이지만 제공 (사용자 상세). React에서 활용하려면 vocal-server에 JSON 버전 추가 필요:

> **Phase B 진행 중 추가 요청**: `GET /admin/api/users/{user_id}` — 사용자 정보 + 통계 (sessions/favorites/attempts 카운트) + 마지막 활동 + status_label 한글화.

### GET /admin/users/{user_id}/sessions (JSON, 이미 존재)

```http
GET /admin/users/{user_id}/sessions
Cookie: admin_session=...
```

**Response 200:** `list[SessionBrief]`
```json
[
  {
    "session_id": "...",
    "song_title": null,
    "song": { "id": "004", "artist": "김범수", "title": "보고싶다" },
    "status": "uploaded",
    "analysis_status": "completed",
    "started_at": null,
    "created_at": "2026-05-03T04:10:00+09:00"
  }
]
```

**에러:** 404 (없는 user_id), 401 (미인증).

---

## 3. 활동 추적

### DB 컬럼 (User)

- `last_seen_at: DateTime(tz)?` — 마지막 인증 요청 시점
- `last_endpoint: String(100)?` — `"GET /sessions"`, `"POST /sessions/{id}/analyze"` 등 정규화된 경로

**정규화 규칙** (server side):
- UUID `[0-9a-f-]{36}` → `{id}`
- hex 12자리 이상 (run_id) → `{id}`
- `/songs/\d{3}` → `/songs/{id}`

**Throttle:** 같은 user + 같은 endpoint, 5분 이내 → DB UPDATE 스킵 (메모리 캐시).

### GET /admin/api/online-users

```http
GET /admin/api/online-users
Cookie: admin_session=...
```

**Response 200:**
```json
{
  "users": [
    {
      "user_id": "9ef3c8af-b8ba-4bdc-b32c-9e993cad689a",
      "nickname": "테스트",
      "email": "vocal2026@test.com",
      "last_seen_at": "2026-05-10T01:38:00+00:00",
      "last_endpoint": "GET /sessions/{id}",
      "activity_kr": "세션 상세 조회",
      "relative_time": "3분 전"
    }
  ],
  "server_time": "2026-05-10T01:42:32+00:00"
}
```

**기준:** `last_seen_at` 5분 이내. `last_seen_at` desc 정렬.

---

## 4. 이벤트 로그

### GET /admin/api/events

```http
GET /admin/api/events?limit=100&since=2026-05-10T00:00:00+00:00
Cookie: admin_session=...
```

**Query:**
- `limit` (int, default 100, max 500)
- `since` (ISO datetime, optional) — 이 시점 이후 이벤트만

**Response 200:**
```json
{
  "events": [
    {
      "timestamp": "2026-05-10T01:38:00+00:00",
      "event_type": "login",
      "nickname": "학생2",
      "email": "student02@test.com"
    }
  ],
  "server_time": "2026-05-10T01:42:32+00:00"
}
```

**event_type 종류:** `signup`, `login` (현재 2가지). 메모리 deque (최대 50개) — 서버 재시작 시 초기화.

> **React 폴링 패턴**: 5초 간격, 첫 호출은 `since` 없이, 이후 마지막 이벤트 timestamp를 `since`로 전달. 새 이벤트만 prepend.

### GET /admin/events/stream — **폐기 (410 Gone)**

Cloudflare Tunnel(QUIC)에서 SSE long-lived connection 끊김 빈번. 폴링으로 대체.

### GET /admin/events (JSON, 호환성)

기존 호환용. `limit/since` 미지원. `/admin/api/events` 사용 권장.

---

## 5. 회원가입 토글

### POST /admin/signup-toggle

```http
POST /admin/signup-toggle
Cookie: admin_session=...
```

**Response (Phase A):** 302 `/admin/users` (form 전제).

**상태:**
- 메모리 변수 `app_state.signup_enabled`
- 서버 startup 시 `.env`의 `SIGNUP_ENABLED`로 초기화
- 토글은 즉시 반영 (`POST /auth/signup`이 다음 요청부터 403 또는 201)
- **서버 재시작 시 .env 값으로 reset**

**현재 상태 확인:** `GET /admin/users` HTML의 토글 카드 또는 `POST /auth/signup` 시도 후 403/201로 추정.

> **Phase B 권장 추가**: vocal-server에 `GET /admin/api/signup-status` (현재 enabled 값 JSON 반환) + `POST /admin/api/signup-toggle` (JSON 응답으로 새 상태 반환). 현재는 GET 없음 → React에서 토글 후 사용자 리스트 갱신 시 form 페이지 결과로 추정해야 함.

---

## 6. DB 스키마 (참고)

| 테이블 | 주요 필드 |
|--------|-----------|
| `users` | `user_id` UUID PK, `email` unique, `nickname`, `created_at`, `role` (user/trainer/admin), `is_approved`, `last_seen_at?`, `last_endpoint?` |
| `sessions` | `session_id` UUID PK, `user_id` FK CASCADE, `song_id` FK→songs, `song_title?`, `status` (uploading/uploaded/analyzing/completed/failed), `created_at` |
| `session_files` | `file_id` UUID PK, `session_id` FK CASCADE, `file_type`, `storage_uri`, `format`, `sample_rate_hz`, `duration_ms` |
| `analysis_runs` | `run_id` UUID PK, `session_id` FK CASCADE, `status` (queued/running/success/no_voice/failed), `requested_at`, `finished_at?`, `error_message?`, `result_json` JSONB |
| `analysis_results` | `result_id` UUID PK, `run_id` FK CASCADE, `metric_key`, `metric_value`, `unit?` |
| `training_attempts` | `attempt_id` UUID PK, `user_id` FK CASCADE, `session_id` FK SET NULL, `original_run_id` FK SET NULL, `chunk_index`, `chunk_start_sec`, `chunk_end_sec`, `indicator_key`, `before_*`, `after_*`, `attempted_at` |
| `training_favorites` | `favorite_id` UUID PK, `user_id` FK CASCADE, `song_id` FK→songs, `original_run_id?`, `chunk_index`, `chunk_start_sec`, `chunk_end_sec`, `chunk_lrc_text?`, `indicator_key`, `created_at`. UNIQUE (user_id, song_id, chunk_index, indicator_key) |
| `songs` | `id` String(8) PK ("001"~"014"), `artist`, `title`, `master_filename?`, `mr_filename?`, `master_duration_sec?`, `mr_duration_sec?`, `lrc_offset_sec?`, `alignment_status?`, `has_lrc`, `has_pitch_guide` |

`result_json` 구조 — `docs/api.md` 섹션 10 참조 (audio_info, indicators, scores, feedback, reliability, timeline_scores, timeline_metadata, user_f0).

---

## 7. Phase B에서 추가 필요 예상 endpoint

vocal-server 페이지에 추가 요청 시점 정리:

| Endpoint | 용도 | 요청 시점 |
|----------|------|----------|
| `GET /admin/api/users/{user_id}` | 사용자 상세 JSON (HTML 버전 데이터를 그대로) | 사용자 상세 페이지 React 전환 시 |
| `GET /admin/api/users/{user_id}/score-trend` | 시계열 점수 (Recharts용) — `[{date, indicator_key, avg_score}]` | 점수 추이 그래프 |
| `GET /admin/api/score-comparison` | 사용자 간 9개 항목 비교 | 학원 평가/리포트 |
| `GET /admin/api/practice-stats` | 일별 활동 요약 (가입/분석 수) | 운영 대시보드 |
| `GET /admin/api/signup-status` | 현재 회원가입 토글 상태 (true/false) | 토글 UI 초기 렌더링 |
| `POST /admin/api/signup-toggle` | JSON 응답 (`{enabled: bool}`) | React 토글 버튼 |
| `POST /admin/api/login` | form 대신 JSON 본문 + JSON 응답 | React SPA 로그인 |

→ Phase B 진행 중 React 페이지가 필요 시점에 vocal-server 페이지에 PR/요청.

---

## 8. 한글 매핑 상수

vocal-server `app/routers/admin.py` 모듈 상수. React에서 동일 매핑 사용 권장 (또는 vocal-server에 `GET /admin/api/labels` 추가하여 한 번에 가져오기).

### `_INDICATOR_KR` (9개 평가 항목)
```python
{
  "1_nasal_oral_ratio": "비강사용",
  "2_chest_head_voice": "흉성두성",
  "3_vocal_fold_contact": "접촉강도",
  "4_breathiness": "호흡식별",
  "5_forward_resonance": "전방공명",
  "6_soft_palate": "연구개위치",
  "7_larynx_tongue_root": "후두설근",
  "8_tongue_tension": "혀경직도",
  "9_pressure_balance": "상압하압",
}
```

### `_STATUS_KR` (분석/세션 status)
```python
{
  "success": "완료",
  "completed": "완료",
  "no_voice": "무음",
  "failed": "실패",
  "queued": "대기 중",
  "running": "분석 중",
  "uploading": "업로드 중",
  "uploaded": "업로드 완료",
  "analyzing": "분석 중",
}
```

### `_ACTIVITY_KR` (last_endpoint → 한글)
```python
{
  "POST /auth/login": "로그인",
  "POST /auth/signup": "회원가입",
  "POST /sessions": "세션 생성",
  "GET /sessions": "세션 목록 조회",
  "GET /sessions/{id}": "세션 상세 조회",
  "POST /sessions/{id}/files": "파일 업로드",
  "POST /sessions/{id}/analyze": "정식 분석 요청",
  "GET /analysis/{id}": "분석 상태 조회",
  "GET /analysis/{id}/results": "분석 결과 조회",
  "GET /analysis/{id}/comparison": "비교 분석 조회",
  "GET /analysis/{id}/user_f0": "F0 데이터 조회",
  "POST /sessions/{id}/training-analyze": "사후 측정 (TrainingScreen)",
  "GET /songs": "곡 목록 조회",
  "GET /songs/{id}/lrc": "가사 조회",
  "GET /songs/{id}/pitch-guide": "음정 가이드 조회",
  "GET /songs/{id}/mr": "MR 음원 조회",
  "GET /users/me/training-attempts": "누적 시도 조회",
  "GET /users/me/favorites": "즐겨찾기 조회",
  "POST /users/me/favorites": "즐겨찾기 추가",
  "DELETE /users/me/favorites/{id}": "즐겨찾기 제거",
}
```

### badge 색상 (status)

| status | bootstrap class |
|--------|----------------|
| `success`, `completed` | `bg-success` |
| `no_voice` | `bg-secondary` |
| `failed` | `bg-danger` |
| `queued`, `running`, `uploading`, `analyzing` | `bg-warning text-dark` |

---

## 9. CORS 정책

**현재 설정** (`vocal-server/app/main.py`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)
```

⚠️ **주의: `allow_origins=["*"]` + `allow_credentials=True` 조합은 브라우저가 거부함** (CORS 스펙). 쿠키 기반 admin 인증은 다음 시나리오만 동작:

1. **same-origin** (권장): React 빌드를 vocal-server가 정적 파일로 서빙 → `https://admin.vocal-fit.com` 단일 origin → CORS 무관, 쿠키 정상.
2. **별도 도메인** (예: `dashboard.vocal-fit.com`에서 React, `api 호출은 admin.vocal-fit.com`): vocal-server 페이지에 명시적 `allow_origins=["https://dashboard.vocal-fit.com"]` 변경 + `allow_credentials=True` 유지 요청.

> **Phase B 권장 인프라**: vocal-admin-server를 빌드해서 정적 파일을 vocal-server `app/static/admin/`에 배치 → `https://admin.vocal-fit.com` 단일 origin 운영. CORS 추가 작업 불필요.

---

## 10. 인프라

### 현재 (Phase A)

```
┌────────────┐   Cloudflare Tunnel    ┌────────────────────┐
│  외부      │ ─────────────────────→ │  Mac Studio M1     │
│  (모바일)  │                         │  vocal-server:8000 │
└────────────┘                         └────────────────────┘
                                            │
                                            ├── localhost (LAN)
                                            └── PostgreSQL 17 (vocal_db)
```

- `https://api.vocal-fit.com` → vocal-server `:8000` (앱)
- `https://admin.vocal-fit.com` → vocal-server `:8000` (admin)
  - vocal-server 내부에서 호스트네임 분기 안 함 (`/admin/*` 경로로만 분리)
  - `api.vocal-fit.com/admin/*`도 기술적으로 동작 (사용자에게 안내 X)
- launchd 서비스: `cloudflared` (root daemon, 영구)
- vocal-server 자체는 **수동 백그라운드** (launchd 미등록) — `bash scripts/restart_server.sh`

### Phase B 전환 옵션

**옵션 A: vocal-admin-server를 vocal-server가 서빙 (권장)**
- React build → `app/static/admin/` 또는 별도 라우트 mount
- 단일 origin, CORS/쿠키 이슈 없음
- vocal-server에 `app.mount("/admin/static", ...)` 또는 React 앱을 `/admin/v2/*`로 catch-all 추가

**옵션 B: 별도 도메인 (`dashboard.vocal-fit.com`)**
- 새 Cloudflare Tunnel 라우팅 추가
- vocal-server CORS 명시적 origin 변경 필수
- Vercel/Cloudflare Pages 등 별도 호스팅 가능

**옵션 C: 별도 vocal-admin-server 백엔드 + vocal-server API 호출**
- vocal-admin-server가 자체 인증, vocal-server는 Bearer 토큰 발급
- 가장 복잡, 현재 프로젝트 규모엔 과함

---

## 11. 로컬 개발 (Phase B)

```bash
# vocal-server 띄우기 (이미 실행 중일 수 있음)
cd /Users/kimjeongwoo/vocal-server/vocal-server
bash scripts/restart_server.sh

# admin 비밀번호 (gitignored .env)
grep "^ADMIN_PASSWORD=" /Users/kimjeongwoo/vocal-server/.env
# → 정우만 알 수 있음. 새 프로젝트 에이전트에게는 전달 X

# 외부 API 테스트 (모바일과 동일 경로)
curl -X POST https://admin.vocal-fit.com/admin/login \
  -d "password=<ADMIN_PASSWORD>" -c /tmp/admin.cookie -L

curl -b /tmp/admin.cookie https://admin.vocal-fit.com/admin/api/users
curl -b /tmp/admin.cookie https://admin.vocal-fit.com/admin/api/online-users
curl -b /tmp/admin.cookie https://admin.vocal-fit.com/admin/api/events
```

---

## 12. 알려진 한계 (Phase B에서 보완 가능)

- **Rate limit**: 메모리 기반, 단일 인스턴스 한정. 서버 재시작 시 초기화.
- **이벤트 deque**: 메모리 기반, 50개만 저장. 영구 보관 필요 시 `event_logs` 테이블 추가 요청.
- **활동 throttle 캐시**: 메모리, 재시작 시 초기화. 정확성보다 DB UPDATE 부담 감소가 목적.
- **현재 SIGNUP_ENABLED 상태 JSON 조회 endpoint 없음**: 화면 토글 카드 HTML에서만 확인.
- **사용자 상세 JSON endpoint 없음**: HTML만. Phase B 진행 시 추가 요청 필요.
- **CORS `*` + credentials 조합 비호환**: same-origin 또는 명시적 origin 필수.

---

## 13. 협업 절차

vocal-admin-server 페이지가 vocal-server에 변경 요청 시:

1. vocal-admin-server 페이지가 Phase B 진행 중 누락 endpoint 발견
2. `vocal-admin-server/REQUESTS.md` 또는 슬랙/이슈로 vocal-server 페이지에 요청
3. vocal-server 페이지가 endpoint 추가 + 이 문서 (`admin_reference.md`) 업데이트 + push
4. vocal-admin-server 페이지가 pull 후 활용

> **vocal-server 코드는 vocal-admin-server 페이지가 직접 수정 X** — 모노레포 내 분리 원칙 (CLAUDE.md 참조).
