# Vocal Server API 문서

앱 개발자용 통합 가이드. Base URL: `http://<서버IP>:8000`

---

## 인증 방식

모든 인증 필요 API는 HTTP 헤더에 Bearer 토큰을 포함합니다.

```
Authorization: Bearer <token>
```

토큰은 `POST /auth/login` 응답의 `token` 필드에서 획득합니다.  
만료 시간: 없음 (현재 정책). 재발급은 재로그인으로 처리.

---

## 인증 흐름

```
1. POST /auth/signup  → 계정 생성
2. POST /auth/login   → token 획득
3. 이후 모든 API: Authorization: Bearer <token>
```

---

## 엔드포인트 목록

| Method | Path | 인증 | 설명 |
|--------|------|------|------|
| POST | `/auth/signup` | 불필요 | 회원가입 |
| POST | `/auth/login` | 불필요 | 로그인 |
| POST | `/sessions` | 필요 | 세션 생성 |
| GET | `/sessions` | 필요 | 내 세션 목록 |
| GET | `/sessions/{session_id}` | 필요 | 세션 상세 (분석 결과 포함) |
| POST | `/sessions/{session_id}/files` | 필요 | 오디오 파일 업로드 |
| POST | `/sessions/{session_id}/analyze` | 필요 | 분석 요청 |
| GET | `/analysis/{run_id}` | 필요 | 분석 실행 상태 조회 |
| GET | `/analysis/{run_id}/results` | 필요 | 분석 결과 조회 |
| POST | `/sessions/{session_id}/compare-pitch` | 필요 | 피치 비교 |
| GET | `/songs` | 불필요 | 등록 곡 목록 |
| GET | `/songs/{song_id}` | 불필요 | 곡 상세 |
| GET | `/songs/{song_id}/pitch` | 불필요 | 곡 피치 데이터 |
| GET | `/songs/{song_id}/lyrics` | 불필요 | 곡 가사 |
| GET | `/songs/{song_id}/audio` | 불필요 | 곡 오디오 스트리밍 |
| POST | `/songs/register` | 필요 | 곡 등록 (관리자용) |

---

## 상세 엔드포인트

### POST /auth/signup

회원가입.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "홍길동"
}
```

**Response 201**
```json
{
  "user_id": "183192a1-209b-40f3-baa0-f3bcf7b50616",
  "email": "user@example.com",
  "nickname": "홍길동",
  "token": "<JWT 토큰>"
}
```

**에러**
| 코드 | 사유 |
|------|------|
| 422 | 필드 누락 또는 형식 오류 |
| 400 | 이미 등록된 이메일 |

---

### POST /auth/login

로그인 후 토큰 획득.

**Request Body**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response 200**
```json
{
  "user_id": "183192a1-209b-40f3-baa0-f3bcf7b50616",
  "email": "user@example.com",
  "nickname": "홍길동",
  "token": "<JWT 토큰>"
}
```

**에러**
| 코드 | 사유 |
|------|------|
| 401 | 이메일 또는 비밀번호 불일치 |

---

### POST /sessions

분석 세션 생성. 파일 업로드 전에 먼저 호출.

**Request Body**
```json
{
  "song_title": "테스트곡"  // optional
}
```

**Response 201**
```json
{
  "session_id": "395ffee2-96a8-46ca-9e79-805d3fcc1f01",
  "status": "uploading",
  "created_at": "2026-04-30T10:00:00+09:00"
}
```

---

### GET /sessions

내 세션 목록 (최신순). `result_json` 미포함 — 상세는 `GET /sessions/{id}` 사용.

**Response 200**
```json
[
  {
    "session_id": "7cd855b1-3fd3-4b5b-9fc8-d15846fcb712",
    "song_title": null,
    "status": "success",
    "analysis_status": "completed",
    "started_at": null,
    "created_at": "2026-04-29T16:45:27.193640+09:00"
  }
]
```

**`analysis_status` 값**
| 값 | 의미 |
|----|------|
| `no_analysis` | 분석 요청 없음 |
| `queued` | 분석 대기 중 |
| `running` | 분석 진행 중 |
| `completed` | 분석 완료 |
| `failed` | 분석 실패 |

---

### GET /sessions/{session_id}

세션 상세 + 가장 최근 분석 결과 포함.

**Response 200**
```json
{
  "session_id": "7cd855b1-3fd3-4b5b-9fc8-d15846fcb712",
  "user_id": "183192a1-209b-40f3-baa0-f3bcf7b50616",
  "song_title": null,
  "status": "success",
  "started_at": null,
  "ended_at": null,
  "created_at": "2026-04-29T16:45:27.193640+09:00",
  "files": [
    {
      "file_id": "2d70c420-...",
      "file_type": "audio",
      "storage_uri": "/Users/.../app/storage/users/{user_id}/sessions/{session_id}/vocals.wav",
      "format": "wav",
      "sample_rate_hz": 16000,
      "duration_ms": 266040,
      "file_size_bytes": 8514124,
      "uploaded_at": "2026-04-29T16:45:30+09:00"
    }
  ],
  "latest_analysis": {
    "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
    "status": "success",
    "requested_at": "2026-04-29T16:45:35+09:00",
    "finished_at": "2026-04-29T16:45:56+09:00",
    "metrics": [
      {"key": "voiced_ratio", "value": 0.566, "unit": "ratio"},
      {"key": "processing_time_ms", "value": 19710.4, "unit": "ms"},
      {"key": "duration_sec", "value": 266.04, "unit": "sec"}
    ],
    "result_json": { /* → result_json 구조 상세 섹션 참고 */ }
  }
}
```

`latest_analysis`는 분석이 없으면 `null`.

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### POST /sessions/{session_id}/files

오디오 파일 업로드. `multipart/form-data`.

**Request**
- Content-Type: `multipart/form-data`
- Field: `file` (WAV / MP3 / M4A)
- Query param: `file_type=audio` (기본값)

```bash
curl -X POST http://host:8000/sessions/{session_id}/files \
  -H "Authorization: Bearer <token>" \
  -F "file=@recording.wav"
