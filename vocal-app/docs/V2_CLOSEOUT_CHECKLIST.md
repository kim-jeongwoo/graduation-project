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

- Add better feedback copy for soft palate and tongue tension cards.
- Revisit whether the yellow high-star mark should appear only on trusted cards.
- Investigate realtime pitch gauge / voice recognition behavior in section training.
- Improve per-item training method and feedback copy after Jungwoo review.

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

## APK feedback follow-up status

- 47 Karaoke MR start failure hardening is included: local MR cache fallback and MR download/load/play/recorder-start stage split.
- 48 TrainingScreen audio focus hotfix is included: AppState/focus/audio mode guard before section-training MR start.
- Feedback video modal playback is included: visible-only `Video` mount plus explicit play/pause control.
- Galaxy validation completed for TrainingScreen MR start, recording start, pause/resume, section analysis, feedback video open/play/close, video close followed by MR restart, and Karaoke MR/pause/resume/full analyze.
- After PR merge, create a new preview APK and reshare the corrected APK link before wider representative testing.
