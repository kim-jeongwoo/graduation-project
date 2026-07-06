# CLAUDE.md — dml-server (AI 모델 / 데이터 파이프라인)

> Legacy Claude handover. Current Codex/GPT operating rules live in `AGENTS.md`; stale manual/nohup service commands here are superseded by `PROJECT_LOG.md` §15 latest entries and `dml-server.service`.

## 프로젝트 한 줄 요약
MIC 음성으로 EGG 추정 + 노래방 데이터 파이프라인. 순천향대 IoT학과 졸업 프로젝트.
GitHub: https://github.com/kim-jeongwoo/graduation-project.git (branch: main, 서브폴더: dml-server/)

---

## 환경

- Ubuntu 25.10 / RTX 5080 (16.6GB) / PyTorch 2.10.0+cu128 / Python 3.11 / Conda: **EGGDML**
- 실제 작업 디렉토리: `~/projects/egg_prediction/` (데이터·체크포인트는 여기 disk에 있음)
- 레포 서브폴더: `dml-server/` (git 추적 파일들)
- 서버 IP: 114.71.220.144 (집/학교 LAN용)
- **외부 시연 URL**: `https://dml.vocal-fit.com` (Cloudflare named tunnel, 영구 도메인)
  - tunnel: `dml-server` (UUID 725417d8-d2f7-4725-a126-6526fd41ebe5)
  - DNS: dml.vocal-fit.com → cfargotunnel (자동 CNAME)
  - HTTPS/WSS 자동, SKT/KT/LGU+ LTE 비표준 포트 차단 우회
  - 인증서: `~/.cloudflared/cert.pem` (vocal-fit.com 권한)
  - WAF 주의: 기본 봇 보호로 `Python-urllib`, `curl` 같은 UA 일부 403. 정상 모바일/브라우저 UA는 통과.
  - systemd: `cloudflared-tunnel.service` (User=dmlserver, Restart=always, RestartSec=10). 재기동 시 다운타임 ~10초, 안정화 ~20초. URL 유지.
  - 진단: `systemctl status cloudflared-tunnel` / `journalctl -u cloudflared-tunnel -f`

```bash
# 환경 활성화
cd ~/projects/egg_prediction && conda activate EGGDML
nvidia-smi

# model_server 실행
# Dev/manual example only. Production is managed by `dml-server.service`; see `AGENTS.md` and `PROJECT_LOG.md` §15 latest.
conda activate EGGDML
python dml-server/model_server/server.py

# data_prep 스크립트 실행 예시
python dml-server/scripts/data_prep/run_all.py
```

---

## 현재 상태 (Best: Exp20 Progressive Window)

| 항목 | 값 |
|------|------|
| 모델 | EfficientEGGNet (non-causal dilated CNN) |
| 구조 | channels=128, n_layers=30, kernel_size=5, n_stacks=5, dropout=0.05 |
| 파라미터 | 5.99M |
| Window | 16384 samples (1024ms @16kHz) |
| Loss | 0.2·MSE + 0.8·CorrLoss |
| **Test Corr** | **0.8249** |
| Val Corr | 0.8218 |
| 체크포인트 | `checkpoints/exp20_progressive/best_model.pt` (disk-only, gitignored) |

검증 완료: Data Leak 없음, Train-Test Gap 0.022, 화자 90%가 Corr ≥ 0.7, Median = 0.8532

---

## 폴더 구조 (레포 내)

```
dml-server/
  ai-model/            # EGG 추정 모델 코드
  model_server/        # FastAPI 추론 서버 (port 8001)
    server.py          # /analyze 엔드포인트
    predictor.py       # EfficientEGGNet 추론 래퍼
    schemas.py
  scripts/
    data_prep/         # 노래방 파이프라인 (Stage 0~2 + t_mr 변환)
    sync_songs.sh      # Mac Studio → dmlserver pull (Mac Studio에서 실행)
    *.py               # 분석·평가 스크립트
  docs/                # dml 관련 문서
  figures/, images/    # 논문/보고서용 시각화
  server/              # 레거시 placeholder
  tests/               # test_analyze.py 등
  PROJECT_LOG.md
  CLAUDE.md            # 이 파일
```

