# Codex ExecPlan Template

긴 작업은 이 템플릿을 `.codex/ACTIVE_PLAN.md`에 복사해서 진행한다.

## 1. Plan Header
- Name:
- Thread:
- Date:
- Owner:
- Status: planned | in_progress | blocked | verification | done

## 2. Source Of Truth
- Latest user instruction:
- Related prior work:
- Current branch / HEAD:
- Batch status:

## 3. Scope
- Goals:
- Non-goals:
- Hard constraints:
- Files allowed to change:
- Files explicitly off-limits:

## 4. Current Findings
- Code facts:
- Runtime/Galaxy facts:
- Unknowns:

## 5. Execution Checklist
- [ ] Inspect current implementation.
- [ ] Summarize approach before edits.
- [ ] Apply minimal patch.
- [ ] Run requested verification.
- [ ] Record verification result.
- [ ] Update ACTIVE_PLAN.md before compact or handoff.

## 6. Verification
- Commands:
- Expected baseline failures:
- Manual/Galaxy checklist:

## 7. Change Log
- YYYY-MM-DD:

## 8. Backlog / Deferred
- Item:
- Reason deferred:
- Candidate files:
