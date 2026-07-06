# VERIFY — vocal-server / vocal-app 저장소·서버 상태 점검

- 점검 일시: 2026-07-07
- 범위: **read-only**. 수정·추측 없음. `.env` 비밀값(키/비밀번호/해시)은 미출력, 호스트 방향 등 구조 정보만 기록.
- 근거는 `파일:라인` 또는 명령 결과로 표기.

---

## [0] 저장소 위치

| 항목 | 경로 | git repo |
|------|------|----------|
| vocal-server (모노레포 루트) | `/Users/kimjeongwoo/vocal-server` | ✅ `.git` 있음 |
| ├ FastAPI 실제 코드 | `/Users/kimjeongwoo/vocal-server/vocal-server/` (main.py, app/, alembic, requirements.txt) | (루트 repo에 포함, 별도 .git 없음) |
| ├ dml-server 코드 | `/Users/kimjeongwoo/vocal-server/dml-server/` | (동상) |
| ├ 가상환경 | `/Users/kimjeongwoo/vocal-server/vocalserver/` (Python 3.14 venv) | — |
| vocal-app (Expo 앱) | `/Users/kimjeongwoo/vocal-app` | ✅ `.git` 있음 |

- **vocal-server, vocal-app 둘 다 이 Mac에 존재.**
- 확정: 프로덕션 FastAPI 서버 실행 위치는 중첩 경로 `vocal-server/vocal-server/`
  (`vocal-server/CLAUDE.md`: `cd /Users/kimjeongwoo/vocal-server/vocal-server` → `uvicorn app.main:app ... --port 8000`).
- 참고로 중첩 `vocal-server/vocal-app/`(no .git)와 top-level `/Users/kimjeongwoo/vocal-app`(git) 이 별도로 존재.
  항목 9·10은 git repo인 top-level `/Users/kimjeongwoo/vocal-app`를 기준으로 확인.
- 그 외 홈에 백업/파생 디렉토리 다수: `vocal-server-backup-20260503/`, `vocal-server-data-cleanup-backups/`,
  `vocal-app-v1-open-test/`(no .git), `vocal-admin-server/`(빈 디렉토리), 편집기 배포 디렉토리들(아래 [4]).

---

## [운영 상태]

### 1. production vocal-server 실행 방식 → **수동 nohup uvicorn (현재 미기동/DOWN)**

- **launchd 아님**: `launchctl list | grep -i vocal` → `com.vocalfit.guide-editor`, `com.vocalfit.song004-editor` **2개뿐**.
  vocal-server/uvicorn/8000용 plist 없음 (`~/Library/LaunchAgents`, `/Library/Launch*` grep 결과 editor 2개만).
- **tmux 아님**: `tmux` 미설치 (`command not found: tmux`).
- **실행 방식 = 수동 nohup**: `vocal-server/vocal-server/scripts/restart_server.sh:31`
  `nohup "$VENV_BIN/uvicorn" app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn_new.log 2>&1 &`
  (graceful: `pkill -TERM -f "uvicorn app.main"` `restart_server.sh:15`; health: `/admin/health` `restart_server.sh:37`).
- **현재 상태 = 미기동**:
  - `pgrep -fl "uvicorn app.main"` → 없음.
  - `lsof -iTCP -sTCP:LISTEN`에 :8000 없음 (리스닝: 8784 song004-editor, 8788 guide-editor, 3000 VS Code).
  - `curl localhost:8000/admin/health` → **HTTP 000 (무응답)**.
  - `/tmp/uvicorn_new.log` 파일 없음.
- 결론: 자동 재기동 수단 없음(수동 실행). 프로세스가 죽어 있고, 그래서 아래 [3]에서 admin이 502.

### 2. MODEL_SERVER_URL 방향 → **터널/도메인 경유 (`https://dml.vocal-fit.com`)**

- `/Users/kimjeongwoo/vocal-server/.env` `MODEL_SERVER_URL` = `https://dml.vocal-fit.com` (호스트 부분만; 값 전체 미노출).
- **IP 직결(114.71.220.144) 아님**, 도메인(dml.vocal-fit.com) 경유.
- (주의) `vocal-server/vocal-server/CLAUDE.md`·`README` 등 문서에는 과거 `114.71.220.144:8001` 표기가 남아 있으나,
  실제 런타임 `.env` 값은 위 도메인. 홈 파일명 `ssh-copy-id dmlserver@114.71.220.144`도 SSH용 흔적일 뿐 MODEL_SERVER_URL과 별개.

