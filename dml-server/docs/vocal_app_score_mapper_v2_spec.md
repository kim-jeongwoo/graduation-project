# vocal-app score_mapper_v2 spec (D3-5)

**작성일**: 2026-05-11
**대상**: vocal-app 페이지 (Expo 앱 측 spec 갱신용)
**전제**: vocal-app 코드 수정 X. 본 spec은 응답 schema 변경사항 + UI 처리 spec.

---

## 1. `/analyze` endpoint 응답 schema 변경

기존 응답에 다음 4개 필드 신규 추가됨 (기존 필드 변경 X):

```json
{
  "...": "기존 필드 유지 (audio_info, scores, feedback, reliability, user_f0, ...)",

  "score_mapper_version": "v2",

  "scores_v2": {
    "3_vocal_fold_contact": 3.2,
    "4_breathiness":        2.8,
    "6_soft_palate":        2.5,
    "8_tongue_tension":     3.0
  },

  "scores_meta": {
    "3_vocal_fold_contact": {
      "tier":           "high",
      "caveats":        [],
      "display_mark":   null,
      "tooltip":        null,
      "rounded_score":  3,
      "icc":            0.898,
      "icc_ratio":      0.816
    },
    "4_breathiness": {
      "tier":           "high_star",
      "caveats":        ["regularization_softened_for_range_v2_fix",
                         "train_val_sign_diverged",
                         "val_total_below_0_5"],
      "display_mark":   "asterisk",
      "tooltip":        "외부 데이터에서 신뢰도 확보, 학습 내부 검증 약함 (모니터링 중)",
      "rounded_score":  3,
      "icc":            0.796,
      "icc_ratio":      0.546
    },
    "6_soft_palate":     { "tier": "high_star", "...": "..." },
    "8_tongue_tension":  { "tier": "high_star", "...": "..." }
  },

  "academic_analysis_scores": {
    "1_nasal_oral_ratio": {
      "ai_score": 1.78,
      "caveats":  ["sign_reversed"],
      "note":     "sign_reversed 학술 분석 전용 (앱 표시 X)"
    },
    "5_forward_resonance": { "...": "..." }
  },

  "reliability": {
    "...": "기존 high_reliability/medium_reliability/unavailable 유지",

    "shown_v2":         ["3_vocal_fold_contact","4_breathiness",
                         "6_soft_palate","8_tongue_tension"],
    "shown_v2_tiers": {
      "3_vocal_fold_contact": "high",
      "4_breathiness":        "high_star",
      "6_soft_palate":        "high_star",
      "8_tongue_tension":     "high_star"
    },
    "academic_only_v2": ["1_nasal_oral_ratio","5_forward_resonance"],
    "deferred_v2":      ["2_chest_head_voice","7_larynx_tongue_root",
                         "9_pressure_balance"]
  }
}
```

**호환성 보장**:
- 기존 `scores` (9 항목) 필드 그대로 유지 — legacy client 영향 없음
- 신규 `scores_v2` (4 항목) 추가 — 권장 사용
- 권장: 신규 client는 `scores_v2` + `scores_meta` 사용

---

## 2. tier별 UI 처리

| tier | 표시 방식 |
|---|---|
| **high** | 기본 표시 (큰 숫자 + 색상 그라데이션) |
| **high_star** | 기본 표시 + **별표(\*)** + 툴팁 (`tooltip` 필드 표시) |
| (academic_only) | **앱 표시 X** (dml-server 내부 학술 분석용) |
| (deferred) | **앱 표시 X** (신뢰도 미달, 측정 불가 표시) |

**high vs high_star 시각 차이 예시**:
```
[기본]                  [별표 + 툴팁]
접촉강도                호흡식별 *
3.2 / 5                 2.8 / 5    (* 외부 데이터에서 신뢰도 확보,
                                       학습 내부 검증 약함)
```

---

## 3. caveat 코드 매핑 (사용자 친화적 문구)

| 코드 | 사용자 표시 | 비고 |
|---|---|---|
| `train_weak_external_only` | "외부 데이터에서 신뢰도 확보, 학습 내부 검증 진행 중" | tooltip에 노출 |
| `regularization_softened_for_range_v2_fix` | (사용자에게 노출 X) | dev only |
| `train_val_sign_diverged` | (사용자에게 노출 X) | dev only |
| `val_total_below_0_5` | (사용자에게 노출 X) | dev only |
| `sign_reversed` | (academic_only 항목이라 앱 표시 X) | — |

→ vocal-app은 `scores_meta[item].tooltip` 필드를 그대로 사용하면 사용자 친화적 문구 자동 노출됨.

