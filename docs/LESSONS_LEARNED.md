# 시행착오 및 난관 정리 (Lessons Learned)

졸업작품 「딥러닝 EGG 추정 기반 가창 발성 평가 시스템」을 진행하며 겪은 실패·난관·교훈을 한 곳에 모은 문서.
여러 문서에 흩어져 있던 내용과, 그동안 dmlserver 로컬에만 있던 분석 문서를 함께 재구성했다.

**작성** 2026-07-26 · **대상 기간** 2026-04 ~ 2026-07
**원문 전체**는 [`docs/research/`](research/) 에, AI 주입용 통합본은 [`docs/AI_CONTEXT_FULL.md`](AI_CONTEXT_FULL.md) 에 있다.

---

## 목차

1. [AI 모델 실험 — 20회 중 성공 6회](#1-ai-모델-실험--20회-중-성공-6회)
2. [데이터 파이프라인 — 조용히 틀리는 실수들](#2-데이터-파이프라인--조용히-틀리는-실수들)
3. [평가·통계 설계 — 가장 큰 난관](#3-평가통계-설계--가장-큰-난관)
4. [서버·네트워크 운영](#4-서버네트워크-운영)
5. [협업·프로세스](#5-협업프로세스)
6. [미해결 항목](#6-미해결-항목)
7. [종합 교훈](#7-종합-교훈)
8. [문서 지도](#8-문서-지도)

---

## 1. AI 모델 실험 — 20회 중 성공 6회

> 원문: [`research/01-model-experiments-full.md`](research/01-model-experiments-full.md) ·
> [`dml-server/ai-model/EXPERIMENT_REPORT.md`](../dml-server/ai-model/EXPERIMENT_REPORT.md)

### 1-1. 성능 궤적

| 실험 | 모델 | Params | Window | Test Corr | 핵심 변경 |
|---|---|---:|---|---:|---|
| Baseline | WaveNet (causal) | 72K | 192 (12ms) | 0.6662 | 초기 모델 |
| Exp1 | Larger WaveNet | 419K | 192 | 0.6784 | 크기 증가 |
| Exp3 | EfficientEGGNet | 1.8M | 4096 (256ms) | 0.7163 | **non-causal 전환** |
| Exp10 | Large Efficient | 5.99M | 4096 | 0.7205 | 스케일업 |
| Exp11 | Multiscale | 5.99M | 8192 (512ms) | 0.7484 | **window 확장** |
| **Exp20** | **Progressive** | **5.99M** | **16384 (1024ms)** | **0.8249** | **window 1024ms ★** |

최종 모델: `EfficientEGGNet`, Test Corr 0.8249 / Val 0.8218, Train-Test Gap 0.022, 화자 90%가 Corr ≥ 0.7.

### 1-2. 실패·중단한 실험 14건

| 실험 | 결과 | 실패 원인 |
|---|---|---|
| Exp1b | 0.6763 | window를 192→1024로 늘렸으나 **causal 구조라 효과 없음** |
| Exp2 (TCN-UNet) | 중단 | 29.4M params, **InstanceNorm + AMP → epoch 3에서 loss=NaN**, 에폭당 19분 |
| Exp4 (Multi-Input) | 0.7137 | Mel spectrogram이 중복 정보, augmentation 무효 |
| Exp5 (고품질 필터) | 0.6956 | 저품질 제거 → **데이터 절반 삭제 → 오히려 하락** |
| Exp6 (Transformer) | 0.7030 | 에폭당 ~32분, 수렴 느림 |
| Exp7 (Conformer) | OOM | self-attention O(N²) → CUDA OOM |
| Exp8 (wav2vec2) | ≈ 0 | 90M 사전학습 모델, **학습 완전 실패** |
| Exp9 (Curriculum) | 0.7126 | 난이도 순 학습 효과 없음 |
| Exp12 (Ensemble) | 0.7191 | 단일 모델보다 낮음 |
| Exp13~19 | 0.74~0.75 | 정규화 / attention / augmentation — 전부 정체 |

### 1-3. 교훈

1. **모델 크기보다 수용 영역(receptive field)이 병목이었다.** Window 192(12ms)는 F0 100Hz 기준 약 1주기뿐 — 파라미터를 72K→419K로 6배 키워도 +0.012에 그쳤다. 반면 non-causal 전환(+0.038)과 window 1024ms(+0.077)가 결정적이었다.
2. **모델이 크면 실험 자체가 불가능해진다.** Exp2는 5 epoch에 0.692로 유망했으나 완주에 25시간이 필요해 중단했다. "가벼운 non-causal + 긴 window + AMP" 조합으로 선회한 것이 Exp3 성공으로 이어졌다.
3. **InstanceNorm은 AMP(float16)와 수치적으로 불안정하다.** GroupNorm(groups=8)으로 대체.
4. **사전학습 모델이 항상 유리하지는 않다.** wav2vec2는 음성인식 표현이라 EGG 파형 회귀로 전이되지 않았다.

---

## 2. 데이터 파이프라인 — 조용히 틀리는 실수들

> 원문: [`dml-server/CLAUDE.md`](../dml-server/CLAUDE.md) §"⚠️ 반복하지 말 것" ·
> [`research/21-midi-octave-check-510.md`](research/21-midi-octave-check-510.md)

| 사건 | 증상 | 원인 | 대응 |
|---|---|---|---|
| **macOS 파일명 NFD** | Linux에서 경로 불일치, 파일을 못 찾음 | macOS가 한글 자모를 분해(NFD)해 저장 | 모든 파일명 비교에 `unicodedata.normalize('NFC', name)` 강제 |
| **LRC 오매칭** | `007 지아 - 물론`, `011 양다일 - 요즘`에 전혀 다른 곡 가사가 붙음 | LRCLIB 검색이 유사 제목을 반환 | title similarity 0.4 미만 auto-accept 금지 |
| **배치 순서 실수** | pitch_guide가 LRC 없는 상태로 생성됨 | `fetch_lrc.py --all` 직후 Stage 2 배치 실행 | Stage 2 전에 `lrc/parsed/` 파일 수 확인 필수 |
| **외부 MIDI 옥타브** | 가이드 음정이 실제 보컬보다 1옥타브 높음 | midiex.net 등의 Steinway Grand Piano 멜로디 트랙이 +12 semitone으로 작성됨 | 자체 F0 추출(`--dry-run`)로 먼저 비교 후 채택 → 이후 **자체 F0 추출로 전환** |
| **CREPE GPU 미지원** | GPU 가속 불가, CPU 84~98s/곡 | RTX 5080(Blackwell)을 TF 2.21이 미지원 | 14곡 캐시로 회피 |
| **import 순서** | ImportError | font 설정 블록을 `from pathlib import Path`보다 위에 배치 | `from pathlib import Path`는 항상 최상단 |

**교훈**: 이 범주의 버그는 **에러 없이 잘못된 결과를 만든다**. 옥타브 문제도 "가수 음역이 이상하다"고 바로 재처리하는 대신 가수 개별 정보를 먼저 조회하는 습관(윤하 진성 A5, F#3 저음 시작은 정상)이 오진을 막았다.

---

## 3. 평가·통계 설계 — 가장 큰 난관

프로젝트에서 가장 오래 붙잡고, 가장 여러 번 방향을 튼 영역이다.

### 3-1. 매칭 방식 아티팩트 (2026-05-03)

> 원문: [`research/10-matching-diagnosis-summary.md`](research/10-matching-diagnosis-summary.md)

**발단**: AI가 EGG를 Test Corr 0.8249로 잘 추정하는데, 흉성두성 항목의 트레이너 점수 상관이 **r = −0.282(음수)** 로 나왔다.

원인은 모델이 아니라 **집계 단위**였다.

| 항목 | per-register (당시 방식) | per-session | 검증 per-session |
|---|---:|---:|---:|
| 흉성두성 | **−0.282** (n=57) | **+0.139** (n=28) | **+0.554** (n=11) |
| 접촉강도 | +0.087 (n=57) | −0.101 (n=19) | +0.627 (n=11) |
| 호흡식별 | +0.569 (n=69) | +0.664 (n=23) | +0.314 (n=11) |

- per-register는 같은 가수 내 "저→고로 갈수록 CQ가 변하는" 패턴을 **가수 간 차이로 오인**한다.
- 게다가 호흡식별(cpp)·전방공명(spectral_centroid)은 파일 전역 지표라 per-register n=69가 **의사반복(pseudoreplication)** 이었다. 실제 독립 관측은 23회.

**결정**: 데이터가 더 올 때까지 매칭 방식을 바꾸지 않았다. per-session이 흉성두성은 개선하지만 접촉강도는 악화시켰고(−0.101), n=11에서의 +0.554가 우연일 가능성을 배제할 수 없었기 때문이다. — **성급한 전환을 참은 것이 옳았다.**

### 3-2. 지표 탐색 실패

흉성두성 개선을 위해 CQ 파생 지표 4종(`cq_high−cq_low`, `cq_high/cq_low`, `cq_variance`, `cq_high_normalized`)을 시도했으나 **4종 모두 실패**. 음역대 간 CQ 변동은 흉성두성과 무관했다.

### 3-3. 마이크 도메인 시프트 (2026-05-10~11)

> 원문: [`research/22-sign-reversal-analysis.md`](research/22-sign-reversal-analysis.md)

학습은 학원 구강 마이크, 검증은 스마트폰이었다.

- **전방공명 클리핑**: `spectral_centroid` 학습 평균 1047Hz vs 5/10 1580Hz(+50%). 학습 매핑의 상한(1095)을 검증 데이터 평균이 넘어 **전원 0점으로 클리핑**됐다.
- **부호 반전**: 비강사용·전방공명에서 학습 시 양(+)이던 관계가 검증에서 음(−)으로 완전히 뒤집혔다. Ridge 기반 phone→oral mapper로도 회복되지 않았다.

**결론**: 마이크가 바뀌면 지표의 **측정값뿐 아니라 의미 자체가 바뀔 수 있다**. 학습 corr이 약한 지표일수록 환경 변경 시 부호 반전 위험이 커진다. 해당 2항목은 `tier="academic_only"`로 앱 표시에서 제외했다.

### 3-4. 검증 신뢰성 재확인 (2026-07-26)

> 원문: [`research/40-rediag-selection-bias-2026-07.md`](research/40-rediag-selection-bias-2026-07.md)
> — **검증 수치에 관해서는 이 문서가 가장 최신이자 가장 정확하다.**

위 대응 이후에도 남아 있던 문제가 확인됐다.

1. **선택 편향** — 9항목 × 24 config 그리드에서 검증셋 상관이 가장 높은 모델을 골랐다. n=17에서 21개 모델 중 최댓값을 고르면 **우연만으로도 \|r\| ≈ 0.62(95분위)** 가 나온다. 보고된 val corr은 성능 추정치가 아니라 선택 편향이 들어간 최댓값 통계량이다.

   | 항목 | 배포 val corr | 선택보정 p | 부트 95% CI | 중첩 CV \|r\| | 판정 |
   |---|---:|---:|---|---:|---|
   | 접촉강도 | +0.733 | 0.023 | [+0.19, +0.92] | 0.506 | ✅ 유의 |
   | 혀경직도 | +0.694 | 0.014 | [+0.37, +0.93] | 0.562 | ✅ 유의 |
   | 연구개위치 | −0.624 | 0.054 | [−0.87, −0.24] | 0.603 | ❌ 미확보 + **부호 반전** |
   | 호흡식별 | +0.434 | **0.333** | **[−0.05, +0.80]** | 0.362 | ❌ 미확보 |

2. **연구개위치 부호 반전** — 전 코호트에서 상관이 음수인데 `tier=high_star`로 앱에 표시 중이다. 3-3에서 잡아낸 것과 같은 증상이 표시 항목에도 있었다.
3. **화자 누설** — 기존 `train_5fold`가 unit 단위 KFold라 같은 가수의 다른 곡이 train/test에 동시 등장했다. 화자 GroupKFold로 바로잡으면 접촉강도 0.470 → **0.103**.
4. **재현성 단절** — 배포 모델을 만든 학습 스크립트가 저장소에 없었다. 역추적해 복원 완료(`rediag/retrain_v2.py`, 기계 정밀도 재현).
5. **표본 대비 차원 과다** — feature 38개에 표본 24개, 설계행렬 rank 23. `a1_p0`와 `h1_a1`은 완전 중복(r = −1.0).
6. **mapper 무용** — phone→oral Ridge mapper는 직접 산출 대비 성능 이득이 없고(중첩 CV 0.507 vs 0.501), 외삽에서 붕괴하며(spectral_centroid OOS r = −0.008), 분산을 1/3로 축소한다.

**교훈**: 검증셋을 모델 선택에 쓰면 그 검증셋으로는 더 이상 성능을 추정할 수 없다. 선택 절차를 포함한 중첩 CV나 별도 홀드아웃이 필요했다.

---

## 4. 서버·네트워크 운영

> 원문: [`dml-server/PROJECT_LOG.md`](../dml-server/PROJECT_LOG.md) §15 배포 이력

| 사건 | 증상 | 원인 | 대응 |
|---|---|---|---|
| **LTE 비표준 포트 차단** (05-09) | 학교 Wi-Fi는 되는데 LTE에서 접속 불가 | SKT/KT/LGU+ 가 8001 포트 차단 | Cloudflare Tunnel → named tunnel `https://dml.vocal-fit.com` 고정 |
| **Cloudflare 125s edge timeout** (05-12) | 전곡 `/analyze`가 524 Origin Time Out. 실측 105s OK / 200s·300s 모두 125.6s에서 실패 | cloudflared edge의 TTFB 상한 | `StreamingResponse` + 5s 간격 공백 keepalive로 TTFB ~0s. 표준 JSON 파서는 leading whitespace 무시(RFC 7159)라 **응답 schema 변경 0** |
| **streaming 중 status code 변경 불가** (05-12) | 분석 중 예외가 나도 HTTP 400을 못 보냄 | StreamingResponse는 첫 바이트 송신 시 status 확정 | 모든 예외를 catch해 `200 + body의 status 필드`로 통일 |
| **health check timeout** (05-04) | 정상인데 실패로 판정 | 기본 5초 부족 | 30초 + 3회 재시도 |
| **재시작 누락** (05-11) | 디스크의 새 코드가 반영되지 않음 | 수동/nohup 운영이라 auto-reload 없음 | `dml-server.service` systemd 전환(05-13). nohup은 emergency rollback 전용 |
| **chunk 임계값 불안정** (05-05) | 접촉강도 chunk 점수 신뢰 불가 | score_mapper 임계값이 좁음(cq_p90 0.5297이 4회 반복) | 접촉강도 timeline 비활성화, `MIN_VOICED_S` 2.0s로 완화 |

---

## 5. 협업·프로세스

### 5-1. endpoint 간 정보 동기화 누락 (05-12)

schema를 바꾸면서 `/analyze`만 vocal-server·앱 측과 사전 공유하고 `/analyze-chunk`를 빠뜨렸다. 5/12 갤럭시 검증에서야 발견됐다.

**대응 규칙**: schema 변경 시 영향받는 **모든 endpoint를 명시**한다 (`/analyze`, `/analyze-chunk`, `/ws/realtime`, `/predict`, `/health`). 각 endpoint별 적용 시점과 변경 내용을 분리 기술하고, 사전 공유 → P1 검증 → P2 본격 적용 순서를 따른다.

### 5-2. 서브프로젝트 경계

`vocal-server/`(Mac Studio)와 `dml-server/`(GPU 서버)를 서로 손대지 않는 규칙을 세웠다. 모노레포 전환 후 경로 계산 실수(`parents[2]` vs `parents[3]`)가 반복돼 규칙으로 못박았다.

### 5-3. 결과 문서가 `.gitignore` 뒤에 갇혀 있었다

분석 보고서 대부분이 `data/`·`results/` 아래에 있어 `.gitignore`(42·46·47행)에 걸려 커밋되지 않았다. 원시 데이터를 제외하려던 규칙이 **문서까지 같이 제외**한 것이다. 2026-07-26에 [`docs/research/`](research/) 로 이관해 해소했다.

---

## 6. 미해결 항목

| 항목 | 내용 | 상태 |
|---|---|---|
| **B1 sample 비결정성** | B1만 pipeline 통과 시 캐시와 Δ 0.3~0.6 차이. direct call은 33 indicator 전부 0% 차이 → pipeline 내부 어딘가의 비결정적 상호작용 ([원문](research/23-b1-difference-root-cause.md)) | 원인 미규명 |
| **연구개위치 부호** | 표시 중인 항목이 사람 평가와 반대 방향 | 2026-07 발견, 조치 대기 |
| **호흡식별 유의성** | 선택 편향 보정 후 p=0.333 | 조치 대기 |
| 실시간 추론 지연 | 모델 window 1024ms → 최소 1s 딜레이 | UX 허용 범위로 판단 |
| 모델 경량화 | 5.99M params, ONNX 변환 미시도 | 백로그 |
| 데이터셋 규모 | paired 표본 29 unit / 19화자. 도메인 갭과 표본 부족을 분리 불가 | **가장 큰 학술적 한계** |

---

## 7. 종합 교훈

1. **성능 병목은 대개 모델 크기가 아니다.** 20회 실험 중 결정적이었던 두 변화는 non-causal 전환과 window 확장이었고, 파라미터를 6배 키운 실험은 +0.012에 그쳤다.
2. **집계 단위가 상관계수의 부호를 바꾼다.** per-register vs per-session 하나로 흉성두성이 −0.282 ↔ +0.554를 오갔다. 의사반복은 n을 3배로 부풀려 통계적 신뢰를 착각하게 만든다.
3. **학습 환경과 배포 환경의 마이크가 다르면 지표의 의미가 달라진다.** 단순 선형 보정(Ridge mapper)으로 회복되지 않는 영역이 존재한다.
4. **검증셋으로 모델을 고르면 그 검증셋은 성능 추정에 쓸 수 없다.** 선택 편향은 n이 작을수록 치명적이다(n=17에서 우연 최댓값 0.62).
5. **재현 스크립트를 남기지 않으면 3개월 뒤 자기 결과를 검증할 수 없다.** 배포 모델의 학습 코드가 없어 역추적에 상당한 공수가 들었다.
6. **`.gitignore`는 데이터를 막되 기록까지 막으면 안 된다.** 가장 값진 분석 문서가 로컬에만 남아 있었다.

---

## 8. 문서 지도

### 사람용

| 문서 | 용도 |
|---|---|
| **이 문서** | 시행착오 전체 조망 |
| [`dml-server/CLAUDE.md`](../dml-server/CLAUDE.md) §"⚠️ 반복하지 말 것" | 재발 방지 체크리스트 15건 |
| [`dml-server/PROJECT_LOG.md`](../dml-server/PROJECT_LOG.md) | 시간순 진행 일지 (947행) |
| [`docs/research/`](research/) | 개별 분석 보고서 원문 17건 |

### AI용

| 문서 | 용도 |
|---|---|
| [`docs/AI_CONTEXT_FULL.md`](AI_CONTEXT_FULL.md) | 위 문서 전체를 **요약 없이** 이어붙인 단일 파일 |
| [`docs/build_docs.py`](build_docs.py) | 이관 + 통합본 재생성 스크립트 |

### 아직 dmlserver 에만 있는 것

원시 데이터와 계산 산출물은 이관하지 않았다.

- `data/vocal_academy/singer_01..22/` — 가수 녹음 원본 (oral/nasal/phone wav)
- `data/vocal_academy/results/sidetrack/*.csv|json` — 지표·모델 산출물
- `data/vocal_academy/results/sidetrack/rediag/` — 2단계 진단 스크립트·JSON (결론은 [40번 문서](research/40-rediag-selection-bias-2026-07.md)에 이관 완료)
- `checkpoints/exp20_progressive/best_model.pt` — 모델 가중치