### 3. admin.vocal-fit.com/admin/users → **HTTP 502 (백엔드 다운), 검색 input 미렌더**

- `curl -s https://admin.vocal-fit.com/admin/users` → **HTTP 502**, body size 16 (Cloudflare 에러). 검색 input 렌더 안 됨(서버 다운이 원인).
- 502의 원인은 항목 1 — vocal-server(:8000) 미기동. admin은 같은 FastAPI(:8000)에 라우팅됨(아래 [4]).
- **코드 상 Phase A-6 검색 input은 repo에 이미 존재**:
  `vocal-server/vocal-server/app/templates/admin/users.html:85-86`
  `<input type="search" name="q" ... placeholder="닉네임 또는 이메일 검색">`, 검색 버튼 `:99`.
- 판단: Phase A-6는 **코드에는 반영됨(커밋됨)**. 단, **프로덕션이 502(다운)라 restart 반영 여부를 라이브로 확인 불가.**
  현재 상태로는 "production에 반영/restart 완료"를 확증할 수 없음(서버를 띄워야 검증 가능).

---

## [도메인/계정]

### 4. guide-editor / song004-editor → **vocal-server repo 범위 밖의 별도 서비스**

- 라우팅은 **cloudflared 단일 터널**(`/etc/cloudflared/config.yml`, 활성 프로세스 `cloudflared --config /etc/cloudflared/config.yml tunnel run`, tunnel id `b929f13d-...`). **nginx 없음**(시스템에 nginx 설정 파일 없음).
- ingress (`/etc/cloudflared/config.yml`):
  - `api.vocal-fit.com` → `http://localhost:8000` (vocal-server, **현재 다운**)
  - `admin.vocal-fit.com` → `http://localhost:8000` (동일 vocal-server의 admin 라우터, **현재 다운**)
  - `song004-editor.vocal-fit.com` → `http://127.0.0.1:8784` (**UP**)
  - `guide-editor.vocal-fit.com` → `http://127.0.0.1:8788` (**UP**)
  - `expo-dev.vocal-fit.com` → `http://127.0.0.1:8081`
- editor 2종은 **별도 배포·별도 프로세스·별도 launchd**:
  - launchd: `~/Library/LaunchAgents/com.vocalfit.guide-editor.plist`, `com.vocalfit.song004-editor.plist`.
  - 실행 파일: `~/guide-editor-deploy/current/serve_guide_editor.py --port 8788`,
    `~/song004-editor-deploy/current/serve_editor_public.py --port 8784` (ps 확인, launchd로 기동 중).
  - 배포/백업 디렉토리: `~/guide-editor-deploy`, `~/guide-editor-backups`, `~/song004-editor-deploy`, `~/song004-editor-backups`, `~/editor-backups`.
- vocal-server repo 내부에는 `guide-editor`/`song004-editor` 호스트 참조 없음(코드/설정 grep 무매치).
- 결론: **두 editor 도메인은 vocal-server repo 범위 밖의 독립 서비스.** 같은 cloudflared 터널만 공유.

### 5. 등록 사용자 목록·role → **총 21명, 전원 `role='user'` (평가자 전용 role 없음)**

- DB `vocal_db.users` 컬럼: `user_id, email, nickname, role, created_at` (+ 해시 컬럼은 조회/출력 안 함).
- **role 분포: `user` 21명 전부.** 관리자/평가자 등 구분 role 없음(평가자는 이메일/닉네임 관례로만 구분).
- **전용 user seed 스크립트 없음** (scripts에는 `seed_songs.py`만 존재 — 곡용). 사용자는 signup 경로로 생성된 것으로 보임.
- 사용자 목록 (nickname | email local-part | role | 생성일; 비밀번호/해시 미출력):
  - 2026-05-03 생성(16): 대표(director), 학생1(student01), 테스트(vocal2026), 평가자2(evaluator02), 평가자3(evaluator03),
    평가자5(evaluator05), 학생5(student05), 팀원4(team04), 학생3(student03), 학생4(student04), 팀원2(team02),
    평가자4(evaluator04), 팀원3(team03), 팀원1(team01), 평가자1(evaluator01), 학생2(student02)
  - 2026-05-24 생성(5): student06, student07, student08, student09, student10
- 정리: student01~10(10명) 외 11명 = **평가자 evaluator01~05(5), 팀원 team01~04(4), 대표 director(1), 테스트 vocal2026(1)**.
- **평가자 계정 포함 여부: 포함됨** (evaluator01~05, 닉네임 평가자1~5). 단 role은 모두 `user`로, 권한상 일반 사용자와 동일.