---

## 4. score_mapper_v2 사용 안내

- **vocal-app 측 호출 코드 변경 X**: `/analyze` endpoint URL과 multipart 요청 형식 그대로
- **응답 처리만 확장**: `score_mapper_version === "v2"` 인 경우 `scores_v2` + `scores_meta` 우선 사용
- **fallback**: `scores_v2` 없거나 `score_mapper_version !== "v2"` 경우 기존 `scores` (v1 9 항목) 사용

---

## 5. 통제 실험 (5/14~5/24) 표시 항목 4개

학원 통제 실험 기간 동안 vocal-app은 다음 4 항목만 표시:

| 항목 ID | 이름 | tier | 표시 |
|---|---|---|---|
| `3_vocal_fold_contact` | 접촉강도 | high | 기본 |
| `4_breathiness` | 호흡식별 | high_star | 별표 + 툴팁 |
| `6_soft_palate` | 연구개위치 | high_star | 별표 + 툴팁 |
| `8_tongue_tension` | 혀경직도 | high_star | 별표 + 툴팁 |

나머지 5 항목 (`1_nasal_oral_ratio`, `2_chest_head_voice`, `5_forward_resonance`, `7_larynx_tongue_root`, `9_pressure_balance`)은 앱 화면에 노출 X.

---

## 6. 예상 latency 증가 안내

v2 통합으로 full-song `/analyze` endpoint 처리 시간 증가:
- 기존 v1: ~10-15s (곡 전체)
- **초기/older estimate: ~80-110s** (33 indicator 산출 추가 기준)
- 현재 full `/analyze` 총 소요 시간은 곡 길이와 timeline 처리 비용에 따라 older estimate를 초과할 수 있음. 최신 측정/운영 기준은 `PROJECT_LOG.md` §15 latest 및 아래 8.5 비용 표 기준으로 확인.

vocal-app 측 처리 안내:
- `StreamingResponse` P2-A는 early TTFB/keepalive로 Cloudflare 524를 회피한다.
- Cloudflare 125s timeout은 total duration cap이 아니라 TTFB 기준으로 취급한다.
- 클라이언트 total timeout은 older 80-110s estimate에 맞추지 말고, full-song 분석 총시간과 안전 마진을 반영한다. 권장값은 8.5의 300s guidance 참조.

`/analyze-chunk` (Phase 4 5-10s chunk): full `/analyze`와 별도 latency 기준의 non-streaming endpoint. current 운영 기준은 대략 3~5s 응답 (`PROJECT_LOG.md` §15 latest 기준). full-song latency 가정을 chunk endpoint에 재사용하지 않는다.
`/ws/realtime` (200ms chunk): **v2 비적용 확정** (latency 부담).
- 응답 schema: v1 유지 (`score_mapper_version` 필드 없음)
- 200ms 음정 일치율 → 즉시 응답
- 5초 호흡 chunk → v1 score_mapper(cpp_mean indicator) 기반 점수
- vocal-app 측 처리: `/ws/realtime` 응답에 `scores_v2`/`scores_meta` 없음 → v1 schema로 처리

---

## 7. 알려진 한계 + follow-up

- **B1 sample 1건 pipeline 내부 인터랙션 차이 발견** (검증 4개 중 1개 Δ 0.3~0.6). direct call로는 일치, pipeline 통과 시 차이. 원인 추적 별도 진행 (5/13 EOD 전).
- **호흡식별 sign divergence**: 학습 5-fold train_corr=-0.13, val_total=+0.43. mapper로 인한 indicator 부호 교정 효과. 학원 통제 실험에서 모니터링.
- **연구개위치/혀경직도 train_5fold≈0**: 외부 검증만 강한 일관성. 학습 단계에서 spurious 가능성 존재. 통제 실험에서 추가 검증.

---

## 8. timeline_scores 4항목 확장 (F4, 2026-05-11)

**변경**: `/analyze` 응답의 `timeline_scores`(LRC chunk 단위) — 호흡식별 1개 float → 4 항목 dict로 확장.

### 8.1 `timeline_scores` 신규 schema

```json
"timeline_scores": [
  {
    "start_sec":         5.0,
    "end_sec":           12.0,
    "lrc_text":          "...",
    "chunk_duration_s":  7.0,
    "scores": {
      "3_vocal_fold_contact": {"ai_score": 2.51, "rounded_score": 3, "tier": "high"},
      "4_breathiness":        {"ai_score": 1.48, "rounded_score": 1, "tier": "high_star"},
      "6_soft_palate":        {"ai_score": 3.29, "rounded_score": 3, "tier": "high_star"},
      "8_tongue_tension":     {"ai_score": 2.87, "rounded_score": 3, "tier": "high_star"}
    },
    "low_confidence_items": []
  },
  ...
]
```

