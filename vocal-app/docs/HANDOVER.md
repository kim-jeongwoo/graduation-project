# HANDOVER.md — vocal-app GPT 이관 인계 문서

**작성일**: 2026-05-12
**대상**: vocal-app 워크스페이스 (Claude → GPT 이관)
**관련 문서**: `docs/CURRENT_STATE_v1.md` (5/10 v1 baseline), `docs/dev-flow.md`, `AGENTS.md`, `CLAUDE.md`

---

## 1. 정우 인계 메시지

> **[TODO: 정우가 다른 워크스페이스(Claude vocal-app 허브)에서 정리한 인계 메시지 본문을 여기에 그대로 붙여넣기]**

---

## 2. 현재 구현 상태

### 2-A. v1 baseline (5/10 학원 데이터 수집 시점)
- 자세한 항목: `docs/CURRENT_STATE_v1.md` 참조
- Git: commit `1e8c9be` / tag `v1.0.0-pre-v2` / branch `backup/v1-pre-v2`
- 복원: `git checkout v1.0.0-pre-v2` 또는 `git checkout backup/v1-pre-v2`

### 2-B. v2 통합 작업 (5/11~5/12 진행, 진행 중)

#### Step 1 (A+B+C) — 완료 + 갤럭시 검증 OK
- **A (commit `319f2e3`)** — `src/types/analyze.ts` + `src/api/analyze.ts` v2 adapter
  - `ScoreTier`, `ScoreMetaEntry` 타입 추가
  - `adaptServerResult`: `score_mapper_version === 'v2' && scores_v2` detect → `scoresV2`/`scoresMeta`/`reliability.shownV2/academicOnlyV2/deferredV2` 매핑
  - timeline_scores 4항목 (3접촉/4호흡/6연구개/8혀) + `lowConfidenceItems` 매핑
  - zone 부재 시 `deriveZone(rounded)` 유도
  - v1 응답 호환 유지
- **B (commit `6a4e629`)** — `EvalResultScreen.renderCard` shown 매핑 v1/v2 분기
  - v2: `reliability.shownV2` 사용 / v1: `timelineMetadata.shownIndicators` (기존)
- **C (commit `392e440`)** — `TierBadge` 컴포넌트 + `EvalItemCard` 통합
  - `src/components/eval/TierBadge.tsx` 신설: `*` 골드 `#FFD54F`, tap → Alert tooltip
  - `EvalItemCard` `tier?` + `tooltip?` props + 헤더 우측 통합

#### Step 2 (D+E) — 완료, 갤럭시 검증 OK
- **D (commit `23ac35d`)** — 호흡 카드 정적 글로우
  - `EvalItemCard` `isHighlighted` prop + `highlightCard` 스타일 (`#8B83FF` 보더 2px + shadow 0.6/8 + elevation 8)
  - `renderCard` 조건: `key === 'breathiness' && scoreMapperVersion === 'v2'`
- **E (commit `0f84a4f`)** — Timeline 5 mode
  - `VisualizationMode`에 `softPalate` / `tongueTension` 추가
  - `MODE_BUTTONS`: 5번째/6번째 v2Only 버튼 (연구개/혀)
  - `TimelineSection.getColor` 4 zone 분기
  - `LEGEND_ITEMS` ZONE_LEGEND 공유 (4항목)
  - `timelineInfo` v2 분기 텍스트 "호흡 + 접촉 + 연구개 + 혀 4가지 기준"

#### Step 3 (F) — 완료
- **F (commit `dd34d6f`)** — `src/domain/weakSections.ts`
  - `IndicatorAppKey` 확장: `soft_palate`, `tongue_tension` 추가
  - `APP_TO_TIMELINE`, `INDICATOR_LABELS` 매핑 확장
  - `extractWeakSections` 자동 작동 (매핑만 추가)

#### Step 4 (H) — 완료
- **H (commit `2ff6f80`)** — API timeout + 로딩 UI
  - `trainingAnalyze`: 10s → 30s
  - `startAnalysis`: 90s → 200s
  - KaraokeScreen `analyzeHint`: "분석 중... (1~2분 소요)"

#### 추가 작업 (commit `2db87cd`) — 완료
- **비활성 5항목 카드 어둡게** — `EvalItemCard` `isDimmed?: boolean` prop + `dimmedCard` (opacity 0.55). v2 분기 시 `trainDisabled` 항목에 적용.
- **카드 순서 재정렬 (v2 분기)**:
  - BASIC_V2: `[breathiness, vocal_fold_contact, soft_palate, tongue_tension]`
  - ADVANCED_V2: `[nasal_oral_ratio, chest_head_voice, forward_resonance, pressure_balance, larynx_tongue_root]`
  - v1 응답은 기존 reliability 기반 순서 유지

#### Step 3 G — 진행 중 (검증 대기)
- 사후 측정 4항목 (FEEDBACK_BY_ZONE 확장 / serverIndicatorKey 매핑 / SoftPalateInfoCard·TongueTensionInfoCard / low_confidence_items 마크)
- 정우 갤럭시에서 `/sessions/{id}/training-analyze` 응답 raw 확인 후 진행 결정
  - Case A (v2 응답): Step 3 G 본격 작업
  - Case B (v1 응답): dml-server `/analyze-chunk` v2 누락, 별도 작업 후 진행

