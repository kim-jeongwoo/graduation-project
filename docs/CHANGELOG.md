# Changelog

이 파일은 `graduation-project` monorepo의 주요 변경 이력을 기록한다.

## 2026-05-13

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
