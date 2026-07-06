# Vocal Server API 문서

앱 개발자용 통합 가이드.

---

## 1. 서버 기본 정보

| 항목 | 값 |
|------|-----|
| 로컬 개발 Base URL | `http://localhost:8000` |
| 외부 접근 Base URL | `https://api.vocal-fit.com` (학원 실험 + 시연용, 5/10~) |
| HTTPS | 자동 (Cloudflare 인증서) |
| 인프라 | Cloudflare Tunnel → Mac Studio `localhost:8000` |
| 응답 형식 | JSON (UTF-8) |
| 인증 방식 | Bearer JWT (`Authorization` 헤더) |
| Swagger UI | `http://localhost:8000/docs` |

---

## 2. 인증 방식

모든 인증 필요 API는 요청 헤더에 Bearer 토큰을 포함합니다.

```http
Authorization: Bearer <token>
```

토큰은 `POST /auth/login` 또는 `POST /auth/signup` 응답의 `token` 필드에서 획득합니다.  
만료 시간: 발급 후 **7일** (서버 환경변수 `JWT_EXPIRE_DAYS`로 조절). 만료 시 재로그인 필요.

---

## 3. 엔드포인트 목록

| Method | Path | 인증 | 설명 |
|--------|------|------|------|
| POST | `/auth/signup` | 불필요 | 회원가입 |
| POST | `/auth/login` | 불필요 | 로그인 |
| POST | `/sessions` | 필요 | 세션 생성 |
| GET | `/sessions` | 필요 | 내 세션 목록 |
| GET | `/sessions/{session_id}` | 필요 | 세션 상세 + 최근 분석 결과 |
| POST | `/sessions/{session_id}/files` | 필요 | 오디오 파일 업로드 |
| POST | `/sessions/{session_id}/training-analyze` | 필요 | 훈련 청크 사후 측정 (휘발 응답, 누적 시도 자동 저장) |
| GET | `/users/me/training-attempts` | 필요 | 누적 시도 기록 조회 (cursor pagination) |
| GET | `/users/me/favorites` | 필요 | 즐겨찾기 목록 |
| POST | `/users/me/favorites` | 필요 | 즐겨찾기 추가 |
| DELETE | `/users/me/favorites/{favorite_id}` | 필요 | 즐겨찾기 삭제 |
| POST | `/sessions/{session_id}/analyze` | 필요 | AI 분석 요청 |
| GET | `/analysis/{run_id}` | 필요 | 분석 실행 상태 조회 |
| GET | `/analysis/{run_id}/results` | 필요 | 분석 결과 전체 조회 |
| GET | `/analysis/{run_id}/comparison` | 필요 | 숙련자 기준 비교 |
| GET | `/songs` | 필요 | 노래방 곡 목록 |
| GET | `/songs/{song_id}/lrc` | 필요 | 곡 가사 (동기화 LRC) |
| GET | `/songs/{song_id}/pitch-guide` | 필요 | 곡 음정 가이드 |
| GET | `/songs/{song_id}/mr` | 필요 | MR 음원 스트리밍 |

> **노래방 API 권한 주의**: `/songs/*`는 인증(Bearer 토큰)이 필요하지만 user_id 검증은 없습니다 — 로그인된 사용자 누구나 접근 가능합니다.

---

## 4. 인증

### POST /auth/signup

회원가입. 성공 시 즉시 토큰을 반환합니다.

```http
POST /auth/signup
Content-Type: application/json
```

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
| 400 | 이미 등록된 이메일 |
| 403 | 회원가입 비활성화됨 (서버 환경변수 `SIGNUP_ENABLED=false`) — 학원 실험/시연 기간 외부인 가입 차단용 |
| 422 | 필드 누락 또는 형식 오류 |

> **회원가입 토글**: 환경변수 `SIGNUP_ENABLED=false`로 설정 시 모든 신규 가입이 차단되며 403 + `"현재 회원가입이 비활성화되어 있습니다. 관리자에게 문의하세요."` 응답이 반환됩니다. 로그인(`POST /auth/login`)은 영향 없음.

---

### POST /auth/login

로그인 후 토큰 획득.

```http
POST /auth/login
Content-Type: application/json
```

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

## 5. 세션

### POST /sessions

분석 세션 생성. 파일 업로드 전에 먼저 호출합니다.

