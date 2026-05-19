# V2 closeout checklist

## Scope

- This document tracks the V2 closeout items before external validation.
- Do not change `dml-server` or `vocal-server` from this app-side checklist.
- Do not change API base URL, Expo tunnel/LAN/package scripts, EAS config, or navigation routes without explicit approval.

## Completed in task 11

- Removed V2 diagnostic logs from runtime result mapping and V2 card rendering.
- Removed the Settings dev button for dml-server `_test_stream`.
- Removed the app-only `_test_stream` utility because the server endpoint is gone.
- Kept full-song `/analyze` timeout handling separate from `training-analyze` timeout handling.
- Added app-side fallback so `training-analyze` can read V2-only `scores_v2` / `scores_meta` when legacy `scores` is absent.

## Backlog, not for task 11

- 대표님 피드백 후 문구 수정.
- 연구개/혀경직도 미달/과함 의도 녹음 검증.
- dml-server score_mapper 분포 검증.
- `target_chunks` 서버 schema/endpoint/app 전환 여부 검토. 현재 vocal-app은 `timeline_scores -> extractWeakSections -> SectionList -> TrainingScreen -> trainingAnalyze` 흐름을 사용한다.
- `pressure_balance` 활성화 여부와 하압 영상 노출 여부 결정.
- 공개 데이터/성별/음역대 기반 개인화 calibration.
- 회원가입/설정 음역대 입력.
- 노래별 key 자동 조절 및 원키 선택.
- `expo-av` -> `expo-audio` migration.
- NativeEventEmitter root cause library replacement or native patch.
- production server auto-start/systemd 운영 정리.

## Production API switch checklist

- Confirm the intended runtime API base before external validation. `EXPO_PUBLIC_API_URL`, if set, overrides `CURRENT_SERVER`.
- Confirm `https://api.vocal-fit.com` auth, sessions, songs, analysis results, and pitch-guide flows on Galaxy.
- Confirm dml production integration separately: realtime WebSocket and vocal-server proxied analysis must point to the matching production stack.
- Confirm timeout expectations separately:
  - full-song `/sessions/{id}/analyze`: long-running full analysis path.
  - `/sessions/{id}/training-analyze`: short section re-analysis path.
  - `/analysis/{runId}` polling: result lookup path after full analysis starts.
- Confirm production accepts current shared request headers, including `ngrok-skip-browser-warning`.
- Confirm Android permissions and cleartext settings before representative / academy validation.
- Keep local/tunnel dev-client scripts as development-only tools; do not treat them as production API switch steps.
