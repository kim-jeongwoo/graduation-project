# HANDOVER_TO_CLAUDE

기준 시점: 2026-07-06, 로컬 저장소 `/Users/kimjeongwoo/vocal-app`.

작성 원칙: 이 문서는 저장소 파일과 git 명령 출력에서 확인한 사실만 기록한다. `.env` / `.env.*` 실제 파일 값은 읽지 않았다.

## 1. 저장소 구조

```text
.
├── .claude/
│   └── worktrees/
├── .codex/
│   └── scripts/
├── assets/
│   └── feedback-videos/
├── docs/
├── scripts/
├── src/
│   ├── api/
│   ├── components/
│   │   ├── eval/
│   │   ├── navigation/
│   │   └── training/
│   ├── config/
│   ├── constants/
│   ├── context/
│   ├── domain/
│   ├── mock/
│   ├── navigation/
│   ├── screens/
│   │   ├── auth/
│   │   ├── goals/
│   │   ├── history/
│   │   ├── home/
│   │   ├── karaoke/
│   │   ├── onboarding/
│   │   ├── record/
│   │   └── settings/
│   ├── services/
│   │   └── audio/
│   ├── store/
│   ├── theme/
│   ├── types/
│   └── utils/
├── App.tsx
├── index.ts
├── app.json
├── eas.json
├── package.json
└── tsconfig.json
```

디렉토리 역할:

| 경로 | 역할 |
|---|---|
| `.claude/` | Claude 작업공간 관련 디렉토리. 현재 `worktrees/` 하위 디렉토리가 있다. |
| `.codex/` | Codex 작업 문서와 점검 스크립트. `.easignore`는 EAS 업로드에서 `.codex`를 제외한다. |
| `assets/` | Expo 앱 아이콘/스플래시 및 훈련 피드백 영상 자산. |
| `assets/feedback-videos/` | `feedbackVideos.ts`에서 require하는 훈련 추천 영상 mp4. |
| `docs/` | 개발 흐름, 현재 상태, 검증, handover 문서. |
| `scripts/` | Expo 개발 실행 보조 스크립트. 현재 `start-expo-cloudflare.sh`가 있다. |
| `src/api/` | Axios API client, 서버 endpoint wrapper, response adapter. |
| `src/components/eval/` | 평가 결과 카드, 점수 게이지, 우선순위/안정도 컴포넌트. |
| `src/components/navigation/` | 숨겨진 BottomTab 대신 쓰는 상단 탭 컴포넌트. |
| `src/components/training/` | 구간 훈련 그래프, 실시간 피드백, 전후 비교 카드. |
| `src/config/` | 앱 부팅 시 적용하는 warning filter. |
| `src/constants/` | 곡별 LRC/guide offset 상수. |
| `src/context/` | Auth, Favorites, Goals, VocalProfile React Context provider. |
| `src/domain/` | 평가 항목, 약점 구간 추출, 피드백 영상 매핑 등 앱 도메인 로직. |
| `src/mock/` | 구형/mock 화면용 mock 데이터. |
| `src/navigation/` | React Navigation stack/tab 구성과 route param 타입. |
| `src/screens/` | 화면 단위 구현. |
| `src/services/audio/` | 녹음기, audio mode, microphone permission, pitch detector. |
| `src/store/` | zustand placeholder store. 실제 상태 정의 TODO만 있다. |
| `src/theme/` | spacing/typography/token 상수. |
| `src/types/` | 서버 raw 타입과 앱 domain 타입. |
| `src/utils/` | 색상, 라벨, note 유틸. |

## 2. 앱 아키텍처

### 화면 구조

`index.ts`는 `registerRootComponent(App)`를 호출한다. `App.tsx`는 provider를 `AuthProvider -> VocalProfileProvider -> GoalsProvider -> FavoritesProvider -> AppNavigator` 순서로 감싼다.

`src/navigation/AppNavigator.tsx` 구조:

```text
AppNavigator
├── token 없음: AuthNavigator
│   ├── Login
│   └── Signup
└── token 있음: AppRootNavigator
    ├── MainTabs
    │   ├── HomeTab -> HomeStackNavigator
    │   │   ├── Home
    │   │   ├── SessionDetail
    │   │   ├── AnalysisResult
    │   │   ├── Settings
    │   │   ├── Profile
    │   │   ├── VocalRangeTest
    │   │   ├── SongComparison
    │   │   ├── SongDetail
    │   │   ├── EvalResult
    │   │   ├── SectionList
    │   │   └── Training
    │   ├── RecordTab -> ResultStackNavigator
    │   │   ├── LatestAnalysis
    │   │   ├── EvalResult
    │   │   ├── SectionList
    │   │   └── Training
    │   └── HistoryTab -> HistoryStackNavigator
    │       ├── HistoryList
    │       ├── HistoryDetail
    │       ├── SongHistory
    │       ├── Favorites
    │       ├── Training
    │       ├── EvalResult
    │       ├── SectionList
    │       └── SongComparison
    └── Karaoke (fullScreenModal)
```

