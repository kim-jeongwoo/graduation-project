# 가창 발성 평가 시스템

순천향대학교 사물인터넷학과 졸업작품. 딥러닝 기반 EGG 추정을 활용한 가창 발성 평가 + 보컬 트레이닝 피드백 시스템.

## 프로젝트 구조

```
graduation-project/
├── ai-model/         # EGG 추정 딥러닝 모델 학습 (EfficientEGGNet)
├── model_server/     # FastAPI 추론 서버 (GPU, dmlserver)
├── server/           # 백엔드 API (FastAPI, Mac Studio)
├── scripts/          # 분석 파이프라인 (score_mapper, batch_analyze, ...)
├── data-prep/        # 14곡 노래방 데이터 준비 (LRC + 음정 곡선)
├── results/          # 검증 결과 JSON + 시각화
├── figures/          # 학습/분석 시각화 PNG
├── docs/             # 프로젝트 문서
├── tests/            # 테스트 코드
├── CLAUDE.md         # 코드 에이전트용 작업 컨텍스트
├── PROJECT_LOG.md    # 프로젝트 진행 기록 (사용자용)
└── README.md         # 본 파일
```

## 핵심 결과

- EGG 추정 모델: Test Corr 0.8249 (Exp20 Progressive)
- 평가자 ICC: 학습 0.875 / 검증 0.817 (우수 기준 0.75 초과)
- 통계적으로 유의미한 평가 항목 2종:
  - 호흡식별 (CPP 기반): Pearson r=0.547, p<0.001
  - 접촉강도 (CQ peak 기반): Pearson r=0.557, p<0.001 (고음역 0.665)

## 발표일

2026년 6월 15일

## 시스템 흐름

```
[사용자 스마트폰 앱]
  ↓ 녹음 + 업로드
[server: 백엔드 API]
  ↓ 분석 요청
[model_server: AI 추론 (GPU)]
  ↓ EGG 추정 + 음향 지표 + 점수 + 피드백
[server에 결과 저장]
  ↓ 응답
[앱에서 시각화 + 피드백]
```

## 모듈별 설명

### ai-model
EfficientEGGNet 기반 EGG 신호 추정 모델. SVD_healthy 데이터셋(687명) + 보컬학원 자유곡 데이터(22명)로 학습. window 16384, 16kHz, non-causal dilated CNN.

### model_server
PyTorch 추론 서버. POST /predict (EGG wav 반환), POST /analyze (9개 항목 점수 + 피드백 JSON 반환).

### server
사용자 인증, 세션 관리, 녹음 저장, 분석 요청 라우팅, 사전/사후 비교 API.

### data-prep
14곡 자유곡에 대한 LRC 가사 + 가수 음정 곡선 추출 파이프라인. Demucs 보컬 분리 + CREPE F0 추출 + LRCLIB 가사 + cross-correlation 시간 정렬.

## 평가 항목 (9개)

| 번호 | 항목 | AI 신뢰도 |
|---|---|---|
| 1 | 비강 사용 | medium |
| 2 | 흉성/두성 | medium |
| 3 | 성대 접촉 강도 | high |
| 4 | 호흡 식별 | high |
| 5 | 전방 공명 | medium |
| 6 | 연구개 위치 | medium |
| 7 | 후두/혀뿌리 위치 | unavailable |
| 8 | 혀 경직도 | unavailable |
| 9 | 상압/하압 비율 | medium |

척도: 0~5점 (0~1=미달, 2~3=적절, 4~5=과함)

## 라이선스 / 저작권

- 졸업작품용 비상업 코드
- 14곡 음원/MR은 KOMCA 라이선스 별도 처리 (레포에 포함되지 않음)
- 사용자 음성 데이터는 개인정보 보호로 레포에 포함되지 않음

## 자세한 내용

PROJECT_LOG.md 참조.
