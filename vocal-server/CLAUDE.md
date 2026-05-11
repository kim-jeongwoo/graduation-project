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
| 가상환경 | `../vocalserver/` (Python 3.14) — repo 루트 기준 |

```bash
# 서버 실행 (vocal-server/ 안에서)
cd /Users/kimjeongwoo/vocal-server/vocal-server
source ../vocalserver/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

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
- `GET /analysis/{run_id}`, `/results`
- `GET /songs`, `GET /songs/{id}`, `/lrc`, `/pitch-guide`, `/mr` (인증 불필요)
- `GET /admin/dashboard`, `/users`, `/events/stream` (SSE)

**파일 구조:**
```
vocal-server/          ← 이 폴더 (모노레포 내 서브프로젝트)
  app/
    main.py            # 라우터 등록
    models/models.py   # ORM: User, Session, Song, SessionFile, AnalysisRun, AnalysisResult
    routers/           # auth, sessions, files, analysis, admin, songs
    services/          # analysis_service.py
    storage/           # 사용자 업로드 + 노래방 데이터 (gitignored)
  alembic/             # DB 마이그레이션
  alembic.ini
  scripts/
    sync_songs.sh      # dmlserver → local 동기화
    seed_songs.py      # songs.json → DB upsert
  docs/
    api.md             # 앱 개발자용 API 문서
  songs/               # 테스트용 vocals.wav (gitignored)
  test_integration.py
  PROGRESS.md          # 진행 현황 (진실의 원천)