---

## [데이터/버그]

### 6. student02 크래시 원인 result_json 구조 → **timeline_scores[].scores 내 4개 지표가 JSON `null`**

- student02(user_id `8ebad94f-...`) analysis_runs 13건, 모두 `status='success'`, top-level 키·타입 일관(이상 없음).
- `analysis_runs.result_json` 타입: `jsonb`.
- **문제 필드**: `result_json.timeline_scores[i].scores` 안에서 아래 4개 indicator 값이 **object가 아니라 `null`**:
  - `3_vocal_fold_contact`, `4_breathiness`, `6_soft_palate`, `8_tongue_tension`
  - student02 기준: 각 지표가 **366개 청크 중 258개에서 `null`**, 108개에서만 object.
  - 정상 object 형태 = `{ tier, ai_score, rounded_score }` (문자열/숫자).
- 나머지 필드(다른 지표 값, `start_sec/end_sec/chunk_duration_s`=number, `lrc_text`=string, `low_confidence_items`=array,
  상위 `scores/scores_v2/indicators/timeline_metadata` 등)는 타입 일관, 이상 없음.
- **student02 국한 아님 — 전역 패턴**: 여러 사용자 result_json에서 동일 4개 지표가 청크별 `null`
  (예: vocal2026 null 4311/obj 1541, student03 2140/680, student02 1032/432 …).
  → dml-server가 신뢰도 부족한 청크에서 해당 4개 지표를 `null`로 반환하는 정상 동작으로 보임.
- 서버 측은 `null` 가드 있음: `vocal-server/vocal-server/app/routers/sessions.py:294`
  `if not isinstance(after, dict): continue`. → **앱(프론트) 파서가 이 `null`을 object로 가정하면 크래시** (아래 [10]과 연결:
  SectionStabilityChart가 소비하는 v2 4개 지표 = 정확히 이 4개).
- (read-only: 값 자체 대량 조회 없이 타입/구조/개수만 확인.)

### 7. training-analyze 에러 status 매핑 → 코드 재확인 (일치, 단 timeout 외 연결오류도 504)

`vocal-server/vocal-server/app/routers/sessions.py` (`POST /{session_id}/training-analyze`, `:180`):

| dml 응답/상황 | vocal-server 반환 | 근거 |
|---|---|---|
| `httpx.TimeoutException` | **504** "분석 서버 응답 시간 초과" | `sessions.py:224-230` |
| `httpx.RequestError`(연결 실패 등) | **504** "분석 서버에 연결할 수 없음" | `sessions.py:231-238` |
| dml `400` | **400** (detail 통과) | `sessions.py:246-252` |
| dml `>= 500` | **502** "분석 서버 오류" | `sessions.py:254-255` |
| 기타 non-2xx | **502** `분석 서버 비정상 응답: HTTP {code}` | `sessions.py:257-258` |
| 응답 JSON 파싱 실패 | **502** "분석 서버 응답 파싱 실패" | `sessions.py:260-263` |

- 요청서 매핑(400→400, 5xx→502, timeout→504)과 일치. **추가 사실**: timeout뿐 아니라 연결오류(RequestError)도 504로 매핑됨.

---

## [git/정리]

### 8. git 상태 (repo: `/Users/kimjeongwoo/vocal-server`)

- `git remote -v`: `origin git@github.com:kim-jeongwoo/graduation-project.git` (fetch/push 동일).
- `git status -sb`: `## main...origin/main [앞: 1]` — **origin/main 대비 1 커밋 ahead** (`rev-list @{u}...HEAD` = `0  1`).
  - ahead 커밋: `cc652f6 docs: add Claude handover code state`.
- **untracked**: `vocal-server/docs/HANDOVER_TO_CLAUDE.md` (1건).
- **추적(tracked) .bak 파일 2건**:
  - `vocal-server/app/routers/admin.py.bak-20260524-003229`
  - `vocal-server/app/templates/admin/users.html.bak-20260524-003229`
  - (둘 다 Phase A-6 admin 검색 작업(20260524) 직전 백업으로 보임. git에 커밋되어 추적 중.)
- **untracked/미추적 .bak**: 없음.
- push 안 함 (지시대로).

---

## [vocal-app repo — `/Users/kimjeongwoo/vocal-app`]

### 9. training-analyze 에러 처리 분기 → **HTTP status + 200+body.status 분기 둘 다 잔존**

