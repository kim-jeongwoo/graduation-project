# vocal-server 진행 상황 인수인계

작성일: 2026-05-02. 새 대화 시작 전 이 파일부터 읽을 것.

---

> ## ⚠️ 중요: 이 문서가 진실의 원천 (Single Source of Truth)
>
> - `PROGRESS.md`, `CLAUDE.md`, `docs/API.md`, 그리고 **현재 코드**가 정답.
> - GitHub history나 옛 커밋, 기억에서 추측한 내용으로 작업하지 말 것.
> - 옛날 폐기된 코드: 잔나비 노래방, librosa.pyin 기반 pitch 비교,
>   `/sessions/{id}/compare-pitch`, `/songs/register` 등은 0단계에서 삭제됨.
> - git log에서 이런 옛 코드 흔적이 보여도 무시. **현재 코드가 맞음.**

> ## 작업 시작 전 필수 확인
>
> 1. `PROGRESS.md` (이 파일) — 현재 어디까지 됐는지
> 2. `CLAUDE.md` — 반복하지 말 것 목록
> 3. `docs/API.md` — API 명세
> 4. `git log --oneline | head -5` — 최근 커밋 (참고용, 의존하지 말 것)

---

## 1. 시스템 개요

- **프로젝트**: 보컬 발성 분석 (9개 항목 AI 피드백) + 노래방 기능 (MR 반주 + LRC 가사 + 음정 가이드)
- **서버 구성**:
  - `vocal-server` (Mac Studio): FastAPI + PostgreSQL
    - 로컬: `http://localhost:8000`
    - 외부: `https://api.vocal-fit.com` (Cloudflare Tunnel)
  - `dml-server` (dmlserver GPU): AI 분석 처리 `/analyze` 엔드포인트
    - 외부: `https://dml.vocal-fit.com` (vocal-server가 호출하는 base URL)
    - 로컬 (LAN): `http://114.71.220.144:8001` (참고용, 현재 미사용)
  - `앱`: iOS/Android, 별도 개발 중
- **일정**: 5/6~7 앱 완성 → 5/10 학원 데이터 수집 시작 → 5/10~24 통제실험 → 6/15 발표

---

## 2. 인프라

- Mac Studio ↔ dmlserver: SSH 키 기반 접속 설정 완료 (`ssh dmlserver@114.71.220.144`)
- 가상환경: `vocalserver/` (Python 3.14), 실행 전 `source vocalserver/bin/activate`
- DB: PostgreSQL 17, `vocal_db`, `localhost:5432`
- Alembic 현재 head: `a1b2c3d4e5f6`
- Cloudflare Tunnel 배포: **완료** (2026-05-09)
  - 외부 도메인: `https://api.vocal-fit.com` → `localhost:8000`
  - 터널 ID: `b929f13d-0429-4fe6-aaa2-c4056b38b16f` (이름: `vocal-fit-api`)
  - launchd 서비스 등록됨 (Mac 부팅 시 자동 실행)
  - HTTPS 자동 (Cloudflare 인증서)

---

## 3. 완료된 단계

### server 코어 (1~5단계)
- 인증: `POST /auth/signup`, `POST /auth/login` (JWT HS256, bcrypt)
- DB 테이블 7개: users, sessions, session_files, analysis_runs, analysis_results, reference_profiles, reference_metrics
- 세션 CRUD, 파일 업로드, 분석 요청/조회 API 16개 (Swagger: `localhost:8000/docs`)
- model_server `POST /analyze` 연동: 응답 JSON 전체를 `analysis_runs.result_json` (JSONB)에 저장
- 핵심 메트릭 3개 별도 저장: `voiced_ratio`, `processing_time_ms`, `duration_sec`
- 파일 저장 경로: `app/storage/users/{user_id}/sessions/{session_id}/{filename}`
- 통합 테스트 26/26 PASS (`test_integration.py`)
- API 문서: `docs/API.md`

