# vocal-app 실제 코드 기반 검증 보고서

작성일: 2026-06-16  
대상 repo: `/Users/kimjeongwoo/vocal-app`  
작업 범위: 실제 로컬 repo read-only 검증 결과를 최종 설계서용으로 정리  
주의: 이 문서는 코드 내용을 설명하기 위한 보고서이며, 기능 코드는 수정하지 않았다.

---

## 0. 결론 요약

`vocal-app`은 Expo SDK 54 / React Native 0.81 기반의 보컬 분석 모바일 앱이다. 현재 코드 기준 핵심 사용자 흐름은 인증 후 Home에서 곡을 선택하고, `KaraokeScreen`에서 MR 재생과 녹음을 진행한 뒤, 서버 분석 완료를 polling하고 `EvalResultScreen`으로 이동하는 구조다. 분석 결과에서는 v2 기준 4개 활성 항목, 즉 호흡 소리 식별, 성대 접촉 강도, 연구개 위치, 혀/구강 공간 경직도를 기본 탭에 표시하고, 나머지 5개 항목은 고급 탭의 참고/비활성 카드로 표시한다.

가장 중요한 정정사항은 세 가지다.

1. 현재 네비게이션에 `GoalsTab`은 없다. `GoalsScreen.tsx` 파일은 존재하지만 `AppNavigator`에는 Home, 분석 결과, 히스토리 3개 탭만 등록되어 있다.
2. 약점 구간은 서버의 `target_chunks`를 쓰지 않는다. 앱이 `timelineScores`를 받아 `src/domain/weakSections.ts`의 `extractWeakSections()`로 직접 추출한다.
3. `KaraokeScreen` 분석 흐름은 단순히 `startAnalysis` 후 바로 결과로 가는 구조가 아니다. `startAnalysis()`로 `run_id`를 받고 `pollAnalysisStatus(run_id)`로 terminal 상태까지 기다린 뒤 결과 화면으로 이동한다.

---

## 1. 확인한 파일과 현재 repo 상태

### 1.1 먼저 확인한 지시문/문서

확인한 파일:

- `AGENTS.md`
- `CLAUDE.md`
- `package.json`
- `app.json`
- `eas.json`
- `.env.example`
- `docs/CURRENT_STATE_v1.md`
- `docs/HANDOVER.md`
- `docs/V2_CLOSEOUT_CHECKLIST.md`
- `docs/dev-flow.md`
- `docs/android-install.md`
- `src/navigation`
- `src/screens`
- `src/components`
- `src/context`
- `src/services/audio`
- `src/api`
- `src/domain`
- `assets/feedback-videos`

확인 결과:

- 루트 `README.md`는 현재 repo에 없다.
- `GPT_NOTES.md`는 현재 repo에 없다.
- `vocal-app gpt.ai.md`는 현재 repo 안에서 찾지 못했다. 따라서 해당 문서의 문장 단위 대조는 하지 못했고, 실제 코드 기준으로 최종 설계서에 반영해야 할 정정/보강사항을 정리했다.

### 1.2 작업 당시 git 상태

작업 시작 시점부터 이미 큰 dirty worktree였다. 이번 검증 과정에서는 코드, 설정, 문서 파일을 수정하지 않았고 read-only 명령만 실행했다. 이후 정우 요청으로 이 보고서 파일만 새로 추가했다.

조사 시점 `git diff --stat` 요약:

```text
46 files changed, 3794 insertions(+), 833 deletions(-)
```

조사 시점 branch:

```text
master
```

주의:

- 위 dirty diff는 이번 검증 작업에서 만든 변경이 아니다.
- 이번에 새로 추가한 파일은 이 보고서 `docs/VOCAL_APP_CODE_VERIFICATION_2026-06-16.md` 하나다.

---

## 2. package / app / EAS 설정

### 2.1 `package.json`

파일: `package.json`

주요 버전:

| 항목 | 실제 값 |
|---|---|
| app name | `vocal-app` |
| version | `1.0.0` |
| main | `index.ts` |
| Expo | `~54.0.33` |
| React Native | `0.81.5` |
| React | `19.1.0` |
| TypeScript | `~5.9.2` |
| React Navigation bottom tabs | `^7.15.2` |
| React Navigation native | `^7.1.31` |
| React Navigation native stack | `^7.14.2` |
| axios | `^1.13.6` |

실제 오디오/파일 관련 dependency:

| dependency | 실제 버전 | 용도 |
|---|---:|---|
| `expo-av` | `~16.0.8` | MR/audio playback, Video, permission API |
| `expo-file-system` | `~19.0.22` | MR cache, captured WAV write |
| `react-native-audio-record` | `^0.2.2` | Android AudioRecord 기반 PCM/WAV 녹음 |
| `react-native-pitchy` | `^1.2.0` | package에 존재하지만 현재 핵심 pitch detect는 `pitchfinder` YIN 사용 |
| `pitchfinder` | `^2.3.4` | local pitch detection |

실제 scripts:

```json
{
  "start": "expo start --dev-client",
  "start:lan": "expo start --dev-client --lan",
  "start:tunnel": "expo start --dev-client --tunnel",
  "start:tunnel:clear": "expo start --dev-client --tunnel --clear",
  "start:cf": "./scripts/start-expo-cloudflare.sh",
  "start:go": "expo start",
  "android": "expo start --android --dev-client",
  "ios": "expo start --ios --dev-client",
  "web": "expo start --web"
}
```

주의:

- `npm run typecheck`, `npm run lint`, `npm test` script는 없다.
- AGENTS 기준 알려진 타입 체크 명령은 `npx tsc --noEmit`이다.

### 2.2 `app.json`

파일: `app.json`

주요 설정:

| 항목 | 실제 값 |
|---|---|
| Expo name/slug/scheme | `vocal-app` |
| version | `1.0.0` |
| orientation | `portrait` |
| `newArchEnabled` | `true` |
| iOS bundle id | `com.vocal.app` |
| Android package | `com.vocal.app` |
| Android versionCode | `1` |
| Android `usesCleartextTraffic` | `false` |
| Android `edgeToEdgeEnabled` | `true` |
| Android `predictiveBackGestureEnabled` | `false` |
| owner | `kingjeongwoo` |
| EAS projectId | `e99f776b-a56b-454c-97b3-dd7a37287b4b` |

Android permissions:

```json
["RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS", "INTERNET"]
```

Plugins:

```json
["expo-secure-store", "expo-dev-client"]
```

### 2.3 `eas.json`

파일: `eas.json`

실제 build profiles:

| profile | environment | distribution | Android output |
|---|---|---|---|
| `development` | `development` | `internal` | APK, dev client |
| `preview` | `preview` | `internal` | APK |
| `production` | `production` | not specified | app-bundle |

실제 설정:

