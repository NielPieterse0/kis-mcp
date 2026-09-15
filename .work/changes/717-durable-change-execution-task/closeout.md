# Closeout: Durable Change Execution Task

## Implemented scope

- Canonical `execute_change_workflow` requires MCP Tasks.
- Runtime observability records per-call Tasks capability negotiation.
- `execute_change_workflow_sync` preserves an explicit non-Tasks compatibility path while the canonical operation remains Tasks-required.
- Durable Docket settings support loopback Redis/Valkey, instance-scoped queues, frontend concurrency zero, and independent workers.
- Backend/worker launchers fail closed; the backend launcher never pulls images.
- A real Redis/Valkey resilience test covers frontend replacement while an independent worker continues the same task.

## Validation evidence

- Focused task/change-execution/registration set: `20 passed, 1 skipped`.
- The single skip is the live Redis/Valkey resilience test because no approved local backend artifact is installed.
- Both PowerShell launchers parse successfully.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed.

## Review

- Manual diff review retained the Work/execution/fencing authority boundary and found no reason to alter once-through workflow shape.
- Live durability is not claimed until the real backend test passes without skip.

## Git and merge

- Branch: `change/717-durable-change-execution-task`.
- Worktree: `.work/worktrees/717-durable-change-execution-task`.
- Initial bootstrap commit: `97148f83b34599d33d7ab240a16ffc607d56752b`.
- Existing PR #723 currently points at earlier reconciled head `99454bcd5e892fa280f38b083a8c828cda56d32e`; it must be reconciled to the final source before merge.
- Merge and cleanup: not yet eligible.

## Residual blockers

- Acquire the pinned `valkey/valkey:9.1.2-alpine` image through an approved external-artifact path; local Docker currently has no Valkey/Redis image.
- Run the live resilience test against that backend without skip.
- Observe Tasks negotiation from the live ChatGPT host after deployment; add a durable-job façade only if Tasks are unavailable.
- Decide whether FastMCP stable upgrade is required in this same execution slice; current implementation remains on the repository pin until that dependency can be governed and verified.
