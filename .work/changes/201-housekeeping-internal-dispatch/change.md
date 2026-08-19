# Change: Housekeeping Internal Dispatch

- **Change ID**: `201-housekeeping-internal-dispatch`
- **Risk Profile**: lean

## Outcome

Complete Change 194 commissioning by separating internal housekeeping operation results from user-facing capability result-budget truncation while preserving effect and approval enforcement.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Preserve capability-dispatch effect, eligibility, and approval enforcement as the first execution boundary.
- When a read-only dispatcher result is replaced by `RESULT_BUDGET_EXCEEDED`, recover the real structured read result without treating transport-budget truncation as domain truncation.
- Never replay change or external operations merely because their dispatcher result exceeded the user-facing result budget.
- Keep the public capability dispatcher result-budget behavior unchanged.

## Implementation and verification

- Development level: Small — one internal invoker boundary and one focused regression suite; architecture-boundary review remains required by the declared risk trigger.
- Plan: add failing invoker regressions; implement the smallest read-only recovery path; run focused housekeeping tests, Ruff, diff/scope checks; review the complete base→head diff; freeze and publish only after reviews are clean.
- Root-cause evidence: the scheduled runners failed with `inventory_truncated`, while provider-native `repo:NielPieterse0/kis-mcp` inventory completed in three pages. `CapabilityExecutionRouter._budget_result` replaces oversized structured results with `{truncated: true, reason: RESULT_BUDGET_EXCEEDED}`, and `FastMCPInvoker` currently returns that envelope as if it were the operation payload.
- Implementation notes: `FastMCPInvoker` now recognizes the dispatcher-only `RESULT_BUDGET_EXCEEDED` envelope. Read-only calls recover by replaying the already-authorized original read tool with middleware enabled; change/external calls fail closed rather than replaying a possible mutation. Public dispatcher budgeting is untouched.
- TDD evidence: the initial three invoker regressions failed 3/3 on the old behavior and passed after the bounded implementation. A fourth regression then proved that a domain payload merely reusing the budget reason must not replay; it failed before strict envelope-signature detection and passed afterward.
- Focused checks: `python -m pytest tests/housekeeping -q` => 35 passed; Ruff on the two changed code/test files => clean; `git diff --check` => clean; `scripts/change-workflow.ps1 check` => declared paths only.
- Review findings: final working-tree fingerprint `4d44c155daf7caf9120aa4a5a52c407b8e53e767ea0a2229c91e0e10c040fcf2`; code-quality, architecture, and test-quality specialist reviews completed clean with no findings. An earlier Codex CLI review attempt failed at the backend process boundary and was superseded by completed configured specialist reviews.
- Residual risk: an oversized read is executed twice: once through the capability dispatcher (which proves read-only eligibility/effect enforcement) and once directly to recover the full structured result. This is bounded to read-only operations and avoids duplicating mutation execution.
- Closeout state: implementation and required pre-publication specialist reviews are complete locally; exact-head GitHub Actions verification, merge, runtime restart, and fresh unattended housekeeping receipts remain required.
