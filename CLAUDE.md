# CLAUDE.md — vocal-app

보컬 연습을 기록·분석하고 피치 비교/목표 관리를 제공하는 React Native(Expo) 모바일 앱.

---

## 환경

### 기술 스택
| 레이어 | 기술 |
|--------|------|
| 프레임워크 | React Native 0.81 / Expo SDK 54 |
| 언어 | TypeScript 5.9 |
| 내비게이션 | React Navigation v7 (Stack + BottomTabs) |
| HTTP | Axios + expo-secure-store (JWT) |
| 오디오/피치 | expo-av, react-native-pitchy |
| 차트 | react-native-svg |
| 빌드 | EAS Build |

### 실행 명령
```bash
npx expo start --dev-client   # 개발 서버 (dev-client)
npx expo start                # Expo Go 모드
npx expo start --ios          # iOS 시뮬레이터
npx expo start --android      # Android 에뮬레이터
```

### 서버 연결 (`src/api/client.ts`)
- `CURRENT_SERVER = "local"` : 동일 네트워크, `192.168.0.16:8000`
- `CURRENT_SERVER = "tunnel"` : ngrok URL (재시작 시 갱신 필요)

---

## 현재 상태
- 인증(로그인/회원가입), 홈, 세션 기록, 분석 결과, 피치 비교, 목표, 설정 화면 구현
- 일부 화면은 `src/mock/mockData.ts` 모의 데이터 사용 중
- 백엔드 API 연동: `src/api/` (auth, sessions, vocal, songs, analysis)
- VocalRangeTestScreen 온보딩 플로우 존재

---

## 에이전트 행동 규칙

### 토큰 효율
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.

### 실수 방지
- 파일 수정 전 뭘 바꿀 건지 먼저 설명.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.
- 되돌릴 수 있는 작업은 물어보지 말고 바로 진행. 삭제·전송 같은 비가역 작업만 확인.
- 추측 금지. 불명확하면 궁금한 것들을 한 번에 묶어 질문.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.

---

## 절대 규칙
- `src/api/client.ts`의 `SERVER_URLS` / `CURRENT_SERVER` 값을 무단으로 수정하지 않는다.
- `expo-secure-store`에 저장된 토큰 키(`auth_token`)를 변경하지 않는다.
- EAS 설정(`eas.json`, `app.json`)을 사용자 확인 없이 수정하지 않는다.
- 기존 화면의 내비게이션 구조(라우트 이름)를 임의로 변경하지 않는다.
- 요청받지 않은 리팩토링·기능 추가를 하지 않는다.

---

## ⚠️ 반복하지 말 것 (Known Pitfalls)

<!-- 형식: [날짜] [카테고리] 실수 / 원인 / 대신 어떻게 -->
<!-- 최신이 위. 기존 항목은 절대 지우지 말고 누적만. -->
<!-- 에이전트가 실수했을 때 즉시 추가 -->

