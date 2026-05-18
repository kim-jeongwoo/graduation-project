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

## Completed in Batch #1

- Added full analyze async polling UX for production-style analysis.
- Aligned segment training recording window and `chunk_meta` with the actual target chunk.
- Hardened production full-song upload timeout and result navigation UX.
- Closed song004 pitch-guide work for the current stage and removed app-side arbitrary offset handling.
- Added conservative feedback fallback for soft palate and tongue tension result cards.
- Removed `high_star` yellow visual emphasis from soft palate and tongue tension cards.
- Corrected v2 shown indicator confidence display so a scored tongue tension card does not show “측정 불가”.
- Kept breathiness and vocal fold contact result-card behavior unchanged.

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

## Batch #2 follow-up

- Navigation typing baseline cleanup completed; source repo TypeScript noEmit passes.
- Temporary V2 score distribution and rendered color audit logs were removed after Galaxy verification.
- V2 graph color policy keeps missing score neutral, low confidence first, and rounded_score-only zone coloring.
- Soft palate and tongue tension feedback wording is refined without changing score thresholds.
- Settings microphone input test is a supporting input test, not completed personalized calibration.

## Remaining backlog after Batch #2

- Intentional recordings for soft palate / tongue tension insufficient and excessive cases.
- dml-server score_mapper distribution validation.
- Additional feedback wording based on the 4/6~5/10 evaluation sheets.
- expo-av to expo-audio migration.
- NativeEventEmitter root cause library replacement or native patch.
