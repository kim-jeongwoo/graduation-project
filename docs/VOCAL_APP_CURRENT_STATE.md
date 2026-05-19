# Vocal App Current State

작성 기준: 2026-05-19
앱 경로: `vocal-app/`
원본 작업 경로: `/Users/kimjeongwoo/vocal-app`

## 현재 상태 요약

`vocal-app`은 React Native/Expo 기반 모바일 앱이며, 보컬 연습 녹음부터 분석 결과 확인과 약점 구간 훈련까지의 핵심 흐름이 구현되어 있다.

최근 Galaxy 검증 결과:

- production API 기준 앱 진입, 로그인, 곡 목록 로드 확인
- song004 KaraokeScreen 진입, MR 재생, 가사 표시, 녹음 확인
- 완곡 업로드와 full analyze async polling 성공
- 결과 화면 이동과 히스토리 저장 정상 확인
- 구간훈련 녹음 window / `chunk_meta` 정렬 후 한 소절 정상 발성 success 확인
- 첫 음절 씹힘 해결 확인
- 연구개위치 / 혀경직도 결과 카드 점수와 피드백 표시 확인
- 혀경직도 “측정 불가” 뱃지 제거 확인
- 연구개위치 / 혀경직도 노란 별 제거 확인
- 호흡소리식별 / 성대접촉강도 기존 흐름 유지 확인
- navigation typing baseline 정리 후 TypeScript noEmit 통과 확인
- 진단 로그 정리 후 Metro 로그 과다 출력 없음
- NativeEventEmitter warning은 화면 LogBox 방해 최소화, expo-av deprecated warning은 migration backlog 유지
- 연구개위치 / 혀경직도 카드 피드백 문구 표시 정상
- V2 그래프 missing/low-confidence 색상 표시 보정 후 임시 audit 로그 제거 확인
- Settings 마이크 입력 테스트 정상 확인
- Favorites 화면 진입, 기존 목록 표시, 빈 상태 문구 확인
- Favorites v2 4항목 재진입에서 연구개/혀경직도가 성대접촉강도로 잘못 바뀌지 않음 확인
- History 화면 진입과 목록/빈 상태 확인
- SongHistory 진입과 목록/빈 상태 확인
- RecordScreen 진입, 안내 문구, Home 이동 확인
- History -> SongHistory -> EvalResult 정상 확인
- Favorites -> Training, SectionList -> TrainingScreen 정상 확인
- Karaoke `no_voice` Alert의 다시 녹음 자동 재시작 확인
- 로그인/로그아웃/재로그인 정상 확인
- 401 auth-expired 재로그인 구조 코드 반영
- 9항목 결과 카드 설명/상태 문구 표시 정상
- 빨간 LogBox 없음 확인
- 곡 004 녹음 전 pitch guide 로드 확인
- 완곡 4분 녹음/분석 성공
- 분석 결과 화면 회색 가이드라인 표시 정상
- 녹음된 실시간 피치 표시 정상
- `/songs/004/pitch-guide` 관련 빨간 LogBox 사라짐
- 과거 분석 결과 재진입 시 가이드라인 유지 확인
- Step 3G 4항목 카드/연습하기 버튼 기존 동작 유지 확인
- 목소리 입력 없이 녹음하면 결과 화면으로 이동하지 않고 안내 표시 확인
- 결과 화면 활성 4항목 평가표 기반 피드백 문구 확인
- SectionList / TrainingScreen 피드백 문구 동기화 확인
- 평가 기준 보기 문구 방향 확인
- 비활성 5항목 참고용/측정 불가 UX와 훈련 CTA 미노출 확인
- `npm run start:cf` 실행, `expo-dev.vocal-fit.com` Metro URL, `/status` 응답 확인
- 5곡 production song asset 앱 검증 완료: 004, 006, 002, 014, 007
- 004 pitch-guide cache/parser/rendering 회귀 hotfix와 GO_BACK safe navigation 확인
- 목표관리 탭 제거 확인
- 004/006 구간훈련 초록 target 끝 잘림 해결, MR/pitch-guide/초록 target 정합성 확인
- 구간훈련 사후측정 성공 확인
- 성대접촉 미달 구간에서 추천 영상 버튼/modal/재생 정상 확인
- 하압 영상은 `pressure_balance` 비활성이라 노출 보류
- `target_chunks`는 현재 vocal-app 미사용, weakSections 기반 구간추천 구조 유지

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

- Batch #1 5/5 안정화 변경
- Batch #2 5/5 안정화 변경
- Batch #3 5/5 안정화 변경
- Batch #4 5/5 피드백/평가 기준/비활성 카드/Cloudflare dev tunnel 실행 정리
- Batch #5 5/5 pitch-guide 회귀 hotfix/목표관리 탭 제거/구간훈련 timing/feedback video/target_chunks 정리
- full analyze async polling UX
- 구간훈련 녹음 window와 `chunk_meta` 정렬
- production 완곡 업로드 timeout/UX 안정화
- song004 pitch-guide 현 단계 종료 및 앱 임의 offset 제거
- 결과 카드 피드백/신뢰도 UI 정리
- navigation typing baseline cleanup
- diagnostic log cleanup and development logging policy
- SDK warning triage and limited NativeEventEmitter LogBox filtering
- 연구개위치 / 혀경직도 피드백 문구 정교화
- V2 score distribution / graph color mapping 검증 및 보정
- Settings 마이크 입력 테스트 supporting cleanup
- Favorites v2 4항목 재진입 mapping 보정
- Karaoke MR 실패 cleanup과 `no_voice` retry flow
- 401 인증 만료 재로그인 UX
- 9항목 평가표 텍스트 매핑 1차
- Favorites/History/SongHistory/Record 빈 상태와 오류 UX 정리
- Step 3G 4항목 훈련 지원 관련 변경
- full analyze status UX hardening
- pitch-guide fix
- AGENTS.md 운영 지시
- 앱 handover/current-state 문서
- 압축 피드백 영상 asset 3개: `vocal-contact-insufficient.mp4`, `vocal-contact-excessive.mp4`, `tongue-tension-excessive.mp4`