disk-only (gitignored):
```
checkpoints/           # best_model.pt 등 (삭제 금지)
data/                  # 학습 데이터 + 노래방 14곡 산출물
results/               # 실험 결과 JSON
.claude/refs/          # 실험 히스토리·데이터셋 레퍼런스
```

---

## 상세 레퍼런스 (필요할 때만 읽을 것)

- 실험 히스토리 & 실패 원인: `.claude/refs/experiments.md`
- 데이터셋 & 전처리 파이프라인: `.claude/refs/dataset.md`
- 폴더 구조: `.claude/refs/folder-structure.md`
- 자주 쓰는 명령어: `.claude/refs/commands.md`

---

## 에이전트 행동 규칙 (Karpathy 4원칙)

### 1. Think Before Coding (추측 금지)
- 가정은 명시적으로 진술. 불확실하면 추측하지 말고 질문 — 여러 개면 한 번에 묶어 질문.
- 해석이 여러 개 가능하면 조용히 하나 고르지 말고 모두 제시.
- 더 단순한 방법이 있으면 그걸 제안 (push back).
- 혼란스러우면 멈추고 뭐가 불명확한지 명시 후 질문.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.
- 파일 수정 전 뭘 바꿀 건지 먼저 설명.
- 되돌릴 수 있는 작업은 물어보지 말고 바로 진행. 삭제·전송 같은 비가역 작업만 확인.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.

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
- **테스트: 모든 수정 라인이 사용자 요청과 직접 연결되는가?**
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.
- 터미널 멀티라인 주의 — Python 코드는 `.py` 파일로 만들어 실행. `-c` 인라인 멀티라인은 쉘 오염.

### 4. Goal-Driven Execution (목표 기반 실행)
- 명령형 작업을 검증 가능한 목표로 변환.
  "버그 고쳐" → "버그 재현하는 테스트 작성 후 통과시킴"
  "검증 추가" → "잘못된 입력에 대한 테스트 작성 후 통과시킴"
- 다단계 작업은 짧은 계획 진술:
  1. [단계] → 검증: [체크]
  2. [단계] → 검증: [체크]
- 강한 성공 기준이 있으면 자율 루프, 약하면 매번 확인 요청.
- ML 특수성: 실험 코드는 'corr X 이상 달성' 같은 측정 가능한 목표로, 학습 스크립트 변경 시 `results/experiment_log*.txt`에 기록되는 것까지가 완료.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.

### 출력 형식
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.

---

## 절대 규칙

