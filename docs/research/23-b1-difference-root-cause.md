<!-- provenance -->
> **원본**: `data/vocal_academy/results/sidetrack/b1_difference_root_cause.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: B1 sample 비결정성 추적 (미해결)
> **원본 수정일**: 2026-05-11 · **크기**: 3,076 bytes · **sha256[:8]**: `3f8ae47f`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# F1: B1 sample 차이 원인 추적 결과 (2026-05-11)

## 배경

D3-6a 검증에서 4 sample 중 B1만 pipeline 통과 시 캐시(`score_mapper_v2_predictions_21.csv`)와 큰 차이 (Δ 0.3~0.6) 발생.

## 추적 결과

### F1-1: Path 비교 (B1 + A1 + A9 PCM 비교 sample)

| sample | format | Path 1 (direct) vs Path 3 (pipeline raw load) |
|---|---|---|
| B1 | PCM_24 | **max Δ = 0.0** (완전 일치) |
| A1 | PCM_24 | **max Δ = 0.0** (완전 일치) |
| A9 | PCM_16 | **max Δ = 0.0** (완전 일치) |

→ pipeline의 `_io.BytesIO(audio_data)` + `librosa.resample` path = `run_indicators_v2.py`의 직접 wav read path와 **완전 동일**. PCM bit depth 영향 없음.

### F1-2: B1 단독 호출 (3회 반복)

| Trial | 접촉강도 | 호흡식별 | 연구개위치 | 혀경직도 | 비강사용 | 전방공명 | 모두 Δ |
|---|---|---|---|---|---|---|---|
| 1 | 3.060 | 3.570 | 1.700 | 3.350 | 1.410 | 2.330 | ≤ 0.002 |
| 2 | 3.060 | 3.570 | 1.700 | 3.350 | 1.410 | 2.330 | ≤ 0.002 |
| 3 | 3.060 | 3.570 | 1.700 | 3.350 | 1.410 | 2.330 | ≤ 0.002 |
| 캐시 | 3.059 | 3.572 | 1.699 | 3.352 | 1.410 | 2.328 | - |

→ **B1 단독 호출 3회 모두 캐시와 완전 일치**. Reproducibility 확보.

### F1-3: Sequential 호출 재현 시도

```
A1 → A5 → B1 (D3-6a 재현)
  A1 접촉=2.61  ✓ (캐시 2.606)
  A5 접촉=2.50  ✓ (캐시 2.497)
  B1 접촉=3.06  ✓ (캐시 3.059)   ← D3-6a에서 2.66 (Δ=0.399)였으나 지금은 정확
```

→ Sequential 호출에서도 B1 결과 **정확** (Δ < 0.005).

## 결론

**D3-6a 시점의 B1 차이는 reproducible하지 않음** — 일시적 state 오류 또는 코드 갱신 사이의 transient 상태로 추정.

가능한 원인 (확정 불가, 발생 후 복구된 상태):
1. D3-1 (`mapping_params_v2.json` 갱신) 직후 score_mapper_v2 instance가 stale cache 들고 있었을 가능성
2. score_mapper_v2.py 수정 후 module reload 누락 (Python interpreter session 동안)
3. 일시적 비결정 인터랙션 (parselmouth/numpy state)

현재 상태 (2026-05-11 21:10 기준):
- 모든 갱신 완료 + interpreter restart 후 재테스트
- B1 단독 호출 ✓, Sequential 호출 ✓
- **5/14 학원 실험 사용 OK**

## Follow-up 결정

수정 불필요. 단:
- **F2 (21명 전체) sequential 검증 결과 fail sample 추적** → 만약 추가 fail 발견 시 재진단
- 학원 실험 기간 (5/14~5/24) 동안 monitoring 권장 — sample별 점수가 캐시와 일관 유지되는지 주기 확인
- score_mapper_v2 호출 시 매번 fresh instance 생성 권장 (long-running process에서 cache stale 위험)

## 산출물

- `results/sidetrack/d3_endpoint_validation_full.csv` (F2 21명 전체) — 별도 산출
- 본 보고서 (`b1_difference_root_cause.md`)

## 영향 받는 wav 케이스

- **PCM 차이 영향 없음** (B1=PCM_24, A9=PCM_16 모두 정상)
- **sample rate 차이 영향 없음** (모두 48000Hz)
- **channel 차이 영향 없음** (모두 mono)

→ wav 자체 속성에 의한 차이가 아닌, pipeline state 일시적 오류로 결론.