BottomTab의 `tabBarStyle`은 `display: 'none'`이다. 홈/결과/히스토리 이동 UI는 `src/components/navigation/MainTopTabs.tsx`가 `navigation.getParent()`로 `HomeTab`, `RecordTab`, `HistoryTab`에 navigate한다.

### 상태 관리 방식

| 상태 | 구현 |
|---|---|
| 인증 | `src/context/AuthContext.tsx`: `expo-secure-store`에 `auth_token`, `auth_user`, `auth_api_base_url` 저장. `BASE_URL` 변경 시 저장 인증 삭제. 401 interceptor callback으로 로그아웃 상태 전환. |
| 즐겨찾기 | `src/context/FavoritesContext.tsx`: token 존재 시 `/users/me/favorites`를 로드. add/remove는 optimistic update 후 서버 POST/DELETE. 서버가 반환하지 않는 `aiScore`, `zone`, `sessionId`는 placeholder를 둔다. |
| 목표 | `src/context/GoalsContext.tsx`: local React state와 `DEFAULT_GOALS`. 서버 연동 없음. |
| 보컬 프로필 | `src/context/VocalProfileContext.tsx`: local React state. `AppNavigator`의 온보딩 분기는 주석 처리되어 있다. |
| 녹음/히스토리 zustand | `src/store/recordingStore.ts`, `src/store/historyStore.ts`: `_placeholder`만 있으며 TODO 주석이 있다. |
| 화면 진행 상태 | `KaraokeScreen`, `EvalResultScreen`, `TrainingScreen` 등 각 화면의 `useState`/`useRef`. |

### 데이터 흐름: 녹음 -> 업로드 -> 결과 표시

1. `HomeScreen`이 `getSongs()`로 `/songs`를 불러와 곡 목록을 표시한다.
2. `SongDetailScreen`에서 `hasLrc && hasPitchGuide`가 true인 곡은 `Karaoke` route로 이동한다.
3. `KaraokeScreen`은 마이크 권한을 요청하고 `getSongKaraokeLyricsOnly(songId)`로 LRC를 먼저 로드한다. 이후 `getSongKaraokeData(songId)`로 pitch guide를 비동기 로드한다.
4. `KaraokeScreen`은 `getSongMrUrl(songId)`에서 만든 `/songs/{songId}/mr` URL을 Authorization header와 함께 Expo AV에 로드한다. MR 파일은 `expo-file-system/legacy` cache directory에 캐시할 수 있다.
5. 카운트다운 후 `VocalRecorder.start()`로 녹음하고 MR을 재생한다. 실시간 pitch 표시가 켜져 있으며 `detectPitch(samples)` 결과를 `userPitch`에 추가한다.
6. 사용자가 stop하면 `VocalRecorder.stop()`으로 `{ uri, fileName, mimeType }`를 얻는다.
7. `createSession({ song_id: songId })`로 `/sessions`를 POST한다.
8. `uploadSessionFile(session.session_id, uri, fileName, mimeType)`로 `/sessions/{sessionId}/files`에 multipart `file`을 POST한다.
9. `startAnalysis(session.session_id)`로 `/sessions/{sessionId}/analyze`를 POST한다.
10. `pollAnalysisStatus(run_id)`가 `/analysis/{runId}`를 1초 간격, 최대 10분 폴링한다.
11. 완료되면 `goToEvalResult(run_id)`가 `MainTabs -> HomeTab -> EvalResult`로 이동하고 `songId`도 전달한다.
12. `EvalResultScreen`은 `getResultsByRunId(runId)`를 호출한다. 이 함수는 `pollAnalysisStatus(runId)` 후 `/analysis/{runId}/results`를 가져와 `adaptServerResult()`로 앱 내부 타입으로 변환한다.

## 3. 핵심 파일 상세

