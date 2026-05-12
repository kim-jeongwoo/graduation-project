# CURRENT_STATE_v1.md — vocal-app ver.1 현재 구현 상태

**기준 시점**: 2026-05-11 (5/10 학원 데이터 수집 시점 안정 동작 상태)
**백업 위치**:
- Git commit: `1e8c9be`
- Git tag: `v1.0.0-pre-v2`
- Git branch: `backup/v1-pre-v2`
- 복원: `git checkout v1.0.0-pre-v2` 또는 `git checkout backup/v1-pre-v2`

이 문서는 v2 (score_mapper_v2 + shown_v2 4항목 + tier별 UI + 호흡 강조) 작업 전 현재 구현을 코드 위치(파일+라인)와 함께 정리.

---

## 1. EvalResultScreen — 점수 카드 + 시간 구간 표시

**파일**: `src/screens/home/EvalResultScreen.tsx`

### 1-A. 9항목 분류 (`EVALUATION_ITEMS`)
**파일**: `src/domain/evaluationItems.ts:22-32`

| key | nameKo | defaultConfidence |
|---|---|---|
| `breathiness` | 호흡식별 | high |
| `vocal_fold_contact` | 접촉강도 | high |
| `nasal_oral_ratio` | 비강사용 | medium |
| `chest_head_voice` | 흉성두성 | medium |
| `forward_resonance` | 전방공명 | medium |
| `soft_palate` | 연구개위치 | medium |
| `pressure_balance` | 상압하압 | medium |
| `larynx_tongue_root` | 공명개방 | unavailable |
| `tongue_tension` | 혀경직도 | unavailable |

### 1-B. 기본/고급 탭 구조
**파일**: `EvalResultScreen.tsx:346-361`
- `BASE_ITEMS = ['breathiness', 'vocal_fold_contact']` (line 27)
- `FOCUS_ITEMS_FROM_USER: EvaluationItemKey[] = []` (line 27, 현재 비어있음)
- `basicItems = [...BASE_ITEMS, ...FOCUS_ITEMS_FROM_USER 제외 BASE]` (line 346-349)
- `advancedItems = [...high_reliability, ...medium_reliability, ...unavailable]` (line 350-354) — 서버 reliability 기반

### 1-C. 음정·박자 점수 카드 (별도)
**파일**: `EvalResultScreen.tsx:286-324, 471-489`
- `pitchPct` / `rhythmPct` 클라이언트 계산 (`useMemo`, line 286-324)
  - 데이터 소스: `userF0` + `midiSegs`
  - 음정 정확도: voiced 프레임 중 1.0반음 이내 비율 (line 291-308)
  - 박자 정확도: 각 segment 시작점 ±0.3s 내 voiced 여부 (line 310-322)
- 카드 표시: `scoreCardsRow` (line 472-489) — `showTimeline && (pitchPct || rhythmPct)` 조건
- `scoreColor()` 함수로 색상 (≥80 녹색 / ≥50 주황 / 그 외 빨강) (line 44-48)
- **상태**: 잘 동작 중, v2에서 변경 X

### 1-D. 9항목 점수 카드 (`renderCard`)
**파일**: `EvalResultScreen.tsx:364-413`
- 9항목 모두 렌더 (활성/비활성 무관 카드 자체는 보임)
- `EvalItemCard`에 전달되는 props:
  - `score`, `zone`, `confidence` (서버 `result.scores[key]`)
  - `feedbackText`, `scoreDescription` (서버 `result.feedback[key]`)
  - `isFocus`: 현재 항상 false (`FOCUS_ITEMS_FROM_USER`이 빈 배열)
  - `onTrainPress`: 호흡/접촉 외 7항목은 클릭 시 "준비 중" Alert (line 384-387)
  - `trainDisabled`: `shown_indicators` 기반 동적 분기 (line 366-370)
- 비활성 항목(unavailable)의 ScoreGauge는 자체 빈 표시 처리 (EvalItemCard 내부)