```

---

## 에이전트 행동 규칙 (Karpathy 4원칙)

### 1. Think Before Coding (추측 금지)
- 가정은 명시적으로 진술. 불확실하면 추측하지 말고 질문.
- 해석이 여러 개 가능하면 조용히 하나 고르지 말고 모두 제시.
- 더 단순한 방법이 있으면 그걸 제안 (push back).
- 혼란스러우면 멈추고 뭐가 불명확한지 명시 후 질문.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.

### 2. Simplicity First (단순함 우선)
- 요청한 것만 구현. 추측성 기능 금지.
- 일회성 코드에 추상화 만들지 말 것.
- 요청되지 않은 "유연성", "설정 가능성" 추가 금지.
- 일어날 수 없는 시나리오에 에러 핸들링 추가 금지.
- 200줄로 될 걸 1000줄로 만들지 말 것. 시니어 엔지니어가 보면 과한가? 그러면 단순화.

### 3. Surgical Changes (외과적 수정)
- 수정해야 할 곳만 건드림. 인접 코드/주석/포맷 임의 개선 금지.
- 망가지지 않은 것 리팩토링 금지.
- 기존 스타일이 마음에 안 들어도 그 스타일을 따를 것.
- 무관한 죽은 코드 발견 시 — 언급만 하고 삭제는 하지 말 것.
- 단, 내 수정 때문에 생긴 고아(unused import/variable)는 정리.
- 파일 수정 전 뭘 바꿀 건지 먼저 설명.
- **테스트: 모든 수정 라인이 사용자 요청과 직접 연결되는가?**

### 4. Goal-Driven Execution (목표 기반 실행)
- 명령형 작업을 검증 가능한 목표로 변환.
  "버그 고쳐" → "버그 재현하는 테스트 작성 후 통과시킴"
  "검증 추가" → "잘못된 입력에 대한 테스트 작성 후 통과시킴"
- 다단계 작업은 짧은 계획 진술:
  1. [단계] → 검증: [체크]
  2. [단계] → 검증: [체크]
- 강한 성공 기준이 있으면 자율 루프, 약하면 매번 확인 요청.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.
- 새 엔드포인트는 '정상 케이스 + 에러 케이스 테스트 통과'까지가 완료.

### 토큰 효율
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.

### 운영 주의사항
- 되돌릴 수 있는 작업은 물어보지 말고 바로 진행. 삭제·전송 같은 비가역 작업만 확인.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.
- 터미널 멀티라인 주의 — Python 코드는 `.py` 파일로 만들어 실행. `-c` 인라인 멀티라인은 쉘 오염을 일으킨다.
- 서버 재시작 후 최소 55초 대기 (startup 포함).
- pycache 클리어 — reload가 반영 안 될 때 `find app -name __pycache__ -exec rm -rf {} +` 후 재시작.
- 인증 불필요 엔드포인트 — songs의 list/get/lrc/pitch-guide/mr는 인증 없음.
- 스키마 변경은 alembic만 (`Base.metadata.create_all` 사용 금지).

---

## 절대 규칙

- DB 테이블 DROP, 데이터 DELETE는 반드시 사용자 확인 후 실행
- `app/storage/songs/` 디렉토리 파일 삭제 금지 (MR 음원, LRC, 피치 가이드)
- `.env` 파일 내용 출력/로그 금지 (SECRET_KEY 포함)
- `git push`, `git reset --hard` 실행 전 확인
- Alembic 도입 후 `Base.metadata.create_all()` 사용 금지

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

- [2026-05-03] [서버 재시작] uvicorn 재시작 시 "Address already in use" 발생하면
  이전 프로세스가 살아있는 것. --reload가 켜져 있어도 코드 변경이 반영 안 될 수 있음.
  해결: `pkill -f "uvicorn app.main"` 후 재시작.
  또는 `lsof -i :8000`으로 PID 확인 후 kill.

- [2026-05-02] [서버/DB] alembic 도입 후에는 `Base.metadata.create_all()` 사용 금지.
  스키마 변경은 무조건 `alembic revision + upgrade`로만.
  이중 관리 시 환경 간 스키마 불일치 발생.

- [2026-05-02] [DB 마이그레이션] NOT NULL 칼럼을 기존 데이터 있는 테이블에 추가할 때
  alembic autogenerate가 server_default를 자동 생성하지 않음.
  마이그레이션 파일에 `server_default` 수동 추가 필요.

- [2026-05-02] [데이터 동기화] lrc/parsed/{id}_aligned.json 변종이 dmlserver에 존재.
  모델 페이지 산출물 확정 후 sync 패턴 재검토 필요. 현재는 {id}.json만 동기화.

- [2026-05-03] [모노레포] vocal-server 코드는 `vocal-server/` 서브폴더 안.
  서버 실행/테스트는 반드시 `cd vocal-server/vocal-server/` 후 진행.
  scripts/sync_songs.sh, seed_songs.py도 vocal-server/vocal-server/ 기준으로 실행.

- [2026-05-04] [분석 상태] dml-server는 status='success' 반환, vocal-server DB에는 그대로 'success' 저장.
  새 코드에서 분석 상태 분기할 때 'success'와 'completed' 둘 다 고려할 것.
  (dml-server response 직후 처리 vs DB에서 읽은 후 처리 모두 해당)
  이번 작업에서 캐싱 조건이 'completed'만 체크해 'success' 누락됐던 사례 있음.

- [2026-05-09] [Cloudflare Tunnel] `cloudflared service install`이 plist에 `tunnel run` 인자를
  자동으로 안 박는 경우 있음. 증상: 로그에 'Use cloudflared tunnel run to start tunnel' 무한 반복.
  해결: plist 수동 작성으로 ProgramArguments에 `--config /etc/cloudflared/config.yml tunnel run` 명시.
  또는 config.yml을 `/etc/cloudflared/` 시스템 위치에 복사 후 root 권한 접근 가능하게.
  현재 설정: `~/.cloudflared/config.yml`, 터널 ID `b929f13d-0429-4fe6-aaa2-c4056b38b16f`.

- [2026-05-11] [Cloudflare 100s 한계] Cloudflare Tunnel 무료/Pro 플랜은 origin timeout 100s 고정.
  vocal-server `_ANALYZE_TIMEOUT`을 늘려도 Cloudflare가 먼저 끊음 (HTTP 524).
  긴 응답 (>100s)은 청크 분할 또는 비동기 처리 필요.
  이전 작업에서 `_ANALYZE_TIMEOUT` 120s → 180s 늘렸지만 Cloudflare 한계는 별도.
  v2 score_mapper로 모델 cold start 시 127s 이상 가능 — 짧은 wav (90s 이내) 권장.
  *(2026-05-12 갱신: dml-server StreamingResponse 도입으로 TTFB 기준 우회됨 — 위 한계 사실상 해소)*

- [2026-05-12] [응답 화이트리스트 위험] dml-server forward endpoint 응답을 화이트리스트(특정 키만 추출)로
  구현하면 dml-server schema 변경 시 신규 필드가 자동 누락됨. /analyze처럼 통째 통과 패턴(필요한 것만 pop,
  나머지 dict 그대로) 권장. 이번에 training-analyze가 화이트리스트 8개로 구현돼 있어 v2 신규 필드 5개
  (score_mapper_version, scores_v2, scores_meta, low_confidence_items, chunk_duration_s) 누락 발생 →
  통째 통과 + run_id만 제외로 전환.
