# vocal-server 진행 상황 인수인계

작성일: 2026-05-02. 새 대화 시작 전 이 파일부터 읽을 것.

---

## 1. 시스템 개요

- **프로젝트**: 보컬 발성 분석 (9개 항목 AI 피드백) + 노래방 기능 (MR 반주 + LRC 가사 + 음정 가이드)
- **서버 구성**:
  - `server` (Mac Studio): FastAPI + PostgreSQL, `localhost:8000`
  - `model_server` (dmlserver, `114.71.220.144:8001`): AI 분석 처리 `/analyze` 엔드포인트
  - `앱`: iOS/Android, 별도 개발 중
- **일정**: 5/6~7 앱 완성 → 5/10 학원 데이터 수집 시작 → 5/10~24 통제실험 → 6/15 발표

---

## 2. 인프라

- Mac Studio ↔ dmlserver: SSH 키 기반 접속 설정 완료 (`ssh dmlserver@114.71.220.144`)
- 가상환경: `vocalserver/` (Python 3.14), 실행 전 `source vocalserver/bin/activate`
- DB: PostgreSQL 17, `vocal_db`, `localhost:5432`
- Alembic 현재 head: `a1b2c3d4e5f6`
- Cloudflare Tunnel 배포: 시연 직전 예정 (미완료)

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