### 1-E. shown_indicators 기반 활성화
**파일**: `EvalResultScreen.tsx:366-370`
```typescript
const shownStripped = (result.timelineMetadata?.shownIndicators ?? [])
  .map(s => s.replace(/^\d+_/, '') as EvaluationItemKey);
const isShown = shownStripped.includes(key);
const trainDisabled = !isShown;
```
- 서버 응답 `timeline_metadata.shown_indicators` (현재 v1: `['4_breathiness']`)
- prefix(`4_`) 제거 후 매칭
- `trainDisabled = true` → 버튼 회색 + 클릭 시 Alert "곧 출시"
- **v2 변경 예정**: shown_v2 4항목 (3접촉/4호흡/6연구개/8혀)

### 1-F. "베타" 마크
**파일**: `src/components/eval/ConfidenceBadge.tsx:13`
- `confidence === 'medium'` → "베타" 라벨
- `confidence === 'unavailable'` → "측정 불가" 라벨
- `confidence === 'high'` → 뱃지 미표시 (`return null`)
- 위치: EvalItemCard 헤더 우측 (nameKo 옆, line 41-51 of EvalItemCard.tsx)
- 색상: `CONFIDENCE_COLORS[confidence]` (`src/theme/tokens.ts`)

### 1-G. "추후 데이터 추가 시 활성화" 메시지
**파일**: `EvalResultScreen.tsx:490-495`
```jsx
<Text style={styles.timelineInfo}>
  이 시각화는 호흡 소리 + 성대 접촉 강도 2가지 기준입니다.{'\n'}
  (다른 항목은 신뢰도가 충분히 높지 않아 시간 구간 표시 X)
</Text>
```
- 위치: 음정·박자 점수 카드 바로 아래 (탭 위)
- 조건: `showTimeline` (= songId 있음)
- **v2 변경 예정**: 4항목 기준으로 텍스트 갱신 또는 동일 유지(정우 결정)

### 1-H. "이 부분 연습하기" 버튼
**파일**: `src/components/eval/EvalItemCard.tsx:45-58` (버튼 렌더), `EvalResultScreen.tsx:367-396` (핸들러)
- EvalItemCard 헤더 우측 (ConfidenceBadge 좌측)
- 버튼 색상: `COLORS.primary` (보라 `#6C63FF`)
- `trainDisabled` 시: 회색 배경 + opacity 0.5 + 텍스트 muted
- 클릭 동작:
  - 비활성: Alert "곧 출시, 데이터 수집 후 활성화 예정입니다."
  - 활성 + breathiness/vocal_fold_contact: `extractWeakSections` 호출 + SectionList navigate
  - 활성 + 다른 항목: Alert "준비 중, 이 항목은 훈련 화면이 아직 준비되지 않았습니다."

### 1-I. 시간 구간 시각화 (TimelineSection)
**파일**: `EvalResultScreen.tsx:77-211`
- 가로 ScrollView + SVG (높이 220px)
- 가이드 라인 (미디 직선) + 사용자 F0 곡선 (정확도별 색상) + 가사 pill
- **현재 시각화 모드 활성**: pitch / breathiness / vocalFoldContact (3 mode)
  - 모드 버튼: `MODE_BUTTONS` (line 57-67)
- 모드별 색상:
  - pitch: 음정 정확도 (녹/주/빨)
  - breathiness: chunk zone (appropriate=녹, 그 외=빨)
  - vocalFoldContact: chunk zone (단, 현재 dml-server는 timeline에 호흡만 활성 → vocalFoldContact chunk 점수 없음 → 단색 "chunk 분석 비활성")
- **v2 변경 예정**: 4항목 chunk 점수 모두 활성 → vocalFoldContact 정상 표시

---

## 2. SectionListScreen — 약점 구간 리스트

**파일**: `src/screens/home/SectionListScreen.tsx`

### 2-A. 약점 구간 추출 로직
**파일**: `src/domain/weakSections.ts:33-65`
- 함수: `extractWeakSections(timelineScores, key, totalDurationSec?)`
- 필터: `chunk.scores[key].zone !== 'appropriate'`
- 매핑: `APP_TO_TIMELINE` (line 7-10)
  - `breathiness` → `breathiness`
  - `vocal_fold_contact` → `vocalFoldContact`
- 패딩:
  - `paddedStartSec = max(0, c.startSec - 4)`
  - `paddedEndSec = min(totalDurationSec ?? Infinity, c.endSec + 3)`
  - (neighbor 클램프 없음 — Phase 8에서 단순화)