제외한 항목:

- `.git/`
- `node_modules/`
- `.expo/`
- `.env*` 실제 환경 파일
- `.claude/`
- `assets/*.png.bak`
- `.codex/ACTIVE_PLAN.md`
- raw handover docs
- 원본 300MB+ 피드백 영상
- native/generated/build 산출물

## 실행 명령

```bash
cd vocal-app
npm install
npm run start:cf
```

주요 scripts:

```json
{
  "start": "expo start --dev-client",
  "start:lan": "expo start --dev-client --lan",
  "start:tunnel": "expo start --dev-client --tunnel",
  "start:tunnel:clear": "expo start --dev-client --tunnel --clear",
  "start:cf": "./scripts/start-expo-cloudflare.sh",
  "android": "expo start --android --dev-client",
  "ios": "expo start --ios --dev-client"
}
```

개인 LAN IP가 박힌 script는 GitHub snapshot에 포함하지 않았다.

## 검증 상태

| 항목 | 상태 |
|---|---|
| production login/song list | 검증 완료 |
| Galaxy dev-client 완곡 녹음/분석 | 검증 완료 |
| full analyze async polling | 검증 완료 |
| 구간훈련 window / chunk_meta 정렬 | 검증 완료 |
| 결과 카드 feedback / 신뢰도 UI | 검증 완료 |
| pitch guide 로드/재진입 유지 | 검증 완료 |
| no_voice 결과 화면 이동 차단 | 검증 완료 |
| no_voice Alert 다시 녹음 retry | 검증 완료 |
| Step 3G 4항목 버튼 기존 동작 | 검증 완료 |
| Favorites/History/SongHistory/Record 빈 상태/오류 UX | 검증 완료 |
| 401 auth-expired 재로그인 UX | 코드 반영 및 앱 흐름 확인 |
| 9항목 결과 카드 설명/상태 문구 | 검증 완료 |
| Batch #4 결과/구간훈련/평가 기준 문구 | 검증 완료 |
| 비활성 5항목 참고용/측정 불가 UX | 검증 완료 |
| Cloudflare dev tunnel `start:cf` | 검증 완료 |
| Batch #5 pitch-guide/timing/feedback video/target_chunks 정리 | 검증 완료 |
| 5곡 production song asset 앱 검증 | 검증 완료 |
| `node_modules/.bin/tsc --noEmit` | source repo 기준 통과 |

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

- 외부 공유 전에는 API URL과 서버 상태를 production 기준으로 다시 확인해야 한다.
- 연구개/혀경직도 미달/과함 분포는 의도 녹음과 dml-server score_mapper 검증이 추가로 필요하다.
- 개인화 calibration, 성별/음역대 기준, 노래별 key 조절은 아직 본기능이 아니다.

## 남은 backlog

| 항목 | 분류 | 완료 기준 |
|---|---|---|
| 대표님 피드백 반영 후 문구 수정 | 앱 UX/평가표 | 최종 피드백 기준 copy 재검토 |
| 연구개/혀경직도 미달/과함 의도 녹음 검증 | 앱/DML | 의도 녹음으로 score_mapper 분포 확인 |
| dml-server score_mapper 분포 검증 | DML | 연구개/혀경직도 2~3 쏠림 여부 검토 |
| target_chunks 서버 schema/endpoint/app 전환 여부 검토 | 앱/서버 계약 | 서버 production 반영과 앱 전환 기준 확정 |
| pressure_balance 활성화 여부와 하압 영상 노출 여부 결정 | 앱/DML/UX | 비활성 항목 활성화 결정 후 노출 |
| 공개 데이터/성별/음역대 기반 개인화 calibration | 앱/DML | 입력 테스트와 분리해 별도 설계 |
| 회원가입/설정 음역대 입력 | 앱 UX | 사용자 range 기반 설정 저장 |
| 노래별 key 자동 조절 및 원키 선택 | 앱/asset | 사용자 음역대와 곡 key 매칭 |
| expo-av -> expo-audio migration | 앱 코드 정리 | Expo SDK 변화에 맞춰 대체 API 검토 |
| NativeEventEmitter root cause library replacement or native patch | 앱 코드 정리 | 원인 모듈 확인 후 warning 제거 |
| production server auto-start/systemd 운영 정리 | 운영 | 서버 재시작/부팅 자동화 확인 |

## 문서 보존/제외 정책

GitHub snapshot에는 안전한 개발 문서만 포함한다. Raw handover/current-state scratch 문서는 source checkout에는 남을 수 있지만 PR snapshot에서는 제외한다.

- 포함: `vocal-app/docs/dev-flow.md`, `vocal-app/docs/android-install.md`, `vocal-app/docs/V2_CLOSEOUT_CHECKLIST.md`
- 제외: `vocal-app/docs/CURRENT_STATE_v1.md`, `vocal-app/docs/HANDOVER.md`, `.codex/ACTIVE_PLAN.md`
