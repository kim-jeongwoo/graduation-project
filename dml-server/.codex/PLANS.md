# dml-server ExecPlan operating guide

## Purpose

The ExecPlan workflow keeps long Codex work resumable through file-based planning instead of relying on chat context alone.

## When to use

- Multi-file changes
- Long debugging sessions
- Work that spans multiple days
- Production-risk work
- Work that must be shared across multiple repos or pages

## When not to use

- Short read-only checks
- Small single-file edits
- Simple result sharing

## ACTIVE_PLAN.md rules

- Keep entries concise but sufficient for another Codex session to resume.
- Separate confirmed facts from assumptions.
- Record changed files, validation commands, remaining risks, and the next active work location.
- Record whether cross-page sharing is needed.
- Do not store sensitive information, secrets, private tokens, raw long logs, or large pasted handovers.

## Recommended template

```markdown
# Title

## Status

## Goal

## Scope

## Non-goals

## Current facts

## Decisions

## Files changed

## Validation

## Risks

## Cross-page sharing

## Next action

## Resume instructions
```