- 정렬: `sortWeakSections` (line 67-76) — excessive 먼저(점수 큰 순) + insufficient(점수 작은 순)

### 2-B. WeakSection 타입
**파일**: `src/domain/weakSections.ts:23-32`
```typescript
interface WeakSection {
  chunkIndex:     number;
  paddedStartSec: number;
  paddedEndSec:   number;
  startSec:       number;
  endSec:         number;
  lrcText:        string;
  aiScore:        number;
  zone:           Zone;
}
```

### 2-C. 즐겨찾기 ⭐ 토글
**파일**: `SectionListScreen.tsx:46-58` (toggleFavorite), `78-94` (UI)
- `useFavorites()` Context 사용
- `songId` 없으면 (자유녹음) ⭐ 버튼 자체 미렌더 (line 81)
- 토글: `addFavorite` / `removeFavoriteByKey`
- ⭐ 활성 색상: `#ffd54f` (골드)

### 2-D. ZONE_LABELS
**파일**: `src/domain/weakSections.ts:17-21`
- `excessive` → "과함"
- `insufficient` → "미달"
- `appropriate` → "적절"

---

## 3. TrainingScreen — 사후 측정 + 실시간 피드백

**파일**: `src/screens/home/TrainingScreen.tsx`

### 3-A. 상태 머신
**파일**: `TrainingScreen.tsx:80-83`
```typescript
type Status = 'idle' | 'countdown' | 'recording' | 'stopped' | 'analyzing' | 'result';
```

### 3-B. 실시간 음정 일치율 (WebSocket)
**파일**: `TrainingScreen.tsx:openWs (~line 156)` + `RealtimeFeedback.tsx`
- WebSocket: `wss://dml.vocal-fit.com/ws/realtime?song_id=XXX` (`src/api/dmlClient.ts:4`)
- 송신: 200ms PCM(int16 LE 3200 samples) — recorder 콜백에서 100ms buffering
- 수신 `pitch_match` (200ms):
  - `msg.user_midi === null` → 게이지 리셋 (verdict='unknown')
  - 그 외: 5프레임 다수결 verdict (accurate/slight_off/wrong)
- 컴포넌트: `PitchCard` (RealtimeFeedback.tsx)
  - 게이지 색상: accurate=`#59dda5` / slight_off=`#ffb780` / wrong=`#ffb4ab`

### 3-C. 실시간 호흡 카드 (WebSocket)
**파일**: `TrainingScreen.tsx:openWs + BreathCard`
- 수신 `breathiness_chunk` (5초):
  - `zone` + `ai_score` → BreathCard 표시
- `indicatorKey === 'breathiness'` 진입 시만 BreathCard
- `indicatorKey === 'vocal_fold_contact'` 진입 시 `BreathInfoCard` 안내 카드 (`RealtimeFeedback.tsx`)

### 3-D. 사후 측정 (training-analyze)
**파일**: `TrainingScreen.tsx:handleAnalyze (~line 343)`, `src/api/sessions.ts:trainingAnalyze`
- 엔드포인트: `POST /sessions/{id}/training-analyze`
- multipart: `audio` (wav from `recorder.stop().uri`) + `chunk_meta` JSON
- 응답 처리:
  - `status === 'no_voice'` → Alert
  - `status === 'success' && scores[serverIndicatorKey]` → `afterScore` set + ResultCard 표시
- `serverIndicatorKey` 매핑 (TrainingScreen.tsx:72):
  - `breathiness` → `4_breathiness`
  - `vocal_fold_contact` → `3_vocal_fold_contact`

### 3-E. 피드백 텍스트 분기 (zone 기반)
**파일**: `TrainingScreen.tsx:24-37 (FEEDBACK_BY_ZONE)`, `~line 580 (UI)`
```typescript
const FEEDBACK_BY_ZONE: Record<IndicatorAppKey, Record<Zone, string>> = {
  breathiness: {
    insufficient: '성대를 더 모아 호흡 새는 소리를 줄이세요.',
    appropriate:  '현재 발성 유지하세요.',
    excessive:    '호흡을 더 섞어 부드럽게 발성하세요.',
  },
  vocal_fold_contact: {
    insufficient: '성대를 더 모아 발성하세요.',
    appropriate:  '현재 발성 유지하세요.',
    excessive:    '성대 접촉을 줄이세요.',
  },
};
```
- 사후 측정 결과(`afterScore`) 있으면 zone 기반 텍스트, 없으면 nav `feedbackText` fallback
- **v2 변경 예정**: 4항목 모두 (6연구개, 8혀 추가)

