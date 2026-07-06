# AGENTS.md — dml-server Codex/GPT operating rules

이 문서는 dml-server에서 Codex/GPT 계열 코드 에이전트가 먼저 읽는 primary 운영 지침이다.
`CLAUDE.md`와 `HANDOVER_TO_GPT.md`는 삭제하지 말고, 과거 Claude 작업 이력과 상세 컨텍스트 보조 문서로 유지한다. 오래된 수동/nohup 운영 지시는 `PROJECT_LOG.md` §15 최신 항목과 이 파일의 systemd 기준이 우선한다.

## Role split

- GPT/ChatGPT is the discussion, review, and instruction-validation hub.
- Codex is the code-editing and server-inspection agent.
- Do not infer missing production details. Inspect files, logs, processes, and service state first.

## 현재 운영 기준

- Repo: `/home/dmlserver/projects/egg_prediction/dml-server`
- Project root: `/home/dmlserver/projects/egg_prediction`
- Model server working dir: `/home/dmlserver/projects/egg_prediction/dml-server/model_server`
- Conda env: `/home/dmlserver/miniconda3/envs/EGGDML`
- Entrypoint: `server.py`
- Service: `dml-server.service`
- External URL: `https://dml.vocal-fit.com`
- Cloudflare target: `http://localhost:8001`
- Log: `/var/log/dml-server.log`
- Health:
  - local: `http://localhost:8001/health`
  - production: `https://dml.vocal-fit.com/health`

`curl` may be unavailable on this host. Use the EGGDML Python `urllib` for health checks when needed.

## Must Read Before Changes

1. `PROJECT_LOG.md` §15 latest deployment history and endpoint status.
2. `CLAUDE.md` for legacy project-specific pitfalls and historical detail only. If CLAUDE.md "현재 진행 위치" or manual service commands conflict with this file or `PROJECT_LOG.md` §15 latest entries, this file and `PROJECT_LOG.md` §15 take precedence.
3. `HANDOVER_TO_GPT.md` only as historical handover context. Some operational notes there may be stale after `dml-server.service` was added; prefer `PROJECT_LOG.md` §15 and this file for current operations.

## Context and ExecPlan workflow

- Short tasks can be handled directly in the Codex chat.
- Long tasks, multi-file changes, debugging sessions, and work that spans days should use the ExecPlan workflow.
- Persistent operating rules live in `AGENTS.md`.
- Long-running plan templates and operating guidance live in `.codex/PLANS.md`.
- The active working state lives in `.codex/ACTIVE_PLAN.md`.
- At the start of a substantial task, read both `AGENTS.md` and `.codex/ACTIVE_PLAN.md` before making changes.
- During long tasks, keep `.codex/ACTIVE_PLAN.md` updated with the current goal, decisions, discovered facts, files changed, validation run, remaining risks, and next action.
- After `/compact` or automatic context compression, resume from `.codex/ACTIVE_PLAN.md` instead of asking for the full prior chat.
- Do not store secrets, credentials, private tokens, raw long logs, or large pasted handovers in `.codex/ACTIVE_PLAN.md`.
- Whether `.codex/ACTIVE_PLAN.md` is committed or left local/untracked is decided per task.
- Subagents are limited to read-only audit, compare, and log-summary work. The main Codex agent owns all file edits.

## Hard invariants

- Do not change model logic, endpoint schemas, `StreamingResponse` P2-A behavior, `score_mapper_v2`, or `analysis_pipeline` unless the user explicitly asks for that exact work.
- `/analyze` keeps HTTP 200 streaming with final body `status`; do not change this status-code policy.
- Cloudflare 125s edge timeout is treated as TTFB-based and handled by early streaming TTFB. Do not remove keepalive behavior.
- Keep per-register matching and the 4-fold criterion unless explicitly instructed otherwise.
- Preserve display categories including `academic_only`, `deferred`, and `excluded`.
- Keep single uvicorn worker unless explicitly instructed otherwise. Current production is `dml-server.service` with ExecStart `python server.py`; do not switch to multi-worker `uvicorn` or `gunicorn`.
- Do not run long `/analyze` verification without explicit permission.
- Do not print `.env`, credentials, tunnel token files, certificates, or private data.
- Do not delete checkpoints, `data/songs/`, `data/vocal_academy/singer_NN/`, or experiment data.
- Do not revert existing dirty git changes unless the user explicitly asks.

## Production safety

- Before modifying production behavior, report the plan and affected files.
- Do not perform state-changing production actions unless the user explicitly requests that exact action.
- This includes deploys, service file edits, `systemctl restart/stop/start/reload`, process signals or kill commands, database/data mutations, checkpoint deletion, and git mutations such as commit, reset, checkout, merge, rebase, or push.
- Do not use broad process kills such as `fuser -k`.
- For dml-server process changes, use targeted PID checks with cwd/exe/cmdline.
- After production changes, verify local and production `/health`.
- Do not run long `/analyze` tests unless explicitly approved.
- Prefer read-only inspection before any operational recommendation.

