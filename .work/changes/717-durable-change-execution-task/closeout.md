# Closeout: Durable Change Execution Task

## Implemented scope

- Canonical long operations use MCP Tasks when the request advertises them and transparently execute synchronously on the same operation name otherwise.
- Runtime observability records per-call Tasks capability negotiation.
- Explicit `_sync` aliases remain compatibility surfaces, not required workflow choices.
- `prepare_reviewable_pull_request` now follows the same transparent capability-aware routing, closing the #663 client/tool mismatch without adding a workflow step.
- Durable Docket settings support loopback Redis/Valkey, instance-scoped queues, frontend concurrency zero, and independent workers.
- Backend/worker launchers fail closed; the backend launcher never pulls images.
- A real Redis/Valkey resilience test covers frontend replacement while an independent worker continues the same task.

## Validation evidence

- Focused task/change-execution/registration/boundary suite passes; only the live Redis/Valkey resilience test is skipped.
- The skip is explicit because no approved local Redis/Valkey broker artifact is installed; local Docker cache, WSL, and `C:\\Projects` contain no broker, and Docket's bundled `memory://` backend is single-process by contract.
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
- Live ChatGPT evidence shows some requests omit Tasks capability; the canonical operations now fall back synchronously without caller ceremony. A separate durable-job façade remains unnecessary for this bounded compatibility defect unless future evidence shows synchronous fallback cannot meet the caller budget.
- No FastMCP version change is required for the capability-routing defect; dependency churn is intentionally excluded from this reliability fix.
