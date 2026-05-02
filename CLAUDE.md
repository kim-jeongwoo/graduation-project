# CLAUDE.md — graduation-project (모노레포)

## 구조
```
graduation-project/
├── vocal-server/   FastAPI 백엔드 (Mac Studio)       → vocal-server/CLAUDE.md
├── dml-server/     AI 모델 + 추론 서버 (dmlserver GPU) → dml-server/CLAUDE.md
└── app/            Expo 앱 (별도 작업)
```

## 에이전트 공통 규칙
- 작업 범위에 맞는 서브폴더 CLAUDE.md를 먼저 읽을 것.
- `vocal-server/`와 `dml-server/`는 서로 손대지 않음.
- force push 금지. DB DROP/DELETE는 사용자 확인 후 실행.