### 노래방 기능 (0~3단계)
- 구버전 코드 완전 폐기: `songs.py`(구), `vocal.py`, `pitch_service.py`, librosa/soundfile/pydub 의존성 제거
- 새 Song 테이블: `id String(8)` PK (`"001"~"014"`), 13개 칼럼, dmlserver `songs.json`과 1:1 매핑
- `sessions.song_id`: `String(8)` FK → `songs.id`, nullable (기존 `song_title` 병행 유지)
- dmlserver 데이터 동기화: `bash scripts/sync_songs.sh`
- DB 시드: `python scripts/seed_songs.py` (upsert, 실제 파일 유무로 `has_lrc`/`has_pitch_guide` 재계산)
- 노래방 API 4개 구현 및 검증 8/8 PASS

---

## 4. 현재 데이터 상태

| 항목 | 상태 |
|------|------|
| `songs` 테이블 | 14행 (전체 곡 메타) |
| `has_lrc=true` | 004번만 (김범수 - 보고싶다) |
| `has_pitch_guide=true` | 004번만 |
| MR 음원 | 14곡 모두 (`app/storage/songs/audio/mr/`, 137MB) |
| `sessions.song_id` | 전체 NULL (노래방 통합 전) |
| `sessions` 행 수 | 21행 (테스트 데이터 포함) |
| Alembic head | `a1b2c3d4e5f6` |

나머지 13곡의 LRC/pitch_guide는 모델 페이지 작업 진행 중. 완성 시 `sync → seed` 재실행.

---

## 5. 남은 작업

### 4단계: 기존 분석 흐름 ↔ 노래방 통합
- `POST /sessions` body에 `song_id` 추가 (선택적, `String(8)`)
- `GET /sessions`, `GET /sessions/{id}` 응답에 `song` 정보 포함 (id, artist, title)
- 통합 테스트 업데이트

### 5단계: API 문서 갱신
- `docs/API.md`에 노래방 API 섹션 추가
- 세션 API 변경 사항 (`song_id`, `song` 필드) 반영

### 그 외
- 나머지 13곡 LRC/pitch_guide 완성 후 `bash scripts/sync_songs.sh && python scripts/seed_songs.py`
- Cloudflare Tunnel 배포 (시연 직전)
- 통제실험 데이터 수집 (5/10~)

---

## 6. 결정된 정책

- API prefix 없음 (`/auth`, `/sessions`, `/analysis`, `/songs`)
- `song_id`는 Session 테이블에만 — SessionFile, AnalysisRun에 추가 안 함
- master 음원 API 없음 (저작권)
- 사용자 WAV 영구 보관 (학습 데이터 활용 가능성 검증 후 정책 결정)
- 스키마 변경은 alembic만 (`Base.metadata.create_all` 사용 금지)
- 라즈베리파이/추가센서 코드 없음 (폐기 완료)

---

## 7. 알려진 이슈 / 주의사항

- model_server `/analyze` 응답의 `audio_info.duration_s` 키가 스펙 `duration_sec`과 다름 → `analysis_service.py`에서 `duration_s or duration_sec` fallback 처리
- model_server `status` 필드가 `"completed"` 아닌 `"success"` 반환 → 그대로 저장, `list_sessions`의 `analysis_status`는 `"completed"`로 매핑
- `lrc/parsed/{id}_aligned.json` 변종이 dmlserver에 존재 — 모델 페이지 산출물 확정 후 `sync_songs.sh` 패턴 재검토 필요. 현재는 `{id}.json`만 동기화
- `GET /songs/{id}/mr`에서 `curl -sI`(HEAD 요청) 시 `content-type: application/json` 오진 — GET 요청으로 확인해야 정상 (`audio/mpeg`)

---

## 8. 주요 파일 위치

```
vocal-server/
├── app/
│   ├── main.py                  # 라우터 등록 (songs 포함)
│   ├── models/models.py         # ORM: User, Session, Song, SessionFile, AnalysisRun, AnalysisResult
│   ├── routers/                 # auth, sessions, files, analysis, admin, songs
│   ├── services/analysis_service.py  # model_server /analyze 호출 + 결과 저장
│   ├── schemas/schemas.py       # Pydantic 스키마 (SongSummary 포함)
│   └── storage/
│       ├── users/               # 사용자 업로드 파일
│       └── songs/               # 노래방 데이터 (audio/mr, lrc/parsed, pitch_guide, meta)
├── alembic/versions/
│   ├── 3a6386a215ec_...py       # 초기 마이그레이션
│   └── a1b2c3d4e5f6_...py       # songs 테이블 교체 + sessions.song_id 추가
├── scripts/
│   ├── sync_songs.sh            # dmlserver → local 동기화
│   └── seed_songs.py            # songs.json → DB upsert
├── docs/API.md                  # 앱 개발자용 API 문서 (노래방 섹션 미반영)
├── test_integration.py          # 통합 테스트 26개
└── CLAUDE.md                    # 에이전트 행동 규칙 + Known Pitfalls
```