1. `checkpoints/exp20_progressive/best_model.pt` **삭제 금지**.
2. **화자 독립 분할(seed=42) 변경 금지**. 프레임 분할은 Corr 0.95로 보이지만 데이터 누수.
3. **시각화는 중앙값 샘플 사용**. cherry-picking 금지.
4. **model_server 리샘플링 불일치 주의** (scipy vs librosa). 수정 시 양쪽 동기화.
5. 실험 결과는 `results/experiment_log*.txt`에 기록.
6. 시각화 한국어 폰트: `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
7. `data/songs/` 디렉토리 파일 삭제 금지 (원곡 MP3, 보컬 WAV, 피치 JSON).
8. `.env` 파일 내용 출력/로그 금지.

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

- [2026-05-04] [외부 MIDI 옥타브] midiex.net 등 외부 MIDI의 Steinway Grand Piano 멜로디 트랙은 실제 보컬보다 +12 semitone(1옥타브) 높게 작성된 경우 있음. 자체 F0 추출(`f0_to_midi_segments.py --dry-run`)으로 먼저 비교 후 채택 결정.

- [2026-05-04] [음역 진단] 가수 음역 이상하다고 바로 재처리하지 말 것. 가수 개별 정보 검색 먼저 (윤하 진성 A5까지, F#3 저음 발라드 시작 정상).

- [2026-05-04] [model_server health] `health check timeout` 기본값 5초 부족 → 30초 + 3회 재시도로 설정.

- [2026-05-05] [chunk MIN_VOICED_S] chunk 단위 분석은 `min_voiced_s=2.0s` 사용 (전체 wav 5.0s와 분리). `timeline_analysis.py`의 `CHUNK_MIN_VOICED_S = 2.0`. **5/10 재검토 대상** — skip 비율 개선 효과와 부정확 증가 여부 측정 필요.

- [2026-05-05] [접촉강도 chunk 비활성화] `TIMELINE_ITEMS = ["4_breathiness"]`로 변경. score_mapper 임계값 narrow (cq_p90 0.5297 4회 반복) → chunk 통계 불안정으로 신뢰 불가. `DEFERRED_ITEMS = ["3_vocal_fold_contact"]`. **5/10 per-session 재학습 후 재활성화 검토.**



- [2026-05-12] [페이지 간 정보 동기화] schema 변경 시 일부 endpoint만 공유, 다른 endpoint 누락. 원인: dml-server 측 작업 시 endpoint별 변경 사항 분리 인지 부족 (5/11 F4에서 `/analyze`만 vocal-server/app과 사전 공유, `/analyze-chunk` 빠뜨림 → 5/12 갤럭시 검증에서 발견). **대신 어떻게**: schema 변경 시 영향 받는 **모든 endpoint** 명시 (`/analyze`, `/analyze-chunk`, `/ws/realtime`, `/predict`, `/health`) + 각 endpoint별 적용 시점/변경 내용 분리 기술. PROJECT_LOG `§15` 운영 규칙 + `§15-6` 현황표 참고. 사전 공유 → P1 검증 → P2 본격 적용 → 자동 통과 패턴 권장.

- [2026-05-12] [Cloudflare Tunnel 125s edge timeout] cloudflared 통과 응답 TTFB > 125s → 524 Origin Time Out. 실측: 105s OK, 200s/300s 모두 524 at 125.6s. 곡 전체 `/analyze` (~150~180s) 위험. **대신 어떻게**: `StreamingResponse` + leading whitespace keepalive (5s 간격 `b" "` ping) → TTFB ~0s 우회. 표준 JSON parser는 leading whitespace 무시 (RFC 7159) → 응답 schema 변경 0. PROJECT_LOG `§15-3` / `§15-4` 참고.

- [2026-05-12] [streaming response 시작 후 status code 변경 불가] StreamingResponse는 첫 byte 송신 시 HTTP status code 확정 (200 고정). 분석 중 발생한 예외(ValueError/Exception)도 200 + body status 필드로 통일 필요. **대신 어떻게**: `_analyze_sync` 안에서 모든 예외 catch → `{"status":"invalid"|"failed", "error":...}` dict 반환. file 검증 실패(400) / 모듈 미로드(503)는 streaming 시작 전 raise 가능.

- [2026-05-11] [model_server restart 누락 — legacy pre-systemd note] disk에 새 코드가 있어도 가동 process가 자동 reload 되지 않는 문제는 과거 수동/nohup 운영 시 발생했다. 2026-05-13 이후 production 기준은 `dml-server.service`다. 코드/운영 변경 후 재시작이 명시적으로 승인된 경우 systemd 기준으로 처리하고, broad `fuser -k`는 사용하지 않는다. manual `nohup python server.py`는 systemd 실패 시 emergency rollback/fallback로만 사용한다.

- [2026-05-09] [SKT/KT/LGU+ LTE 비표준 포트 차단] 8001 외부 직접 접속 LTE에서 차단됨. 학교/공유 Wi-Fi는 OK. **외부 시연용 endpoint는 항상 Cloudflare Tunnel(trycloudflared) 사용**. 임시 URL은 cloudflared 프로세스 살아 있는 동안만 유효 (재시작 시 변경). 현재 URL: `~/.cloudflared/current-url.txt`.

- [2026-05-09] [스크립트 parents 경로] `dml-server/scripts/` 직하위 스크립트는 `parents[2]`로 egg_prediction root 계산. `parents[3]`은 `scripts/data_prep/` 한 단계 더 깊은 경우에만 사용.

- [2026-05-03] [모노레포] dml-server 코드는 `dml-server/` 서브폴더 안.
  스크립트 실행: `cd ~/projects/egg_prediction && python dml-server/scripts/data_prep/run_all.py`
  data_prep 스크립트는 `parents[3]`으로 project root(`egg_prediction/`) 계산. `parents[2]` 아님.

- [2026-04] [import 순서] font 설정 블록(`Path(_NOTO).exists()`)을 `from pathlib import Path` 전에 배치 → ImportError. **`from pathlib import Path`는 항상 최상단.**

- [2026-04] [배치 실행] `fetch_lrc.py --all` 1회 실행 후 바로 Stage 2 배치 돌림 → LRC 누락 상태로 pitch_guide 생성. **Stage 2 전에 `lrc/parsed/` 파일 수 확인 필수.**

- [2026-04] [파일명] macOS 업로드 파일명이 NFD(jamo 분해)로 저장됨 → Linux에서 경로 불일치. **모든 파일명 비교 시 `unicodedata.normalize('NFC', name)` 적용.**

- [2026-04] [LRC 매칭] `007 지아 - 물론`, `011 양다일 - 요즘` LRCLIB 검색 시 전혀 다른 곡 반환 → title similarity 0.4 미달 곡 auto-accept 금지.

- [2026-04] [환경] CREPE GPU: RTX 5080(Blackwell) TF 2.21 미지원 → CPU fallback. 14곡 캐시 완료로 재실행 부담 없음.

---

## 🗓 프로젝트 현황 (2026-05-10)

### 현재 진행 위치
Historical snapshot; current production/deployment status is `AGENTS.md` + `PROJECT_LOG.md` §15 latest.

**Phase 1+2 완료 + 데이터 카탈로그 보강 (2026-05-11). Phase 3 새 채팅방에서 진행 예정.**

**필독 인계 자료** (새 채팅방 시작 시):
- `PROJECT_LOG.md` §11 — Phase 1 (5/10 ICC + MIDI 옥타브)
- `PROJECT_LOG.md` §12 — Phase 2 (per-register 채택 + 신뢰도 재분류)
- `PROJECT_LOG.md` §13 — **데이터 자산 카탈로그** (14곡 / 학습 22명 / validation 11명 / 5/10 21명 / phone 19명 / 평가지 메타)
- `PROJECT_LOG.md` §14 — score_mapper 학습 명세 (510 rows, n=99 매핑, 7항목 임계값)

**핵심 명세 (요약)**:
- 학습 22명 oral+nasal 보유 (singer_01~22). **phone 채널 19명 보유** (singer_01,04,22 미보유). raw_2026 12명은 학습 디렉토리에 통합됨 확인.
- score_mapper: oral.wav만 학습. 매핑 단위 (singer, song, register), n=99. 7항목 매핑 / 2항목 skip.
- 평가자 ID 1~5는 학습(20260427)/5/10(20260509) 양쪽 동일 — 동일인 가능성 강함.
- 5/10 21명 곡: 대부분 14곡 외 학원 자유곡. A1/A9/A10만 14곡 매칭(007/004/007).
- 가수 ID 누설: 명명체계 다름(1~22 / test_NN / A·B). 가수 실명 메타 부재 → 직접 비교 불가. **학원에 실명 매핑 요청 권장**.
- 마이크 분포: spectral_centroid +50% shift (1047→1576), 전방공명 클리핑 원인. cq/cpp 계열은 마이크 강건.

### AI 모델 — 완료 ✓
Exp20 Progressive Window, Test Corr 0.8249. 체크포인트 보존됨.

### T1 데이터 파이프라인 — 완료 ✓
14/14곡 Stage 0~2. pitch_guide (guide_source=f0) + _mr.json 생성. Mac Studio 동기화 완료.

### model_server endpoints — 완료 ✓
- `/analyze` (9항목 + timeline + user_f0)
- `/ws/realtime` (200ms 음정 + 5s 호흡)
- `/analyze-chunk` (Phase 4 통합 점수)
- 무음 가드 Guard A/B 4종 endpoint 공통
- `https://dml.vocal-fit.com` Cloudflare named tunnel + systemd 자동 재시작 (LTE 우회)

