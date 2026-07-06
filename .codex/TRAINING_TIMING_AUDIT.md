# 37 - Training Timing Audit

Date: 2026-05-19
Scope: read-only audit of local vocal-server song storage plus app-side TrainingScreen timing policy.

## Sources

- LRC: `/Users/kimjeongwoo/vocal-server/vocal-server/app/storage/songs/lrc/parsed/{songId}.json`
- Pitch guide: `/Users/kimjeongwoo/vocal-server/vocal-server/app/storage/songs/pitch_guide/{songId}.json`
- App formula audited by: `.codex/scripts/audit-training-timing.js`

## Current App Finding

Before this task, `TrainingScreen` applied `SECTION_END_TRIM_SEC = 1` to both:

- target chunk end used by the green marker / "불러야 하는 구간"
- recording end / `chunk_meta.end_sec`

That made the displayed target and analyzed audio window end one second before the source LRC chunk. For short LRC lines this removes a large portion of the phrase.

## Five-Song Summary

| songId | LRC lines | guide segments | current target < 90% of LRC | no guide overlap | low guide overlap | target under 3s | min current coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| 004 | 25 | 230 | 22 | 0 | 2 | 0 | 0.780 |
| 006 | 35 | 199 | 35 | 6 | 2 | 2 | 0.558 |
| 002 | 35 | 300 | 32 | 0 | 1 | 0 | 0.680 |
| 014 | 24 | 251 | 22 | 0 | 3 | 0 | 0.800 |
| 007 | 38 | 260 | 38 | 1 | 1 | 5 | 0.253 |

## Worst Examples

| songId | section | LRC start-end | current coverage | guide overlap | issue |
|---|---:|---|---:|---:|---|
| 004 | 22 | 204.550-209.100 | 0.780 | 0.818 | 1s trim cuts LRC end |
| 004 | 12 | 118.040-122.740 | 0.787 | 0.779 | 1s trim cuts LRC end |
| 006 | 15 | 91.690-93.950 | 0.558 | 0.000 | short line plus no guide overlap |
| 006 | 17 | 98.160-101.130 | 0.663 | 0.017 | short line plus guide mismatch |
| 002 | 5 | 45.054-48.182 | 0.680 | 0.937 | 1s trim cuts LRC end despite guide coverage |
| 014 | 1 | 31.040-36.040 | 0.800 | 0.744 | 1s trim cuts LRC end |
| 007 | 36 | 210.117-211.455 | 0.253 | 0.613 | very short line; 1s trim removes most target |
| 007 | 37 | 232.292-233.630 | 0.253 | 0.000 | very short line plus no guide overlap |

## Applied App Policy

- target marker: `chunkInfo.startSec ~ chunkInfo.endSec`
- recording start: `max(sectionStartSec, targetStart - 1.0s)`
- recording end: `min(trainingSectionEndSec, targetEnd + 0.35s)`
- MR playback and graph window: `sectionStartSec ~ recordingEndSec`
- `chunk_meta.start_sec/end_sec`: same as actual audio recording window

## Video Asset Audit

Video directory: `/Users/kimjeongwoo/Desktop/졸업작품/피드백`

| file | size |
|---|---:|
| `성대접촉이약할경우.mp4` | 315,961,447 bytes |
| `구강이 과할경우.mp4` | 333,382,347 bytes |
| `성대접촉이 강한경우.mp4` | 461,405,308 bytes |
| `하압이 과할경우.mp4` | 543,586,228 bytes |

Decision: do not copy into app assets in this task. The files are too large for immediate app bundling, and privacy/licensing/content review is unverified.

## Video Mapping Candidate

| indicatorKey | zone | video | status |
|---|---|---|---|
| `vocal_fold_contact` | `insufficient` | `성대접촉이약할경우.mp4` | candidate, not exposed yet |
| `vocal_fold_contact` | `excessive` | `성대접촉이 강한경우.mp4` | candidate, not exposed yet |
| `tongue_tension` | `excessive` | `구강이 과할경우.mp4` | candidate, representative confirmation recommended |
| `pressure_balance` | `excessive` | `하압이 과할경우.mp4` | backlog only; inactive indicator |