- `development.android.buildType = "apk"`
- `preview.android.buildType = "apk"`
- `production.android.buildType = "app-bundle"`
- `submit` profile은 없다.

### 2.4 `.env.example`

파일: `.env.example`

문서화된 public env:

```text
EXPO_PUBLIC_API_URL=https://api.vocal-fit.com
EXPO_PUBLIC_USE_MOCK=false
EXPO_PUBLIC_ENABLE_SPEECH_WEB=false
```

중요 설명:

- EAS remote build는 로컬 `.env`가 아니라 Expo dashboard/EAS env에 설정된 값을 사용한다고 주석에 명시되어 있다.
- `EXPO_PUBLIC_ENABLE_SPEECH_WEB=true`일 때만 Home에 스피치 평가 웹 버튼이 표시된다.
- 학원 배포용/상용화 빌드는 speech web flag를 `false`로 둔다.

---

## 3. 실제 화면과 파일 트리

### 3.1 실제 `src/screens` 파일 목록

```text
src/screens/auth/LoginScreen.tsx
src/screens/auth/SignupScreen.tsx
src/screens/goals/GoalsScreen.tsx
src/screens/history/FavoritesScreen.tsx
src/screens/history/HistoryDetailScreen.tsx
src/screens/history/HistoryScreen.tsx
src/screens/history/SongHistoryScreen.tsx
src/screens/home/AnalysisResultScreen.tsx
src/screens/home/EvalResultScreen.tsx
src/screens/home/HomeScreen.tsx
src/screens/home/SectionListScreen.tsx
src/screens/home/SessionDetailScreen.tsx
src/screens/home/SongComparisonScreen.tsx
src/screens/home/SongDetailScreen.tsx
src/screens/home/TrainingScreen.tsx
src/screens/karaoke/KaraokeScreen.tsx
src/screens/onboarding/VocalRangeTestScreen.tsx
src/screens/record/RecordScreen.tsx
src/screens/settings/ProfileScreen.tsx
src/screens/settings/SettingsScreen.tsx
```

설계서 반영 포인트:

- `GoalsScreen.tsx` 파일은 존재한다.
- 하지만 현재 `AppNavigator`에는 `GoalsTab`이 없다. 최종 설계서에서 현재 실제 탭으로 쓰면 안 된다.

### 3.2 주요 component/domain/context/service 파일

네비게이션:

```text
src/navigation/AppNavigator.tsx
src/navigation/types.ts
src/components/navigation/MainTopTabs.tsx
```

평가 결과 컴포넌트:

```text
src/components/eval/EvalItemCard.tsx
src/components/eval/ScoreGauge.tsx
src/components/eval/ConfidenceBadge.tsx
src/components/eval/TierBadge.tsx
```

훈련 컴포넌트:

```text
src/components/training/SectionPitchGraph.tsx
src/components/training/RealtimeFeedback.tsx
src/components/training/ResultCard.tsx
```

context:

```text
src/context/AuthContext.tsx
src/context/FavoritesContext.tsx
src/context/GoalsContext.tsx
src/context/VocalProfileContext.tsx
```

audio services:

```text
src/services/audio/audioMode.ts
src/services/audio/microphone.ts
src/services/audio/pitchDetector.ts
src/services/audio/recorder.ts
```

domain:

```text
src/domain/evaluationItems.ts
src/domain/feedbackVideos.ts
src/domain/weakSections.ts
```

feedback video assets:

```text
assets/feedback-videos/tongue-tension-excessive.mp4
assets/feedback-videos/vocal-contact-excessive.mp4
assets/feedback-videos/vocal-contact-insufficient.mp4
```

---

## 4. Navigation 구조

### 4.1 실제 AppNavigator 구조

파일: `src/navigation/AppNavigator.tsx`

Root flow:

```text
AppNavigator
└─ NavigationContainer
   ├─ AuthNavigator, token 없을 때
   │  ├─ Login
   │  └─ Signup
   └─ AppRootNavigator, token 있을 때
      ├─ MainTabs
      └─ Karaoke, fullScreenModal
```

AppRootStack:

```text
AppRootStack
├─ MainTabs
└─ Karaoke
```

Bottom tabs:

```text
MainTabNavigator
├─ HomeTab
├─ RecordTab
└─ HistoryTab
```

중요:

- `tabBarStyle: { display: 'none' }`라서 기본 bottom tab bar는 숨겨져 있다.
- 실제 화면 상단에서 쓰는 tab UI는 `MainTopTabs`다.
- 현재 `GoalsTab`은 등록되어 있지 않다.

### 4.2 HomeStack

파일: `src/navigation/AppNavigator.tsx`

HomeStack screens:

```text
Home
SessionDetail
AnalysisResult
Settings
Profile
VocalRangeTest
SongComparison
SongDetail
EvalResult
SectionList
Training
```

### 4.3 ResultStack

ResultStack screens:

```text
LatestAnalysis
EvalResult
SectionList
Training
```

`LatestAnalysis` component는 `RecordScreen`이다.

### 4.4 HistoryStack

HistoryStack screens:

```text
HistoryList
HistoryDetail
SongHistory
Favorites
Training
EvalResult
SectionList
SongComparison
```

### 4.5 MainTopTabs

파일: `src/components/navigation/MainTopTabs.tsx`

실제 top tab:

```text
HomeTab: 홈
RecordTab: 분석 결과
HistoryTab: 히스토리
```

동작:

- HomeTab 클릭: `HomeTab`의 `Home`으로 이동
- RecordTab 클릭: `RecordTab`의 `LatestAnalysis`로 이동
- HistoryTab 클릭: `HistoryTab`의 `HistoryList`로 이동

---

## 5. HomeScreen 구조와 speech web demo-only flag

파일: `src/screens/home/HomeScreen.tsx`

### 5.1 화면 구조

HomeScreen은 다음 순서로 렌더링한다.

```text
container
├─ header
│  ├─ greeting / nickname
│  └─ settings button
├─ MainTopTabs activeTab="HomeTab"
├─ speechCard, flag true일 때만
└─ songs FlatList
```

곡 목록:

- `useEffect`에서 mount 시 `getSongs()` 1회 호출
- `GET /songs`는 정적 14곡 데이터라는 주석이 있으며, focus마다 재호출하지 않는다.
- 곡 card 클릭 시 `SongDetail`로 이동한다.

### 5.2 speech web flag

실제 코드:

```ts
const SPEECH_WEB_URL = 'https://speech.vocal-fit.com';
const showSpeechWeb = process.env.EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true';
```

동작:

- `EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true'`일 때만 스피치 평가 카드 표시
- 버튼 클릭 시 `Linking.canOpenURL()` 확인 후 `Linking.openURL('https://speech.vocal-fit.com')`
- 실패 시 Alert:
  - 제목: `스피치 평가를 열 수 없습니다`
  - 본문: `네트워크 상태를 확인한 뒤 다시 시도해 주세요.`

