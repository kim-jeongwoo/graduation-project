# AGENTS.md — vocal-app

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

## Project workflow
- 이 repo는 vocal feedback project의 Expo 모바일 앱 `vocal-app`이다.
- 작업은 허브 페이지/사용자 지시문을 우선 source of truth로 삼고, repo 내부 active agent 지시는 `AGENTS.md`를 기준으로 한다.
- 코드 변경 전 현재 구현을 먼저 확인하고 접근 방법을 3~5줄로 요약한다.
- 작업이 plan-first 또는 "정우 OK 후 진행"을 명시하면, 정우 OK 전에는 파일을 수정하지 않는다.
- 기존 패턴 위에 최소 diff로 변경한다.
- key/schema/API 응답 매핑은 추측하지 말고 raw/schema/code를 먼저 확인한다.
- Galaxy 검증 실패 시 추측 수정하지 말고 진단 로그와 raw 출력 확인을 먼저 요청한다.

## Codex ExecPlan workflow
- 긴 작업은 `/compact` 단독에 의존하지 말고 `AGENTS.md` + `.codex/PLANS.md` + `.codex/ACTIVE_PLAN.md` 조합으로 운영한다.
- 새 긴 작업을 시작하면 `.codex/PLANS.md` 템플릿을 복사해 `.codex/ACTIVE_PLAN.md`에 현재 목표, 금지 범위, 진행 상태, 검증 기준을 기록한다.
- context 압축, 새 Codex 재개, 장시간 중단 후에는 먼저 `AGENTS.md`를 읽고 이어서 `.codex/ACTIVE_PLAN.md`를 읽은 뒤 현재 작업을 복원한다.
- 작업 중 결정, 검증 결과, 남은 리스크가 바뀌면 기능 코드와 분리해 `.codex/ACTIVE_PLAN.md`를 갱신한다.
- `.codex/ACTIVE_PLAN.md`는 현재 진행 중인 작업의 source of continuity이며, 사용자 최신 지시문과 충돌하면 사용자 최신 지시문이 우선한다.
- `.codex/PLANS.md`는 템플릿/운영 규칙 파일이다. 특정 작업의 상세 진행 상황은 `ACTIVE_PLAN.md`에만 적는다.
- ExecPlan 문서 업데이트 작업은 앱 기능 코드 변경과 분리한다. 사용자가 명시하지 않으면 `src/`, API URL, package scripts, server repo를 건드리지 않는다.

## Model selection
- 복잡한 설계, 다중 파일 의존성, 디버깅, schema migration, 위험한 edge case는 GPT-5 high reasoning 또는 사용 가능한 가장 강력한 GPT/Codex 모델을 사용한다.
- 단순 매핑, 로그 추가, timeout/text 변경, 기존 패턴 복사는 빠른 Codex/GPT 모델을 사용할 수 있다.
- 데드라인이 촉박하고 한 번에 정확히 끝내야 하면 단순해 보여도 강한 모델을 우선 사용한다.

## Parallel Codex workflow
- 작업이 복잡하고 안전하게 분할 가능하면 Codex subagent/parallel thread를 사용한다.
- 좋은 병렬 대상: read-only codebase exploration, schema/type/data-flow audit, test failure triage, log/raw analysis, 독립적인 파일 패턴 조사, uncommitted diff review.
- 같은 파일에 대한 write-heavy 병렬 작업은 피한다.
- 병렬 에이전트는 보통 inspect/report만 수행한다.
- 최종 patch 적용은 하나의 main integrator가 담당한다.
- 병렬 에이전트를 사용한 경우 완료 보고에 각 agent의 scope, key findings, conflicts/disagreements, final integrated decision을 포함한다.

## Codex Computer Use / Browser verification

정우 has enabled Codex Computer Use and Google Chrome for verification tasks.

Use Computer Use or Chrome when verification can be done through:
- public or approved web pages
- local development servers
- API health pages
- GitHub PR pages
- browser-visible app/admin pages
- Expo/Metro web-accessible diagnostics

Prefer Codex self-verification for:
- production API health checks
- endpoint reachability checks
- GitHub PR/document review
- browser-based UI checks
- local server pages that can be opened in Chrome
- console/log inspection that does not require secrets

Do not ask 정우 to manually verify browser/API things Codex can verify with allowed tools.

Limits:
- Real Galaxy microphone input, singing, vocal training feel, MR/MIDI/LRC timing by ear, and physical device UX still require 정우 verification.
- Do not enter passwords, tokens, or sensitive credentials unless 정우 is present and explicitly approves.
- Do not use Computer Use for destructive actions such as deploy, reset, delete, merge, or production state changes without explicit approval.
- Keep browser tasks narrow: one app/page/flow at a time.
- If Computer Use is unavailable or permission is missing, report that clearly and provide a one-shot command or URL for 정우.

