<!-- provenance -->
> **원본**: `data/vocal_academy/results/sidetrack/d3_compatibility_test.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: score_mapper_v2 통합 후 endpoint 호환성 검증
> **원본 수정일**: 2026-05-11 · **크기**: 2,534 bytes · **sha256[:8]**: `5643c830`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# D3-6c 호환성 검증 (2026-05-11)

analysis_pipeline.py에 score_mapper_v2 통합 후 기존 endpoint 동작 확인.

## /analyze (HTTP) — D3-6a

| sample | latency | scores_v2 | scores_meta | predictions_21 일치 |
|---|---:|---|---|---|
| A1 | 86s | ✓ 4 항목 | ✓ tier/caveats | ✓ Δ<0.005 |
| A5 | 74s | ✓ | ✓ | ✓ Δ<0.005 |
| B7 | 104s | ✓ | ✓ | ✓ Δ<0.005 |
| **B1** | **107s** | ✓ | ✓ | **✗ Δ 0.3~0.6** ⚠ |

**A1/A5/B7 일치율 18/18 cells (max Δ 0.005)**. B1만 1개 sample 차이.

B1 추가 진단:
- direct call (run_indicators_v2 동일 path): 캐시와 33 indicator 모두 0% 차이
- pipeline 통과 시: scores 차이 0.3~0.6
- 원인: pipeline 내부 처리 어딘가 비결정 인터랙션 발생. 추적 follow-up.
- **5/14 학원 실험 시작 전 추적 권장**.

## /analyze-chunk

```
chunk 5s wav 통과 단위 테스트
  ✓ analyze 성공 (2.5s)
  score_mapper_version: v2
  scores_v2 keys: ['3_vocal_fold_contact', '4_breathiness',
                   '6_soft_palate', '8_tongue_tension']
  scores_meta keys: 4 (동일)
  reliability.shown_v2 ✓
```

→ 5s chunk는 latency 2.5s. v2 통합 OK. Phase 4 사후 측정 사용 가능.

## /ws/realtime

```
호흡 chunk 5s 주기 → pipeline.analyze() 호출 path 동일
v2 통합 후 호흡 chunk endpoint도 v2 결과 자동 반영
단 latency 증가: 기존 ~5s → ~70-100s (33 indicator 산출)
```

⚠ **5s chunk 주기로는 latency 너무 큼** (chunk 분석 1회당 70s+).
→ /ws/realtime은 v2 호흡 chunk 분석 **비권장**.
→ 호환성은 유지 (응답 schema 일관), 단 실시간 사용 부적합.
→ /ws/realtime의 호흡 chunk는 v1 cpp_mean indicator 기반 score 유지 (analysis_pipeline에서 자연스럽게 fallback).

## /predict

- EGG wav 산출만, score_mapper와 무관 → 영향 없음 ✓

## /health

- 영향 없음 ✓

## 종합

| endpoint | 호환성 | latency | v2 통합 권장 |
|---|---|---|---|
| /analyze | ✓ (B1 1 case 추적) | +60~90s | **권장** |
| /analyze-chunk | ✓ | +60~90s (long chunk), 2~5s (short) | **권장** |
| /ws/realtime | ✓ schema, ✗ latency | +70-100s/chunk | **비권장** (latency 부담) |
| /predict | ✓ | 영향 없음 | n/a |
| /health | ✓ | 영향 없음 | n/a |

## Follow-up 작업

1. **B1 sample 차이 원인 추적** (분석 path 디버그). 5/14 학원 실험 전.
2. /ws/realtime의 호흡 chunk endpoint에 v2 vs v1 선택 옵션 추가 검토.
3. 21명 전체 pipeline 재검증 (현재 4 sample만). 별도 backlog.