---

## 9. 운영 명령어

---

## 10. 향후 백로그 (5/9 후 발생 예정)

TrainingScreen 관련 작업이 5/9 데드라인 이후 vocal-server에도 영향 발생.
지금은 작업 없음. 시점 도래 시 아래 항목 참고.

### Phase 7: TrainingScreen 즐겨찾기 + 누적 시도 기록
- 신규 DB 테이블 (예: `training_sessions`, `training_attempts`)
- 신규 REST endpoint
- **알림**: vocal-app 페이지가 5/10 이후 요청 예정

### WebSocket vocal-server 경유 전환
- 현재: 앱 → dml-server 직접 (LAN, 인증 없음)
- 향후: 앱 → vocal-server proxy → dml-server (JWT 토큰 검증)
- **트리거**: 6/15 발표 전 또는 학원 데이터 수집(외부 네트워크) 직전
- 작업 범위: WebSocket endpoint 신규 + 토큰 relay + dml-server 호출

### ~~Cloudflare Tunnel 배포 + JWT 만료 정책 갱신~~ ✅ 완료 (2026-05-09)
- Cloudflare Tunnel: `https://api.vocal-fit.com` (launchd 자동 실행)
- JWT 만료: `JWT_EXPIRE_DAYS=7` 환경변수화

### dml-server score_mapper v2 자동 통과 (2026-05-11)
- vocal-server 코드 수정 0줄 — `result_json = data` 통째 통과 패턴으로 자동 호환
- v2 신규 필드 통과 검증: `score_mapper_version`, `scores_v2`, `scores_meta`, `academic_analysis_scores`, `reliability.{shown_v2, shown_v2_tiers, academic_only_v2, deferred_v2}` 모두 DB 저장 + 응답 정상
- `_ANALYZE_TIMEOUT` 120s → **180s** (cold start + 긴 wav 여유)

### GPT 이관 — HANDOVER.md 작성 (2026-05-12)
- Claude → GPT+Codex 이관 결정 (토큰 사용량 + 캐시 버그)
- `HANDOVER.md` 신규 작성 — GPT 측이 단일 문서로 컨텍스트 복원 가능 (16 섹션)
- 추천 view 순서: `HANDOVER.md` → `CLAUDE.md` → `PROGRESS.md` → `docs/api.md` → `docs/admin_reference.md`
- 6환경 (dml-server / vocal-app / vocal-server × gpt.ai + Codex) 유지

### training-analyze v2 필드 통과 수정 (2026-05-12)
- POST `/sessions/{id}/training-analyze`가 화이트리스트 8개 필드만 반환 → v2 신규 5개(`score_mapper_version`, `scores_v2`, `scores_meta`, `low_confidence_items`, `chunk_duration_s`) 누락 사례 발견
- **통째 통과 + `run_id` 제외 + `session_id`/`chunk_meta` 추가** 패턴으로 전환 (`/analyze`와 일관성 확보)
- 실측: dml-server `/analyze-chunk` 11 keys → vocal-server 12 keys (`-run_id +session_id +chunk_meta`)
- §15-3 운영 규칙 적용 범위가 **모든 dml-server endpoint** (단순 `/analyze`뿐 아니라 `/analyze-chunk` 등)임을 학습. 향후 신규 dml-forward endpoint 추가 시 처음부터 통째 통과 패턴 권장.

