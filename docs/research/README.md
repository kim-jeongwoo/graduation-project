# docs/research — 연구·분석 문서 원문

이 디렉터리는 **그동안 dmlserver 로컬에만 있던 분석 보고서**를 저장소로 옮겨 놓은 곳이다.
원본들은 `data/`·`results/`·`.claude/` 아래에 있어 [`.gitignore`](../../.gitignore) 42·46·47행에 걸려
커밋되지 않고 있었다. 원시 데이터를 제외하려던 규칙이 문서까지 같이 제외한 결과였다.

각 파일 상단에는 원본 경로·수정일·크기·해시가 `provenance` 헤더로 붙어 있으며,
**본문은 한 글자도 고치지 않았다.**

- 사람이 읽을 정리본: [`../LESSONS_LEARNED.md`](../LESSONS_LEARNED.md)
- AI 주입용 통합본: [`../AI_CONTEXT_FULL.md`](../AI_CONTEXT_FULL.md)
- 재생성: `python docs/build_docs.py`

---

## 문서 목록

### 0x — 모델 / 데이터 레퍼런스

| 문서 | 내용 |
|---|---|
| [`01-model-experiments-full.md`](01-model-experiments-full.md) | **EGG 추정 모델 실험 전체 이력.** 성공 6건 + 실패·중단 14건(Exp1b·2·4~9·12·13~19)의 원인. GitHub의 `EXPERIMENT_REPORT.md`는 Exp0~4까지만 다루므로 이 문서가 유일한 전체 기록이다 |
| [`02-dataset-reference.md`](02-dataset-reference.md) | 데이터셋 레퍼런스 |
| [`03-folder-structure.md`](03-folder-structure.md) | 저장소 폴더 구조 상세 |

### 1x — 매칭 방식 진단 (2026-05-03)

| 문서 | 내용 |
|---|---|
| [`10-matching-diagnosis-summary.md`](10-matching-diagnosis-summary.md) | **per-register vs per-session 진단 보고서.** 흉성두성 r이 −0.282 ↔ +0.554로 뒤집힌 원인이 모델이 아니라 집계 단위였음을 규명. 의사반복(pseudoreplication) 발견 |
| [`11-matching-diagnosis-slides.md`](11-matching-diagnosis-slides.md) | 위 진단의 발표 슬라이드 초안 |

### 2x — 5/10 데이터 검증 (2026-05-10 ~ 05-11)

| 문서 | 내용 |
|---|---|
| [`20-icc-510-report.md`](20-icc-510-report.md) | 평가자 5명 간 신뢰도(ICC) 검증. 9항목 평균 0.793, 접촉강도 0.898, 연구개위치 B그룹 0.321(poor) |
| [`21-midi-octave-check-510.md`](21-midi-octave-check-510.md) | 외부 MIDI 6곡 옥타브 검증 (전부 정상) |
| [`22-sign-reversal-analysis.md`](22-sign-reversal-analysis.md) | **부호 반전 학술 분석.** 마이크가 바뀌면 지표의 측정값뿐 아니라 의미 자체가 바뀔 수 있음. 비강사용·전방공명을 `academic_only`로 강등한 근거 |
| [`23-b1-difference-root-cause.md`](23-b1-difference-root-cause.md) | **B1 sample 비결정성 추적 — 미해결.** direct call은 33 indicator 전부 일치하는데 pipeline 통과 시만 Δ 0.3~0.6 |
| [`24-d3-compatibility-test.md`](24-d3-compatibility-test.md) | score_mapper_v2 통합 후 endpoint 호환성 검증 |
| [`25-handover-2026-05-11.md`](25-handover-2026-05-11.md) | 2026-05-11 인계 문서. F4(timeline 4항목 확장) 작업 상세와 당시 산출물 위치 |
| [`26-presentation-key-messages.md`](26-presentation-key-messages.md) | 발표용 핵심 메시지 |

### 3x — 최종 검증 리포트

| 문서 | 내용 |
|---|---|
| [`30-egg-model-contribution.md`](30-egg-model-contribution.md) | EGG 모델 기여도 분석 |
| [`31-final-validation-report.md`](31-final-validation-report.md) | 최종 검증 리포트 |
| [`32-graduation-final-summary.md`](32-graduation-final-summary.md) | 졸업작품 최종 요약 |
| [`33-validation-feedback-report.md`](33-validation-feedback-report.md) | 검증 11명 × 3음역대 AI vs 트레이너 피드백 전수 비교 (1,403행). 원자료 성격 |

### 4x — 검증 신뢰성 재확인 (2026-07-26)

| 문서 | 내용 |
|---|---|
| [`40-rediag-selection-bias-2026-07.md`](40-rediag-selection-bias-2026-07.md) | **검증 수치에 관해 가장 최신·정확한 문서.** 선택 편향 정량화(우연 max\|r\|=0.62), 화자 부트스트랩 CI, 중첩 CV, 재학습 파이프라인 복원, mapper 무용성, 학습집합 25쌍/16화자 확정 |

---

## 읽는 순서

**처음 보는 사람**
1. [`../LESSONS_LEARNED.md`](../LESSONS_LEARNED.md) — 전체 조망
2. `01` — 모델이 어떻게 0.67 → 0.82까지 갔는지, 무엇이 실패했는지
3. `10` → `22` → `40` — 평가 설계가 세 번에 걸쳐 어떻게 교정됐는지

**검증 수치를 인용해야 하는 경우**
`40` 을 먼저 볼 것. 그 이전 문서들의 corr 값은 선택 편향이 보정되지 않은 값이다.

**같은 실수를 피하고 싶은 경우**
[`../../dml-server/CLAUDE.md`](../../dml-server/CLAUDE.md) §"⚠️ 반복하지 말 것" + `23`(미해결 건)

---

## 이관하지 않은 것

원시 데이터와 계산 산출물은 저장소에 넣지 않았다. dmlserver 로컬에만 있다.

| 경로 | 내용 |
|---|---|
| `data/vocal_academy/singer_01..22/` | 가수 녹음 원본 (oral/nasal/phone wav) |
| `data/vocal_academy/results/**/*.csv`, `*.json` | 지표·모델 산출물 |
| `data/vocal_academy/results/sidetrack/rediag/` | 2단계 진단 스크립트·JSON (결론은 `40` 에 이관 완료) |
| `checkpoints/exp20_progressive/best_model.pt` | 모델 가중치 (5.99M params) |
