# EGG Prediction & Vocal Analysis Server — API Reference

**Base URL:** `http://114.71.220.144:8001`  
**Version:** 2.0.0  
**Auth:** None (Phase L+1에서 추가 예정)

---

## Endpoints

### GET /health

서버 상태 및 모델 로드 여부 확인.

**Response**
```json
{
  "status": "ok",
  "model_loaded": true,
  "gpu_available": true,
  "device": "cuda"
}
```

---

### POST /predict

WAV 파일 → EGG 추정 신호 WAV 반환 (기존 엔드포인트, 하위 호환 유지).

**Request**
```
Content-Type: multipart/form-data
- file: WAV 파일 (필수)
- run_id: string (query, 선택)
```

**curl 예시**
```bash
curl -X POST http://114.71.220.144:8001/predict \
  -F "file=@audio.wav" \
  --output egg_estimated.wav
```

**Response**
```json
{
  "run_id": "abc123",
  "status": "success",
  "egg_signal_uri": "outputs/abc123/egg_estimated.wav",
  "duration_ms": 10240.0,
  "processing_time_ms": 854.3
}
```

---

### POST /analyze ⭐ New

WAV 파일 → 9개 발성 항목 종합 분석 JSON 반환.

**Request**
```
Content-Type: multipart/form-data
- file: WAV 파일 (필수, 단일 마이크 입력)
- run_id: string (query, 선택)
```

**curl 예시**
```bash
curl -X POST http://114.71.220.144:8001/analyze \
  -F "file=@recording.wav" \
  | python3 -m json.tool
```

**Response (status 200)**
```json
{
  "run_id": "abc123",
  "status": "success",
  "processing_time_ms": 3241.5,
  "audio_info": {
    "duration_s": 102.7,
    "sample_rate": 16000,
    "voiced_ratio": 0.7891,
    "voiced_duration_s": 81.1,
    "f0_min": 89.3,
    "f0_max": 412.1,
    "f0_mean": 245.6
  },
  "register_boundaries": {
    "low_max": 189.4,
    "mid_max": 297.8
  },
  "registers": {
    "low": {
      "n_frames": 1847,
      "cq_mean": 0.452,
      "cq_peak": 0.521,
      "cpp": 0.381,
      "hnr": 12.4,
      "spectral_centroid": 1023.7,
      "spectral_tilt": -0.891,
      "h1_h2": 3.21,
      "singers_formant_ratio": 0.028,
      "a1_p0": 8.14
    },
    "mid": { "..." : "..." },
    "high": { "..." : "..." }
  },
  "indicators": {
    "cq_mean": 0.461,
    "cq_peak": 0.534,
    "cpp_mean": 0.394,
    "hnr_mean": 11.8,
    "spectral_centroid_mean": 1187.3,
    "spectral_tilt_mean": -0.923,
    "h1_h2_mean": 2.87,
    "singers_formant_ratio_mean": 0.031,
    "a1_p0_mean": 7.42,
    "nasal_ratio": null
  },
  "scores": {
    "1_nasal_oral_ratio": {
      "ai_score": null,
      "rounded_score": null,
      "zone": null,
      "confidence": "medium"
    },
    "3_vocal_fold_contact": {
      "ai_score": 2.85,
      "rounded_score": 3,
      "zone": "appropriate",
      "confidence": "high"
    },
    "4_breathiness": {
      "ai_score": 2.71,
      "rounded_score": 3,
      "zone": "appropriate",
      "confidence": "high"
    }
  },
  "feedback": {
    "3_vocal_fold_contact": {
      "name_ko": "성대 접촉 강도",
      "ai_score": 2.85,
      "score_description": "안정적인 접촉으로 명료하고 힘 있는 발성이 형성됨",
      "feedback_text": "성대 접촉 강도가 적절합니다. 현재 발성을 유지하세요.",
      "zone": "appropriate",
      "zone_label": "적절",
      "ai_indicator": { "name": "cq_peak", "value": 0.534 }
    },
    "4_breathiness": {
      "name_ko": "호흡 소리 식별",
      "ai_score": 2.71,
      "score_description": "필요한 정도의 호흡이 섞여 자연스러운 질감 형성",
      "feedback_text": "호흡과 발성의 균형이 적절합니다. 현재 질감을 유지하세요.",
      "zone": "appropriate",
      "zone_label": "적절",
      "ai_indicator": { "name": "cpp", "value": 0.394 }
    }
  },
  "reliability": {
    "high_reliability": ["3_vocal_fold_contact", "4_breathiness"],
    "medium_reliability": [
      "1_nasal_oral_ratio", "2_chest_head_voice",
      "5_forward_resonance", "6_soft_palate", "9_pressure_balance"
    ],
    "unavailable": ["7_larynx_tongue_root", "8_tongue_tension"]
  }
}
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| 400 | 잘못된 파일 포맷 또는 파일 너무 작음 |
| 422 | 음성 유효 구간 < 5초 |
| 503 | 분석 모듈 미로드 |
| 500 | 내부 처리 오류 |

```json
{ "detail": "Voiced audio too short: 2.1s < 5.0s required" }
```

---

## Response Fields 상세

### scores[항목키]
| 필드 | 설명 |
|------|------|
| `ai_score` | AI 산출 점수 (0.0~5.0), null = 측정 불가 |
| `rounded_score` | 반올림 정수 점수 (0~5) |
| `zone` | `insufficient` \| `appropriate` \| `excessive` \| null |
| `confidence` | `high` \| `medium` \| `unavailable` |

### feedback[항목키]
| 필드 | 설명 |
|------|------|
| `name_ko` | 항목명 (한국어) |
| `score_description` | 평가 기준표 v3 해당 점수의 발성 기준 텍스트 |
| `feedback_text` | zone별 개선 피드백 텍스트 |
| `ai_indicator.name` | 사용된 AI 지표명 (cq_peak, cpp 등) |
| `ai_indicator.value` | AI 지표 원시값 |

### 항목키 목록
| 키 | 항목명 | AI 지표 | 신뢰도 |
|----|--------|---------|--------|
| `1_nasal_oral_ratio` | 비강/구강 공명 비율 | nasal_ratio (단일 마이크 불가) | medium |
| `2_chest_head_voice` | 흉성/두성 경향 | cq_mean | medium |
| `3_vocal_fold_contact` | 성대 접촉 강도 | cq_peak | **high** |
| `4_breathiness` | 호흡 소리 식별 | cpp | **high** |
| `5_forward_resonance` | 전방 공명 정도 | spectral_centroid | medium |
| `6_soft_palate` | 연구개 위치 | nasal_ratio (단일 마이크 불가) | medium |
| `7_larynx_tongue_root` | 후두/혀뿌리 위치 | 없음 | unavailable |
| `8_tongue_tension` | 혀/구강 경직도 | 없음 | unavailable |
| `9_pressure_balance` | 상압/하압 비율 | spectral_tilt | medium |

---

## 인터랙티브 API 문서

서버 실행 후 브라우저에서:
- **Swagger UI**: http://114.71.220.144:8001/docs
- **ReDoc**: http://114.71.220.144:8001/redoc

---

## 서버 실행

```bash
cd ~/projects/egg_prediction/model_server
conda activate EGGDML
uvicorn server:app --host 0.0.0.0 --port 8001
```