| 파일 | 핵심 로직 |
|---|---|
| `index.ts` | `src/config/warningFilters`를 import한 뒤 Expo `registerRootComponent(App)` 실행. |
| `App.tsx` | Auth/VocalProfile/Goals/Favorites provider를 중첩하고 `AppNavigator` 렌더. |
| `src/api/client.ts` | Axios client 생성. `BASE_URL`은 `process.env.EXPO_PUBLIC_API_URL` 우선, 없으면 `https://api.vocal-fit.com` fallback. timeout 15000ms. request interceptor가 SecureStore `auth_token`을 `/auth/*` 외 요청에 Bearer로 붙인다. 401 response는 저장 auth를 삭제하고 handler를 호출한다. |
| `src/navigation/AppNavigator.tsx` | 인증 분기, Auth stack, app root stack, hidden BottomTab, Home/Result/History stack 구성. |
| `src/navigation/types.ts` | `EvalResult`, `SectionList`, `Training`, MainTab, AppRoot route params 타입 정의. `TrainingParams`에는 `lowConfidenceItems?: string[]`가 포함된다. |
| `src/screens/karaoke/KaraokeScreen.tsx` | 곡 LRC/MR/pitch guide 로드, MR 재생, 녹음, 실시간 pitch 표시, 세션 생성, 파일 업로드, 분석 시작, 상태 폴링, `EvalResult` 이동. `USE_REALTIME_PITCH = true`, `USE_MOCK = EXPO_PUBLIC_USE_MOCK === 'true'`, `MOCK_RUN_ID` 상수 존재. |
| `src/screens/record/RecordScreen.tsx` | 파일명은 `LatestAnalysisScreen`. `RecordTab` 진입 시 `/sessions`에서 `analysis_status === 'completed'` 최신 세션을 찾고 `/sessions/{id}` detail에서 run id를 추출해 `EvalResult`로 reset한다. |
| `src/api/analyze.ts` | `/analysis/{runId}/results`의 `result_json`을 앱 `AnalyzeResult`로 변환. 숫자 prefix 제거, v2 `scores_v2`, `scores_meta`, `timeline_scores`, `timeline_metadata`, `user_f0`를 매핑. `analyzeRecording()`은 아직 `throw new Error('analyzeRecording: P1에서 구현 예정')`. |
| `src/screens/home/EvalResultScreen.tsx` | 결과 표시 본체. v2이면 기본 탭 4항목 `breathiness`, `vocal_fold_contact`, `soft_palate`, `tongue_tension`; 고급 탭 5항목을 표시. `extractWeakSections()`로 약점 구간을 만들고 `SectionList`로 이동. timeline visualization은 pitch와 4개 발성 mode를 지원. |
| `src/screens/home/SectionListScreen.tsx` | `weakSections` route param을 FlatList로 표시. section 선택 시 `Training`으로 `indicatorKey`, `runId`, `songId`, `sessionId`, padded start/end, 원본 chunk info, score info, `lowConfidenceItems`, feedback text를 전달. 즐겨찾기 토글은 `FavoritesContext` 사용. |
| `src/screens/home/TrainingScreen.tsx` | 구간 훈련 본체. MR 재생 구간과 실제 녹음 구간을 계산하고, WebSocket `/ws/realtime?song_id=...`로 pitch_match/breathiness_chunk를 받는다. 녹음 후 `/sessions/{sessionId}/training-analyze`를 호출해 before/after 결과를 보여준다. |
| `src/domain/weakSections.ts` | `IndicatorAppKey`, label, zone label, `SECTION_FEEDBACK_BY_ZONE`, `extractWeakSections()`, `sortWeakSections()`, `zoneColor()`. 약점 구간은 v2 roundedScore 기준 zone이 `appropriate`가 아닌 chunk만 추출하고 앞 4초/뒤 3초 padding 적용. |
| `src/domain/feedbackVideos.ts` | `vocal_fold_contact` insufficient/excessive, `tongue_tension` excessive에 대해 mp4 require 매핑. |
| `src/components/eval/EvalItemCard.tsx` | 평가 항목 카드. `ScoreGauge`, `ConfidenceBadge`, `TierBadge`, 훈련 버튼, 설명 접기/펼치기, v2 highlight/dimmed 스타일 처리. |
| `src/components/eval/ImprovementPriorityCard.tsx` | 4개 활성 항목의 개선 우선순위 bar 표시. `isDataMissing`이면 `데이터 부족`과 `--` 표시. |
| `src/components/eval/SectionStabilityChart.tsx` | timeline chunk의 roundedScore를 안정도 0~100으로 변환. low confidence chunk는 제외한다. 가장 낮은 안정도 구간을 표시. |
| `src/components/training/RealtimeFeedback.tsx` | `PitchCard`, `BreathCard`, `BreathInfoCard`, `SoftPalateInfoCard`, `TongueTensionInfoCard`, `VoiceInputCard` 정의. TrainingScreen의 InfoCard 계열이 여기 있다. |
| `src/components/training/ResultCard.tsx` | 사후 측정 before/after 점수 비교. `beforeLowConfidence`/`afterLowConfidence`가 true면 `신뢰도 낮음`을 표시. |

### FEEDBACK_BY_ZONE 및 InfoCard

`TrainingScreen`은 `SECTION_FEEDBACK_BY_ZONE as FEEDBACK_BY_ZONE`로 import한다. 원본 위치는 `src/domain/weakSections.ts`이며, 4개 indicator와 3개 zone별 한국어 피드백 문구를 가진다.

InfoCard 계열은 `src/components/training/RealtimeFeedback.tsx`에 있다.