---

## 3. 진단 로그 정리 필요 (Step 3 G 완료 후 일괄 제거)

### 3-A. `[V2 진단]` (Step 1 검증용)
| 파일 | 라인 위치 | 내용 |
|---|---|---|
| `src/api/analyze.ts` | `adaptServerResult` 진입부 | 6줄 (raw keys / score_mapper_version / has scores_v2 / has scores_meta / reliability keys / shown_v2 / isV2 detect) |
| `src/screens/home/EvalResultScreen.tsx` | `renderCard` `key === 'breathiness'` 가드 | 5줄 (scoreMapperVersion / reliability.shownV2 / shownStripped / tier / tooltip) |
| `src/components/eval/TierBadge.tsx` | 컴포넌트 진입부 | 1줄 (nameKo / tier / tooltip) — 9항목마다 출력 |

### 3-B. `[V2 진단 chunk]` (사후 측정 검증용)
| 파일 | 위치 | 내용 |
|---|---|---|
| `src/api/sessions.ts` | `trainingAnalyze` 응답 직후 (return 직전) | 1줄 (response.data raw 1500자 slice) |

### 3-C. `[stream test]` (P1-3 streaming 사전 점검 — 검증 OK 후 제거 필요)
| 파일 | 정리 |
|---|---|
| `src/utils/testStream.ts` | **파일 자체 삭제** (dml-server `_test_stream` endpoint 제거됨) |
| `src/screens/settings/SettingsScreen.tsx` | `__DEV__` 가드 dev 버튼 + import 제거 |

### 3-D. 일괄 제거 검증
```bash
grep -rn "진단\]\|진단 chunk\]\|stream test\]\|V2 진단" src/ 2>/dev/null
# 결과 0개 확인
```

---

## 4. 미해결/백로그 항목 (5/10 후 작업 예정)

| 항목 | 작업 | 우선순위 |
|---|---|---|
| 401 자동 로그인 갱신 | client.ts interceptor에 토큰 만료 시 navigate to Login | 5/16 (학원 14일 실험 중간) |
| expo-updates 도입 | OTA 업데이트 가능하게 (네이티브 변경 없는 수정용) | 5/14 후 |
| admin Phase A-5 | 사용자 상세 화면 | 5/14 후 |
| 이슈 5 dml-server 측 PCM 임계값 | 음성 미감지 자주 발생 → 임계값 조정 | dml-server 측 |
| 이슈 4 마이크 볼륨 자동 조정 | 노래방·훈련 마이크 입력 정규화 | 5/14 후 |
| 7개 deferred 항목 활성화 | 학습 후 dml-server shown_indicators 확장 시 자동 활성화 (코드 변경 없음) | 데이터 학습 후 |

---

## 5. 워크스페이스 구조 요약

### 5-A. 디렉토리 핵심
```
vocal-app/
├─ src/
│  ├─ api/
│  │  ├─ client.ts        # axios + JWT interceptor (timeout 15s default)
│  │  ├─ analyze.ts       # adaptServerResult v1/v2 분기 ★
│  │  ├─ sessions.ts      # getSessions, getSessionDetail, trainingAnalyze (timeout 30s) ★
│  │  ├─ songs.ts         # /songs, /songs/{id}/mr, /songs/{id}/pitch-guide
│  │  ├─ dmlClient.ts     # WebSocket URL (wss://dml.vocal-fit.com)
│  │  └─ training.ts      # favorites + training-attempts endpoints
│  ├─ components/
│  │  ├─ eval/
│  │  │  ├─ EvalItemCard.tsx    # 9항목 카드 (tier, tooltip, highlighted, dimmed) ★
│  │  │  ├─ TierBadge.tsx       # * 골드 + tap Alert ★
│  │  │  ├─ ConfidenceBadge.tsx # 베타/측정불가
│  │  │  └─ ScoreGauge.tsx
│  │  └─ training/
│  │     ├─ SectionPitchGraph.tsx
│  │     ├─ RealtimeFeedback.tsx  # PitchCard, BreathCard, BreathInfoCard
│  │     └─ ResultCard.tsx
│  ├─ context/
│  │  ├─ AuthContext.tsx
│  │  ├─ FavoritesContext.tsx   # 서버 sync 즐겨찾기
│  │  └─ GoalsContext.tsx
│  ├─ domain/
│  │  ├─ evaluationItems.ts     # 9항목 정의
│  │  └─ weakSections.ts        # extractWeakSections (4항목) ★
│  ├─ screens/
│  │  ├─ home/
│  │  │  ├─ EvalResultScreen.tsx    # 9항목 카드 + Timeline + 음정/박자 ★
│  │  │  ├─ SectionListScreen.tsx
│  │  │  ├─ TrainingScreen.tsx      # 실시간 + 사후 측정 + FEEDBACK_BY_ZONE ★
│  │  │  └─ HomeScreen.tsx
│  │  ├─ karaoke/
│  │  │  └─ KaraokeScreen.tsx       # 노래방 (analyzeHint 1~2분) ★
│  │  ├─ history/
│  │  │  ├─ HistoryScreen.tsx       # 곡별 폴더
│  │  │  ├─ SongHistoryScreen.tsx
│  │  │  └─ FavoritesScreen.tsx
│  │  ├─ record/
│  │  │  └─ RecordScreen.tsx        # = LatestAnalysisScreen (분석 결과 탭)
│  │  ├─ settings/
│  │  │  └─ SettingsScreen.tsx      # __DEV__ testStream 버튼 (제거 필요)
│  │  └─ auth/
│  ├─ navigation/
│  │  └─ AppNavigator.tsx           # HomeStack, ResultStack, HistoryStack
│  ├─ types/
│  │  └─ analyze.ts                 # AnalyzeResult, ScoreTier, ScoreMetaEntry ★
│  └─ utils/
│     ├─ colors.ts                  # COLORS (보라 #6C63FF 메인)
│     └─ testStream.ts              # 임시 (제거 필요)
├─ docs/
│  ├─ CURRENT_STATE_v1.md           # v1 baseline 상세
│  ├─ HANDOVER.md                   # 이 문서
│  ├─ android-install.md
│  └─ dev-flow.md
├─ android/                          # 없음 (Expo managed)
├─ app.json                          # Expo 설정 (usesCleartextTraffic, network_security_config)
├─ eas.json                          # EAS build profiles (development/preview/production)
├─ App.tsx
├─ AGENTS.md                         # 에이전트 규칙
└─ CLAUDE.md                         # Claude 작업 규칙
```