### 자체 F0 추출 파이프라인 — 완료 ✓
외부 MIDI Steinway 트랙 옥타브 +12 어긋남 발견 → 자체 vocals.wav F0 추출로 전환.
002/004 처리 완료. 5/10 도착 외부 미디 6곡은 옥타브 정상 (자체 F0 불필요).

### Phase 1+2 (5/10 데이터) — 완료 ✓ (2026-05-10)
- A 10명 + B 11명 + 평가지 5개 + 미디 6곡 정리 완료
- ICC: A+B 통합 9항목 평균 0.793 (호흡식별 0.796 / 접촉강도 0.898 / 상압하압 0.910)
- **per-register 채택** (per-session 가설 기각, 학습 데이터 z corr ≈0)
- **신뢰도 재분류: high 0개 / medium 2개(호흡식별·상압하압) / unavailable 7개**
- 전방공명 클리핑 원인 — spectral_centroid 마이크 의존 (학습 1047 → 5/10 1580)

### 백엔드 서버 — vocal-server 페이지 담당
진행 중. 이 페이지에서는 손대지 않음.

---

## 🔑 결정 사항 누적

- 라즈베리파이 → 미사용
- 14곡 자유곡 + KOMCA 라이센스
- CREPE CPU 사용 (RTX 5080 + TF 2.21 미호환)
- LRC 미확보 3곡(001, 007, 011) → manual_required.txt 기록, Whisper 처리 미실행
- timeline 분석은 high 신뢰 항목만 (접촉강도 `3_vocal_fold_contact`, 호흡식별 `4_breathiness`)
- **guide_source 정책**: `"f0"` 우선 → `"midi"` fallback (옥타브 검증 필수) → `"crepe"` 최후
- score_mapper per-session 매칭 채택은 5월 10일 데이터 후 결정 (현재 per-register 유지)
- 외부 MIDI(midiex.net 등) 직접 사용 금지 — 옥타브 검증 없이 쓰면 +12 오류 발생

