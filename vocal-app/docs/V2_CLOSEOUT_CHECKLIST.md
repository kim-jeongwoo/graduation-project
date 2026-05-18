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

## Completed through Batch #4

- Batch #2: navigation typing cleanup, diagnostic log cleanup, SDK warning triage, research-palate/tongue-tension copy refinement, V2 graph color mapping.
- Batch #3: Favorites/History/Record UX, Karaoke cleanup/no_voice retry, 401 re-login UX, 9-item description/status copy, empty/error state cleanup.
- Batch #4: evaluation-rubric-based copy for active indicators, SectionList/Training feedback synchronization, evaluation criteria copy, inactive five-card UX, Cloudflare dev tunnel start script.

## Backlog, not for task 11

- Pitch-guide 수동 정렬 완료 후 song004 및 다른 곡에 재반영한다.
- MR/LRC/pitch-guide 정합성을 여러 곡에서 최종 검증한다.
- 대표님 피드백 반영 후 문구를 수정한다.
- 연구개/혀경직도 미달/과함 의도 녹음과 dml-server score_mapper 분포를 추가 검증한다.
- 공개 데이터/성별/음역대 기반 개인화 calibration은 입력 테스트와 분리해 별도 설계한다.
- 회원가입/설정 음역대 입력과 노래별 key 자동 조절/원키 선택은 후속 기능으로 다룬다.
- `expo-av` -> `expo-audio` migration과 NativeEventEmitter root cause replacement/native patch는 SDK warning cleanup backlog로 유지한다.
- production server auto-start/systemd 운영 정리는 서버 운영 backlog로 유지한다.

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
