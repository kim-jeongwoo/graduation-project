# DML_RESPONSE_SPEC.md — dml-server 응답 스펙 (vocal-server / vocal-app 소비자용)

- 작성 기준: 코드 실측 (2026-07-07). 판단이 아닌 코드 사실만. 근거는 `파일:라인`.
- 대상 코드: `dml-server/model_server/{server.py, analysis_pipeline.py, schemas.py, services/{chunk_analysis,timeline_analysis}.py, score_mapper_v2 경유}`
- 라우팅: 외부 `https://dml.vocal-fit.com` → tunnel `dml-server`(UUID 725417d8) → `http://localhost:8001` (근거는 `docs/VERIFY_dmlserver.md` 및 본 세션 라우팅 실측 보고).

---

## 0. 공통

- 9항목 key 체계 (`CSV_TO_CRITERIA`, [analysis_pipeline.py:73-84](../dml-server/model_server/analysis_pipeline.py#L73)):
  `1_nasal_oral_ratio`(비강사용), `2_chest_head_voice`(흉성두성), `3_vocal_fold_contact`(접촉강도), `4_breathiness`(호흡식별), `5_forward_resonance`(전방공명), `6_soft_palate`(연구개위치), `7_larynx_tongue_root`(공명개방), `8_tongue_tension`(혀경직도), `9_pressure_balance`(상압하압).
- **score_mapper_version**: 문자열 `"v2"` — score_mapper(=v2 매핑) 버전. 응답에 포함 ([analysis_pipeline.py:684](../dml-server/model_server/analysis_pipeline.py#L684)).
- **EGG 모델 자체 version / checkpoint hash: 응답 어디에도 없음 (사실).** `/health`도 미포함 ([server.py:74-81](../dml-server/model_server/server.py#L74)). 소비자는 EGG 모델 버전을 응답에서 알 수 없다.

---

## 1. `POST /analyze`

전곡 종합 분석. **StreamingResponse** (`media_type="application/json"`), leading-whitespace keepalive(5s 간격 `b" "`) → Cloudflare 125s edge timeout 우회. 표준 JSON 파서는 leading whitespace 무시. ([server.py:184-255](../dml-server/model_server/server.py#L184))

Query: `run_id`(opt, 없으면 자동 생성), `song_id`(opt, 지정 시 LRC 타임라인 포함).

### HTTP status
| 상황 | HTTP | 근거 |
|---|---|---|
| 정상/무음/잡음/분석오류 (스트리밍 시작 후) | **200 고정** | [server.py:234-255](../dml-server/model_server/server.py#L234) |
| 파일 read 실패 | 400 | [server.py:228-229](../dml-server/model_server/server.py#L228) |
| 파일 < 1000 bytes | 400 | [server.py:231-232](../dml-server/model_server/server.py#L231) |
| pipeline 미로드 | 503 | [server.py:219-220](../dml-server/model_server/server.py#L219) |

> 스트리밍 시작(첫 byte) 이후 HTTP status 변경 불가 → 아래 body `status` 필드로 결과 구분.

### body `status` enum (실제 방출값)
`success` | `no_voice` | `invalid` | `failed` ([server.py:150-162,178](../dml-server/model_server/server.py#L150))
- (참고: `schemas.AnalysisStatus`에는 `success/completed/failed/no_voice`만 정의, `invalid`는 enum 미등록 — 실제 방출은 문자열. [schemas.py:14-18](../dml-server/model_server/schemas.py#L14))

### 성공 응답 schema (`status:"success"`)
`server.py`가 `{run_id, status:"success", **result, timeline_scores, timeline_metadata}` 조립 ([server.py:177-181](../dml-server/model_server/server.py#L177)). `result`는 `pipeline.analyze()` 반환 ([analysis_pipeline.py:663-704](../dml-server/model_server/analysis_pipeline.py#L663)).

| 필드 | 타입 | 비고 |
|---|---|---|
| `run_id` | str | |
| `status` | "success" | |
| `processing_time_ms` | float | |
| `audio_info` | obj | `{duration_s, sample_rate(=16000), voiced_ratio, voiced_duration_s, f0_min?, f0_max?, f0_mean?}` |
| `register_boundaries` | obj | `{low_max, mid_max}` (Hz) |
| `registers` | obj | key `low/mid/high`, 각 `{n_frames, cq_mean, cq_peak, cpp, hnr, spectral_centroid, spectral_tilt, h1_h2, singers_formant_ratio, a1_p0}` (값은 float 또는 null) [analysis_pipeline.py:520-527](../dml-server/model_server/analysis_pipeline.py#L520) |
| `indicators` | obj | `{cq_mean, cq_peak, cpp_mean, hnr_mean, spectral_centroid_mean, spectral_tilt_mean, h1_h2_mean, singers_formant_ratio_mean, a1_p0_mean, nasal_ratio(=항상 null)}` [analysis_pipeline.py:539-548](../dml-server/model_server/analysis_pipeline.py#L539) |
| `scores` | obj | **v1 legacy, 9 key**. 각 `{ai_score(float|null), rounded_score(int|null), zone(str|null), confidence("high"/"medium"/"unavailable")}` [analysis_pipeline.py:587-592](../dml-server/model_server/analysis_pipeline.py#L587) |
| `scores_v2` | obj | **표시 4 key만** (tier high/high_star). `{key: ai_score(float)}` — 값이 점수 자체 [analysis_pipeline.py:638-639](../dml-server/model_server/analysis_pipeline.py#L638) |
| `scores_meta` | obj | 표시 4 key. 각 `{tier, caveats[], display_mark("asterisk"|null), tooltip(str|null), rounded_score(int), icc, icc_ratio}` [analysis_pipeline.py:640-649](../dml-server/model_server/analysis_pipeline.py#L640) |
| `academic_analysis_scores` | obj | academic_only 2 key (앱 표시 X). 각 `{ai_score, caveats[], note}` [analysis_pipeline.py:650-655](../dml-server/model_server/analysis_pipeline.py#L650) |
| `score_mapper_version` | str | `"v2"` |
| `feedback` | obj | 9 key. 각 `{name_ko, ai_score, score_description, feedback_text, zone, zone_label("미달"/"적절"/"과함"/""), ai_indicator:{name, value}}` [analysis_pipeline.py:598-609](../dml-server/model_server/analysis_pipeline.py#L598) |
| `reliability` | obj | §3 tier 매핑 참조 [analysis_pipeline.py:686-702](../dml-server/model_server/analysis_pipeline.py#L686) |
| `user_f0` | obj | `{frame_hz:25, values:[float|null,...]}` — voiced=Hz, unvoiced=null (sparse-null) [analysis_pipeline.py:242-247](../dml-server/model_server/analysis_pipeline.py#L242) |
| `timeline_scores` | list \| null | `song_id` 지정 & LRC 존재 시에만 값. 아니면 null. §4 |
| `timeline_metadata` | obj \| null | 위와 동일 조건. LRC 없으면 null; 타임라인 예외 시 `{error:str}` [server.py:164-176](../dml-server/model_server/server.py#L164) |

### 비-성공 응답
- `no_voice` ([server.py:150-158](../dml-server/model_server/server.py#L150)): `{run_id, status:"no_voice", reason, processing_time_ms, audio_info, scores:null, feedback:null, reliability:null, registers:null, register_boundaries:null, indicators:null, timeline_scores:null, timeline_metadata:null, user_f0:null}`. (Guard A/B — §무음가드)
- `invalid` ([server.py:159-160](../dml-server/model_server/server.py#L159)): `{run_id, status:"invalid", error}`.
- `failed` ([server.py:161-162,249-253](../dml-server/model_server/server.py#L161)): `{run_id, status:"failed", error}`.

### 무음 가드 (Guard A/B, `/analyze`는 min_voiced_s=5.0 고정)
- Guard A ([analysis_pipeline.py:380-387](../dml-server/model_server/analysis_pipeline.py#L380)): `voiced_s < min_voiced_s` → no_voice. (`/analyze`는 기본 `MIN_VOICED_S=5.0`)
- Guard B ([analysis_pipeline.py:389-401](../dml-server/model_server/analysis_pipeline.py#L389)): `voiced_ratio > 0.95` **AND** voiced 프레임 `cpp_mean < 0.15` → no_voice.

---

## 2. `POST /analyze-chunk`

단일 chunk(3~10초 권장) 사후 분석. **StreamingResponse 아님 → 실제 HTTP status 사용.** ([server.py:259-393](../dml-server/model_server/server.py#L259))

Query: `run_id`(opt), `start_sec`(opt), `end_sec`(opt), `song_id`(opt, **현재 미사용**).

### HTTP status
| 상황 | HTTP | body | 근거 |
|---|---|---|---|
| pipeline 미로드 | 503 | detail | [server.py:275-276](../dml-server/model_server/server.py#L275) |
| 파일 read 실패 / <1000B | 400 | detail | [server.py:283-286](../dml-server/model_server/server.py#L283) |
| **chunk < 3.0s** | **400** | `{error:"chunk_too_short", reason, duration_sec, min_required_sec:3.0}` | [server.py:293-302](../dml-server/model_server/server.py#L293) |
| 디코드 실패 | 400 | detail | [server.py:303-304](../dml-server/model_server/server.py#L303) |
| 무음(SilentInputError) | **200** | `status:"no_voice"` | [server.py:309-323](../dml-server/model_server/server.py#L309) |
| 정상 | **200** | `status:"success"` | [server.py:381-393](../dml-server/model_server/server.py#L381) |
| 내부 예외 | 500 | `{run_id, status:"failed", error}` | [server.py:324-328](../dml-server/model_server/server.py#L324) |

- chunk confidence: `duration ≥ 5.0` → "high", `3.0 ≤ duration < 5.0` → "medium" ([chunk_analysis.py:70](../dml-server/model_server/services/chunk_analysis.py#L70)).
- min_voiced_s = `duration × 0.4` (chunk 전용, [chunk_analysis.py:69](../dml-server/model_server/services/chunk_analysis.py#L69)) → Guard A 판정에 사용.

### 성공 응답 (`status:"success"`, HTTP 200)
| 필드 | 타입 | 비고 |
|---|---|---|
| `run_id` | str | |
| `status` | "success" | |
| `duration_sec` | float | slice 후 chunk 길이 |
| `chunk_duration_s` | float | 동일 값(소수 3자리) |
| `scores` | obj | **v1 legacy 2 key**: `3_vocal_fold_contact`, `4_breathiness`. 각 `{ai_score, rounded_score, zone, confidence}` (confidence는 chunk confidence 또는 "unavailable") [server.py:344-352](../dml-server/model_server/server.py#L344) |
| `scores_v2` | obj | **4 key**: `3_vocal_fold_contact,4_breathiness,6_soft_palate,8_tongue_tension`. 각 `{ai_score, rounded_score, zone("insufficient"/"appropriate"/"excessive"/null), confidence, tier}` [server.py:357-367](../dml-server/model_server/server.py#L357) |
| `scores_meta` | obj | v2 meta 원본 [server.py:388](../dml-server/model_server/server.py#L388) |
| `low_confidence_items` | list[str] | `duration<5.0` → `["4_breathiness","6_soft_palate","8_tongue_tension"]`, else `[]` [server.py:368-371](../dml-server/model_server/server.py#L368) |
| `score_mapper_version` | str | `"v2"` |
| `indicators` | obj | `{voiced_ratio, cpp_mean, cq_p90(=cq_peak)}` [server.py:373-379](../dml-server/model_server/server.py#L373) |
| `processing_time_ms` | float | |

### no_voice 응답 (HTTP 200, [server.py:309-323](../dml-server/model_server/server.py#L309))
`{run_id, status:"no_voice", reason, duration_sec, chunk_duration_s, scores:null, scores_v2:null, scores_meta:null, low_confidence_items:null, score_mapper_version:null, indicators:null, processing_time_ms}`.

---

## 3. `scores_meta.tier` / reliability 매핑 (analysis_pipeline.py:686-701)

포함 규칙: v2 mapper 6항목 중 tier에 따라 응답 분기 ([analysis_pipeline.py:637-655](../dml-server/model_server/analysis_pipeline.py#L637)).

| 그룹 | key | tier | 응답 위치 |
|---|---|---|---|
| 표시 (shown_v2) | `3_vocal_fold_contact` | **high** | `scores_v2` + `scores_meta` |
| 표시 (shown_v2) | `4_breathiness` | **high_star** | `scores_v2` + `scores_meta` (display_mark=asterisk) |
| 표시 (shown_v2) | `6_soft_palate` | **high_star** | `scores_v2` + `scores_meta` (asterisk) |
| 표시 (shown_v2) | `8_tongue_tension` | **high_star** | `scores_v2` + `scores_meta` (asterisk) |
| academic_only_v2 | `1_nasal_oral_ratio` | academic_only | `academic_analysis_scores` (앱 표시 X) |
| academic_only_v2 | `5_forward_resonance` | academic_only | `academic_analysis_scores` (앱 표시 X) |
| deferred_v2 (제외) | `2_chest_head_voice` | — | **미산출** (응답에 점수 없음) |
| deferred_v2 (제외) | `7_larynx_tongue_root` | — | **미산출** |
| deferred_v2 (제외) | `9_pressure_balance` | — | **미산출** |

- 정확한 key 목록은 `reliability` 객체에 그대로 노출 ([analysis_pipeline.py:691-701](../dml-server/model_server/analysis_pipeline.py#L691)):
  - `shown_v2 = ["3_vocal_fold_contact","4_breathiness","6_soft_palate","8_tongue_tension"]`
  - `shown_v2_tiers = {3_vocal_fold_contact:"high", 4_breathiness:"high_star", 6_soft_palate:"high_star", 8_tongue_tension:"high_star"}`
  - `academic_only_v2 = ["1_nasal_oral_ratio","5_forward_resonance"]`
  - `deferred_v2 = ["2_chest_head_voice","7_larynx_tongue_root","9_pressure_balance"]`
- (별개) v1 reliability 분류 ([analysis_pipeline.py:65-70](../dml-server/model_server/analysis_pipeline.py#L65)): `high_reliability=[3,4]`, `medium_reliability=[1,2,5,6,9]`, `unavailable=[7,8]` — `scores[*].confidence` 계산에 사용. **v2 tier와 다른 분류이므로 혼동 주의.**

---

## 4. `timeline_scores` 원소 shape & **null 계약** (앱 크래시 방지)

`song_id` 지정 + LRC 파싱 파일 존재 시에만 생성. 소스: [timeline_analysis.py:153-278](../dml-server/model_server/services/timeline_analysis.py#L153).

### 원소 shape ([timeline_analysis.py:237-244](../dml-server/model_server/services/timeline_analysis.py#L237))
```
{
  "start_sec": float, "end_sec": float,
  "lrc_text": str,
  "chunk_duration_s": float,
  "scores": {                       # 4 key 고정
     "3_vocal_fold_contact": {ai_score, rounded_score, tier} | null,
     "4_breathiness":        {...} | null,
     "6_soft_palate":        {...} | null,
     "8_tongue_tension":     {...} | null
  },
  "low_confidence_items": [str, ...]
}
```

### `scores[*]`가 **null**이 되는 조건 — **설계된 출력** (의도치 않은 누락 아님)
1. **초기화**: 매 chunk `scores_out = {k: None for k in TIMELINE_ITEMS}` — 기본이 4개 모두 null ([timeline_analysis.py:199](../dml-server/model_server/services/timeline_analysis.py#L199)).
2. **skip 경로**: `not v2_available` **또는** `chunk_dur < CHUNK_MIN_VOICED_S(=2.0s)` → 4개 모두 null 유지, `n_skipped++` ([timeline_analysis.py:202-205](../dml-server/model_server/services/timeline_analysis.py#L202), 상수 [:67](../dml-server/model_server/services/timeline_analysis.py#L67)).
3. **예외 경로**: chunk 채점 중 예외 → 4개 모두 null, `n_skipped++` ([timeline_analysis.py:225-228](../dml-server/model_server/services/timeline_analysis.py#L225)).
4. **부분 누락(이론상)**: 채점 성공했으나 특정 key 미반환 시 해당 key만 null 유지 ([timeline_analysis.py:220-223](../dml-server/model_server/services/timeline_analysis.py#L220)). 단 `ScoreMapperV2._build_scores`는 항상 4개 모두 non-None `ai_score`를 반환하므로([score_mapper_v2.py:129-138](../dml-server/scripts/sidetrack/score_mapper_v2.py#L129)) **실무상 partial-null은 발생하지 않음 → chunk 단위 all-or-nothing.**

**판정: 설계된 출력.** `scores` 하위 4 key는 값(dict) 또는 null이며, chunk가 skip/예외이면 **4개 전부 null**. 실측 366청크 중 258 null은 위 2·3 경로(주로 `chunk_dur < 2.0s` skip)와 정합 — 코드상 의도된 skip이다. 정확한 원인 분해(skip vs 예외)는 `timeline_metadata.n_skipped`/`n_ok`로 확인 가능(§4 metadata).

### 소비자(앱) 계약 — **반드시 null 처리**
- `timeline_scores` 자체가 `null`일 수 있다 (song_id 미지정 / LRC 없음 → [server.py:165-176](../dml-server/model_server/server.py#L165)).
- `timeline_scores`가 배열이어도 각 원소의 `scores[key]`가 `null`일 수 있다 (위 조건). **`scores[key]`를 역참조하기 전 null 검사 필수.** null인 항목은 "해당 구간 신뢰 가능한 점수 없음"으로 표시/스킵해야 한다.
- `low_confidence_items`에 포함된 key는 값이 있어도 저신뢰 — 별도 표기 대상.

### `timeline_metadata` shape ([timeline_analysis.py:256-276](../dml-server/model_server/services/timeline_analysis.py#L256))
`{n_chunks, n_ok, n_skipped, processing_time_ms, items, shown_indicators, shown_indicators_meta, shown_indicators_reason, chunk_score_items, deferred_indicators(=["2_chest_head_voice","7_larynx_tongue_root","9_pressure_balance"]), deferred_reason, deferred_revisit_after, chunk_min_voiced_s(=2.0), low_confidence_threshold_s(=5.0), max_chunk_sec(=15.0), score_mapper_version("v2"), v2_chunk_cost_avg_ms}`.

---

## 5. `low_confidence_items` shape

- **`/analyze-chunk` 최상위**: `list[str]`. `duration<5.0` → `["4_breathiness","6_soft_palate","8_tongue_tension"]`, else `[]` ([server.py:368-371](../dml-server/model_server/server.py#L368)).
- **`timeline_scores` 원소별**: `list[str]`. 구성 ([timeline_analysis.py:200,221-235](../dml-server/model_server/services/timeline_analysis.py#L200)): skip/예외 시 4항목 전체; 부분 누락 key; 추가로 `chunk_dur < 5.0s`면 `["4_breathiness","6_soft_palate","8_tongue_tension"]` 병합(접촉강도 제외).

---

## 6. `rounded_score` 생성 위치

- **v1 scores** (`/analyze`, `/analyze-chunk` legacy): `rounded = min(5, max(0, round(ai_score)))` ([analysis_pipeline.py:576](../dml-server/model_server/analysis_pipeline.py#L576)); ai_score None이면 rounded None ([:577-579](../dml-server/model_server/analysis_pipeline.py#L577)).
- **v2 (ScoreMapperV2)**: `rounded_score = int(round(pred_clipped))`, `pred_clipped = max(0, min(5, pred))` ([score_mapper_v2.py:129-132](../dml-server/scripts/sidetrack/score_mapper_v2.py#L129)). → `scores_meta[*].rounded_score`, `timeline_scores[*].scores[*].rounded_score`의 출처.
- `/analyze-chunk`의 `scores_v2[*].rounded_score`는 v2 meta에서 가져옴 (`m.get("rounded_score")`, [server.py:363](../dml-server/model_server/server.py#L363)).

---

## 7. 요약 (소비자 체크리스트)
- HTTP status: `/analyze`는 스트리밍 시작 후 **200 고정**, 결과는 body `status`로 판별. `/analyze-chunk`는 실제 status(`chunk_too_short=400` 확정, no_voice/success=200, 내부오류=500).
- `status` enum: `success | no_voice | invalid(analyze) | failed`.
- `scores_v2` 표시 4항목(high 1 / high_star 3), academic 2항목은 `academic_analysis_scores`, deferred 3항목은 미산출.
- `timeline_scores`와 그 원소의 `scores[key]`는 **null 가능 — 반드시 null 처리** (설계된 skip, 특히 chunk<2.0s).
- `score_mapper_version="v2"` 존재. **EGG 모델 버전/해시는 응답에 없음.**