### 3-F. ResultCard (Before/After)
**파일**: `src/components/training/ResultCard.tsx`
- Before: nav `scoreInfo` (EvalResult 원본 chunk 점수)
- After: 사후 측정 응답 score
- 개선/악화/변화 없음 판정 (zone 변화 기반, line 21-43)

---

## 4. KaraokeScreen — 노래방 모드

**파일**: `src/screens/karaoke/KaraokeScreen.tsx` (624 lines)

### 4-A. 노래방 피치 그래프
**파일**: `KaraokeScreen.tsx:60-201 (PitchGraph 컴포넌트)`
- 윈도우+커서 방식: 커서 X 고정, 시간이 좌→우 흐름
- 윈도우: 전 3초 + 후 5초 (WINDOW_BEFORE_SEC=3, WINDOW_AFTER_SEC=5)
- 가이드라인: midi 직선 또는 CREPE 곡선
- 사용자 피치 색상: `getPitchAccuracy` (accurate/slight_off/wrong)
- **노래방 자체 점수 표시 없음** — 실시간 정확도 색상만

### 4-B. 노래 끝 → 분석 흐름
**파일**: `KaraokeScreen.tsx:handleStop (~line 380)`
- recorder.stop() → wav uri
- `createSession` → `uploadSessionFile` → `startAnalysis` (sync)
- run_id 받으면 `navigation.replace('EvalResult', { runId, songId })`
- 분석 단계 오버레이 (`ANALYZE_STEPS`, line 58)

### 4-C. 가이드 offset
**파일**: `src/constants/songGuideOffsets.ts`
- 노래별 가이드 시간 시프트 값 (`SONG_GUIDE_OFFSETS[songId]`)
- KaraokeScreen + TrainingScreen 둘 다 적용

---

## 5. API 처리

### 5-A. analyze 응답 (v1)
**파일**: `src/api/analyze.ts:18-63 (adaptServerResult)`
- 입력: `ServerAnalyzeResultsResponse.result_json` (prefix `1_`, `2_`, ...)
- 출력: `AnalyzeResult` (prefix 제거된 `EvaluationItemKey`)
- 변환:
  - `scores[key]`, `feedback[key]` — 9항목
  - `reliability.{high,medium,unavailable}_reliability[]`
  - `timelineScores[]` (각 chunk: `breathiness` + `vocalFoldContact` 필드만 매핑) — line 39-55
  - `timelineMetadata.shownIndicators` — line 56-60
  - `userF0` — line 61
  - `session_id` — line 21 (top-level wrapper에서)
- `stripPrefix(key)`: `key.replace(/^\d+_/, '')` (line 14-16)

### 5-B. session helpers
**파일**: `src/api/sessions.ts`
- `getSessions()` (line 14): GET /sessions
- `getSessionDetail(id)` (line 19): GET /sessions/{id}
- `extractRunId(detail)` (line 24): `detail.latest_analysis.run_id` 추출 (Phase 8)
- `trainingAnalyze(sessionId, fileUri, chunkMeta)` (line 65): 사후 측정
- `uploadSessionFile`, `startAnalysis`, `createSession`

### 5-C. timeout
**파일**: `src/api/client.ts:36`
- 기본 `apiClient.timeout = 15000` (15초)
- `startAnalysis`: 90초 override (sessions.ts:88)
- `uploadSessionFile`: 60초 override (sessions.ts:35)
- `trainingAnalyze`: 10초 override (sessions.ts:81)
- **v2 변경 예정**: 분석 후처리 추가 시 200초 검토 필요

### 5-D. dml-server WebSocket
**파일**: `src/api/dmlClient.ts`
- `DEFAULT_DML_WS_URL = 'wss://dml.vocal-fit.com'` (named tunnel)
- `buildRealtimeWsUrl(songId)` → `wss://.../ws/realtime?song_id=XXX`

### 5-E. training (즐겨찾기·시도)
**파일**: `src/api/training.ts`
- `appToServerKey`, `serverToAppKey` 매핑 (line 8-19, breathiness/vocal_fold_contact만)
- `getTrainingAttempts`, `getFavoritesList`, `postFavorite`, `deleteFavorite`

