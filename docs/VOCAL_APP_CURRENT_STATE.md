# Vocal App Current State

작성 기준: 2026-05-13
앱 경로: `vocal-app/`
원본 작업 경로: `/Users/kimjeongwoo/vocal-app`

## 현재 상태 요약

`vocal-app`은 React Native/Expo 기반 모바일 앱이며, 보컬 연습 녹음부터 분석 결과 확인과 약점 구간 훈련까지의 핵심 흐름이 구현되어 있다.

최근 Galaxy 검증 결과:

- 곡 004 녹음 전 pitch guide 로드 확인
- 완곡 4분 녹음/분석 성공
- 분석 결과 화면 회색 가이드라인 표시 정상
- 녹음된 실시간 피치 표시 정상
- `/songs/004/pitch-guide` 관련 빨간 LogBox 사라짐
- 과거 분석 결과 재진입 시 가이드라인 유지 확인
- Step 3G 4항목 카드/연습하기 버튼 기존 동작 유지 확인
- 목소리 입력 없이 녹음하면 결과 화면으로 이동하지 않고 안내 표시 확인

## 기술 스택

| 영역 | 기술 |
|---|---|
| Framework | React Native 0.81 / Expo SDK 54 |
| Language | TypeScript 5.9 |
| Navigation | React Navigation v7 |
| HTTP/Auth | Axios, expo-secure-store |
| Audio/Pitch | expo-av, react-native-audio-record, react-native-pitchy |
| Chart | react-native-svg |

## 주요 구현 파일

| 경로 | 역할 |
|---|---|
| `src/api/client.ts` | Axios client, JWT, API error logging |
| `src/api/sessions.ts` | session 생성/업로드/analyze/training-analyze |
| `src/api/songs.ts` | songs, MR, LRC, pitch guide |
| `src/api/analyze.ts` | server result adapter |
| `src/screens/karaoke/KaraokeScreen.tsx` | 노래방 녹음/분석 시작 |
| `src/screens/home/EvalResultScreen.tsx` | 분석 결과 화면 |
| `src/screens/home/SectionListScreen.tsx` | 약점 구간 리스트 |
| `src/screens/home/TrainingScreen.tsx` | 약점 구간 연습/사후 측정 |
| `src/domain/weakSections.ts` | 약점 구간 추출 |
| `src/types/analyze.ts` | 분석 결과 타입 |

## 현재 포함된 변경 범위

이번 monorepo snapshot에는 현재 local `vocal-app` working tree 상태를 반영했다. 포함 성격:

- Step 3G 4항목 훈련 지원 관련 변경
- full analyze status UX hardening
- pitch-guide fix
- AGENTS.md 운영 지시
- 앱 handover/current-state 문서

제외한 항목:

- `.git/`
- `node_modules/`
- `.expo/`
- `.env*` 실제 환경 파일
- `.claude/`
- `assets/*.png.bak`
- native/generated/build 산출물

## 실행 명령

```bash
cd vocal-app
npm install
npm run start:tunnel
```

주요 scripts:

```json
{
  "start": "expo start --dev-client",
  "start:lan": "expo start --dev-client --lan",
  "start:tunnel": "expo start --dev-client --tunnel",
  "android": "expo start --android --dev-client",
  "ios": "expo start --ios --dev-client"
}
```

개인 LAN IP가 박힌 script 변경은 commit 대상에서 제외했다.

## 검증 상태

| 항목 | 상태 |
|---|---|
| Galaxy dev-client 완곡 녹음/분석 | 검증 완료 |
| pitch guide 로드/재진입 유지 | 검증 완료 |
| no_voice 결과 화면 이동 차단 | 검증 완료 |
| Step 3G 4항목 버튼 기존 동작 | 검증 완료 |
| `npx tsc --noEmit` | 기존 navigation typing baseline 오류로 실패 가능 |

### 2026-05-13 Galaxy 검증 조건

| 항목 | 값 |
|---|---|
| 실행 방식 | tunnel dev-client |
| 테스트 곡 | `004` |
| 녹음 길이 | 약 4분 완곡 |
| 확인 화면 | Karaoke, EvalResult, 과거 분석 결과 재진입, Training 진입 |
| 서버/API | 개발 검증은 local/tunnel 조합, 외부 검증 전 production 전환 예정 |

검증 완료 기준:

- 녹음 전 pitch guide가 로드된다.
- 완곡 녹음 후 분석이 성공한다.
- 결과 화면에서 회색 가이드라인과 사용자 실시간 피치가 함께 표시된다.
- 과거 분석 결과 재진입 후에도 가이드라인이 유지된다.
- 목소리 입력이 없을 때 결과 화면으로 이동하지 않고 안내가 표시된다.

### 알려진 검증 한계

- `npx tsc --noEmit`은 기존 navigation typing 오류가 있어 현재 snapshot 품질을 단독으로 판단하는 기준으로 쓰기 어렵다.
- `혀, 구강 공간의 경직도` 훈련 화면 내용과 재시작 버튼 문제는 아직 해결되지 않은 backlog다.
- 외부 공유 전에는 API URL과 서버 상태를 production 기준으로 다시 확인해야 한다.

## 남은 backlog

| 항목 | 분류 | 완료 기준 |
|---|---|---|
| `혀, 구강 공간의 경직도` 연습 화면 내용이 비어 있음 | 앱 UX | 훈련 화면에 항목별 안내/피드백 표시 |
| 녹음 구간에서 재시작 버튼 확인 후 녹음이 다시 시작되지 않음 | 앱 버그 | 재시작 확인 후 녹음 flow 재개 |
| 외부 검증 전 API URL을 `https://api.vocal-fit.com`으로 전환 | 운영 검증 필요 | login/record/analyze/result production smoke test |
| 진단 로그 제거 시점 결정 | 운영/개발 정책 | 검증 완료 후 제거 또는 유지 범위 결정 |
| navigation typing baseline 오류 정리 여부 결정 | 앱 코드 정리 | baseline 오류 목록과 신규 오류 구분 |

## 보존 문서

- `vocal-app/docs/CURRENT_STATE_v1.md`: 2026-05-10 v1 baseline
- `vocal-app/docs/HANDOVER.md`: GPT 이관/진행 상태 문서
- `vocal-app/docs/dev-flow.md`: Galaxy dev-client 개발 흐름
- `vocal-app/docs/android-install.md`: Android 설치 가이드
