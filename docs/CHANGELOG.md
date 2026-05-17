# Changelog

이 파일은 `graduation-project` monorepo의 주요 변경 이력을 기록한다.

## 2026-05-14

### Vocal App Stability Batch #1

- full analyze를 즉시 응답 + polling UX에 맞춰 안정화했다.
- 구간훈련 녹음 window와 `chunk_meta`를 실제 target chunk 기준으로 정렬했다.
- production 완곡 업로드 timeout/UX를 보강하고 결과 화면 이동 흐름을 안정화했다.
- song004 pitch-guide 작업은 현 단계에서 종료하고 앱 임의 offset을 제거했다.
- 결과 카드 피드백/신뢰도 UI를 정리했다.
  - 연구개위치 / 혀경직도에 보수적 feedback fallback 추가.
  - 연구개위치 / 혀경직도의 `high_star` 노란 별 표시 제거.
  - v2 표시 항목에 점수가 있을 때 legacy `unavailable` 때문에 “측정 불가”가 뜨는 모순 보정.

### Validation

- production API 기준 앱 진입, 로그인, 곡 목록 로드 확인.
- song004 KaraokeScreen 진입, MR 재생, 가사 표시, 녹음 확인.
- 완곡 업로드와 full analyze async polling 성공.
- 결과 화면 이동과 히스토리 저장 정상 확인.
- 구간훈련 녹음 window / `chunk_meta` 정렬 후 한 소절 정상 발성 success 확인.
- 연구개위치 / 혀경직도 결과 카드 점수와 피드백 표시 확인.
- 혀경직도 “측정 불가” 뱃지 제거, 연구개/혀경직도 노란 별 제거 확인.

### Notes

- 이 PR은 Batch #1 반영용이며 main merge는 포함하지 않는다.
- pitch-guide asset work는 여러 곡 수동 정렬 완료 후 재개한다.
- `.codex/ACTIVE_PLAN.md`, raw handover docs, 개인 LAN IP scripts는 snapshot에서 제외한다.

## 2026-05-13

### V2 Closeout PR

- 녹음 재시작, pitch-guide cache/fallback, no_voice 결과 화면 차단 흐름을 Galaxy 검증 결과 기준으로 반영.
- `shown_v2` 4항목 카드/그래프와 weak section/구간훈련 흐름을 `rounded_score` 기준으로 보정.
- V2 진단 로그와 dml-server `_test_stream` dev 버튼/유틸 제거.
- `result_json.status` 실패 guard와 `training-analyze` v2 fallback을 추가.
- `vocal-app/docs/V2_CLOSEOUT_CHECKLIST.md` 추가.

### Added

- `vocal-app/` workspace를 monorepo에 추가.
- `docs/VOCAL_FIT_PROJECT_OVERVIEW.md` 추가.
- `docs/VOCAL_APP_CURRENT_STATE.md` 추가.
- root `README.md`에 Vocal App 요약/링크 섹션 추가.

### Snapshot Details

| 항목 | 내용 |
|---|---|
| branch | `add-vocal-app-2026-05-13` |
| commit | `f1168fb feat: add vocal-app project snapshot` |
| base | `main` / `16a11e0` |
| 포함 | `vocal-app/` source, app docs, root project docs |
| 제외 | `.git/`, `node_modules/`, `.expo/`, `.claude/`, 실제 `.env*`, `*.bak` |

주요 앱 변경 범위:

- Step 3G 4항목 훈련 지원 관련 snapshot
- full analyze status UX hardening
- pitch-guide 로드/재진입 안정화
- 앱 handover/current-state 문서 포함
- 개인 LAN IP가 박힌 `package.json` script는 포함하지 않음

### Verified

- Galaxy dev-client에서 곡 004 pitch guide 로드 확인.
- 완곡 4분 녹음/분석 성공.
- 분석 결과 화면 회색 pitch guide 라인 표시 정상.
- 녹음된 실시간 피치 표시 정상.
- 과거 분석 결과 재진입 시 가이드라인 유지 확인.
- 목소리 입력 없는 녹음에서 결과 화면으로 이동하지 않고 안내 표시 확인.

### Notes

- 기존 `main` 직접 push 없이 `add-vocal-app-2026-05-13` branch에서 작업.
- 기존 `vocal-server/`, `dml-server/`, root README/docs를 삭제하지 않음.
- 앱 snapshot 복사 시 `.env*`, `.git/`, `node_modules/`, `.expo/`, `.claude/`, `assets/*.bak` 등은 제외.
- 개인 LAN IP script 변경은 포함하지 않음.
- PR 생성 후 main merge는 정우 최종 OK 전까지 보류.

### Known Limitations

- `npx tsc --noEmit`은 기존 navigation typing baseline 오류가 있어 별도 정리가 필요하다.
- `혀, 구강 공간의 경직도` 연습 화면 내용과 녹음 재시작 flow는 backlog로 남아 있다.
- 외부 검증 전 production API 전환과 smoke test가 필요하다.

## 2026-05-10~2026-05-12

### Vocal App

- v1 baseline을 `v1.0.0-pre-v2`로 보존.
- v2 score mapper adapter 추가.
- `shown_v2` 기반 4항목 우선 표시.
- TierBadge, timeline 5 mode, weakSections 4항목 매핑 추가.
- full analyze status UX hardening 추가.
- `no_voice`, `failed`, `invalid`, `error` 상태에서 결과 화면 이동을 차단하는 방향으로 개선.

### Server/DML

- `vocal-server`가 DML 분석 결과를 저장하고 앱 API로 전달.
- `training-analyze` 응답의 v2 필드 passthrough 확인.
- Cloudflare timeout과 streaming behavior 관련 운영 문서 보강.