**breaking change** (vocal-app 측 처리 갱신 필수):
- 기존: `timeline_scores[i].scores["4_breathiness"]` = float
- 신규: `timeline_scores[i].scores["4_breathiness"]` = `{ai_score, rounded_score, tier}` dict

### 8.2 `timeline_metadata` 신규 schema

```json
"timeline_metadata": {
  "n_chunks": 28,
  "n_ok":      28,
  "n_skipped": 0,
  "processing_time_ms": 76400,
  "shown_indicators": ["3_vocal_fold_contact","4_breathiness",
                       "6_soft_palate","8_tongue_tension"],
  "shown_indicators_meta": {
    "3_vocal_fold_contact": {"tier":"high",      "display_mark": null},
    "4_breathiness":        {"tier":"high_star", "display_mark": "asterisk"},
    "6_soft_palate":        {"tier":"high_star", "display_mark": "asterisk"},
    "8_tongue_tension":     {"tier":"high_star", "display_mark": "asterisk"}
  },
  "chunk_score_items": ["3_vocal_fold_contact","4_breathiness",
                        "6_soft_palate","8_tongue_tension"],
  "low_confidence_threshold_s": 5.0,
  "chunk_min_voiced_s":         2.0,
  "score_mapper_version":       "v2",
  "v2_chunk_cost_avg_ms":       2695.8
}
```

### 8.3 `low_confidence_items` 규칙

`chunk_duration_s < 5.0` 시 다음 3 항목이 `low_confidence_items` 리스트에 표시됨:
- `4_breathiness`, `6_soft_palate`, `8_tongue_tension`

`3_vocal_fold_contact`는 chunk 길이 영향이 작아 제외.

vocal-app UI 처리:
- `low_confidence_items`에 포함된 항목은 별도 회색 또는 "(짧은 구간)" 표시 권장
- 점수는 그대로 표시하되 신뢰도 낮음 안내

### 8.4 `/analyze-chunk` (Phase 4) 응답 확장

기존 응답에 다음 필드 추가:

```json
{
  "status":            "success",
  "duration_sec":      8.5,
  "chunk_duration_s":  8.5,

  "scores": {                          // legacy v1 (2 항목, 호환 유지)
    "3_vocal_fold_contact": {...},
    "4_breathiness":        {...}
  },

  "scores_v2": {                       // F4-3 신규: 4 항목 (권장 사용)
    "3_vocal_fold_contact": {
      "ai_score": 2.83, "rounded_score": 3,
      "zone": "appropriate", "confidence": "high", "tier": "high"
    },
    "4_breathiness":    { "...": "tier=high_star" },
    "6_soft_palate":    { "...": "tier=high_star" },
    "8_tongue_tension": { "...": "tier=high_star" }
  },

  "scores_meta":         { ... /analyze 와 동일 },
  "low_confidence_items": ["4_breathiness","6_soft_palate","8_tongue_tension"],
  "score_mapper_version": "v2"
}
```

- `zone`: v1 로직 그대로 (ai_score round ≤1 insufficient / 2-3 appropriate / 4-5 excessive)
- `confidence`: chunk_duration ≥ 5s → "high", 3~5s → "medium"
- `low_confidence_items`: chunk < 5s 시 high_star 3 항목 명시

### 8.5 비용 (실측)

| 단위 | 비용 (실측, B1 wav 204.5s) |
|---|---|
| `/analyze` core pass (EGG + v1 + v2 indicators, older B1 estimate) | ~80-110s |
| timeline chunk loop (4 항목, N=28×7s) | **~76s** (chunk당 평균 2.7s) |
| **full `/analyze` 곡 1개 총 (v2 통합 + timeline 4항목)** | **~160-190s** |
| `/analyze-chunk` 단일 (8s chunk) | current 운영 기준 ~3~5s, non-streaming (`PROJECT_LOG.md` §15 latest 기준) |

vocal-app 측 권장 total timeout: **300s** (안전 마진). Cloudflare 125s는 total timeout이 아니라 TTFB 기준이며, full `/analyze`는 `StreamingResponse` P2-A의 early whitespace/keepalive 후 최종 JSON body를 전송한다. `/analyze-chunk` latency는 별도 기준으로 보고, full-song latency assumption을 재사용하지 않는다.