- `trainingAnalyze()` `src/api/sessions.ts:169-185`: `apiClient.post(... timeout: 30000)` 후 `return res.data`.
  → 비-2xx(400/502/504)는 axios가 throw, 호출측으로 전파. (함수 자체엔 HTTP 코드별 분기 없음.)
- **200 + body.status 분기 잔존**:
  - `ANALYZE_SUCCESS_STATUSES = {success, completed, complete, done}` `sessions.ts:10`,
    `ANALYZE_FAILURE_STATUSES = {failed, invalid, no_voice, error}` `sessions.ts:11`.
  - `isAnalyzeSuccessStatus/isAnalyzeFailureStatus` `sessions.ts:65-72`, `assertAnalyzeBodyStatus`(body.status로 throw) `sessions.ts:91-94`.
  - training 전용: `normalizeTrainingAnalyzeStatus`가 `body_status ?? bodyStatus ?? status` 사용
    `src/screens/home/TrainingScreen.tsx:198-201`, `getTrainingAnalyzeReason` `:205-215`.
  - 응답 타입에 `status`, `body_status` 필드 존재 `sessions.ts:151-167`.
- HTTP status 자체도 읽음(전용 502/504 분기는 아님, generic): `getApiErrorInfo`가 `response.status`/`err.status`를 code로 추출
  `TrainingScreen.tsx:55-66`. client 인터셉터는 401만 특별 처리 + status/code/apiMeta 부착 `src/api/client.ts:90-92,128`.
- 결론: 앱은 **HTTP 상태코드를 일반적으로 읽으면서도, 200+body.status 성공/실패 문자열 분기가 그대로 남아 있음.**
  502/504를 구분해 다르게 처리하는 전용 분기는 확인되지 않음. (서버 에러 정책을 HTTP 코드 기반으로 확정하려면 이 body.status 분기 정리 필요 — 사실만 보고, 수정 없음.)

### 10. SectionStabilityChart / VocalRecorder / ACTIVE_PLAN

- **SectionStabilityChart**: EvalResultScreen에 **실제 노출됨**.
  - import `src/screens/home/EvalResultScreen.tsx:17`.
  - 렌더 `EvalResultScreen.tsx:907-913` — `insightSection` 안에서 **조건 없이** 렌더:
    `<SectionStabilityChart timelineScores={result.timelineScores ?? []} activeIndicatorKeys={activeStabilityKeys} />`.
  - 컴포넌트 정의 `src/components/eval/SectionStabilityChart.tsx:57`.
  - 연계: 같은 화면 안내문(`EvalResultScreen.tsx:899-902`)이 v2에서 4지표(호흡 소리/성대 접촉/연구개/혀 경직도)를 명시 —
    **항목 6의 null 4개 지표와 정확히 동일**. 이 차트가 timeline_scores의 그 4개 지표를 소비.
- **VocalRecorder 오디오 설정** `src/services/audio/recorder.ts:9-19`:
  - `SAMPLE_RATE = 16000`, `CHANNELS = 1`(mono), `BITS_PER_SAMPLE = 16`, `audioSource = 6`(VOICE_RECOGNITION), `wavFile = 'recording.wav'`.
  - 피치 검출도 동일 16000: `src/services/audio/pitchDetector.ts:3` `YIN({ sampleRate: 16000, threshold: 0.10 })`.
  - 클래스 정의 `recorder.ts:62`, `AudioRecord.init(...)` `recorder.ts:151`.
- **`.codex/ACTIVE_PLAN.md`**: **존재** — `/Users/kimjeongwoo/vocal-app/.codex/ACTIVE_PLAN.md` (263,258 bytes, 2026-06-20).

---

## 요약 (사실만)

- 프로덕션 vocal-server(:8000)는 **수동 nohup uvicorn 방식이며 현재 미기동** → `api`·`admin` 모두 **502**.
- 따라서 Phase A-6(admin 검색) 코드는 **repo엔 존재**하나 **프로덕션 반영은 라이브 확인 불가**(서버 다운).
- MODEL_SERVER_URL은 **도메인(dml.vocal-fit.com) 경유**, IP 직결 아님.
- editor 2종은 **별도 서비스**(별도 launchd/포트), cloudflared 터널만 공유. nginx 없음.
- 사용자 21명 **전원 role=user**, 평가자(evaluator01~05) 포함되나 별도 role 아님.
- student02 크래시 후보 = **timeline_scores[].scores의 4개 지표 null**(전역 패턴). 서버는 dict 가드 있음, 앱은 해당 4지표를 SectionStabilityChart로 소비.
- training-analyze 서버 매핑: 400→400 / 5xx→502 / timeout·연결오류→504 (코드 확인).
- 앱은 HTTP status와 **200+body.status 분기를 둘 다** 보유.
- git: origin/main 대비 **1 ahead**(docs 커밋), untracked `HANDOVER_TO_CLAUDE.md`, tracked `.bak` 2건(admin.py, users.html; 20260524). push 안 함.