## Hard constraints
- `KaraokeScreen`은 명시 요청 없이는 건드리지 않는다.
- 즐겨찾기, 곡별 폴더, history, 사후 측정 흐름은 명시 요청 없이는 건드리지 않는다.
- 정우가 요청하지 않으면 EAS build를 제안하지 않는다.
- 검증 완료된 기존 flow는 유지한다.
- 검증 후 명시 요청이 있기 전까지 diagnostic log를 제거하지 않는다.
- `.env` / `.env.*` 파일은 명시 요청 없이는 읽지 않는다.

## Verification
- 실행 가능한 검증 명령은 `package.json` 기준으로 확인한다.
- 현재 `vocal-app`의 알려진 타입 체크 명령은 `npx tsc --noEmit`이다.
- `npm run typecheck`, `npm run lint`, `npm test`는 script가 있을 때만 실행한다.
- typecheck가 기존 unrelated navigation typing error로 실패하면 별도 보고하고, 금지된 화면은 명시 승인 없이 수정하지 않는다.
- 완료 보고에는 항상 `git diff --stat`을 포함한다.

## Reporting format
- 조사 전용 작업:
  1. Current state
  2. Findings
  3. Recommended action
  4. Files that would change
  5. Questions/risks
- 구현 작업:
  1. Changed files
  2. Core changes in 3 lines
  3. Verification result
  4. git diff --stat
  5. Manual/Galaxy verification checklist if relevant

---

## 에이전트 행동 규칙 (Karpathy 4원칙)

### 1. Think Before Coding (추측 금지)
- 가정은 명시적으로 진술. 불확실하면 추측하지 말고 질문.
- 해석이 여러 개 가능하면 조용히 하나 고르지 말고 모두 제시.
- 더 단순한 방법이 있으면 그걸 제안 (push back).
- 혼란스러우면 멈추고 뭐가 불명확한지 명시 후 질문.
- 코드 작성 전 접근 방법 3~5줄 요약 → 사용자 OK 후 진행.
- 불명확한 것은 한 번에 묶어서 질문. 개별 확인 왕복 금지.
- 모든 작업 시작 전 아래 "반복하지 말 것"을 먼저 읽는다.

### 2. Simplicity First (단순함 우선)
- 요청한 것만 구현. 추측성 기능 금지.
- 일회성 코드에 추상화 만들지 말 것.
- 요청되지 않은 "유연성", "설정 가능성" 추가 금지.
- 일어날 수 없는 시나리오에 에러 핸들링 추가 금지.
- 200줄로 될 걸 1000줄로 만들지 말 것. 시니어 엔지니어가 보면 과한가? 그러면 단순화.

### 3. Surgical Changes (외과적 수정)
- 수정해야 할 곳만 건드림. 인접 코드/주석/포맷 임의 개선 금지.
- 망가지지 않은 것 리팩토링 금지.
- 기존 스타일이 마음에 안 들어도 그 스타일을 따를 것.
- 무관한 죽은 코드 발견 시 — 언급만 하고 삭제는 하지 말 것.
- 단, 내 수정 때문에 생긴 고아(unused import/variable)는 정리.
- 파일 수정 전 뭘 바꿀 건지 먼저 설명. 되돌릴 수 있는 작업은 바로 진행, 비가역 작업만 확인.
- **테스트: 모든 수정 라인이 사용자 요청과 직접 연결되는가?**

### 4. Goal-Driven Execution (목표 기반 실행)
- 명령형 작업을 검증 가능한 목표로 변환.
  "버그 고쳐" → "버그 재현 후 수정, 동일 조건에서 재현 안 됨 확인"
  "검증 추가" → "잘못된 입력 케이스 정의 후 처리 확인"
- 다단계 작업은 짧은 계획 진술:
  1. [단계] → 검증: [체크]
  2. [단계] → 검증: [체크]
- 강한 성공 기준이 있으면 자율 루프, 약하면 매번 확인 요청.
- 분석만 하고 멈추지 말 것. 구현 → 검증 → 결과 설명까지.
- 새 화면/기능은 "실기기 또는 시뮬레이터에서 동작 확인"까지가 완료.
  화면 추가 시 기존 네비게이션 구조와 디자인 토큰을 유지(Surgical Changes).

### 출력·탐색 규칙
- 탐색은 좁게: 디렉토리 전체 덤프 금지. grep/glob으로 후보 좁힌 뒤 타겟 파일만 read.
- 이번 세션에 이미 읽은 파일은 다시 읽지 않는다.
- 출력은 diff 중심. 파일 전체 재출력 / 불필요한 서론·마무리 금지.
- 완료 요약은 "뭘 바꿨는지 / 왜 / 테스트 필요 여부" 3줄 이내.

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