설계서 정정:

- speech web은 앱 기본 기능으로 항상 표시되는 것이 아니다.
- 졸업작품 시연용 demo-only flag 기능이다.
- 학원 배포용/상용화 빌드에서는 `.env.example` 기준 false다.

---

## 6. KaraokeScreen 구조

파일: `src/screens/karaoke/KaraokeScreen.tsx`

### 6.1 주요 역할

`KaraokeScreen`은 곡별 MR을 재생하고 사용자의 보컬을 녹음하며, 실시간 pitch graph를 표시하고, 종료 후 full-song analysis를 시작한다.

핵심 상태:

- `loading`
- `countdown`
- `lyrics`
- `pitchGuide`
- `pitchGuideStatus`
- `userPitch`
- `currentTime`
- `playing`
- `paused`
- `resumeCountdown`
- `isAnalyzing`
- `analyzeStep`

핵심 ref:

- `soundRef`: `Audio.Sound`
- `recorderRef`: `VocalRecorder`
- `currentTimeRef`
- `playingRef`
- `pausedRef`
- `isAnalyzingRef`
- stale navigation/analyze attempt guard refs

### 6.2 데이터 로드

초기 진입 시:

1. `requestMicrophonePermission()`으로 마이크 권한 확인
2. `getSongKaraokeLyricsOnly(songId)`로 LRC 먼저 로드
3. countdown 시작
4. background로 `getSongKaraokeData(songId)` 호출
5. pitch guide 성공 시 LRC offset 반영 및 pitch guide 표시
6. pitch guide 실패 시 MR/녹음은 계속 가능

특수 처리:

- `songId === '004'`일 때 `clearSongPitchGuideCache(songId)` 실행

### 6.3 MR cache 구조

MR URL:

```ts
getSongMrUrl(songId) => `${BASE_URL}/songs/${songId}/mr`
```

cache key:

- `FileSystem.cacheDirectory`
- safe song id
- `hashForCacheKey(mrUrl)`

cache URI 형식:

```text
{cacheDirectory}/mr-{safeSongId}-{hash}.mp3
```

cache 검증:

- `MR_CACHE_MIN_BYTES = 1024`
- 파일 존재 및 size가 최소값 이상이면 local cache 사용
- cache가 깨졌거나 load 실패하면 삭제 후 재다운로드
- 재다운로드 후에도 실패하면 remote URL 직접 load fallback

Authorization:

- remote download/load 시 token이 있으면 `Authorization: Bearer {token}` header 사용
- local cache load에는 header 필요 없음

### 6.4 MR + recorder start order

`startMrAndRecord()` 흐름:

1. mock이 아니면 마이크 권한 재확인
2. `prepareMrSound()`로 MR sound 준비
3. mock이 아니면 `recorderRef.current.start(..., { capturePcm: true })`
4. `sound.playFromPositionAsync(0)`

의미:

- MR load가 성공한 뒤 recorder를 시작한다.
- 녹음은 `capturePcm: true`로 시작되므로 pause/resume이 있는 경우 segment concat WAV 생성 가능하다.

### 6.5 pause/resume 구조

pause:

1. `sound.pauseAsync()`
2. `recorderRef.current.pause()`
3. `pausedRef.current = true`
4. UI `paused = true`

resume:

1. 3초 resume countdown
2. `recorderRef.current.resumeRecording(...)`
3. `sound.playAsync()`
4. pause state 해제

녹음 segment 처리:

- `VocalRecorder.pause()`가 AudioRecord를 stop하고 `pausedSegmentCount` 증가
- `resumeRecording()`은 `resetCapture: false`로 이어서 PCM capture
- 최종 `stop()` 때 pause segment가 있으면 captured PCM을 하나의 WAV로 새로 작성

### 6.6 종료 후 분석 흐름

`handleStop()` 실제 흐름:

```text
recorder.stop()
→ createSession({ song_id: songId })
→ uploadSessionFile(session_id, wav uri, fileName, mimeType)
→ startAnalysis(session_id)
→ pollAnalysisStatus(run_id)
→ goToEvalResult(run_id)
```

중요 정정:

- `startAnalysis()`만 호출하고 바로 결과로 가는 구조가 아니다.
- `pollAnalysisStatus(run_id)`가 성공 terminal 상태를 확인한다.
- polling timeout은 `src/api/analysis.ts` 기준 10분이다.

분석 overlay:

```text
0: 녹음 업로드 중...
1: 분석 요청 접수 중...
2: AI 분석 중...
3: 결과 정리 중...
```

분석 실패 처리:

- `no_voice` / `invalid`: 다시 녹음 유도
- `failed` / `error`: 분석 실패 Alert
- `AnalysisPollingTimeoutError`: 히스토리에서 결과 확인 안내
- auth expired는 별도 401 처리 경로에 맡김

### 6.7 피치 그래프

PitchGraph:

- window 방식
  - 이전 3초
  - 이후 5초
- cursor X 고정
- guide는 MIDI 직선 또는 CREPE curve
- user pitch는 `pitchfinder` YIN 기반 local pitch detection
- 색상:
  - 정확: `#59dda5`
  - 살짝 어긋남: `#ffb780`
  - 틀림: `#ffb4ab`

---

## 7. EvalResultScreen 구조

파일: `src/screens/home/EvalResultScreen.tsx`

### 7.1 데이터 로드

초기 load:

```text
getResultsByRunId(runId)
→ setResult(data)
```

`songId`가 있으면:

```text
getSongMidiSegmentsOptional(songId, 'eval')
→ midiSegs / lrcOffsetSec 설정
```

`getResultsByRunId()`는 mock mode 또는 runId 부재 시 `MOCK_FIXED_RESULT`를 반환하고, 실제 runId가 있으면:

```text
pollAnalysisStatus(runId)
→ getAnalysisResults(runId)
→ adaptServerResult(raw)
```

### 7.2 v2 기본/고급 탭 구조

v2 여부:

```ts
const isV2 = result.scoreMapperVersion === 'v2';
```

v2 기본 탭:

```ts
const BASIC_V2 = [
  'breathiness',
  'vocal_fold_contact',
  'soft_palate',
  'tongue_tension',
];
```

v2 고급 탭:

```ts
const ADVANCED_V2 = [
  'nasal_oral_ratio',
  'chest_head_voice',
  'forward_resonance',
  'pressure_balance',
  'larynx_tongue_root',
];
```

설계서 정정:

- v2 기준 활성 기본 항목은 4개다.
- 과거 문서의 “호흡/접촉 2개 활성” 설명은 v1 기준이므로 최신 설계서에는 그대로 쓰면 안 된다.

### 7.3 활성/비활성 판단

활성 item list:

```ts
const shownStripped =
  result.scoreMapperVersion === 'v2' && result.reliability.shownV2
    ? result.reliability.shownV2
    : result.timelineMetadata?.shownIndicators.map(stripPrefix)
```

비활성 카드 조건:

- `!isShown`
- 또는 `academicOnlyV2`
- 또는 `deferredV2`

비활성 카드 처리:

- score null
- zone null
- feedback은 참고용/측정불가 문구로 대체
- score gauge label:
  - `현재 측정 불가`
  - 또는 `참고용 항목`
- v2 비활성 카드는 `isDimmed`로 opacity 0.55
- train button 자체는 `onTrainPress={undefined}`라 표시되지 않는다.

### 7.4 score source

v2 score:

1. `scoresMeta[key].roundedScore` 우선
2. 없으면 `scoresV2[key]`

legacy score:

- `result.scores[key].ai_score`

v2 zone:

- `roundedScore <= 1`: `insufficient`
- `roundedScore >= 4`: `excessive`
- 나머지: `appropriate`

### 7.5 tier badge

파일:

- `src/components/eval/TierBadge.tsx`
- `src/components/eval/EvalItemCard.tsx`

동작:

- `tier === 'high_star'`면 `*` 표시
- tap 시 tooltip이 있으면 Alert
- `soft_palate`, `tongue_tension`은 `HIDE_HIGH_STAR_ITEMS`에 들어 있어 `high_star`를 `high`처럼 숨긴다.

### 7.6 highlighted/dimmed

`EvalItemCard` props:

- `isHighlighted`
- `isDimmed`

현재 highlight:

```ts
isHighlighted={key === 'vocal_fold_contact' && result.scoreMapperVersion === 'v2'}
```

주의:

- 과거 `HANDOVER.md`에는 호흡 카드 강조로 설명된 부분이 있으나, 최신 코드 기준 highlight 대상은 `vocal_fold_contact`다.

### 7.7 timeline visualization mode

mode:

```text
pitch
breathiness
vocalFoldContact
softPalate
tongueTension
```

v2 only mode:

- `softPalate`
- `tongueTension`

기타 inactive mode button도 존재하지만 disabled:

- nasal
- register
- resonance
- larynx
- pressure

timeline 색상 기준:

- pitch mode:
  - 정확: `#59dda5`
  - 살짝 어긋남: `#ffb780`
  - 틀림: `#ffb4ab`
  - 가이드 없음: `#7ecfff`
- indicator mode:
  - 적절: `#59dda5`
  - 미달/과함: `#ffb4ab`
  - 신뢰도 낮음: `#9ca3af`
  - 데이터 없음: `#6b7280`

### 7.8 음정/박자 점수 카드

EvalResult에는 별도 음정/박자 점수 카드가 있다.

데이터 source:

- `userF0`
- `midiSegs`

음정 정확도:

- voiced frame 중 nearest midi와 1.0 semitone 이내인 비율

박자 정확도:

- 각 midi segment start 주변 ±0.3s 내 voiced 여부

설계서 포인트:

- 이 점수는 서버 score_mapper v2 4항목과 별개의 client 계산 카드다.

---

## 8. weakSections와 SectionList 구조

파일:

- `src/domain/weakSections.ts`
- `src/screens/home/SectionListScreen.tsx`

### 8.1 지원 indicator

`IndicatorAppKey`:

```ts
type IndicatorAppKey =
  | 'breathiness'
  | 'vocal_fold_contact'
  | 'soft_palate'
  | 'tongue_tension';
```

timeline score field mapping:

| app key | timeline field |
|---|---|
| `breathiness` | `breathiness` |
| `vocal_fold_contact` | `vocalFoldContact` |
| `soft_palate` | `softPalate` |
| `tongue_tension` | `tongueTension` |

### 8.2 extractWeakSections

함수:

```ts
extractWeakSections(timelineScores, key, totalDurationSec?)
```

실제 로직:

1. app key를 timeline field로 변환
2. 각 chunk에서 해당 entry 확인
3. `roundedScore`가 없으면 skip
4. `roundedScore`로 zone 유도
   - 0~1: insufficient
   - 2~3: appropriate
   - 4~5: excessive
5. `appropriate`이면 skip
6. 앞 4초, 뒤 3초 padding
7. `totalDurationSec`가 있으면 뒤 padding을 duration으로 clamp
8. sortWeakSections로 정렬

padding:

```ts
paddedStartSec = max(0, startSec - 4)
paddedEndSec = min(totalDurationSec ?? Infinity, endSec + 3)
```

정렬:

- excessive 먼저
- excessive는 aiScore 큰 순
- insufficient는 aiScore 작은 순

### 8.3 target_chunks 미사용

repo 검색 기준 `target_chunks` 또는 `targetChunks` 소비 코드는 확인되지 않았다. 최신 설계서에는 다음처럼 써야 한다.

```text
서버가 weak section list를 별도 target_chunks로 내려주는 구조가 아니라,
앱이 analysis result의 timeline_scores를 받아 활성 indicator별 약점 구간을 직접 추출한다.
```

### 8.4 WeakSection 타입

```ts
interface WeakSection {
  chunkIndex: number;
  paddedStartSec: number;
  paddedEndSec: number;
  startSec: number;
  endSec: number;
  lrcText: string;
  aiScore: number;
  zone: Zone;
  lowConfidenceItems?: string[];
}
```

---

## 9. TrainingScreen 구조

파일: `src/screens/home/TrainingScreen.tsx`

### 9.1 지원 indicator와 server key mapping

```ts
const SERVER_INDICATOR_KEY = {
  breathiness: '4_breathiness',
  vocal_fold_contact: '3_vocal_fold_contact',
  soft_palate: '6_soft_palate',
  tongue_tension: '8_tongue_tension',
};
```

설계서 정정:

- TrainingScreen은 최신 코드 기준 4개 indicator 진입을 모두 지원한다.
- 다만 실시간 indicator card는 항목별로 다르다.

### 9.2 연습 구간 계산

route params:

- `sectionStartSec`: padded master time
- `sectionEndSec`: padded master time
- `chunkInfo.startSec/endSec`: 원본 chunk master time
- `scoreInfo`
- `lowConfidenceItems`

계산:

```ts
trainingSectionEndSec = max(sectionStartSec, sectionEndSec - 1)
trainingChunkStartSec = chunkInfo.startSec
trainingChunkEndSec = max(trainingChunkStartSec, chunkInfo.endSec)
recordingStartSec = max(sectionStartSec, trainingChunkStartSec - 1)
recordingEndSec = min(trainingSectionEndSec, trainingChunkEndSec + 0.35)
```

상수:

- `SECTION_END_TRIM_SEC = 1`
- `RECORDING_PRE_ROLL_SEC = 1`
- `RECORDING_POST_ROLL_SEC = 0.35`
- `MIN_TRAINING_ANALYZE_SEC = 3`

### 9.3 audio focus / audio mode

TrainingScreen은 다음 helper를 사용한다.

파일: `src/services/audio/audioMode.ts`

- `waitForAppActive()`
- `prepareAudioForRecordAndPlayback()`
- `prepareAudioForPlaybackOnly()`
- `isAudioStartBlockedError()`
- `isAudioFocusNotAcquiredError()`

MR/record 시작 전:

- screen focus 확인
- AppState active 확인
- record+playback audio mode 준비

feedback video 재생 전:

- playback-only audio mode 준비

### 9.4 WebSocket 실시간 분석

파일:

- `src/screens/home/TrainingScreen.tsx`
- `src/api/dmlClient.ts`

WebSocket URL:

```text
wss://dml.vocal-fit.com/ws/realtime?song_id={songId}
```

env override:

```ts
EXPO_PUBLIC_DML_WS_URL
```

openWs 흐름:

1. `new WebSocket(url)`
2. `ws.binaryType = 'arraybuffer'`
3. 3초 connect timeout
4. onopen 시 meta 전송

meta:

```json
{
  "type": "meta",
  "sample_rate": 16000,
  "start_timestamp": recordingStartSec
}
```

PCM 송신:

- recorder callback의 Float32 samples를 buffer에 누적
- 3200 samples 단위로 전송
- 16kHz 기준 3200 samples는 200ms
- Int16 LE buffer로 변환해 WebSocket binary send

수신 메시지:

- `pitch_match`
  - `user_midi` 없으면 noVoice
  - `match_score`로 verdict 계산
  - 최근 5프레임 다수결
- `breathiness_chunk`
  - `zone`
  - `ai_score`

### 9.5 실시간 feedback card

파일: `src/components/training/RealtimeFeedback.tsx`

항상 표시:

- `VoiceInputCard`
- `PitchCard`

indicator별 card:

| indicator | card |
|---|---|
| `breathiness` | `BreathCard` |
| `vocal_fold_contact` | `BreathInfoCard` |
| `soft_palate` | `SoftPalateInfoCard` |
| `tongue_tension` | `TongueTensionInfoCard` |

의미:

- 호흡은 WebSocket `breathiness_chunk`로 실시간 zone/score 표시
- 접촉/연구개/혀는 사후 측정 안내 card 표시

### 9.6 사후 측정 trainingAnalyze

함수:

```ts
trainingAnalyze(sessionId, recordedUri, chunkMeta)
```

endpoint:

```text
POST /sessions/{sessionId}/training-analyze
```

multipart:

- `audio`: WAV file
- `chunk_meta`: JSON string

chunkMeta:

```ts
{
  chunk_index: chunkIndex,
  start_sec: recordingStartSec,
  end_sec: recordingEndSec,
  original_run_id: runId,
}
```

timeout:

```text
30000ms
```

응답 score 처리:

1. legacy `scores[serverIndicatorKey]` 또는 `scores[indicatorKey]`
2. 없으면 `scores_meta[...].rounded_score`
3. 없으면 `scores_v2[...]`
4. rounded score로 zone 유도

low confidence:

- `low_confidence_items`에서 server key, app key, prefix 제거 key를 모두 비교한다.

### 9.7 ResultCard

파일: `src/components/training/ResultCard.tsx`

props:

- `before`
- `after`
- `beforeLowConfidence`
- `afterLowConfidence`

개선 판단:

- after가 `appropriate`이면 개선
- before가 `appropriate`였는데 after가 벗어나면 악화
- 둘 다 non-appropriate zone 변화는 변화
- 같은 zone이면 target score 3과의 거리로 개선/악화 판단

### 9.8 feedback video modal

파일:

- `src/domain/feedbackVideos.ts`
- `src/screens/home/TrainingScreen.tsx`

현재 asset mapping:

| indicator | zone | asset |
|---|---|---|
| `vocal_fold_contact` | `insufficient` | `vocal-contact-insufficient.mp4` |
| `vocal_fold_contact` | `excessive` | `vocal-contact-excessive.mp4` |
| `tongue_tension` | `excessive` | `tongue-tension-excessive.mp4` |

현재 없는 mapping:

- breathiness 전체
- soft_palate 전체
- tongue_tension insufficient/appropriate
- vocal_fold_contact appropriate

modal 구조:

- React Native `Modal`
- `expo-av` `Video`
- `ResizeMode.CONTAIN`
- `useNativeControls`
- custom 재생/일시정지 버튼
- modal close 시 `video.stopAsync()`

button 노출 조건:

- mapping이 있어야 함
- countdown/preparing/recording/analyzing 중이면 숨김 또는 block

설계서 정정:

- feedback video는 전체 항목에 대해 제공되는 것이 아니다.
- 현재 실제 asset은 3개 케이스만 있다.

---

## 10. API 레이어

### 10.1 client 설정

파일: `src/api/client.ts`

현재 server fallback:

```ts
const SERVER_URLS = {
  production: 'https://api.vocal-fit.com',
};
const CURRENT_SERVER = 'production';
```

base URL 우선순위:

```text
process.env.EXPO_PUBLIC_API_URL
→ SERVER_URLS.production
```

default timeout:

```text
15000ms
```

default headers:

```json
{
  "Content-Type": "application/json",
  "ngrok-skip-browser-warning": "true"
}
```

fetch default headers:

```json
{
  "ngrok-skip-browser-warning": "true",
  "Accept": "application/json"
}
```

### 10.2 auth / 401 처리 / SecureStore key

파일:

- `src/api/client.ts`
- `src/context/AuthContext.tsx`

SecureStore keys:

```ts
TOKEN_KEY = 'auth_token'
USER_KEY = 'auth_user'
API_BASE_MARKER_KEY = 'auth_api_base_url'
```

request interceptor:

- SecureStore에서 `auth_token` 읽음
- `/auth/` 요청이 아니면 `Authorization: Bearer {token}` 자동 추가

response interceptor:

- 401이면 stored auth 삭제
- auth request가 아니고 Authorization header가 있던 요청이면 auth expired로 판단
- 등록된 auth expired handler 호출

AuthContext:

- 앱 시작 시 token/user/api base marker 복원
- 저장된 API base가 현재 `BASE_URL`과 다르면 auth 삭제
- auth 만료 시 Alert:
  - 제목: `로그인 만료`
  - 본문: `로그인 시간이 만료되었습니다. 다시 로그인해 주세요.`

설계서 포인트:

- SecureStore token key `auth_token`은 유지된다.
- API base marker로 server base 변경 시 stale token을 제거한다.

### 10.3 endpoint 목록

Auth:

| method | endpoint | file |
|---|---|---|
| POST | `/auth/signup` | `src/api/auth.ts` |
| POST | `/auth/login` | `src/api/auth.ts` |

Sessions:

| method | endpoint | file | timeout |
|---|---|---|---:|
| POST | `/sessions` | `src/api/sessions.ts` | default |
| GET | `/sessions` | `src/api/sessions.ts` | default |
| GET | `/sessions/{sessionId}` | `src/api/sessions.ts` | default |
| POST | `/sessions/{sessionId}/files` | `src/api/sessions.ts` | 300000ms |
| POST | `/sessions/{sessionId}/analyze` | `src/api/sessions.ts` | 200000ms |
| POST | `/sessions/{sessionId}/training-analyze` | `src/api/sessions.ts` | 30000ms |

Analysis:

| method | endpoint | file |
|---|---|---|
| GET | `/analysis/{runId}` | `src/api/analysis.ts` |
| GET | `/analysis/{runId}/results` | `src/api/analysis.ts` |

Songs:

| method | endpoint | file |
|---|---|---|
| GET | `/songs` | `src/api/songs.ts` |
| GET | `/songs/{songId}/pitch-guide` | `src/api/songs.ts` |
| GET | `/songs/{songId}/lrc` | `src/api/songs.ts` |
| GET URL | `/songs/{songId}/mr` | `src/api/songs.ts` |

Training/favorites:

| method | endpoint | file |
|---|---|---|
| GET | `/users/me/training-attempts` | `src/api/training.ts` |
| GET | `/users/me/favorites` | `src/api/training.ts` |
| POST | `/users/me/favorites` | `src/api/training.ts` |
| DELETE | `/users/me/favorites/{favoriteId}` | `src/api/training.ts` |

Legacy vocal:

| method | endpoint | file |
|---|---|---|
| POST | `/vocal/detect-pitch` | `src/api/vocal.ts` |
| GET | `/vocal/famous-singers` | `src/api/vocal.ts` |

DML WebSocket:

| protocol | endpoint | file |
|---|---|---|
| WSS | `/ws/realtime?song_id={songId}` | `src/api/dmlClient.ts` |

### 10.4 analysis status handling

파일:

- `src/api/sessions.ts`
- `src/api/analysis.ts`

success statuses:

```text
success, completed, complete, done
```

failure statuses:

```text
failed, invalid, no_voice, error
```

`pollAnalysisStatus(runId)`:

- 1초 interval
- 10분 timeout
- success terminal이면 return
- failure terminal이면 `AnalyzeStatusError` throw
- timeout이면 `AnalysisPollingTimeoutError` throw

### 10.5 analyze result adapter

파일: `src/api/analyze.ts`

핵심:

- 서버 raw key `"4_breathiness"` 같은 prefix key를 app key `"breathiness"`로 변환
- v2 여부:

```ts
inner.score_mapper_version === 'v2' && !!inner.scores_v2
```

mapping:

- `scores`
- `feedback`
- `reliability.high_reliability`
- `reliability.medium_reliability`
- `reliability.unavailable`
- `reliability.shownV2`
- `reliability.academicOnlyV2`
- `reliability.deferredV2`
- `timelineScores`
- `timelineMetadata`
- `userF0`
- `scoresV2`
- `scoresMeta`

timeline v2 field mapping:

| server key | app timeline score field |
|---|---|
| `4_breathiness` | `breathiness` |
| `3_vocal_fold_contact` | `vocalFoldContact` |
| `6_soft_palate` | `softPalate` |
| `8_tongue_tension` | `tongueTension` |

---

## 11. FavoritesContext와 v2 key mapping

파일:

- `src/context/FavoritesContext.tsx`
- `src/api/training.ts`

### 11.1 app/server indicator mapping

`src/api/training.ts`:

```ts
const APP_TO_SERVER = {
  breathiness: '4_breathiness',
  vocal_fold_contact: '3_vocal_fold_contact',
  soft_palate: '6_soft_palate',
  tongue_tension: '8_tongue_tension',
};
```

server to app:

- server key에서 숫자 prefix 제거
- `breathiness`
- `vocal_fold_contact`
- `soft_palate`
- `tongue_tension`

### 11.2 FavoritesContext state

`FavoriteSection`:

```ts
interface FavoriteSection {
  id: string;
  indicatorKey: IndicatorAppKey;
  weakSection: WeakSection;
  songId: string;
  songTitle?: string;
  songArtist?: string;
  runId?: string;
  sessionId?: string;
  feedbackText: string;
  addedAt: number;
}
```

server favorite response limitation:

- server GET 응답에는 paddedStart/EndSec, aiScore, zone이 없음
- 앱은 `chunk_start_sec - 4`, `chunk_end_sec + 3`로 padding 복원
- `aiScore`는 0 placeholder
- `zone`은 `appropriate` placeholder
- `sessionId`는 server 미반환이라 undefined

설계서 포인트:

- 즐겨찾기에서 다시 들어온 ResultCard의 원본 점수는 placeholder 제약이 있을 수 있다.
- 즐겨찾기 key mapping은 v2 4항목까지 확장되어 있다.

---

## 12. recorder.ts 녹음 포맷과 segment concat

파일: `src/services/audio/recorder.ts`

### 12.1 기본 녹음 포맷

`react-native-audio-record` 사용:

```ts
const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const BITS_PER_SAMPLE = 16;
```

AudioRecord init options:

```ts
{
  sampleRate: 16000,
  channels: 1,
  bitsPerSample: 16,
  audioSource: 6,
  wavFile: 'recording.wav'
}
```

`audioSource: 6`:

- Android `VOICE_RECOGNITION`
- low noise processing
- vocal analysis용

### 12.2 callback data

`AudioRecord.on('data')`:

- base64 PCM Int16LE 수신
- Float32 [-1, 1]로 변환
- local pitch detection 및 WS PCM send에 사용
- `capturePcm`이 true면 raw PCM chunk를 `pcmChunks`에 누적

### 12.3 pause/resume concat

pause:

- AudioRecord stop
- initialized false
- `pausedSegmentCount += 1`
- playback-only audio mode로 전환

resume:

- `startInternal(..., { resetCapture: false })`
- 기존 `pcmChunks` 유지

final stop:

- AudioRecord stop 결과 URI 확보
- `capturePcm && pausedSegmentCount > 0 && pcmByteLength > 0`이면 captured PCM으로 새 WAV 작성
- 새 파일명:

```text
recording-paused-{Date.now()}.wav
```

return:

```ts
{
  uri,
  fileName: 'recording-paused.wav' 또는 'recording.wav',
  mimeType: 'audio/wav',
  temporary: true/false
}
```

### 12.4 upload URI

- AudioRecord stop path가 `file://`로 시작하지 않으면 `file://` prefix를 붙인다.
- server upload는 `audio/wav` multipart로 진행한다.