---

## ✅ 다음 작업 큐 (2026-05-10 갱신)

### Phase 3 (새 채팅방, 즉시 진행 예정)
- [ ] **K-9 마이크 강건성 분석**: training/validation/A/B 항목별 corr 비교 + Δ corr 시각화 (발표 슬라이드 D)
- [ ] **K-10 매핑 재학습 결정**: per-register 유지 + 5/10 데이터로 임계값 재학습 (특히 전방공명) / 마이크별 매핑 분리 검토
- [ ] **K-11 종합 보고서** `phase2_report.md`
- [ ] **score_mapper per-session 가설 기각 확정** (Phase 2에서 결정, per-register 채택)

### 5/24 이후
- [ ] B그룹 After 도착 → Before/After 비교 (사전/사후 분석)
- [ ] 통제 실험 결과 분석

### 백로그
- [ ] 14곡 활성화 (vocal-server DB 메타 갱신)
- [ ] vocal-app 갤럭시 재검증 결과 대기 (002 가이드라인 피치 일치 여부)
- [ ] WS 인증 추가 / 세션 영속화 / WS idle timeout (운영 환경 전환 시)
- [ ] 흉성두성/접촉강도 본질 지표 재검토 (cq_mean/cq_peak 외 후보 탐색)
- [ ] 접촉강도 timeline 재활성화 검토 (DEFERRED_ITEMS, score_mapper 재학습 후)
- [x] LRC 3곡(001/007/011) Whisper ASR — 완료 (001: 26줄, 007: 23줄 conf 0.93, 011: 34줄 conf 0.96)
- [x] 무음 입력 가드 — Guard A (voiced_s<5s) + Guard B (voiced_ratio>0.95 & cpp<0.15) → 200 no_voice
- [x] user_f0 응답 추가 — 25Hz sparse null, schemas.py UserF0, 실측 최대 ~100KB
- [x] timeline_scores 진단 — vocal-server song_id 미전달 원인 확정. dml-server 수정 없음.
- [x] /ws/realtime WebSocket — 음정 일치율(200ms binary PCM→pitch_match) + 호흡 chunk(5초→breathiness_chunk). pitch latency p95=2.9ms. services/realtime.py 신규.
- [x] /analyze-chunk endpoint (Phase 4 사후 측정) — 호흡/접촉 통합 점수 1개. duration<3s→400, voiced_s<dur×0.4→no_voice. 5s=368ms / 10s=716ms. services/chunk_analysis.py 신규.