---

## 6. 컴포넌트 구조

### 6-A. EvalItemCard
**파일**: `src/components/eval/EvalItemCard.tsx`
- props: itemKey, nameKo, score, zone, confidence, feedbackText, scoreDescription, isFocus, onTrainPress, trainDisabled
- 레이아웃: 헤더(nameKo + 우측 [ConfidenceBadge + TrainBtn]) / 게이지 / 피드백 / 평가기준 토글
- `isFocus=true` 시: border `primary` 색상 + 두께 `FOCUS_BORDER_WIDTH=2` (tokens.ts:28-29)

### 6-B. ScoreGauge
**파일**: `src/components/eval/ScoreGauge.tsx`
- 0~5 점수 게이지

### 6-C. ConfidenceBadge
**파일**: `src/components/eval/ConfidenceBadge.tsx`
- "베타" / "측정 불가" 뱃지

### 6-D. SectionPitchGraph
**파일**: `src/components/training/SectionPitchGraph.tsx`
- TrainingScreen용 (구간 폭 SVG + 타임라인)
- height: 200(SVG) + 24(타임라인) = 224

### 6-E. RealtimeFeedback (PitchCard, BreathCard, BreathInfoCard)
**파일**: `src/components/training/RealtimeFeedback.tsx`
- 실시간 음정 게이지 + 호흡 카드 + 안내 카드(접촉 항목)

### 6-F. ResultCard
**파일**: `src/components/training/ResultCard.tsx`
- 사후 측정 Before/After

---

## 7. 색상 시스템

**파일**: `src/utils/colors.ts:1-16`

| 토큰 | 값 | 용도 |
|---|---|---|
| `background` | `#121212` | 전체 배경 (다크) |
| `card` | `#1E1E2E` | 카드 배경 |
| `cardBorder` | `#2A2A3E` | 카드 테두리 |
| `surface` | `#252538` | 카드 내부 서브 영역 |
| `primary` | `#6C63FF` | 주요 액센트 (보라) |
| `primaryLight` | `#8B83FF` | 밝은 액센트 (밝은 보라) |
| `success` | `#4CAF50` | 성공/긍정 (녹) |
| `warning` | `#FFC107` | 경고 (노랑) |
| `danger` | `#f44336` | 실패 (빨강) |
| `textPrimary` | `#EAEAEA` | 주요 텍스트 |
| `textSecondary` | `#9E9E9E` | 보조 텍스트 |
| `textMuted` | `#666666` | 흐린 텍스트 |
| `divider` | `#2A2A3E` | 구분선 |
| `fab` | `#f44336` | FAB 버튼 |

**메인 톤**: 보라 `#6C63FF` (primary) + 다크 `#121212` (background) + 카드 남색-회색 톤 `#1E1E2E / #252538`.

### 보색 후보 (v2 호흡 강조용)
- 메인 보라 `#6C63FF` (HSL 약 243°)의 보색은 노랑·오렌지 계열 (HSL 약 60-30°)
- 후보:
  - **골드** `#FFC107` (warning과 같음 — 충돌 가능, 회피)
  - **앰버** `#FFB300`
  - **소프트 옐로우** `#FFD54F` (이미 ⭐ 즐겨찾기에 사용)
  - **오렌지골드** `#FFA726`
- 추천: `#FFA726` (오렌지골드) 또는 `#FFD54F` (이미 사용) — v2 spec에서 정우 결정 필요

### Pitch accuracy 색상 (고정)
- `accurate` → `#59dda5` (밝은 녹)
- `slight_off` → `#ffb780` (주황)
- `wrong` → `#ffb4ab` (연한 빨강)
- `unknown` → `#7ecfff` (밝은 파랑) 또는 `textMuted`

### CONFIDENCE_COLORS
**파일**: `src/theme/tokens.ts`
- medium / unavailable 별 색상 정의 (베타/측정불가 뱃지용)

---

## 8. 네비게이션 구조

**파일**: `src/navigation/AppNavigator.tsx`