---

## 13. audioMode helper

파일: `src/services/audio/audioMode.ts`

제공 기능:

```ts
AudioStartBlockedError
isAudioStartBlockedError(error)
isAudioFocusNotAcquiredError(error)
waitForAppActive(timeoutMs = 500)
prepareAudioForRecordAndPlayback()
prepareAudioForPlaybackOnly()
```

record+playback mode:

```ts
Audio.setAudioModeAsync({
  allowsRecordingIOS: true,
  playsInSilentModeIOS: true,
  playThroughEarpieceAndroid: false,
  staysActiveInBackground: false,
  shouldDuckAndroid: true,
})
```

playback-only mode:

```ts
Audio.setAudioModeAsync({
  allowsRecordingIOS: false,
  playsInSilentModeIOS: true,
  playThroughEarpieceAndroid: false,
  staysActiveInBackground: false,
  shouldDuckAndroid: true,
})
```

설계서 포인트:

- Galaxy에서 audio focus 문제가 있었던 흐름을 막기 위해 AppState active guard와 screen focus guard가 들어가 있다.
- Training feedback video도 playback-only mode를 사용한다.

---

## 14. result/training/feedback video 최신 구조

### 14.1 EvalResult 최신 기준

최신 코드 기준 EvalResult는 다음을 지원한다.

- v1/v2 adapter
- v2 4개 active item 기본 탭
- v2 5개 inactive/reference item 고급 탭
- `shownV2` 우선 활성 판단
- `academicOnlyV2`, `deferredV2` 비활성 처리
- inactive card dimming
- score unavailable label
- score_mapper v2 `scores_v2` / `scores_meta`
- high_star tier badge
- low confidence timeline color
- pitch/rhythm client score cards
- 5개 timeline mode: pitch + 4 indicators

### 14.2 Training 최신 기준

Training은 다음 구조다.

```text
SectionList
→ TrainingScreen
→ MR 구간 재생
→ target 구간 녹음
→ WebSocket 실시간 pitch/breath feedback
→ stop
→ trainingAnalyze
→ ResultCard before/after
→ optional feedback video modal
```

4개 indicator server key:

- `4_breathiness`
- `3_vocal_fold_contact`
- `6_soft_palate`
- `8_tongue_tension`

### 14.3 Feedback video 최신 기준

현재 영상 asset은 3개다.

```text
assets/feedback-videos/vocal-contact-insufficient.mp4
assets/feedback-videos/vocal-contact-excessive.mp4
assets/feedback-videos/tongue-tension-excessive.mp4
```

mapping:

```ts
vocal_fold_contact.insufficient
vocal_fold_contact.excessive
tongue_tension.excessive
```

설계서에는 “피드백 영상 기능이 있다”는 말과 “모든 항목/zone에 영상이 있다”는 말을 구분해야 한다.

---

## 15. 배포 / APK / 문서 상태

### 15.1 EAS preview APK 설정

`eas.json` 기준:

- `preview` profile은 internal distribution APK
- `development` profile도 APK지만 dev client 포함
- `production`은 app-bundle

`docs/android-install.md`:

- Galaxy에서 APK 설치 절차 문서화
- preview APK 직접 설치 방식 설명

### 15.2 최신 APK artifact URL 문서화 여부

실제 artifact URL은 `.codex/APK_FEEDBACK_TRACKER.md`에 있다.

```text
https://expo.dev/artifacts/eas/eNayYSHePP19QtF85FnZgR.apk
```

추가 정보:

- build ID: `6fb8e9b2-6211-47f2-8293-bcfed90aba13`
- build profile: `preview`
- build status: 완료
- Galaxy 설치 검증 여부: 완료
- EAS submit / Play Store production: 미진행
- 기록일: 2026-05-19

주의:

- `docs/` 공개 문서에는 실제 최신 APK URL이 아니라 예시 또는 “Expo 대시보드 참조” 수준이다.
- `.codex/APK_FEEDBACK_TRACKER.md`는 scratch 문서이며 GitHub 반영 대상이 아니라고 문서 자체에 적혀 있다.

### 15.3 PR #10 이후 최신 APK URL

repo 검색 기준:

- `PR #10`
- `#10`
- 실제 APK artifact URL

이 항목들이 `docs/`에는 최신 release note 형태로 정리되어 있지 않았다. 실제 APK artifact URL은 `.codex` scratch 문서에만 있다.

---

## 16. README/docs 최신성 평가

### 16.1 README

루트 `README.md`는 없다. 최종 설계서에서 “README 기준”이라고 쓰면 안 된다.

### 16.2 `docs/CURRENT_STATE_v1.md`

이 문서는 2026-05-11 v1 baseline 문서다. 일부 내용은 최신 코드와 다르다.

최신 코드와 다른 예:

- 현재 EvalResult v2 기본 탭은 4개 active item이다.
- 현재 TrainingScreen은 4개 indicator key mapping을 가지고 있다.
- 현재 `startAnalysis` timeout은 200초다.
- 현재 uploadSessionFile timeout은 300초다.
- 현재 KaraokeScreen은 async analysis polling을 수행한다.
- 현재 MainTabs에는 GoalsTab이 없다.

### 16.3 `docs/HANDOVER.md`

이 문서는 2026-05-12 이관 문서이며 v2 진행 상태 일부를 담고 있다. 그러나 최신 코드와 일부 차이가 있다.

최신 코드와 다른 예:

- 문서에는 Step 3 G 진행 중이라고 되어 있지만 현재 TrainingScreen은 4개 indicator mapping과 soft palate/tongue tension info card를 포함한다.
- 문서에는 호흡 카드 강조 기록이 있으나 최신 EvalResult 코드의 `isHighlighted` 대상은 `vocal_fold_contact`다.
- 문서에는 EAS 마지막 빌드가 5/9 run ID라고 되어 있으나 `.codex/APK_FEEDBACK_TRACKER.md`에는 2026-05-19 preview APK 정보가 있다.

### 16.4 `docs/V2_CLOSEOUT_CHECKLIST.md`

이 문서는 V2 closeout 항목을 비교적 최신으로 반영한다.

확인된 내용:

- V2 diagnostic log 제거
- `_test_stream` utility 제거
- Settings dev button 제거
- training-analyze v2 fallback 추가
- production API switch checklist 존재

### 16.5 `docs/dev-flow.md`

개발 서버 실행 흐름과 release env policy가 정리되어 있다.

중요 내용:

- `npm run start:cf`
- Cloudflare dev tunnel은 production build script가 아님
- EAS remote build는 local `.env` 자동 포함으로 가정하지 말 것
- `EXPO_PUBLIC_ENABLE_SPEECH_WEB=true`일 때만 Home speech web 버튼 표시
- 학원 배포용/상용화 빌드는 speech web flag false

