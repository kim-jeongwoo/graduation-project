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

**Response 200** (정상)
```json
{
  "session_id": "7cd855b1-...",
  "status": "success",
  "scores": {
    "3_vocal_fold_contact": {
      "ai_score": 3.4,
      "rounded_score": 3,
      "zone": "appropriate",
      "confidence": "high"
    },
    "4_breathiness": {
      "ai_score": 2.8,
      "rounded_score": 3,
      "zone": "appropriate",
      "confidence": "high"
    }
  },
  "reason": null,
  "duration_sec": 7.0,
  "indicators": {
    "cpp_mean": 0.21,
    "voiced_ratio": 0.78
  },
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

`chunk_meta`는 클라이언트가 보낸 값을 그대로 echo. 보내지 않았으면 `null`. `run_id`는 의도적으로 제외 (휘발 분석이므로 정식 `AnalysisRun.run_id`와 혼동 방지).

**필드별 케이스**

| 필드 | success | no_voice | 비고 |
|------|---------|----------|------|
| `scores` | dict (2개 항목) | `null` | `3_vocal_fold_contact`, `4_breathiness` |
| `reason` | `null` | string (한국어 메시지) | 앱에서 사용자에게 표시 권장 |
| `duration_sec` | float | float | 청크 길이 |
| `indicators` | dict | `null` | cpp_mean, voiced_ratio 등 원시 지표 |
| `processing_time_ms` | float | float | dml-server 처리 시간 |
| `chunk_meta` | echo | echo | 클라이언트가 보낸 값 그대로 |

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
| 504 | dml-server timeout 또는 연결 실패 |

---

## 7. 분석

### POST /sessions/{session_id}/analyze

AI 분석 요청. **동기 처리** — 응답까지 10~30초 소요 (타임아웃 최소 60초 권장).  
세션 `status`가 `uploaded` 상태여야 합니다.

```http
POST /sessions/{session_id}/analyze
Authorization: Bearer <token>
```

**Response 201**
```json
{
  "run_id": "f199f109-8f96-4528-9b61-be811eef7ef1",
  "status": "success"
}
```

분석 실패 시에도 201 반환, `status: "failed"`. 무음/잡음 감지 시 `status: "no_voice"` 반환.

**에러**
| 코드 | 사유 |
|------|------|
| 400 | 세션 상태가 `uploaded`가 아님 (파일 미업로드 또는 이미 분석됨) |
| 403 | 다른 사용자의 세션 |
| 404 | 존재하지 않는 session_id |

---

### GET /analysis/{run_id}

분석 실행 상태 조회. 비동기 폴링 전환 시 사용.

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
| `"failed"` | 분석 중 에러 발생 |
| `"no_voice"` | 무음/잡음 감지로 분석 스킵 (정상 흐름) |

**에러**
| 코드 | 사유 |
|------|------|
| 403 | 다른 사용자의 분석 |
| 404 | 존재하지 않는 run_id |

---

### GET /analysis/{run_id}/results

분석 결과 전체 조회. `result_json`에 scores, feedback, indicators 포함.

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

**`result_json.status` 값**

| 값 | 의미 | scores/feedback |
|----|------|-----------------|
| `"completed"` | 정상 분석 완료 | 정상 포함 |
| `"failed"` | 분석 중 에러 발생 | `null` |
| `"no_voice"` | 무음/잡음 감지로 분석 스킵 | `null` |

> **앱 처리 권장**: `result_json.status` 분기 → `"no_voice"`이면 `reason` 텍스트 표시 + 재녹음 유도.

---

**정상 분석 응답 (`status: "completed"`)**

```json
{
  "run_id": "f199f109-...",
  "status": "completed",
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
    "unavailable":        ["7_larynx_tongue_root", "8_tongue_tension"]
  }
}
```

`feedback`에는 `confidence: "unavailable"` 항목은 포함되지 않습니다.

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

현재 분석은 **동기 처리** (10~30초). `POST /analyze` 응답까지 대기하면 됩니다.  
타임아웃은 **최소 60초** 설정 권장.

비동기 전환 시를 대비한 폴링 패턴:

```python
import time, httpx

run_id = "f199f109-..."
headers = {"Authorization": "Bearer <token>"}

for _ in range(30):  # 최대 150초 대기
    r = httpx.get(f"http://host:8000/analysis/{run_id}", headers=headers)
    status = r.json()["status"]
    if status in ("success", "completed", "failed"):
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
| GET | `/admin/dashboard` | 실시간 활동 로그 대시보드 (HTML, 인증 필요) |
| GET | `/admin/users` | 사용자 리스트 페이지 + 회원가입 토글 카드 (HTML, 인증 필요). Query: `show_test=true`로 테스트 계정 포함 |
| POST | `/admin/signup-toggle` | 회원가입 ON/OFF 토글 (메모리 상태, 인증 필요) → 302 `/admin/users` |
| GET | `/admin/api/users` | 사용자 리스트 JSON (dashboard JS용, 인증 필요) |
| GET | `/admin/users/{id}/sessions`, `/admin/events`, `/admin/events/stream` | 인증 필요 |

**회원가입 토글 동작**: `app_state.signup_enabled` 메모리 변수로 관리. 서버 startup 시 `.env`의 `SIGNUP_ENABLED`로 초기화. admin 페이지에서 `POST /admin/signup-toggle`로 즉시 변경되지만 **서버 재시작 시 .env 값으로 reset**됨 — 영구 변경은 `.env` 수정 + 재시작.

**테스트 계정 필터** (`/admin/users` Query `show_test`): 기본 false → 운영 계정만 표시. 테스트 계정은 이메일 prefix 패턴(`test_a_`, `test_b_`, `hdrtest_`, `tmtest_`, `trtest`, `raw_`, `p7a_`/`p7b_`, `sigtest_`, `toggle_test_`, `signup_check`)으로 자동 식별. `show_test=true` 시 전체 표시 + 운영/테스트 분리 카운트.

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