## Service Operations

Safe read-only checks:

```bash
git status --short
systemctl is-active dml-server.service
systemctl is-enabled dml-server.service
systemctl show dml-server.service -p MainPID -p Restart -p RestartUSec -p RuntimeMaxUSec --no-pager
tail -n 80 /var/log/dml-server.log
```

Health checks with Python:

```bash
/home/dmlserver/miniconda3/envs/EGGDML/bin/python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/health', timeout=8).read().decode())"
/home/dmlserver/miniconda3/envs/EGGDML/bin/python -c "import urllib.request; req=urllib.request.Request('https://dml.vocal-fit.com/health', headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}); print(urllib.request.urlopen(req, timeout=15).read().decode())"
```

Restart/stop/start/reload operations require an explicit user request. Use targeted process operations only when the user approves them; avoid broad commands such as `fuser -k`.

## systemd baseline

- `dml-server.service` runs `/home/dmlserver/miniconda3/envs/EGGDML/bin/python server.py` from `model_server`.
- Port 8001 and cloudflared target `http://localhost:8001` are preserved.
- Logs append to `/var/log/dml-server.log`.
- `RuntimeMaxSec=3600` is the current periodic restart policy.
- 50-request restart is not implemented unless an explicit app-side mechanism is added.

## Deployment Log Discipline

- `PROJECT_LOG.md` §15 is the deployment source of truth.
- Add a new §15 entry for production restart, endpoint/schema changes, service changes, or model-serving behavior changes.
- For docs-only cleanups, do not update `PROJECT_LOG.md` unless the user asks or the documentation change affects operating procedure materially.

## Change scope discipline

- Keep diffs narrowly scoped to the user-requested task.
- Do not perform opportunistic refactors, formatting churn, dependency updates, or documentation rewrites unless they are required for the requested change.
- Preserve unrelated dirty work. If existing changes affect the task, work around them carefully and mention the interaction in the final response.

## Validation style

- Use the narrowest validation that proves the change: targeted tests, focused scripts, import checks, or read-only health checks as appropriate.
- Do not run long `/analyze`, load-heavy model checks, production traffic tests, or service verification with side effects without explicit permission.
- In final responses, state what validation was run and what was intentionally skipped.

## Parallel subagent usage

Use Codex subagents/parallel work when the task is naturally parallel, such as:

- codebase exploration,
- document migration audits,
- independent endpoint/schema review,
- log/test-result summarization,
- comparing multiple implementation options,
- auditing stale instructions across docs,
- comparing endpoint/schema references across files,
- checking test or script coverage.

Constraints:

- Subagents may only read, audit, compare, and summarize.
- Do not use subagents for state-changing production actions: `systemctl start/stop/restart`, process kill, deployment, database or file deletion, git reset/revert, or writing final patches without main-agent review.
- Do not delegate file edits, git operations, `systemctl`, process signals, kill commands, deployment, or service verification to subagents.
- Give each subagent a narrow, non-overlapping question and ask for file paths plus line references.
- The main Codex agent must synthesize subagent findings, decide the final plan, own all edits, run final verification, and keep the final diff scoped.

## Reporting

- Separate confirmed facts from assumptions.
- Report changed files/paths, validation commands, and remaining risks.
- Keep final reports concise and diff-centered.

## Legacy project-specific pitfalls

- Use median samples for visualization; do not cherry-pick examples.
- Keep `model_server` scipy/librosa resampling behavior synchronized when touching audio preprocessing.
- Record experiment results in `results/experiment_log*.txt` when changing experiment/training code.
- Use `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` for Korean visualization text.
- Before adopting external MIDI, compare octave with the self F0 pipeline dry run; external MIDI can be +12 semitones.
- Before reprocessing apparently unusual singer ranges, verify singer/song-specific range expectations.
- Preserve chunk-analysis voiced-time decisions unless explicitly changing that endpoint: `CHUNK_MIN_VOICED_S = 2.0` for chunks.
- Keep script root calculations straight: scripts directly under `dml-server/scripts/` use `parents[2]`; deeper `scripts/data_prep/` scripts may need `parents[3]`.
- Import `Path` before font config blocks that call `Path(...)`.
- Before Stage 2 batch pitch-guide generation, verify `lrc/parsed/` file count.
- Normalize macOS-uploaded filenames to NFC before comparing paths.
- Do not auto-accept LRCLIB results below title similarity threshold; known mismatches include `007 지아 - 물론` and `011 양다일 - 요즘`.
- CREPE GPU is unsupported on RTX 5080 with TF 2.21; use CPU fallback/cache behavior.

## Documentation Ownership

- `AGENTS.md`: primary Codex/GPT operating guide.
- `PROJECT_LOG.md`: project history and production deployment log.
- `CLAUDE.md`: legacy Claude-oriented project memory; keep for pitfalls and historical detail.
- `HANDOVER_TO_GPT.md`: one-time Claude-to-Codex handover; keep as archived context unless the user approves rename/deletion.