| 컴포넌트 | TrainingScreen 사용 조건 |
|---|---|
| `BreathCard` | `indicatorKey === 'breathiness'`. WebSocket `breathiness_chunk`의 `zone`, `ai_score`를 표시. |
| `BreathInfoCard` | `indicatorKey === 'vocal_fold_contact'`. |
| `SoftPalateInfoCard` | `indicatorKey === 'soft_palate'`. |
| `TongueTensionInfoCard` | 그 외 현재 코드상 `tongue_tension`. |

### low_confidence 처리 위치

| 위치 | 처리 |
|---|---|
| `src/types/analyze.ts` | 서버 raw `timeline_scores[].low_confidence_items?: string[]`와 앱 `TimelineChunkScore.lowConfidenceItems?: string[]` 타입 정의. |
| `src/api/analyze.ts` | `adaptServerResult()`에서 `chunk.low_confidence_items`를 `lowConfidenceItems`로 매핑. |
| `src/screens/home/EvalResultScreen.tsx` | `hasLowConfidence()`가 server key/app key/score field/prefix 제거 key를 비교한다. low confidence chunk는 timeline color를 `COLOR_LOW_CONFIDENCE`로 표시한다. |
| `src/components/eval/SectionStabilityChart.tsx` | low confidence chunk는 stability 계산 대상에서 제외한다. |
| `src/domain/weakSections.ts` | weak section에 `lowConfidenceItems`를 그대로 보존한다. |
| `src/screens/home/SectionListScreen.tsx` | `Training` route param으로 `lowConfidenceItems` 전달. |
| `src/screens/home/TrainingScreen.tsx` | before는 `lowConfidenceItems?.includes(serverIndicatorKey)`, after는 `res.low_confidence_items`를 `hasLowConfidenceItem()`으로 검사. |
| `src/components/training/ResultCard.tsx` | low confidence flag가 있으면 점수 아래 `신뢰도 낮음` 표시. |

## 4. vocal-server API 호출부

API base: `src/api/client.ts`의 Axios `apiClient`. 인증 토큰은 `/auth/*` 외 request에 Bearer로 자동 추가된다.

| Method | Endpoint | 호출 파일 | 요청에서 실제 사용하는 필드 | 응답에서 실제 사용하는 필드 |
|---|---|---|---|---|
| POST | `/auth/signup` | `src/api/auth.ts`, `AuthContext` | `email`, `password`, `nickname` | `user_id`, `email`, `nickname`, `token` |
| POST | `/auth/login` | `src/api/auth.ts`, `AuthContext` | `email`, `password` | `user_id`, `email`, `nickname`, `token` |
| POST | `/sessions` | `src/api/sessions.ts`, `KaraokeScreen` | `song_id` 또는 `song_title` 타입 존재. 실제 KaraokeScreen은 `{ song_id: songId }` 사용. | `session_id` |
| GET | `/sessions` | `src/api/sessions.ts`, `RecordScreen`, history/profile/favorites related screens | 없음 | `session_id`, `song_title`, `song_id`, `song.id/title/artist`, `status`, `analysis_status`, `started_at`, `created_at` |
| GET | `/sessions/{sessionId}` | `src/api/sessions.ts`, `RecordScreen`, `SessionDetailScreen` | path `sessionId` | 타입상 `files`, `analysis`; `extractRunId()`는 실제로 `latest_analysis.run_id`도 읽는다. |
| POST | `/sessions/{sessionId}/files` | `src/api/sessions.ts`, `KaraokeScreen` | multipart `file` with `{ uri, name, type }` | `file_id`, `file_type`, `storage_uri`, `duration_ms` |
| POST | `/sessions/{sessionId}/analyze` | `src/api/sessions.ts`, `KaraokeScreen`, `SessionDetailScreen` | 빈 JSON `{}` | `run_id`, `status`, `reason`, `message`, `detail` |
| GET | `/analysis/{runId}` | `src/api/analysis.ts`, polling | path `runId` | `run_id`, `session_id`, `model_name`, `status`, `requested_at`, `finished_at`; terminal status 판단에 `status` 사용 |
| GET | `/analysis/{runId}/results` | `src/api/analysis.ts`, `src/api/analyze.ts` | path `runId` | wrapper: `run_id`, `session_id`, `user_id`, `metrics`, `result_json`; 실제 표시는 `result_json`의 필드를 adapter가 사용 |
| GET | `/songs` | `src/api/songs.ts`, `HomeScreen` | 없음 | `id`, `title`, `artist`, `master_duration_sec`, `mr_duration_sec`, `has_lrc`, `has_pitch_guide` |
| GET | `/songs/{songId}/lrc` | `src/api/songs.ts`, `KaraokeScreen` | path `songId` | 각 line의 `time_start`, `time_end`, `text` |
| GET | `/songs/{songId}/pitch-guide` | `src/api/songs.ts`, `KaraokeScreen`, `EvalResultScreen`, `TrainingScreen` | path `songId` | `song_id`, `duration_sec`, `frame_hz`, `alignment_status`, `guide_source`, `lrc_offset_sec`, `review_segments`, `points`, `midi_segments` |
| GET | `/songs/{songId}/mr` | `src/api/songs.ts`, `KaraokeScreen`, `TrainingScreen` | path `songId`; Expo AV/FileSystem caller가 Authorization header를 붙임 | 오디오 파일/stream. TypeScript response 타입 없음. |
| POST | `/sessions/{sessionId}/training-analyze` | `src/api/sessions.ts`, `TrainingScreen` | multipart `audio`; optional `chunk_meta` JSON with `chunk_index`, `start_sec`, `end_sec`, `original_run_id` | `session_id`, `status`, `body_status`, `scores`, `reason`, `message`, `detail`, `error`, `duration_sec`, `indicators`, `scores_v2`, `scores_meta`, `low_confidence_items`, `processing_time_ms`, `chunk_meta` |
| GET | `/users/me/training-attempts` | `src/api/training.ts` | query `indicator_key`, `song_id`, `original_run_id`, `cursor`, `limit` | `items`, `next_cursor`, `has_more`; item fields include attempt/session/run/chunk/indicator/before/after/improvement/attempted_at |
| GET | `/users/me/favorites` | `src/api/training.ts`, `FavoritesContext` | query `indicator_key`, `song_id` | `items`; item fields `favorite_id`, `song_id`, `song_title`, `song_artist`, `original_run_id`, `chunk_index`, `chunk_start_sec`, `chunk_end_sec`, `chunk_lrc_text`, `indicator_key`, `created_at` |
| POST | `/users/me/favorites` | `src/api/training.ts`, `FavoritesContext` | `original_run_id`, `chunk_index`, `indicator_key` | `FavoriteServerItem` fields above. 409 error handling reads `response.data.detail.existing_favorite_id`. |
| DELETE | `/users/me/favorites/{favoriteId}` | `src/api/training.ts`, `FavoritesContext` | path `favoriteId` | body 사용 안 함 |
| POST | `/vocal/detect-pitch` | `src/api/vocal.ts`, onboarding | multipart `file` with m4a | `detected_note`, `frequency_hz`, `confidence`, `stable_duration_ms`, optional `all_notes`, `pitch_range.low_hz/high_hz` |
| GET | `/vocal/famous-singers` | `src/api/vocal.ts`, onboarding | query `low`, `high` | `name`, `range_low`, `range_high`, `voice_type`, `famous_songs`, `youtube_query` |
| WS | `/ws/realtime?song_id={songId}` on `wss://dml.vocal-fit.com` or `EXPO_PUBLIC_DML_WS_URL` | `src/api/dmlClient.ts`, `TrainingScreen` | query `song_id`; first message JSON `{ type: 'meta', sample_rate: 16000, start_timestamp }`; then Int16 PCM buffers | message `type === 'pitch_match'`: `user_midi`, `match_score`; message `type === 'breathiness_chunk'`: `zone`, `ai_score` |

`GET /analysis/{runId}/results`의 `result_json`에서 adapter가 실제 사용하는 필드:

| 그룹 | 필드 |
|---|---|
| 기본 | `run_id`, `status`, `processing_time_ms`, `audio_info`, `registers`, `indicators`, `register_boundaries` |
| scores/feedback | `scores`, `feedback`의 key에서 숫자 prefix 제거. score는 `ai_score`, `zone`, `confidence`; feedback은 `name_ko`, `ai_score`, `score_description`, `feedback_text`, `zone`, `ai_indicator.name/value`. |
| reliability | `high_reliability`, `medium_reliability`, `unavailable`, v2 optional `shown_v2`, `academic_only_v2`, `deferred_v2` |
| v2 score | `score_mapper_version`, `scores_v2`, `scores_meta.tier/caveats/display_mark/tooltip/rounded_score/icc/icc_ratio` |
| timeline | `timeline_scores[].start_sec/end_sec/lrc_text/chunk_duration_s/scores/low_confidence_items`; score keys `4_breathiness`, `3_vocal_fold_contact`, `6_soft_palate`, `8_tongue_tension` |
| timeline metadata | `timeline_metadata.chunk_method`, `shown_indicators`, `shown_indicators_reason` |
| pitch | `user_f0.frame_hz`, `user_f0.values` |

## 5. 빌드/실행

### 개발 실행 명령

`package.json` scripts:

| 명령 | 내용 |
|---|---|
| `npm run start` | `expo start --dev-client` |
| `npm run start:lan` | `expo start --dev-client --lan` |
| `npm run start:tunnel` | `expo start --dev-client --tunnel` |
| `npm run start:tunnel:clear` | `expo start --dev-client --tunnel --clear` |
| `npm run start:go` | `expo start` |
| `npm run android` | `expo start --android --dev-client` |
| `npm run ios` | `expo start --ios --dev-client` |
| `npm run web` | `expo start --web` |
| `npm run start:cf` | `./scripts/start-expo-cloudflare.sh` |