```http
POST /sessions
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body** (모든 필드 optional)
```json
{
  "song_id": "004",
  "song_title": "테스트곡"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `song_id` | `string` (3자리 숫자, optional) | 노래방 14곡 중 선택. `"001"`~`"014"` 형식 |
| `song_title` | `string` (optional) | 자유 입력 곡 이름. `song_id`가 있으면 무시됨 |

- `song_id`와 `song_title` 둘 다 없어도 됩니다.
- 존재하지 않는 `song_id` 전달 시 400 반환.

**Response 201**
```json
{
  "session_id": "395ffee2-96a8-46ca-9e79-805d3fcc1f01",
  "status": "uploading",
  "created_at": "2026-04-30T10:00:00+09:00"
}
```

**에러**
| 코드 | 사유 |
|------|------|
| 400 | 존재하지 않는 `song_id` |

---

### GET /sessions

내 세션 목록 (최신순). `result_json` 미포함 — 상세는 `GET /sessions/{id}` 사용.

```http
GET /sessions
Authorization: Bearer <token>
```

**Response 200**
```json
[
  {
    "session_id": "7cd855b1-3fd3-4b5b-9fc8-d15846fcb712",
    "song_title": null,
    "status": "success",
    "analysis_status": "completed",
    "started_at": null,
    "created_at": "2026-04-29T16:45:27.193640+09:00",
    "song": {
      "id": "004",
      "artist": "김범수",
      "title": "보고싶다"
    }
  }
]
```

**`song` 필드 3가지 케이스**

| 케이스 | `song` 값 | 설명 |
|--------|-----------|------|
| 노래방 14곡 선택 | `{"id": "004", "artist": "김범수", "title": "보고싶다"}` | `song_id`로 세션 생성 |
| 자유 입력 곡명 | `{"id": null, "artist": null, "title": "테스트곡"}` | `song_title`만으로 생성 |
| 곡 정보 없음 | `null` | `song_id`, `song_title` 모두 없이 생성 |

**`analysis_status` 값**
| 값 | 의미 |
|----|------|
| `"no_analysis"` | 분석 요청 없음 |
| `"queued"` | 분석 대기 중 |
| `"running"` | 분석 진행 중 |
| `"completed"` | 분석 완료 |
| `"failed"` | 분석 실패 |

---

### GET /sessions/{session_id}

세션 상세 + 가장 최근 분석 결과 포함.

```http
GET /sessions/{session_id}
Authorization: Bearer <token>
```

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
  "song": {
    "id": "004",
    "artist": "김범수",
    "title": "보고싶다"
  },
  "files": [
    {
      "file_id": "2d70c420-...",
      "file_type": "audio",
      "storage_uri": "/...storage/users/{user_id}/sessions/{session_id}/vocals.wav",
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
    "result_json": { }
  }
}
```

`latest_analysis`는 분석이 없으면 `null`. `result_json` 구조는 [10. 공통 응답 모델](#10-공통-응답-모델) 참고.

`song` 필드는 위 `GET /sessions` 섹션의 3가지 케이스와 동일합니다.

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

## 6. 파일 업로드

### POST /sessions/{session_id}/files

오디오 파일 업로드. `multipart/form-data`.

```http
POST /sessions/{session_id}/files
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request**
- Field: `file` — WAV / MP3 / M4A 파일
- Query param: `file_type=audio` (기본값, 생략 가능)

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

세션 `status`가 `uploading` → `uploaded`로 자동 변경됩니다.

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### POST /sessions/{session_id}/training-analyze

TrainingScreen 사후 측정용 청크 분석. **응답은 휘발성** — dml-server `/analyze-chunk` 결과를 그대로 전달합니다. 정식 분석 흐름(`/analyze`)과 별개.

> **자동 저장**: status가 `"success"`이고 `chunk_meta`에 `original_run_id`, `chunk_index`가 포함되면 백엔드가 `training_attempts` 테이블에 자동 INSERT (응답 스키마 영향 없음). 누적 기록은 `GET /users/me/training-attempts`로 조회.
>
> **Timeout 기준**: vocal-server는 dml-server `/analyze-chunk` 응답을 최대 25초 대기합니다. 25초 초과 또는 연결 실패 시 504를 반환하며, 서버 로그에는 `session_id`, elapsed, timeout, DML HTTP status/body status(가능한 경우)가 기록됩니다.

```http
POST /sessions/{session_id}/training-analyze
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request**
- Field: `audio` — WAV 파일 (필수)
- Field: `chunk_meta` — JSON 문자열 (선택). 클라이언트가 echo 받고 싶은 메타. 예: `{"chunk_index": 5, "start_sec": 24.0, "end_sec": 31.0, "original_run_id": "..."}`

```bash
curl -X POST http://host:8000/sessions/{session_id}/training-analyze \
  -H "Authorization: Bearer <token>" \
  -F "audio=@chunk.wav" \
  -F 'chunk_meta={"chunk_index":5,"start_sec":24.0,"end_sec":31.0}'
```

**응답 패턴 (2026-05-12 변경)**: dml-server `/analyze-chunk` 응답을 **통째 통과** + `session_id`, `chunk_meta` 추가 + `run_id` 제외. dml-server schema에 신규 필드(v2 등) 추가 시 자동 통과됨.

**Response 200** (정상, v2 score_mapper)
```json
{
  "session_id": "7cd855b1-...",
  "status": "success",
  "scores": {
    "3_vocal_fold_contact": {"ai_score": 3.4, "rounded_score": 3, "zone": "appropriate", "confidence": "high"},
    "4_breathiness":         {"ai_score": 2.8, "rounded_score": 3, "zone": "appropriate", "confidence": "high"}
  },
  "score_mapper_version": "v2",
  "scores_v2": {
    "3_vocal_fold_contact": { },
    "4_breathiness": { },
    "6_soft_palate": { },
    "8_tongue_tension": { }
  },
  "scores_meta": {
    "3_vocal_fold_contact": { },
    "4_breathiness": { },
    "6_soft_palate": { },
    "8_tongue_tension": { }
  },
  "low_confidence_items": [],
  "duration_sec": 8.0,
  "chunk_duration_s": 8.0,
  "indicators": { "cpp_mean": 0.21, "voiced_ratio": 0.78 },
  "processing_time_ms": 412.3,
  "chunk_meta": {"chunk_index": 5, "start_sec": 24.0, "end_sec": 31.0}
}
```

**Response 200** (무음/잡음)
```json
{
  "session_id": "7cd855b1-...",
  "status": "no_voice",
  "scores": null,
  "reason": "잡음만 녹음되었습니다. 마이크는 동작하지만 사람 목소리가 감지되지 않았습니다. 다시 녹음해주세요.",
  "duration_sec": 5.0,
  "indicators": null,
  "processing_time_ms": 66.6,
  "chunk_meta": {"chunk_index": 5}
}
```

`chunk_meta`는 클라이언트가 보낸 값을 그대로 echo. 보내지 않았으면 `null`.  
`run_id`는 의도적으로 제외 (dml-server 발급 휘발 ID — 정식 `AnalysisRun.run_id`와 혼동 방지).

**필드별 케이스**

| 필드 | success | no_voice | 비고 |
|------|---------|----------|------|
| `scores` (legacy) | dict (2개) | `null` | `3_vocal_fold_contact`, `4_breathiness` |
| `score_mapper_version` | `"v2"` | `null` 가능 | v2 mapper 식별자 |
| `scores_v2` | dict (4개) | `null` 가능 | `3/4/6/8` (mapper v2 결과) |
| `scores_meta` | dict (4개) | `null` 가능 | scores_v2 항목별 메타 |
| `low_confidence_items` | array | `null` 가능 | 저신뢰 항목 키 리스트 |
| `chunk_duration_s` | float | float | 청크 길이 (dml 별칭) |
| `reason` | `null` | string (한국어) | 앱에서 사용자에게 표시 권장 |
| `duration_sec` | float | float | 청크 길이 |
| `indicators` | dict | `null` | cpp_mean, voiced_ratio 등 |
| `processing_time_ms` | float | float | dml-server 처리 시간 |
| `chunk_meta` | echo | echo | 클라이언트가 보낸 값 그대로 |

> **주의**: `/analyze-chunk`에는 `academic_analysis_scores`, `reliability`, `timeline_scores`, `timeline_metadata`, `user_f0`, `feedback`, `registers`, `audio_info`, `register_boundaries` **없음**. 이 필드들은 `/analyze`(정식 분석)에만 있음. 두 endpoint 응답 구조 차이 — vocal-app은 호출하는 endpoint에 맞춰 분기 처리.

**Response 400** (chunk_too_short)
```json
{
  "detail": {
    "error": "chunk_too_short",
    "reason": "분석을 위해 최소 3초 이상 녹음이 필요합니다.",
    "duration_sec": 0.5,
    "min_required_sec": 3.0
  }
}
```

`detail`은 객체 형태. 앱에서 `error.detail.reason`으로 사용자 메시지 접근.

**에러**
| 코드 | 사유 |
|------|------|
| 400 | dml-server 검증 실패 (예: `chunk_too_short`) — detail 객체 그대로 전달 |
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |
| 502 | dml-server 5xx 또는 응답 파싱 실패 |
| 504 | dml-server 25초 timeout 또는 연결 실패 |

---

## 7. 분석

### POST /sessions/{session_id}/analyze

AI 분석 시작 요청. **비동기 start endpoint** — 요청을 접수하면 DML 분석 완료를 기다리지 않고 즉시 `run_id`와 `status: "queued"`를 반환합니다.
세션 `status`가 `uploaded` 상태여야 합니다.

> **Cloudflare 524 회피 방식**: vocal-server가 POST 응답에서 DML `/analyze` 완료를 기다리지 않습니다. 실제 DML 호출과 `AnalysisRun.status/result_json` 저장은 background task에서 진행되며, 앱은 `GET /analysis/{run_id}`로 polling합니다.
>
> **구분**: 정식 full analyze는 이 endpoint + polling 흐름을 사용합니다. `/sessions/{session_id}/training-analyze`는 TrainingScreen 사후 측정용이며 내부적으로 dml-server `/analyze-chunk`를 호출합니다. `/analyze-chunk` 흐름은 이번 전환과 무관하게 기존 동작을 유지합니다.

```http
POST /sessions/{session_id}/analyze
Authorization: Bearer <token>
```

**Response 201**
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "status": "queued"
}
```

이 응답은 **분석 완료 결과가 아니라 접수 결과**입니다. 앱은 POST 직후 결과 화면으로 이동하지 말고 `GET /analysis/{run_id}`를 polling해야 합니다.

**에러**
| 코드 | 사유 |
|------|------|
| 400 | 세션 상태가 `uploaded`가 아님 (파일 미업로드 또는 이미 분석됨) |
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### GET /analysis/{run_id}

분석 실행 상태 조회. 앱은 `queued`/`running` 동안 polling하고, terminal status가 되면 `GET /analysis/{run_id}/results`를 조회합니다.

```http
GET /analysis/{run_id}
Authorization: Bearer <token>
```

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

**`status` 값**

| 값 | 의미 |
|----|------|
| `"queued"` | 분석 대기 중 |
| `"running"` | 분석 진행 중 |
| `"success"` | 정상 분석 완료 |
| `"completed"` | 정상 분석 완료 (호환 상태) |
| `"failed"` | 분석 중 에러 발생 |
| `"invalid"` | dml-server가 유효하지 않은 입력/분석 불가 상태 반환 (dml enum 미등록 문자열이지만 그대로 저장됨) |
| `"no_voice"` | 무음/잡음 감지로 분석 스킵 (정상 흐름) |

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 run_id |

---

### GET /analysis/{run_id}/results

분석 결과 전체 조회. `result_json`에 scores, feedback, indicators 등 dml-server `/analyze` 응답 JSON 전체가 저장됩니다.

앱 권장 흐름:
1. `GET /analysis/{run_id}`가 `success` 또는 `completed`이면 결과 화면 진입 후 이 endpoint를 호출합니다.
2. `failed`, `invalid`, `no_voice`이면 결과 화면 대신 실패/재녹음/안내 UX를 표시하고, 필요하면 이 endpoint의 `result_json.status/reason/error`를 확인합니다.
3. `queued`/`running` 중에는 결과가 아직 없을 수 있으므로 이 endpoint를 최종 결과로 사용하지 않습니다. 현재 구현상 완료 전 호출도 200을 반환할 수 있지만 `metrics`가 비어 있고 `result_json`이 `null`일 수 있습니다.

```http
GET /analysis/{run_id}/results
Authorization: Bearer <token>
```

**Response 200**
```json
{
  "run_id": "f199f109-...",
  "session_id": "7cd855b1-...",
  "user_id": "183192a1-...",
  "metrics": [
    {"key": "voiced_ratio",       "value": 0.566,    "unit": "ratio"},
    {"key": "processing_time_ms", "value": 19710.4,  "unit": "ms"},
    {"key": "duration_sec",       "value": 266.04,   "unit": "sec"}
  ],
  "result_json": { }
}
```

`result_json` 구조는 [10. 공통 응답 모델](#10-공통-응답-모델) 참고.

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 run_id |

---

### GET /analysis/{run_id}/comparison

숙련자 기준 데이터와 비교. **현재 reference profile 미구축 상태** → `comparisons`가 빈 배열로 반환됩니다.

> **주의**: 이 endpoint는 `analysis_results` 테이블(구형 3개 metric: `voiced_ratio`, `processing_time_ms`, `duration_sec`)만 기준으로 비교를 계산합니다. `scores_v2`/`scores_meta`/`academic_analysis_scores` 등 v2 필드는 반영하지 않습니다.

```http
GET /analysis/{run_id}/comparison
Authorization: Bearer <token>
```

**Response 200** (reference profile 없을 때 — 현재 상태)
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "reference_name": null,
  "comparisons": []
}
```

**Response 200** (reference profile 구축 후)
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "reference_name": "숙련자 기준 v1",
  "comparisons": [
    {
      "key": "4_breathiness",
      "user_value": 0.203,
      "reference_mean": 0.512,
      "z_score": -2.14,
      "percentile": 1.62
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `reference_name` | `string \| null` | 기준 프로필 이름. 미구축 시 `null` |
| `comparisons` | `array` | 지표별 비교 결과. 미구축 시 빈 배열 `[]` |
| `comparisons[].key` | `string` | 지표 키 (예: `"4_breathiness"`) |
| `comparisons[].user_value` | `float` | 사용자 측정값 |
| `comparisons[].reference_mean` | `float` | 숙련자 평균값 |
| `comparisons[].z_score` | `float \| null` | 표준편차 기준 편차 |
| `comparisons[].percentile` | `float \| null` | 백분위 (0~100) |

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 run_id |

---

## 8. 노래방

> `song_id` 형식: 정확히 **3자리 숫자** (`"001"`~`"014"`). 형식 불일치 시 422 반환.

### GET /songs

노래방 14곡 메타 리스트.

```http
GET /songs
Authorization: Bearer <token>
```

**Response 200**
```json
[
  {
    "id": "004",
    "artist": "김범수",
    "title": "보고싶다",
    "master_duration_sec": 274.5,
    "mr_duration_sec": 274.5,
    "has_lrc": true,
    "has_pitch_guide": true
  },
  {
    "id": "001",
    "artist": "한로로",
    "title": "시간을 달리네",
    "master_duration_sec": 231.2,
    "mr_duration_sec": 231.2,
    "has_lrc": false,
    "has_pitch_guide": true
  }
]
```

| 필드 | 설명 |
|------|------|
| `has_lrc` | `true`이면 `/lrc` 호출 가능. `false`이면 404 반환 |
| `has_pitch_guide` | `true`이면 `/pitch-guide` 호출 가능. `false`이면 404 반환 |
| `master_duration_sec` | 원곡 길이(초). 없으면 `null` |
| `mr_duration_sec` | MR 길이(초). 없으면 `null` |

---

### GET /songs/{song_id}/lrc

해당 곡의 동기화 가사 데이터. `has_lrc: true`인 곡만 사용 가능.

```http
GET /songs/{song_id}/lrc
Authorization: Bearer <token>
```

**Response 200** — 배열 직접 반환
```json
[
  {"time_start": 12.45, "time_end": 15.80, "text": "그대가 떠나던 날"},
  {"time_start": 15.80, "time_end": 19.20, "text": "하늘도 알았는지"}
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `time_start` | `float` | 가사 시작 시각 (초, master 음원 기준) |
| `time_end` | `float` | 가사 종료 시각 (초, master 음원 기준) |
| `text` | `string` | 가사 텍스트 |

> **MR 재생 시 타임라인 변환**: `t_mr = t_master - lrc_offset_sec`  
> `lrc_offset_sec`은 향후 songs 메타 API에 포함 예정.

**에러**
| 코드 | 사유 |
|------|------|
| 404 | 존재하지 않는 곡 또는 LRC 미준비 (`has_lrc: false`) |
| 422 | song_id 형식 오류 (3자리 숫자가 아님) |

---

### GET /songs/{song_id}/pitch-guide

해당 곡의 가수 음정 곡선. `has_pitch_guide: true`인 곡만 사용 가능.

```http
GET /songs/{song_id}/pitch-guide
Authorization: Bearer <token>
```

**Response 200** — 객체 직접 반환
```json
{
  "song_id": "004",
  "lrc_offset_sec": 0.0,
  "points": [
    {
      "t": 12.45,
      "freq": 293.66,
      "midi": 62,
      "voiced": true,
      "conf": 0.92
    },
    {
      "t": 12.51,
      "freq": null,
      "midi": null,
      "voiced": false,
      "conf": 0.08
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `points[].t` | `float` | 시각 (초, master 음원 기준) |
| `points[].freq` | `float \| null` | 주파수 (Hz). `voiced: false`이면 `null` |
| `points[].midi` | `int \| null` | MIDI 노트 번호. `voiced: false`이면 `null` |
| `points[].voiced` | `bool` | 유성음 여부 |
| `points[].conf` | `float` | CREPE 신뢰도 (0~1) |
| `lrc_offset_sec` | `float` | LRC 오프셋 (초). MR 재생 시 `t_mr = t - lrc_offset_sec` |

**에러**
| 코드 | 사유 |
|------|------|
| 404 | 존재하지 않는 곡 또는 pitch_guide 미준비 |
| 422 | song_id 형식 오류 |

---

### GET /songs/{song_id}/mr

MR 음원 파일 스트리밍 (MP3).

```http
GET /songs/{song_id}/mr
Authorization: Bearer <token>
```

**Response 200**
- Content-Type: `audio/mpeg`
- 파일 바이너리 직접 반환 (FileResponse)

> **주의**: 현재 range request 미구현. 앱에서 탐색(seek) 기능이 필요하면 별도 구현 요청 필요.

**에러**
| 코드 | 사유 |
|------|------|
| 404 | 존재하지 않는 곡 또는 MR 파일 미준비 |
| 422 | song_id 형식 오류 |

---

## 9. Training Attempts and Favorites (Phase 7)

TrainingScreen에서 사용하는 누적 시도 기록 + 즐겨찾기 API. 모든 엔드포인트는 토큰의 `user_id`를 사용하므로 URL에 user_id 노출 없음.

### GET /users/me/training-attempts

누적 시도 기록 조회. `attempted_at` DESC, cursor pagination.

```http
GET /users/me/training-attempts?indicator_key=4_breathiness&limit=50&cursor=<base64>
Authorization: Bearer <token>
```

| Query | 설명 |
|-------|------|
| `indicator_key` | 지표 필터 (선택) |
| `song_id` | 노래방 곡 필터 (선택, JOIN: AnalysisRun → Session) |
| `original_run_id` | 특정 분석에 묶인 시도만 (선택) |
| `cursor` | 다음 페이지용 (응답의 `next_cursor`) |
| `limit` | 1~200, 기본 50 |

**Response 200**
```json
{
  "items": [
    {
      "attempt_id": "...",
      "session_id": "...",
      "original_run_id": "...",
      "chunk_index": 5,
      "chunk_start_sec": 24.0,
      "chunk_end_sec": 31.0,
      "indicator_key": "4_breathiness",
      "before_ai_score": 2.1,
      "before_rounded_score": 2,
      "before_zone": "appropriate",
      "after_ai_score": 3.4,
      "after_rounded_score": 3,
      "after_zone": "appropriate",
      "improvement": 1.3,
      "attempted_at": "2026-05-10T09:00:00+00:00"
    }
  ],
  "next_cursor": "MjAyNi0wNS0xMFQwOTowMDowMHwuLi4=",
  "has_more": true
}
```

`improvement` = `after_ai_score - before_ai_score`. `before_ai_score`가 `null`이면 `improvement: null`.

---

### GET /users/me/favorites

즐겨찾기 목록. `created_at` DESC. Song 테이블 JOIN으로 `song_title`, `song_artist` 포함.

```http
GET /users/me/favorites?indicator_key=4_breathiness&song_id=004
Authorization: Bearer <token>
```

**Response 200**
```json
{
  "items": [
    {
      "favorite_id": "b8c0a4df-...",
      "song_id": "004",
      "song_title": "보고싶다",
      "song_artist": "김범수",
      "original_run_id": "bdf18c1d-...",
      "chunk_index": 5,
      "chunk_start_sec": 24.0,
      "chunk_end_sec": 31.0,
      "chunk_lrc_text": "아무리 기다려도 나는 못가",
      "indicator_key": "4_breathiness",
      "created_at": "2026-05-10T09:00:00+00:00"
    }
  ]
}
```

---

### POST /users/me/favorites

즐겨찾기 추가. **노래방 14곡 한정** — 자유녹음 세션은 400 반환.

```http
POST /users/me/favorites
Authorization: Bearer <token>
Content-Type: application/json
```

**Request**
```json
{
  "original_run_id": "bdf18c1d-...",
  "chunk_index": 5,
  "indicator_key": "4_breathiness"
}
```

**Response 201**
- `GET /users/me/favorites` 응답의 `items[]` 한 항목과 동일 구조

**에러**
| 코드 | 사유 |
|------|------|
| 400 | 자유녹음 세션 (`song_id` 없음) 또는 `chunk_index` 범위 초과 |
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 `original_run_id` |
| 409 | 이미 즐겨찾기된 chunk — `detail: {error, existing_favorite_id}` |

**409 응답 예시**
```json
{
  "detail": {
    "error": "already_favorited",
    "existing_favorite_id": "b8c0a4df-..."
  }
}
```

UNIQUE 키: `(user_id, song_id, chunk_index, indicator_key)`.

---

### DELETE /users/me/favorites/{favorite_id}

즐겨찾기 삭제. 본인 데이터만 가능.

```http
DELETE /users/me/favorites/{favorite_id}
Authorization: Bearer <token>
```

**Response 204** — No Content

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 즐겨찾기 |
| 404 | 존재하지 않는 `favorite_id` |

---

## 10. 공통 응답 모델

### result_json 구조

`GET /analysis/{run_id}/results`의 `result_json` 및 `GET /sessions/{id}`의 `latest_analysis.result_json` 공통 구조.

**`result_json.status` 값** (dml-server가 방출하는 그대로, `AnalysisRun.status`에도 동일 문자열로 저장됨)

| 값 | 의미 | scores/feedback |
|----|------|-----------------|
| `"success"` | 정상 분석 완료 | 정상 포함 |
| `"no_voice"` | 무음/잡음 감지로 분석 스킵 (정상 흐름) | `null` |
| `"invalid"` | 파일/입력 오류로 분석 불가 | `null` |
| `"failed"` | 분석 중 에러 발생 | `null` |

> **주의**: `"invalid"`는 dml-server `schemas.AnalysisStatus` enum에 등록되지 않은 문자열이지만 실제로 방출되며, vocal-server는 이를 그대로 `AnalysisRun.status`/`result_json.status`에 저장한다. 앱은 enum 검증 없이 문자열 비교로 처리해야 한다.
>
> **앱 처리 권장**: `result_json.status` 분기 → `"no_voice"`이면 `reason` 텍스트 표시 + 재녹음 유도. `"invalid"`/`"failed"`는 실패 UX 표시.

---

**정상 분석 응답 (`status: "success"`)**

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
    "1_nasal_oral_ratio":   {"ai_score": null, "rounded_score": null, "zone": null,           "confidence": "medium"},
    "2_chest_head_voice":   {"ai_score": 1.83, "rounded_score": 2,    "zone": "appropriate",  "confidence": "medium"},
    "3_vocal_fold_contact": {"ai_score": 0.0,  "rounded_score": 0,    "zone": "insufficient", "confidence": "high"},
    "4_breathiness":        {"ai_score": 0.0,  "rounded_score": 0,    "zone": "insufficient", "confidence": "high"},
    "5_forward_resonance":  {"ai_score": 0.0,  "rounded_score": 0,    "zone": "insufficient", "confidence": "medium"},
    "6_soft_palate":        {"ai_score": null, "rounded_score": null, "zone": null,           "confidence": "medium"},
    "7_larynx_tongue_root": {"ai_score": null, "rounded_score": null, "zone": null,           "confidence": "unavailable"},
    "8_tongue_tension":     {"ai_score": null, "rounded_score": null, "zone": null,           "confidence": "unavailable"},
    "9_pressure_balance":   {"ai_score": 1.91, "rounded_score": 2,    "zone": "appropriate",  "confidence": "medium"}
  },

  "score_mapper_version": "v2",
  "scores_v2": {
    "3_vocal_fold_contact": 3.4,
    "4_breathiness": 2.8,
    "6_soft_palate": 1.9,
    "8_tongue_tension": 2.2
  },
  "scores_meta": {
    "3_vocal_fold_contact": {"tier": "high",      "caveats": [], "display_mark": null,        "tooltip": null, "rounded_score": 3, "icc": 0.0, "icc_ratio": 0.0},
    "4_breathiness":        {"tier": "high_star", "caveats": [], "display_mark": "asterisk",  "tooltip": null, "rounded_score": 3, "icc": 0.0, "icc_ratio": 0.0},
    "6_soft_palate":        {"tier": "high_star", "caveats": [], "display_mark": "asterisk",  "tooltip": null, "rounded_score": 2, "icc": 0.0, "icc_ratio": 0.0},
    "8_tongue_tension":     {"tier": "high_star", "caveats": [], "display_mark": "asterisk",  "tooltip": null, "rounded_score": 2, "icc": 0.0, "icc_ratio": 0.0}
  },
  "academic_analysis_scores": {
    "1_nasal_oral_ratio":  {"ai_score": 1.2, "caveats": [], "note": "academic_only"},
    "5_forward_resonance": {"ai_score": 0.8, "caveats": [], "note": "academic_only"}
  },

  "feedback": {
    "4_breathiness": {
      "name_ko": "호흡 소리 식별",
      "ai_score": 0.0,
      "zone": "insufficient",
      "zone_label": "미달",
      "score_description": "호흡 소리가 매우 강하게 들리며 발성보다 숨소리가 두드러짐",
      "feedback_text": "성대 접촉을 좀 더 확보하세요. ...",
      "ai_indicator": {
        "name": "hnr",
        "value": 0.2031
      }
    }
  },

  "reliability": {
    "high_reliability":   ["3_vocal_fold_contact", "4_breathiness"],
    "medium_reliability": ["1_nasal_oral_ratio", "2_chest_head_voice", "5_forward_resonance", "6_soft_palate", "9_pressure_balance"],
    "unavailable":        ["7_larynx_tongue_root", "8_tongue_tension"],
    "shown_v2": ["3_vocal_fold_contact", "4_breathiness", "6_soft_palate", "8_tongue_tension"],
    "shown_v2_tiers": {"3_vocal_fold_contact": "high", "4_breathiness": "high_star", "6_soft_palate": "high_star", "8_tongue_tension": "high_star"},
    "academic_only_v2": ["1_nasal_oral_ratio", "5_forward_resonance"],
    "deferred_v2": ["2_chest_head_voice", "7_larynx_tongue_root", "9_pressure_balance"]
  },

  "timeline_scores": null,
  "timeline_metadata": null
}
```

`feedback`에는 `confidence: "unavailable"` 항목은 포함되지 않습니다.

`scores`는 **v1 legacy** 9키 전체(과거 호환용). `scores_v2`/`scores_meta`는 **표시 대상 4키만**(`3_vocal_fold_contact`(tier `high`), `4_breathiness`/`6_soft_palate`/`8_tongue_tension`(tier `high_star`)). `academic_analysis_scores`는 앱 비표시 2키(`1_nasal_oral_ratio`, `5_forward_resonance`). 나머지 3키(`2_chest_head_voice`, `7_larynx_tongue_root`, `9_pressure_balance`)는 v2 체계에서 **미산출**(deferred) — `reliability.deferred_v2` 참고. `timeline_scores`/`timeline_metadata`는 `song_id` 지정 + LRC 존재 시에만 값이 채워지며, 그 외에는 `null`(아래 timeline_scores 섹션 참고).

---

**무음/잡음 감지 응답 (`status: "no_voice"`)**

```json
{
  "run_id": "f199f109-...",
  "status": "no_voice",
  "reason": "음성이 감지되지 않았거나 잡음만 녹음되었습니다. 다시 녹음해주세요.",
  "processing_time_ms": 200,
  "audio_info": {
    "duration_sec": 60.0,
    "sr": 16000,
    "voiced_ratio": 0.00,
    "f0_range": null
  },
  "indicators": { },
  "registers": null,
  "scores": null,
  "feedback": null,
  "reliability": null,
  "timeline_scores": null,
  "timeline_metadata": null
}
```

- `Session.status`는 `"completed"`로 저장됨 (분석 가드가 정상 응답한 것)
- `AnalysisRun.status`는 `"no_voice"`로 저장됨
- `scores`, `feedback`, `reliability`는 모두 `null`
- 앱: `result_json.status === "no_voice"` 감지 → `reason` 텍스트 표시 + 재녹음 유도

---

### timeline_scores 계약

`song_id` 지정 + 해당 곡 LRC 파싱 파일이 존재할 때만 값이 채워짐. 그 외에는 `timeline_scores`/`timeline_metadata` 모두 `null`.

**원소(item) shape**
```json
{
  "start_sec": 24.0,
  "end_sec": 31.0,
  "lrc_text": "가사 한 줄",
  "chunk_duration_s": 7.0,
  "scores": {
    "3_vocal_fold_contact": {"ai_score": 3.4, "rounded_score": 3, "tier": "high"},
    "4_breathiness":        null,
    "6_soft_palate":        {"ai_score": 1.9, "rounded_score": 2, "tier": "high_star"},
    "8_tongue_tension":     null
  },
  "low_confidence_items": ["4_breathiness", "8_tongue_tension"]
}
```

구간 경계 필드명은 `start_sec`/`end_sec`로 고정. `scores`는 항상 4키(`3_vocal_fold_contact`, `4_breathiness`, `6_soft_palate`, `8_tongue_tension`) 고정.

**`scores[key]`의 null 규칙 (설계된 skip — 버그 아님)**
- 매 chunk 기본값은 4키 전부 `null`.
- chunk 유성 구간이 2.0초 미만이거나 v2 mapper 미가용이면 4키 전부 `null` 유지.
- 채점 중 예외 발생 시에도 4키 전부 `null`.
- 이론상 특정 key만 부분적으로 `null`인 경로가 코드에 존재하나, `ScoreMapperV2`가 항상 4키 모두 값을 반환하므로 **실무상 chunk 단위 all-or-nothing** (전부 값 또는 전부 null).

**소비자(앱) 계약**: `timeline_scores` 자체가 `null`일 수 있고(1단계), 배열이어도 각 원소의 `scores[key]`가 `null`일 수 있다(2단계). **두 단계 모두 역참조 전 null 검사 필수.** null 항목은 "해당 구간 신뢰 가능한 점수 없음"으로 처리.

---

### low_confidence_items 계약

`list[str]` — 9항목 key 체계를 따르는 문자열 배열(dict 아님).

- `/analysis/{run_id}/results`의 `result_json.low_confidence_items`(전체 분석)와 `POST /sessions/{id}/training-analyze` 응답 최상위(§6 참고)는 chunk `duration < 5.0초`일 때 `["4_breathiness", "6_soft_palate", "8_tongue_tension"]`, 그 외에는 `[]`.
- `timeline_scores[*].low_confidence_items`도 동일 규칙으로 chunk 단위 병합되며, 여기에 skip/예외로 인한 전체-null chunk의 키가 추가로 포함될 수 있음.

---

### rounded_score 생성 위치

vocal-server는 `rounded_score`를 직접 계산하거나 가공하지 않음 — dml-server가 계산한 값을 그대로 전달.

- **v1 legacy `scores[*].rounded_score`**: `rounded = min(5, max(0, round(ai_score)))`. `ai_score`가 `null`이면 `rounded_score`도 `null`.
- **v2 `scores_meta[*].rounded_score` / `timeline_scores[*].scores[*].rounded_score`**: `ScoreMapperV2`가 `pred_clipped = max(0, min(5, pred))` → `rounded_score = int(round(pred_clipped))`로 계산.
- v1과 v2는 **독립된 계산 경로**이며 한쪽이 실패하면 다른 쪽으로 대체하는 fallback 체인은 없음.

---

### 평가 항목 9개

| 키 | 한국어 이름 | 신뢰도 |
|----|------------|--------|
| `1_nasal_oral_ratio` | 비강, 구강 공명의 비율 | medium |
| `2_chest_head_voice` | 흉성, 두성의 비율 | medium |
| `3_vocal_fold_contact` | 성대 접촉률 | high |
| `4_breathiness` | 호흡 소리 식별 | high |
| `5_forward_resonance` | 전방 공명 | medium |
| `6_soft_palate` | 연구개 상태 | medium |
| `7_larynx_tongue_root` | 후두, 설근 긴장 | unavailable |
| `8_tongue_tension` | 혀 긴장 | unavailable |
| `9_pressure_balance` | 호흡압 균형 | medium |

### scores.zone 값

| 값 | 의미 | 점수 범위 |
|----|------|----------|
| `"appropriate"` | 적절 | 2~3 |
| `"insufficient"` | 부족 | 0~1 |
| `"excessive"` | 과도 | 4~5 |
| `null` | 평가 불가 (confidence: unavailable) | — |

### scores.confidence 값

| 값 | 의미 | UI 권장 |
|----|------|---------|
| `"high"` | 높은 신뢰도 | 강조 표시 |
| `"medium"` | 중간 신뢰도 | 일반 표시 |
| `"unavailable"` | 평가 불가 | "측정 불가" 표시, `ai_score: null` |

---

## 11. 에러 코드

| 코드 | 사유 | 주요 발생 상황 |
|------|------|---------------|
| 400 | 잘못된 요청 | 존재하지 않는 `song_id`, 이미 등록된 이메일 |
| 401 | 인증 필요 / 실패 | 토큰 없음, 만료, 비밀번호 불일치 |
| 403 | 권한 없음 | 다른 사용자의 세션·파일·분석 결과 접근 |
| 404 | 리소스 없음 | 없는 session_id / run_id / song_id, LRC·MR 미준비 |
| 422 | 입력 형식 오류 | 필드 누락, 타입 불일치, song_id 형식 불일치 |
| 500 | 서버 오류 | 예상치 못한 내부 오류 |

---

## 12. 폴링 가이드

`POST /sessions/{session_id}/analyze`는 **비동기 start endpoint**입니다. 응답은 접수 결과(`run_id`, `status:"queued"`)일 뿐이며, 실제 분석은 background task에서 진행됩니다. 앱은 `GET /analysis/{run_id}`를 polling하다가 terminal status(`success`/`completed`/`failed`/`invalid`/`no_voice`)가 되면 `GET /analysis/{run_id}/results`를 호출해야 합니다.

폴링 패턴:

```python
import time, httpx

run_id = "f199f109-..."
headers = {"Authorization": "Bearer <token>"}

for _ in range(30):  # 최대 150초 대기
    r = httpx.get(f"http://host:8000/analysis/{run_id}", headers=headers)
    status = r.json()["status"]
    if status in ("success", "completed", "failed", "invalid", "no_voice"):
        break
    time.sleep(5)

results = httpx.get(
    f"http://host:8000/analysis/{run_id}/results", headers=headers
).json()
result_json = results["result_json"]
```

---

## 13. 권한 모델

- 세션, 파일, 분석 결과는 **생성한 사용자만 접근** 가능. 타인 접근 시 `403`.
- `/songs/*` 노래방 API는 인증(Bearer 토큰)만 필요. user_id 검증 없음 — 로그인한 누구나 동일 데이터 접근 가능.
- 토큰 만료 / 유효하지 않은 토큰 → `401` → 재로그인 후 새 토큰 사용.

---

## 14. 관리자 웹 (Admin)

> 앱과 무관. `https://admin.vocal-fit.com`에서 접근하며 별도 비밀번호 인증 사용. 앱 개발 참고용으로만 명시.

| 메소드 | 경로 | 용도 |
|--------|------|------|
| GET | `/admin` | 302 → `/admin/login` |
| GET | `/admin/health` | 인증 불필요 헬스 체크 (`{"admin":"ok"}`) |
| GET | `/admin/login` | 로그인 페이지 (HTML) |
| POST | `/admin/login` | form `password` 제출 → 302 `/admin/dashboard` (성공) / `?error=invalid_password` (실패) |
| POST | `/admin/logout` | 세션 clear → 302 `/admin/login` |
| GET | `/admin/dashboard` | (구) SSE 대시보드 — 사용 비권장. `/admin/logs`로 대체 |
| GET | `/admin/logs` | 실시간 로그 페이지 (HTML, 5초 폴링, 인증 필요) |
| GET | `/admin/api/events` | 이벤트 JSON (`?limit=&since=`, 인증 필요) |
| GET | `/admin/api/online-users` | 5분 이내 활동 사용자 JSON (인증 필요) |
| GET | `/admin/events/stream` | **폐기** (410 Gone). Cloudflare Tunnel SSE 불안정 → 폴링 전환 |
| GET | `/admin/users` | 사용자 리스트 페이지 + 회원가입 토글 카드 (HTML, 인증 필요). Query: `show_test=true`로 테스트 계정 포함 |
| GET | `/admin/users/{user_id}` | 사용자 상세 (HTML, 인증 필요): 분석 세션 50개 + 즐겨찾기 전체 + 누적 시도 100개 탭 |
| POST | `/admin/signup-toggle` | 회원가입 ON/OFF 토글 (메모리 상태, 인증 필요) → 302 `/admin/users` |
| GET | `/admin/api/users` | 사용자 리스트 JSON (dashboard JS용, 인증 필요) |
| GET | `/admin/users/{id}/sessions`, `/admin/events`, `/admin/events/stream` | 인증 필요 |

**회원가입 토글 동작**: `app_state.signup_enabled` 메모리 변수로 관리. 서버 startup 시 `.env`의 `SIGNUP_ENABLED`로 초기화. admin 페이지에서 `POST /admin/signup-toggle`로 즉시 변경되지만 **서버 재시작 시 .env 값으로 reset**됨 — 영구 변경은 `.env` 수정 + 재시작.

**테스트 계정 필터** (`/admin/users` Query `show_test`): 기본 false → 운영 계정만 표시. 테스트 계정은 이메일 prefix 패턴(`test_a_`, `test_b_`, `hdrtest_`, `tmtest_`, `trtest`, `raw_`, `p7a_`/`p7b_`, `sigtest_`, `toggle_test_`, `signup_check`)으로 자동 식별. `show_test=true` 시 전체 표시 + 운영/테스트 분리 카운트.

**활동 추적** (Phase A-5-d): `ActivityTrackerMiddleware`가 인증된 일반 사용자 요청을 추적하여 `users.last_seen_at`, `users.last_endpoint`에 기록.
- **추적 제외**: `/admin/*`, `/health`, `/docs`, `/openapi.json`, `/redoc`, `/static`
- **Throttle**: 같은 user + 같은 endpoint 5분 이내면 DB UPDATE 스킵 (메모리 캐시, 단일 인스턴스 한정)
- **경로 정규화**: UUID·hex(12+자리)·3자리 song_id → `{id}` (예: `/sessions/abc-...-def/analyze` → `POST /sessions/{id}/analyze`)
- **Best-effort**: 추적 실패는 로그만 남기고 응답에 영향 없음
- **상태 라벨**: admin 화면에서만 `success`/`completed` → `완료`, `no_voice` → `무음` 한글 통일 (DB 값은 그대로 — vocal-app 호환성)

**인증**: `SessionMiddleware` 기반 `admin_session` 쿠키 (24시간, https_only, lax). 미인증 시 401.

**Rate limit**: 5분 윈도우 내 실패 5회 → 5분 차단 (IP 기준, X-Forwarded-For 사용). `?error=rate_limited&retry={seconds}` redirect로 안내. 메모리 기반이라 서버 재시작 시 초기화.

**환경변수** (`.env`, gitignored):
- `ADMIN_PASSWORD` — 로그인 비밀번호
- `ADMIN_SESSION_SECRET` — 세션 쿠키 서명 키 (`secrets.token_urlsafe(48)`)

---

## 15. 폐기된 엔드포인트

아래 엔드포인트는 **현재 서버에 존재하지 않습니다**. 호출 시 404 또는 라우팅 오류 발생.

| Method | Path | 폐기 사유 |
|--------|------|----------|
| POST | `/sessions/{id}/compare-pitch` | 구버전 노래방 (librosa 기반). 신규 songs API로 대체 |
| POST | `/songs/register` | 구버전 곡 등록 엔드포인트. 현재 DB seed 방식으로 대체 |
| GET | `/songs/{id}/audio` | 저작권 이슈로 영구 제거 (master 음원 노출 금지) |
| GET | `/songs/{id}/pitch` | `/songs/{id}/pitch-guide`로 대체 |
| GET | `/songs/{id}/lyrics` | `/songs/{id}/lrc`로 대체 |