```
RootStack (auth 분기)
├─ AuthNavigator (Login, Signup)
└─ AppRootNavigator (Stack)
   ├─ MainTabs (BottomTab)
   │  ├─ HomeTab → HomeStack (Home, SessionDetail, AnalysisResult,
   │  │            Settings, Profile, VocalRangeTest, SongComparison,
   │  │            SongDetail, EvalResult, SectionList, Training)
   │  ├─ RecordTab → ResultStack (LatestAnalysis, EvalResult,
   │  │             SectionList, Training)  [라벨 "분석 결과" 📈]
   │  ├─ HistoryTab → HistoryStack (HistoryList, HistoryDetail [deprecated],
   │  │              SongHistory, Favorites, Training, EvalResult,
   │  │              SectionList, SongComparison)
   │  └─ GoalsTab → GoalsScreen
   └─ Karaoke (fullScreenModal)
```

### Tab listeners (popToTop)
- HomeTab: `tabPress` → `navigation.dispatch(CommonActions.navigate({ name: 'HomeTab', params: { screen: 'Home' } }))`
- RecordTab: 동일 패턴, `screen: 'LatestAnalysis'` (재fetch + reset to EvalResult)

---

## 9. 주요 데이터 흐름

### 9-A. 노래 분석 흐름
KaraokeScreen → 녹음 → handleStop → createSession → uploadSessionFile → startAnalysis (sync, ~30s) → run_id → EvalResult (push to HomeStack)

### 9-B. 약점 구간 훈련 흐름
EvalResult → "이 부분 연습하기" → SectionList (extractWeakSections) → 카드 클릭 → Training → 카운트다운 → MR + WebSocket + recorder → 정지 → 사후 측정 → ResultCard

### 9-C. 즐겨찾기 흐름
SectionList ⭐ 토글 → POST /users/me/favorites → FavoritesContext state
HistoryTab → ⭐ 즐겨찾기 → FavoritesScreen → 카드 클릭 → getResultsByRunId 재조회 → Training 진입

### 9-D. 분석 결과 탭 흐름
RecordTab 클릭 → LatestAnalysisScreen (useFocusEffect) → GET /sessions → 최신 completed → getSessionDetail → extractRunId → CommonActions.reset → EvalResult

### 9-E. 히스토리 흐름
HistoryTab → HistoryScreen (곡별 폴더, song_id 그룹화) → 곡 카드 → SongHistoryScreen (회차 리스트) → 회차 카드 → getSessionDetail → extractRunId → EvalResult

---

## 10. 5/10 학원 검증 완료 동작

- ✅ EvalResult 9항목 표시 + 호흡/접촉 활성 + 7항목 disabled + Alert
- ✅ Timeline (호흡 chunk zone 색상)
- ✅ SectionList → Training → 카운트다운 → MR + 실시간 음정/호흡
- ✅ 사후 측정 (호흡, 접촉) + Before/After
- ✅ 즐겨찾기 (서버 sync)
- ✅ 히스토리 곡별 폴더
- ✅ 분석 결과 탭 자동 EvalResult 이동
- ✅ 노래방 → 분석 → EvalResult 흐름

---

## 11. v2 작업 시 건드리지 말 것 (정우 명시)

- 음정/박자 카드 (별도 클라이언트 계산)
- 기본/고급 탭 구조
- 베타 뱃지 표시 (ConfidenceBadge)
- 비활성 항목 어둡게 처리 + Alert
- "추후 데이터 추가 시 활성화" 안내 텍스트 영역 (텍스트 내용은 4항목으로 갱신 가능)
- 시간 구간 시각화 컴포넌트 자체 (TimelineSection)
- KaraokeScreen 동작
- 즐겨찾기 / 곡별 폴더 / 분석 결과 탭 / 사후 측정 흐름

## 12. v2 변경 영역 (Step 3 spec에서 상세화)

A. analyze 응답 v2 분기 (`score_mapper_version === 'v2'` 시 `scores_v2 + scores_meta + reliability.shown_v2`)
B. shown_v2 4항목 활성화 (3, 4, 6, 8)
C. tier별 UI (high / high_star + 별표 + 툴팁)
D. 호흡소리식별 카드 강조 (보색 정적 글로우)
E. timeline_scores 4항목 처리
F. SectionList 약점 구간 4항목
G. TrainingScreen 사후 측정 4항목 (FEEDBACK_BY_ZONE 확장)
H. API timeout 200s 검토