`scripts/start-expo-cloudflare.sh`는 8081/8082/19000/19001/19002 listener와 expo/ngrok process를 종료한 뒤 `EXPO_PACKAGER_PROXY_URL="https://expo-dev.vocal-fit.com" npx expo start --dev-client --clear --port 8081`을 실행한다.

### EAS 빌드 설정 현황

`eas.json`:

| profile | environment | distribution | android |
|---|---|---|---|
| `development` | `development` | `internal` | `buildType: apk`, `developmentClient: true` |
| `preview` | `preview` | `internal` | `buildType: apk` |
| `production` | `production` | 기본값 | `buildType: app-bundle` |

`app.json`:

| 항목 | 값 |
|---|---|
| Expo SDK package | `expo` dependency `~54.0.33` |
| React Native | `0.81.5` |
| app name/slug/scheme | `vocal-app` |
| iOS bundle id | `com.vocal.app` |
| Android package | `com.vocal.app` |
| Android versionCode | `1` |
| Android permissions | `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `INTERNET` |
| plugins | `expo-secure-store`, `expo-dev-client` |
| EAS projectId | `e99f776b-a56b-454c-97b3-dd7a37287b4b` |
| owner | `kingjeongwoo` |

`.easignore` excludes `.git`, `node_modules`, `.expo`, `.env`, `.env.*` except `.env.example`, `.claude`, `.codex`, `*.bak`, logs/tmp, selected docs, and backup assets.

### 환경 변수 목록

값은 `.env.example`에 예시가 있으나 실제 `.env` 값은 읽지 않았다.

| 변수 | 코드 사용 위치 | 주입 위치/설명 |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `src/api/client.ts` | local `.env` 또는 shell. EAS remote build는 Expo dashboard/EAS env 값 사용. 없으면 `https://api.vocal-fit.com` fallback. |
| `EXPO_PUBLIC_USE_MOCK` | `src/api/analyze.ts`, `src/screens/karaoke/KaraokeScreen.tsx` | local `.env` 또는 EAS env. `true`면 mock result/run id 경로 사용. |
| `EXPO_PUBLIC_ENABLE_SPEECH_WEB` | `src/screens/home/HomeScreen.tsx` | local `.env` 또는 EAS env. `true`면 Home에 speech web 버튼 표시. |
| `EXPO_PUBLIC_DML_WS_URL` | `src/api/dmlClient.ts` | local `.env` 또는 shell/EAS env. 없으면 `wss://dml.vocal-fit.com` fallback. |
| `EXPO_PACKAGER_PROXY_URL` | `scripts/start-expo-cloudflare.sh` | script 내부에서 `https://expo-dev.vocal-fit.com`로 주입해 Expo dev server 실행. |

## 6. 의존성

`package.json` 기준:

| 패키지 | 버전 |
|---|---|
| `expo` | `~54.0.33` |
| `react-native` | `0.81.5` |
| `react` | `19.1.0` |
| `typescript` | `~5.9.2` |
| `@react-navigation/native` | `^7.1.31` |
| `@react-navigation/native-stack` | `^7.14.2` |
| `@react-navigation/bottom-tabs` | `^7.15.2` |
| `axios` | `^1.13.6` |
| `expo-secure-store` | `~15.0.8` |
| `expo-av` | `~16.0.8` |
| `expo-dev-client` | `~6.0.20` |
| `expo-file-system` | `~19.0.22` |
| `expo-status-bar` | `~3.0.9` |
| `@expo/ngrok` | `^4.1.3` |
| `react-native-pitchy` | `^1.2.0` |
| `react-native-audio-record` | `^0.2.2` |
| `pitchfinder` | `^2.3.4` |
| `react-native-svg` | `15.12.1` |
| `victory-native` | `^41.20.2` |
| `zustand` | `^5.0.12` |
| `react-native-reanimated` | `~4.1.1` |
| `react-native-safe-area-context` | `~5.6.0` |
| `react-native-screens` | `~4.16.0` |
| `babel-preset-expo` | `~54.0.10` |
| `@types/react` | `~19.1.0` |

## 7. git 이력

### 브랜치

```text
backup/v1-pre-v2              1e8c9be chore(v1): baseline snapshot before v2 score_mapper integration
claude/elastic-swirles-c8a3d4 2b02e6c Initial commit
master                        40895ff chore: snapshot current v2 state
```

현재 브랜치: `master`.

### 태그

```text
v1.0.0-pre-v2
v2.x-gpt-final
```

`v2.x-gpt-final`은 이 문서 작성 전 현재 상태 보존 커밋 `40895ff`에 생성했다.

### 최근 커밋

저장소에는 최근 30개 요청에 대해 실제 23개 커밋이 있었다.

```text
40895ff chore: snapshot current v2 state
2db87cd feat(v2): 비활성 카드 어둡게 + 카드 순서 재정렬 (4활성 우선)
bc07493 chore(v2): _test_stream 사전 점검 유틸 + Settings dev 버튼
2ff6f80 feat(v2-H): API timeout 확대 + 로딩 UI 안내 갱신
dd34d6f feat(v2-F): SectionList weakSections 4항목 매핑 확장
0f84a4f feat(v2-E): timeline 5 mode (softPalate/tongueTension 추가)
23ac35d feat(v2-D): 호흡 카드 정적 글로우 (v2 분기)
392e440 feat(v2-C): TierBadge 컴포넌트 + EvalItemCard 통합
6a4e629 feat(v2-B): shown_v2 분기로 4항목 활성화
319f2e3 feat(v2-A): analyze response v2 adapter
1e8c9be chore(v1): baseline snapshot before v2 score_mapper integration
3428d63 fix(P1-A): correct pitch_guide field mapping (t→time, freq→freq_hz, conf→confidence)
c90cc1b fix(P1-A): fullScreenModal, layout, totalSec NaN, pitch diagnostic logs
eae96d8 fix(P1-A): map server Song fields to domain (id, mrDurationSec, hasLrc)
d4d900c feat(P1-A): karaoke screen with LRC sync, pitch graph, MR playback
8a56b55 feat(P0): connect real server analysis API + fix field mapping
f350a30 fix: 분석 결과 응답 구조 + 도메인 키 서버 일치
e21960f fix: 폴링 종료 조건 'success' 추가 (server 실제 응답값 반영)
3aec5ab feat: P0 — 실서버 API 연동 + 분석 결과 어댑터
2a8766c feat: Step B++ — 게스트 로그인 + 개발 환경 정비
a64ea71 feat: Step B+ — EAS Android(.apk) 빌드 세팅
9d6583a feat: Step A+B — 평가 결과 화면 기반 구현
2b02e6c Initial commit
```

### `v1.0.0-pre-v2` 이후 흐름

```text
40895ff chore: snapshot current v2 state
2db87cd feat(v2): 비활성 카드 어둡게 + 카드 순서 재정렬 (4활성 우선)
bc07493 chore(v2): _test_stream 사전 점검 유틸 + Settings dev 버튼
2ff6f80 feat(v2-H): API timeout 확대 + 로딩 UI 안내 갱신
dd34d6f feat(v2-F): SectionList weakSections 4항목 매핑 확장
0f84a4f feat(v2-E): timeline 5 mode (softPalate/tongueTension 추가)
23ac35d feat(v2-D): 호흡 카드 정적 글로우 (v2 분기)
392e440 feat(v2-C): TierBadge 컴포넌트 + EvalItemCard 통합
6a4e629 feat(v2-B): shown_v2 분기로 4항목 활성화
319f2e3 feat(v2-A): analyze response v2 adapter
```

## 8. TODO/FIXME/HACK 주석

`rg -n "TODO|FIXME|HACK" -S . -g '!node_modules/**' -g '!.git/**' -g '!docs/app-ui-source-bundle.md'` 기준:

```text
src/store/recordingStore.ts:3:// TODO: Step B에서 실제 상태 정의
src/store/historyStore.ts:3:// TODO: Step B에서 실제 상태 정의
docs/HANDOVER.md:11:> **[TODO: 정우가 다른 워크스페이스(Claude vocal-app 허브)에서 정리한 인계 메시지 본문을 여기에 그대로 붙여넣기]**
src/screens/home/EvalResultScreen.tsx:29:// TODO(Step E): 사용자 목표에서 가져오기
```

## 9. 위험 지점

코드/문서에서 확인한 하드코딩, 임시방편, 깨지기 쉬운 지점:

| 위치 | 내용 |
|---|---|
| `src/api/client.ts` | `SERVER_URLS.production = 'https://api.vocal-fit.com'`, `CURRENT_SERVER = 'production'` fallback. 환경 변수가 없으면 production API로 간다. |
| `src/api/dmlClient.ts` | `DEFAULT_DML_WS_URL = 'wss://dml.vocal-fit.com'`. 주석에 `6/15 시연까지 사용` 및 env override 예정이라고 적혀 있다. |
| `src/screens/home/HomeScreen.tsx` | `SPEECH_WEB_URL = 'https://speech.vocal-fit.com'`. `EXPO_PUBLIC_ENABLE_SPEECH_WEB === 'true'`일 때만 표시. |
| `src/screens/karaoke/KaraokeScreen.tsx` | `USE_REALTIME_PITCH = true`, `MOCK_RUN_ID = 'c65d43fa-ef3f-4a46-a70e-c102c61eee6c'` 하드코딩. |
| `src/screens/karaoke/KaraokeScreen.tsx` | `songId === '004'`이면 `clearSongPitchGuideCache(songId)` 실행. 특정 곡 예외 처리. |
| `src/constants/songGuideOffsets.ts`, `src/constants/songLrcOffsets.ts` | 곡별 client-side offset 상수로 guide/LRC 시간 보정. |
| `src/domain/weakSections.ts` | 약점 구간 padding이 `PAD_START_SEC = 4`, `PAD_END_SEC = 3`으로 고정. 정렬 주석에 5/10 학원 데이터 기준 재조정 가능이라고 적혀 있다. |
| `src/screens/home/TrainingScreen.tsx` | 녹음/분석 기준 상수 다수: WebSocket timeout 3000ms, 최소 분석 3초, voice recent 900ms, input level threshold 0.06, section end trim 1초, pre-roll 1초, post-roll 0.35초. |
| `src/context/FavoritesContext.tsx` | 서버 favorites GET 응답에 `aiScore`, `zone`, `sessionId`가 없어 `aiScore: 0`, `zone: 'appropriate'`, `sessionId: undefined` placeholder를 둔다. |
| `src/api/analyze.ts` | `analyzeRecording()`은 아직 구현되지 않았고 호출 시 throw한다. |
| `src/store/recordingStore.ts`, `src/store/historyStore.ts` | zustand store가 placeholder만 가진다. |
| `src/screens/history/HistoryDetailScreen.tsx`, `src/screens/home/AnalysisResultScreen.tsx`, `src/screens/home/SessionDetailScreen.tsx` | deprecated/stub/legacy 주석이 남아 있다. |
| `src/screens/home/SongComparisonScreen.tsx`, `src/screens/goals/GoalsScreen.tsx`, `src/screens/history/HistoryDetailScreen.tsx` | `src/mock/mockData.ts`를 import한다. |
| `src/screens/auth/LoginScreen.tsx`, `SignupScreen.tsx` | `게스트로 시작 (개발/시연용)` 버튼이 있다. |
| `scripts/start-expo-cloudflare.sh` | 실행 시 8081/8082/19000/19001/19002 listener와 expo/ngrok process를 kill한다. 개발 편의용이지만 실행 영향 범위가 크다. |
| `.easignore` | `.claude`, `.codex`, `docs/HANDOVER.md`, `docs/CURRENT_STATE_v1.md`, backup assets 등을 EAS upload에서 제외한다. |
| `docs/HANDOVER.md` | placeholder TODO가 남아 있다. |

## 10. 미커밋/미푸시 상태

작업 시작 시 `git status --short --branch` 결과는 `## master`와 함께 다수의 modified/untracked/deleted 파일을 표시했다. 요청에 따라 먼저 전체 상태를 보존 커밋으로 만들었다.

보존 커밋:

```text
40895ff chore: snapshot current v2 state
73 files changed, 23267 insertions(+), 833 deletions(-)
```

주요 포함 내용:

```text
create mode 100644 .codex/APK_FEEDBACK_TRACKER.md
create mode 100644 .codex/EVAL_RUBRIC_MAPPING_DRAFT.md
create mode 100644 .codex/FEEDBACK_COPY_REPRESENTATIVE_REVIEW.md
create mode 100644 .codex/FEEDBACK_COPY_REVIEW_DRAFT.md
create mode 100644 .codex/PLANS.md
create mode 100644 .codex/TRAINING_TIMING_AUDIT.md
create mode 100644 .codex/scripts/audit-training-timing.js
create mode 100644 .easignore
create mode 100644 assets/feedback-videos/tongue-tension-excessive.mp4
create mode 100644 assets/feedback-videos/vocal-contact-excessive.mp4
create mode 100644 assets/feedback-videos/vocal-contact-insufficient.mp4
create mode 100644 docs/CURRENT_STATE_v1.md
create mode 100644 docs/HANDOVER.md
create mode 100644 docs/V2_CLOSEOUT_CHECKLIST.md
create mode 100644 docs/VOCAL_APP_CODE_VERIFICATION_2026-06-16.md
create mode 100644 docs/app-ui-source-bundle.md
create mode 100755 scripts/start-expo-cloudflare.sh
create mode 100644 src/components/eval/ImprovementPriorityCard.tsx
create mode 100644 src/components/eval/SectionStabilityChart.tsx
create mode 100644 src/components/navigation/MainTopTabs.tsx
create mode 100644 src/config/warningFilters.ts
create mode 100644 src/domain/feedbackVideos.ts
create mode 100644 src/navigation/types.ts
create mode 100644 src/services/audio/audioMode.ts
delete mode 100644 src/utils/testStream.ts
```

태그:

```text
v2.x-gpt-final -> 40895ff
```

Push 상태:

`git remote -v` 출력이 비어 있었다. `git push --follow-tags`는 아래 오류로 실패했다.

```text
fatal: No configured push destination.
Either specify the URL from the command-line or configure a remote repository using

    git remote add <name> <url>

and then push using the remote name

    git push <name>
```

따라서 이 문서 작성 시점의 브랜치와 태그는 로컬에만 있다.
