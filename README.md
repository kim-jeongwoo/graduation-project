# 가창 발성 평가 시스템

순천향대학교 사물인터넷학과 졸업작품. 딥러닝 기반 EGG 추정을 활용한 가창 발성 평가 + 보컬 트레이닝 피드백 시스템.

## 프로젝트 구조 (모노레포)

```
graduation-project/           # 이 레포 루트
├── vocal-server/             # FastAPI 백엔드 (Mac Studio)
│   ├── app/                  #   라우터, 서비스, ORM 모델
│   ├── alembic/              #   DB 마이그레이션
│   ├── scripts/              #   동기화·시드 스크립트
│   ├── docs/                 #   API 문서
│   ├── PROGRESS.md
│   └── CLAUDE.md
├── dml-server/               # AI 모델 + 추론 서버 (dmlserver GPU)
│   ├── ai-model/             #   EGG 추정 모델 학습 (EfficientEGGNet)
│   ├── model_server/         #   FastAPI 추론 서버 (port 8001)
│   ├── scripts/              #   분석 파이프라인 + 노래방 데이터 준비
│   ├── figures/, images/     #   시각화 PNG
│   ├── docs/                 #   dml 관련 문서
│   ├── tests/                #   테스트 코드
│   ├── PROJECT_LOG.md
│   └── CLAUDE.md
├── app/                      # Expo 앱 (별도 작업)
├── CLAUDE.md                 # 모노레포 공통 규칙
└── README.md                 # 본 파일
```

## 핵심 결과

- EGG 추정 모델: Test Corr 0.8249 (Exp20 Progressive Window)
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
[vocal-server: 백엔드 API (Mac Studio, port 8000)]
  ↓ 분석 요청
[dml-server/model_server: AI 추론 (dmlserver GPU, port 8001)]
  ↓ EGG 추정 + 음향 지표 + 점수 + 피드백
[vocal-server에 결과 저장 → 앱에서 시각화]
```

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
