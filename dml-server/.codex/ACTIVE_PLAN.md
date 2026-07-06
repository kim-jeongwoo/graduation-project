# dml-server active plan

## Status

completed

## Goal

Regenerate only song `007` guide-editor pitch-guide candidate against the new MR at `/tmp/007_new_mr.mp3`.

## Scope

- Existing `007` candidate from `/tmp/guide-editor-f0-candidates-20260517-222703/` is stale because it used the old MR.
- Keep `002`, `006`, and `014` candidates unchanged.
- Use existing dml-server original/master, LRC, cached Demucs stems, and cached CREPE F0 for `007`.
- Write new outputs only under `/tmp/guide-editor-f0-candidates-20260517-222703-007-new-mr/`.

## Non-goals

- Do not change dml-server production service/schema/model/API.
- Do not write to production app/storage or vocal-server target.
- Do not permanently modify repo/data source files.
- Do not run git mutations, service operations, process signals, or long `/analyze`.

## Current facts

- `/tmp/007_new_mr.mp3` exists.
- `/tmp/007_new_mr.mp3` decodes as 48kHz stereo, 233.882s, 9,355,298 bytes.
- Existing old `007` candidate is stale because it used the old MR duration 236.860s and offset 2.854s.
- New MR alignment estimate: offset 0.096s, confidence medium, correlation peak 0.5487.

## Files changed

- `.codex/ACTIVE_PLAN.md` updated for this follow-up.
- Created `/tmp/guide-editor-f0-candidates-20260517-222703-007-new-mr/`.
- Created `/tmp/guide-editor-f0-candidates-20260517-222703-007-new-mr/candidates/007_pitch_guide_candidate_new_mr.json`.
- Created report/summary/previews under the same `/tmp` work dir.

## Validation

- New candidate validation passed: 23388 points, 260 segments, `timebase=mr_current_time_sec`.
- Status: `007_NEW_MR_REVIEW` due medium alignment confidence.
- No production service/schema/model/API, repo data source, or git mutation was performed.

## Risks

- New MR is closer in duration to the original, but alignment confidence remains medium; 007 timing should be checked first in guide-editor.

## Next action

- Share new 007 candidate package with vocal-server guide-editor team; keep 002/006/014 candidates from the prior package unchanged.

## Resume instructions

- Resume from this plan, use `/tmp/007_new_mr.mp3`, and avoid production/service/git mutations.