### dml-server StreamingResponse 자동 통과 (2026-05-12, P1-2)
- dml-server `/_test_stream?duration=130` (chunked + leading whitespace keepalive) 실측 검증
- 결과: HTTP 200 / 130.7s (Cloudflare 524 발생 안 함) / `Transfer-Encoding: chunked` / 첫 30 bytes `'                           {"t'` (leading whitespace ping) / `response.json()` 정상 파싱
- httpx 동기 `httpx.post(...).json()` 패턴이 leading whitespace를 RFC 7159 따라 자동 허용 → vocal-server 코드 수정 0
- **Cloudflare timeout 수치 확정**: 130s 응답 통과 → Cloudflare edge timeout은 **TTFB 기준** (first byte 보내면 그 뒤로 무관). 이전 5/11 측정 127s 524는 dml-server가 첫 byte를 끝까지 안 보내서 발생한 것.
- 백로그 (Cloudflare 100s 한계)는 StreamingResponse 도입으로 해결됨 — vocal-server 측 추가 작업 없음

---

## 9. 운영 명령어

### 5/10 운영 — 실행 방식 + 토글 (현재 상태)

| 항목 | 상태 |
|------|------|
| 실행 방식 | **수동 백그라운드** (`launchd` 등록 ❌). 부모 프로세스 종료 후 PPID=1로 reparent됨 |
| 재부팅 시 자동 시작 | ❌ — Mac Studio 재부팅 시 정우가 `bash scripts/restart_server.sh` 직접 실행 |
| 실행 명령어 | `nohup vocalserver/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &` |
| `--reload` 플래그 | ❌ — 코드 변경 시 수동 재시작 필요 |
| cloudflared | 별개 launchd 서비스. vocal-server 재시작과 무관 (재시작 4~5초 동안만 502) |
| 진행 중인 요청 | 재시작 스크립트가 SIGTERM(graceful) → 10초 대기 → SIGKILL fallback. 정상 응답은 끊김 최소 |

#### 안전 재시작
```bash
cd /Users/kimjeongwoo/vocal-server/vocal-server
bash scripts/restart_server.sh
# graceful shutdown (~2s) + 새 프로세스 + /admin/health 200 대기 (~2s) = 총 ~5s
```

#### SIGNUP_ENABLED 토글 (5/10 학원 배포 직전 OFF)
```bash
# 외부인 가입 차단 (학원 실험 시작 시)
bash scripts/signup_toggle.sh off
# → .env 수정 + 안전 재시작 + 검증 (curl POST /auth/signup → 403)

# 다시 허용 (실험 종료 후)
bash scripts/signup_toggle.sh on
# → 검증 (curl POST /auth/signup → 201 또는 400 already-exists)
```

#### 수동 검증 (스크립트 안 쓰고)
```bash
# SIGNUP_ENABLED 상태 확인
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.vocal-fit.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"signup_check@test.com","password":"check1234","nickname":"check"}'
# 201 또는 400 → ENABLED=true / 403 → ENABLED=false

# 서버 + cloudflared 모두 살아있는지
curl -s -o /dev/null -w "vocal-server: %{http_code}\n" https://api.vocal-fit.com/admin/health
ps aux | grep -E "uvicorn app.main|cloudflared" | grep -v grep | wc -l  # 2 기대
```

#### Known limits
- **재부팅 시 미기동**: Mac Studio 정전·강제재부팅 후에는 정우가 SSH/직접 접속하여 `restart_server.sh` 실행 필요. (Phase 후속: launchd plist 등록 검토)
- **rate limit**: 메모리 기반이라 vocal-server 재시작 시 admin login 실패 카운터 초기화

---

## 9. 운영 명령어

```bash
# 서버 시작 (vocal-server/ 에서)
source vocalserver/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 데이터 동기화 + 시드
bash scripts/sync_songs.sh
python scripts/seed_songs.py

# DB 접속
/opt/homebrew/Cellar/postgresql@17/17.8/bin/psql vocal_db

# DB 백업
/opt/homebrew/Cellar/postgresql@17/17.8/bin/pg_dump vocal_db > /tmp/backup_$(date +%Y%m%d).sql

# 마이그레이션
alembic revision --autogenerate -m "설명"
alembic upgrade head
alembic current

# 통합 테스트
python test_integration.py

# pycache 클리어 (reload 미반영 시)
find app -name __pycache__ -exec rm -rf {} +
```
