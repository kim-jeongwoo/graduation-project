<!-- provenance -->
> **원본**: `.claude/refs/dataset.md` (dmlserver 로컬, `.gitignore` 로 커밋 제외되던 파일)
> **설명**: 데이터셋 레퍼런스
> **원본 수정일**: 2026-04-17 · **크기**: 1,996 bytes · **sha256[:8]**: `2f30469f`
> 이 사본은 내용 수정 없이 그대로 옮긴 것이다. 갱신은 원본을 고친 뒤 `python docs/build_docs.py` 재실행.

---

# 데이터셋 & 전처리

## SVD (Saarbrücken Voice Database)

- 687명 건강 화자, MIC+EGG 동시 녹음
- 원본 포맷: **50kHz, 16-bit** (IFF FORM/DS16, `.nsp`/`.egg`)
- 총 파일 쌍: 9,565개
- 위치: `data/SVD_healthy/{speaker_id}/vowels/`, `.../sentences/`
- 파일명 패턴: `X-Y_h.nsp` + `X-Y_h-egg.egg`

## 전처리 파이프라인 (ai-model 학습 기준)

```
NSP/EGG (50kHz, int16)
  → float32 / 32768.0          [int16 → float32 [-1,1]]
  → librosa.resample(50k→16k)  [soxr_hq, 기본 res_type]
  → z-score per-file           [(x - mean) / std, threshold 1e-8]
  → sliding window 분할        [window=16384, hop=8192]
```

없는 것: pre-emphasis, DC offset 제거(z-score mean이 처리), 밴드패스 필터

## ⚠️ 학습 vs 서버 전처리 불일치

| 단계 | ai-model (학습) | model_server (추론) |
|------|----------------|---------------------|
| 리샘플링 | `librosa.resample` (soxr_hq) | `scipy.signal.resample` (FFT) |
| 정규화 | z-score per-file | z-score (동일) |
| 입력 로딩 | `read_nsp()` (커스텀 파서) | `sf.read(dtype='float32')` |

실질적 차이는 미미하나, 추후 통일 시 model_server를 librosa로 맞출 것.

## 화자 독립 분할 (seed=42, 변경 금지)

| Split | 화자 수 | 파일 수 |
|-------|---------|---------|
| Train | 549 | 7,645 |
| Val | 68 | 946 |
| Test | 70 | 974 |

코드 위치: `ai-model/utils/dataset.py` → `speaker_split()`, `SVDEggDataset`

## 보컬 학원 데이터 (2026-04 추가)

- 위치: `data/vocal_academy/singer_01/` ~ `singer_12/`
- 포맷: 48kHz/24bit/mono WAV
- 파일명: `{singer}-{song}_{oral|nasal|phone}.wav`
- Singer 1, 4: phone 없음 (oral+nasal만)
- Singer 6 Song 8: 사실상 무음 (불량)
- 분석 결과: `data/vocal_academy/results/`

## 48kHz 호환성 (검증 완료 2026-04-05)

- 50k→16k vs 48k→16k 리샘플링 경로: Corr=1.0, 차이 없음
- 모델 추론: NaN/Inf 없음, max|x|=2.38
- 결과: `results/compatibility_test/`