★ = v2 작업 영향 파일

### 5-B. 주요 토큰
- 메인 보라: `#6C63FF` (primary), `#8B83FF` (primaryLight, 호흡 글로우)
- 골드: `#FFD54F` (즐겨찾기 ⭐, TierBadge `*`)
- Zone 색상: 적절 `#59dda5`, 과함/미달 `#ffb4ab`, 데이터없음 `#7ecfff`
- Pitch accuracy: accurate `#59dda5`, slight_off `#ffb780`, wrong `#ffb4ab`

---

## 6. 서버 연동 환경

| 서버 | URL | 처리 |
|---|---|---|
| vocal-server | `https://api.vocal-fit.com` (Cloudflare Tunnel) | REST API (auth, sessions, songs, favorites, analysis) |
| dml-server | `wss://dml.vocal-fit.com` (named tunnel) | WebSocket 실시간 (`/ws/realtime`) + REST (`/analyze`, `/analyze-chunk`) via vocal-server proxy |

- `src/api/client.ts` `CURRENT_SERVER = 'production'` (5/10 학원 실험부터)
- `src/api/dmlClient.ts` `DEFAULT_DML_WS_URL = 'wss://dml.vocal-fit.com'`

---

## 7. EAS 빌드

- 프로필: `preview` (APK + internal distribution, dev client 미포함)
- 명령: `eas build --platform android --profile preview --non-interactive --no-wait`
- 마지막 빌드: 5/9 ~21분 소요 (run ID `70b4e3a5-...`)
- 빌드 후 APK 다운로드 URL은 Expo 대시보드 참조

---

## 8. 작업 원칙 (CLAUDE.md, AGENTS.md 참조)

1. ver.1 (`v1.0.0-pre-v2`) 백업 유지. 큰 문제 시 즉시 복원.
2. 음정/박자 카드, 기본/고급 탭, 베타 뱃지, 비활성 처리, KaraokeScreen, 즐겨찾기/곡별 폴더/분석 결과 탭/사후 측정 흐름 — 건드리지 말 것.
3. 새 기능은 기존 위에 확장만. 추측 X.
4. 갤럭시 Metro 검증 안 되면 진단 우선.
5. Step 완료 시 commit. 갤럭시 검증 후 다음 Step.

---

## 9. 다음 단계 (5/12 EOD)

1. **정우 갤럭시 Metro에서 사후 측정 응답 확인** (`[V2 진단 chunk]` raw)
   - Case A: v2 응답 → Step 3 G 작업 시작
   - Case B: v1 응답 → dml-server 측 별도 작업 필요
2. Step 3 G 작업 (Case A 확정 시):
   - `FEEDBACK_BY_ZONE` 4항목 확장 (soft_palate, tongue_tension 추가)
   - `serverIndicatorKey` 매핑 추가 (`soft_palate → 6_soft_palate`, `tongue_tension → 8_tongue_tension`)
   - `SoftPalateInfoCard`, `TongueTensionInfoCard` 신규 컴포넌트
   - `ResultCard` low_confidence_items "신뢰도 낮음" 마크
3. 진단 로그 일괄 제거 (`grep` 검증)
4. `testStream.ts` 파일 + Settings dev 버튼 제거 (`_test_stream` endpoint 제거됨)
5. 5/13 대표님 사전 배포 → 5/14 학원 배포