---

## [실행 로그] 재기동 + 검증 + git 백업 (2026-07-07)

> 아래는 위 점검 이후 **실제로 실행한 작업**의 결과. (앞 섹션의 "DOWN/502"는 실행 전 상태 스냅샷.)

### 재기동 (요청 1)
- `bash scripts/restart_server.sh` → `[restart] 기동 완료 (3s, /admin/health 200)`.
- 프로세스 지속 확인: PID 1055 (`.../vocalserver/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`), `:8000 LISTEN`.
- 로컬 health: `curl localhost:8000/admin/health` → `{"admin":"ok"}` HTTP **200**.

### 라이브 검증 (요청 2)
- `https://api.vocal-fit.com/admin/health` (터널) → `{"admin":"ok"}` HTTP **200**.
- `https://admin.vocal-fit.com/admin/users` (미인증) → HTTP **401** (이전 502 → 서버 기동됨, 세션 인증 요구).
  - admin 인증 = SessionMiddleware 쿠키 (`admin.py:259-303`, POST `/admin/login`에 `ADMIN_PASSWORD` 비교).
- **Phase A-6 라이브 확정**: 로컬에서 `/admin/login`(HTTP 302 성공) → 쿠키로 `/admin/users` GET → HTTP **200**,
  `<title>사용자 관리 — Vocal Fit Admin</title>`, 검색 input 렌더 확인
  (`name="q"`, `placeholder="닉네임 또는 이메일 검색"`, `검색` 버튼).
  - 기능 확인: `/admin/users?q=student02` → student02만 필터되어 반환(다른 student0X 미매치). 검색 동작 정상.
  - (사용한 세션 쿠키 파일은 검증 후 삭제. 비밀번호는 미노출.)
- **서버→dml 경로 헬스**: `https://dml.vocal-fit.com/health` → HTTP **200** (MODEL_SERVER_URL 대상, dml-server `server.py:65`).
  → vocal-server가 사용하는 dml 도메인/터널 정상.

### launchd 등록 초안 (요청 3 — 작성만, 미적용)
- 초안 파일: `docs/com.vocalfit.vocal-server.plist.draft` (Label `com.vocalfit.vocal-server`, RunAtLoad/KeepAlive, WorkingDirectory `vocal-server/vocal-server`, venv uvicorn, :8000).
- **미적용** — `~/Library/LaunchAgents`에 복사/`launchctl load` 안 함. 정우 승인 후 초안 내 [적용 절차] 참고.
- 목적: 현 수동 nohup 방식의 재부팅 시 미기동 한계 보완.

### git 백업 (요청 4·5, repo `/Users/kimjeongwoo/vocal-server`)
- **[4]** `cc652f6`(ahead 1) → `git push origin main` 성공 (`8e939c0..cc652f6`).
- **[5]** 추가 커밋 2건 후 push (`cc652f6..edc29a5`):
  - `0ce8d73` chore: remove tracked admin .bak snapshots (admin.py.bak / users.html.bak 20260524 제거).
  - `edc29a5` docs: track vocal-server HANDOVER_TO_CLAUDE.md (untracked였던 파일 add).
  - 현재 `main` = `origin/main` 동기화 완료.
- 미추적으로 남긴 파일(요청 범위 밖이라 커밋 안 함): `docs/VERIFY_vocal-server.md`(본 문서), `docs/com.vocalfit.vocal-server.plist.draft`.

### 요청 6 — vocal-app push (대기: repo URL 필요)
- repo `/Users/kimjeongwoo/vocal-app` 상태: **remote 없음**, 브랜치 `master`(HEAD `f93270f`, clean), 태그 `v1.0.0-pre-v2`·`v2.x-gpt-final` **둘 다 존재**.
- 정우가 GitHub repo URL 제공 시 실행 예정(아직 미실행):
  ```
  git remote add origin <URL>
  git push -u origin master
  git push origin v1.0.0-pre-v2 v2.x-gpt-final
  ```