---

## 17. student02 결과 crash 관련 확인

repo 검색 기준 `student02` 문자열은 확인되지 않았다.

확인한 사실:

- 코드에는 optional chaining, null fallback, score/result guard가 여러 곳에 있다.
- 그러나 `student02`라는 특정 학생 결과 crash에 대한 명시적 재현 코드, regression test, issue note, fix note는 repo에서 찾지 못했다.

설계서 반영 권장:

```text
student02 결과 crash는 현재 repo 코드/문서에서 명시적 해결 여부를 확인할 수 없다.
최신 코드에는 null/optional guard가 다수 반영되어 있으나, 해당 특정 crash가 해결됐다고 단정하려면 실제 run_id/raw response 또는 Galaxy 재현 검증 로그가 필요하다.
```

---

## 18. 최종 설계서에 반드시 반영할 정정사항

### 18.1 Navigation

정정 전:

```text
MainTabs = Home / Record / History / Goals
```

정정 후:

```text
현재 실제 MainTabs = HomeTab / RecordTab / HistoryTab
GoalsScreen 파일은 있으나 AppNavigator에는 등록되어 있지 않다.
Bottom tab bar는 숨겨져 있고, MainTopTabs가 화면 상단 3탭 UI를 제공한다.
```

### 18.2 Result active items

정정 전:

```text
활성 항목은 호흡/접촉 2개다.
```

정정 후:

```text
v2 응답 기준 기본 탭 활성 항목은 호흡 소리 식별, 성대 접촉 강도, 연구개 위치, 혀/구강 공간 경직도 4개다.
v1 응답 또는 shownV2 부재 시 fallback logic이 있다.
```

### 18.3 weak sections

정정 전:

```text
서버 target_chunks 기반으로 약점 구간을 사용한다.
```

정정 후:

```text
앱은 target_chunks를 사용하지 않는다.
EvalResultScreen이 result.timelineScores를 받아 extractWeakSections()로 zone !== appropriate 구간을 직접 추출한다.
```

### 18.4 Full analysis flow

정정 전:

```text
녹음 종료 후 startAnalysis 결과를 받아 EvalResult로 이동한다.
```

정정 후:

```text
녹음 종료 후 createSession, uploadSessionFile, startAnalysis로 run_id를 받은 뒤 pollAnalysisStatus(run_id)로 terminal 상태를 기다리고 EvalResult로 이동한다.
```

### 18.5 Speech web

정정 전:

```text
Home에 스피치 평가 웹 버튼이 있다.
```

정정 후:

```text
Home의 스피치 평가 웹 버튼은 EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true'일 때만 보이는 demo-only 기능이다.
기본 env example은 false다.
```

### 18.6 Feedback videos

정정 전:

```text
Training feedback video modal은 훈련 항목별로 제공된다.
```

정정 후:

```text
Training feedback video modal 구조는 있으나 실제 asset mapping은 vocal_fold_contact insufficient/excessive, tongue_tension excessive 3개 케이스뿐이다.
```

### 18.7 APK artifact

정정 전:

```text
최신 APK URL은 docs에 정리되어 있다.
```

정정 후:

```text
실제 APK artifact URL은 .codex/APK_FEEDBACK_TRACKER.md scratch 문서에 있다.
docs/에는 실제 최신 APK URL이 release note처럼 정리되어 있지 않다.
```

### 18.8 README

정정 전:

```text
README 기준 최신 상태
```

정정 후:

```text
현재 repo 루트에 README.md가 없다.
최신 상태는 실제 코드, docs, .codex scratch 문서가 서로 일부 다르므로 코드 기준으로 우선 정리해야 한다.
```

---

## 19. 설계서용 추천 문장

다음 문장을 최종 설계서 지식 베이스에 반영하는 것을 권장한다.

```text
vocal-app은 Expo SDK 54 / React Native 0.81 기반 모바일 앱이며, 인증 후 Home에서 곡을 선택하고 KaraokeScreen에서 MR 재생과 녹음을 수행한다. 녹음 종료 시 앱은 세션 생성, WAV 업로드, 분석 시작 요청을 순서대로 수행하고, run_id에 대해 analysis status polling을 진행한 뒤 EvalResultScreen으로 이동한다.
```

```text
최신 v2 결과 화면은 기본 탭에 4개 활성 항목, 즉 호흡 소리 식별, 성대 접촉 강도, 연구개 위치, 혀/구강 공간 경직도를 표시한다. 고급 탭에는 비강/구강 공명 비율, 흉성/두성 경향, 전방 공명 정도, 상압/하압 비율, 공명 개방감 5개 참고/비활성 항목을 표시한다.
```

```text
약점 구간은 서버가 별도 target_chunks로 내려주는 구조가 아니라, 앱이 analysis result의 timeline_scores를 받아 rounded_score 기반으로 zone을 유도하고, appropriate이 아닌 구간을 extractWeakSections()에서 추출한다. 각 구간은 앞 4초, 뒤 3초 padding을 적용해 SectionList와 TrainingScreen으로 전달된다.
```

```text
TrainingScreen은 선택된 약점 구간에 대해 MR을 해당 구간 주변부터 재생하고, 목표 chunk 근처에서 사용자 음성을 다시 녹음한다. 녹음 중에는 WebSocket을 통해 실시간 pitch_match와 breathiness_chunk 메시지를 처리하고, 녹음 종료 후 /sessions/{sessionId}/training-analyze에 WAV와 chunk_meta를 multipart로 전송해 before/after 결과를 비교한다.
```

```text
Home의 스피치 평가 웹 버튼은 상시 기능이 아니라 EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true'일 때만 노출되는 졸업작품 시연용 보조 기능이다. 학원 배포용 또는 상용화 빌드에서는 false로 두는 정책이다.
```

```text
현재 실제 네비게이션은 Auth 분기 이후 AppRootStack 안에 MainTabs와 Karaoke fullscreen modal이 있고, MainTabs는 HomeTab, RecordTab, HistoryTab 3개만 가진다. GoalsScreen 파일은 존재하지만 현재 AppNavigator에 GoalsTab으로 등록되어 있지 않다.
```

---

## 20. 이번 작업에서 하지 않은 것

이번 검증 및 문서화 작업에서 하지 않은 것:

- 기능 코드 수정 안 함
- API URL 변경 안 함
- package script 변경 안 함
- dependency 추가/삭제 안 함
- dml-server/vocal-server 변경 안 함
- `.env` 실제 값 읽기/출력 안 함
- commit 안 함
- push 안 함
- PR 생성/수정/merge 안 함
- EAS build 안 함
- EAS submit 안 함
- Cloudflare token/credential 출력 안 함

이번 요청으로 새로 만든 파일:

```text
docs/VOCAL_APP_CODE_VERIFICATION_2026-06-16.md
```

