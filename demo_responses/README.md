# Demo Responses (Mock Data)

앱 페이지가 UI 개발 시 사용하는 model_server `/analyze` 응답 mock 데이터.

## 5종 케이스

| 파일 | test_id | 설명 |
|---|---|---|
| `excellent_high.json` | test_11 | 잘 부른 사례. 호흡식별/접촉강도 모두 적절 범위(2~3점) |
| `needs_work_breathing.json` | test_08 | 호흡식별 0~1점. 기식음 과다 케이스 |
| `needs_work_contact.json` | test_05 | 접촉강도 4~5점. 성대 과압박 케이스 |
| `needs_work_both.json` | test_01 | 호흡식별 + 접촉강도 모두 양극단. 종합 개선 필요 |
| `medium_quality.json` | test_10 | 모든 항목 2~3점 평균. 전반적 평균 수준 |

## JSON 구조

각 케이스 JSON은 다음 필드를 포함합니다:

```
{
  "case_name": "...",
  "test_id": "test_XX",
  "case_description": "한국어 설명",
  "expected_feedback_focus": ["4_breathiness:appropriate", ...],
  "duration_sec": ...,
  "processing_time_ms": ...,
  "trainer_overall": { "3_vocal_fold_contact": ..., ... },
  "trainer_per_register": { "low": {...}, "mid": {...}, "high": {...} },
  "analyze_response": {        // model_server /analyze 응답 그대로
    "run_id": "...",
    "status": "success",
    "audio_info": {...},
    "registers": {...},
    "indicators": {...},
    "scores": {...},
    "feedback": {...},
    "reliability": {...}
  }
}
```

`index.json`은 5종 케이스 메타 + 트레이너 점수 + 처리 시간을 한 파일에 정리한 요약본입니다.

## 갱신 방법

5월 10일 검증 데이터 도착 후 점수 매핑이 변경될 경우:

```bash
cd ~/projects/egg_prediction

# 1. model_server 실행 확인
# 2. mock 응답 재생성
conda activate EGGDML
python dml-server/scripts/data_prep/select_demo_cases.py

# 3. 루트 demo_responses/에 동기화
bash dml-server/scripts/sync_demo_responses.sh

# 4. git 커밋
git add demo_responses/
git commit -m "Update demo_responses: retrained score mapper"
git push origin main
```

## 사용처

- **앱 페이지**: `/analyze` mock API 응답으로 사용 (실제 서버 없이 UI 개발)
- **서버 페이지**: 서버가 직접 사용하지 않음 (개발 참고용)
- **dml-server**: `dml-server/results/demo_responses/`가 원본, 이 폴더는 동기화 사본