```

**Response 201**
```json
{
  "file_id": "09eedf93-fac4-40df-8280-d92ab4c3527a",
  "file_type": "audio",
  "storage_uri": "/...storage/users/{user_id}/sessions/{session_id}/recording.wav",
  "duration_ms": 266040
}
```

세션 `status`가 `uploading` → `uploaded`로 자동 변경됨.

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### POST /sessions/{session_id}/analyze

AI 분석 요청. **동기 처리** — 응답까지 10~30초 소요.  
세션 `status`가 `uploaded` 상태여야 합니다.

**Response 201**
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "status": "success"
}
```

분석 실패 시에도 201 반환, `status: "failed"`.

**에러**
| 코드 | 사유 |
|------|------|
| 400 | 세션 상태가 `uploaded`가 아님 (이미 분석됐거나 파일 미업로드) |
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### GET /analysis/{run_id}

분석 실행 상태 조회. 폴링 시 사용.

**Response 200**
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "session_id": "7cd855b1-...",
  "model_name": "vocal-analysis",
  "model_version": "0.1.0",
  "status": "success",
  "requested_at": "2026-04-29T16:45:35+09:00",
  "finished_at": "2026-04-29T16:45:56+09:00"
}
```

**`status` 값**: `queued` → `running` → `success` / `failed`

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 run_id |

---

### GET /analysis/{run_id}/results

분석 결과 전체 조회. `result_json`에 scores, feedback, indicators 포함.

**Response 200**
```json
{
  "run_id": "f199f109-...",
  "session_id": "7cd855b1-...",
  "user_id": "183192a1-...",
  "metrics": [
    {"key": "voiced_ratio", "value": 0.566, "unit": "ratio"},
    {"key": "processing_time_ms", "value": 19710.4, "unit": "ms"},
    {"key": "duration_sec", "value": 266.04, "unit": "sec"}
  ],
  "result_json": { /* → result_json 구조 상세 섹션 참고 */ }
}
```

---

## result_json 구조 상세

`GET /analysis/{run_id}/results` 또는 `GET /sessions/{id}`의 `latest_analysis.result_json` 필드.

```json
{
  "run_id": "f199f109-...",
  "status": "success",
  "processing_time_ms": 19710.4,

  "audio_info": {
    "duration_s": 266.04,
    "sample_rate": 16000,
    "voiced_ratio": 0.566,
    "voiced_duration_s": 150.58,
    "f0_min": 77.3,
    "f0_max": 597.7,
    "f0_mean": 219.8
  },

  "indicators": {
    "cq_mean": 0.462,
    "cq_peak": 0.527,
    "cpp_mean": 0.203,
    "hnr_mean": -4.572,
    "h1_h2_mean": 0.643,
    "a1_p0_mean": 0.745,
    "spectral_tilt_mean": -0.996,
    "spectral_centroid_mean": 1238.7,
    "nasal_ratio": null,
    "singers_formant_ratio_mean": 0.0065
  },

  "scores": {
    "1_nasal_oral_ratio":    {"ai_score": null,  "rounded_score": null, "zone": null,          "confidence": "medium"},
    "2_chest_head_voice":    {"ai_score": 1.83,  "rounded_score": 2,    "zone": "appropriate", "confidence": "medium"},
    "3_vocal_fold_contact":  {"ai_score": 0.0,   "rounded_score": 0,    "zone": "insufficient","confidence": "high"},
    "4_breathiness":         {"ai_score": 0.0,   "rounded_score": 0,    "zone": "insufficient","confidence": "high"},
    "5_forward_resonance":   {"ai_score": 0.0,   "rounded_score": 0,    "zone": "insufficient","confidence": "medium"},
    "6_soft_palate":         {"ai_score": null,  "rounded_score": null, "zone": null,          "confidence": "medium"},
    "7_larynx_tongue_root":  {"ai_score": null,  "rounded_score": null, "zone": null,          "confidence": "unavailable"},
    "8_tongue_tension":      {"ai_score": null,  "rounded_score": null, "zone": null,          "confidence": "unavailable"},
    "9_pressure_balance":    {"ai_score": 1.91,  "rounded_score": 2,    "zone": "appropriate", "confidence": "medium"}
  },

  "feedback": {
    "4_breathiness": {
      "name_ko": "호흡 소리 식별",
      "ai_score": 0.0,
      "zone": "insufficient",
      "zone_label": "미달",
      "score_description": "호흡 소리가 매우 강하게 들리며 발성보다 숨소리가 두드러짐",
      "feedback_text": "성대 접촉을 좀 더 확보하세요. 기식음이 과도하면 소리가 흐려지므로...",
      "ai_indicator": {
        "name": "hnr",
        "value": 0.2031
      }
    }
    // 나머지 8개 동일 구조
  },

  "reliability": {
    "high_reliability":   ["3_vocal_fold_contact", "4_breathiness"],
    "medium_reliability": ["1_nasal_oral_ratio", "2_chest_head_voice", "5_forward_resonance", "6_soft_palate", "9_pressure_balance"],
    "unavailable":        ["7_larynx_tongue_root", "8_tongue_tension"]
  }
}
```

### scores.zone 값

| 값 | 의미 |
|----|------|
| `"appropriate"` | 적절 |
| `"insufficient"` | 부족 |
| `"excessive"` | 과도 |
| `null` | 신뢰도 부족으로 평가 불가 |

### scores.confidence 값

| 값 | 의미 |
|----|------|
| `"high"` | 높은 신뢰도 — UI에 강조 표시 권장 |
| `"medium"` | 중간 신뢰도 |
| `"unavailable"` | 평가 불가 — `ai_score: null`, UI에 "측정 불가" 표시 권장 |

### 분석 항목 9개

| 키 | 한국어 이름 |
|----|------------|
| `1_nasal_oral_ratio` | 비강, 구강 공명의 비율 |
| `2_chest_head_voice` | 흉성, 두성의 비율 |
| `3_vocal_fold_contact` | 성대 접촉률 |
| `4_breathiness` | 호흡 소리 식별 |
| `5_forward_resonance` | 전방 공명 |
| `6_soft_palate` | 연구개 상태 |
| `7_larynx_tongue_root` | 후두, 설근 긴장 |
| `8_tongue_tension` | 혀 긴장 |
| `9_pressure_balance` | 호흡압 균형 |

---

## 분석 요청 후 폴링 패턴

현재 분석은 동기 처리(10~30초)이므로 `POST /analyze` 응답까지 기다리면 됩니다.  
타임아웃 설정: **최소 60초** 권장.

비동기 처리로 전환 시를 대비한 폴링 패턴:

```python
import time, httpx

run_id = "..."
headers = {"Authorization": "Bearer <token>"}

for _ in range(30):  # 최대 150초 대기
    r = httpx.get(f"http://host:8000/analysis/{run_id}", headers=headers)
    status = r.json()["status"]
    if status in ("success", "completed", "failed"):
        break
    time.sleep(5)

# 결과 조회
results = httpx.get(f"http://host:8000/analysis/{run_id}/results", headers=headers).json()
result_json = results["result_json"]
```

---

## 권한 모델

- 모든 세션, 파일, 분석 결과는 **생성한 사용자만 접근** 가능
- 타인의 리소스 접근 시 `403 Forbidden` 반환
- `GET /songs/*` 및 인증 없이 접근 가능한 곡 관련 API 제외

**공통 에러 코드**

| 코드 | 사유 |
|------|------|
| 401 | 토큰 없음 또는 유효하지 않은 토큰 |
| 403 | 다른 사용자의 리소스 접근 |
| 404 | 존재하지 않는 리소스 |
| 422 | 요청 바디 유효성 검사 실패 |

---

## Swagger UI

서버 실행 후 `http://localhost:8000/docs` 에서 직접 테스트 가능.
