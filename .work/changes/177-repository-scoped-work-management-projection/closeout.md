# Closeout: Repository Scoped Work Management Projection

## #318 command-plane contract matrix

| Area | Status | Executable finding |
| --- | --- | --- |
| Lifecycle/status transitions | CURRENTLY CORRECT | Declared transition graph, required metadata, evidence-field ownership, and terminal-command separation pass focused tests. |
| Ready / Hold / Deferred / release | CURRENTLY CORRECT | Ready/claim preview fails closed without Priority/Effort/Documentation Impact; Hold/Deferred preview accepts required Review Trigger; release is owner-gated in command tests. |
| Execution ownership / claims | CURRENTLY CORRECT | Claim requires Ready metadata, rejects existing ownership, requires apply idempotency, re-reads owner before activation, and release requires exact expected owner. |
| Take-next deterministic selection | DEFECT | Ranking is deterministic, but live `next_work(kis-mcp)` evaluated eligible foreign Project records because inventory was not repository-scoped. |
| Guarded completion | CURRENTLY CORRECT | Completion uses lifecycle/traceability gates and only requests source close when reconciliation succeeds. |
| Dependency/blocking interpretation | CURRENTLY CORRECT | Native dependency evidence and lifecycle blocking are consumed fail-closed by selection/transition tests. |
| Classification synchronization | CURRENTLY CORRECT | Schema-v4 local scope is authoritative for Change ID/Complexity/Risk Triggers; only evidence-owned Project fields are projected. |
| Traceability/readiness | CURRENTLY CORRECT | Exact branch/worktree identity and stage evidence are checked; closed trace requires merge, closeout, and post-merge documentation evidence. |
| Merge readiness | CURRENTLY CORRECT | Exact-head provider-native GitHub Actions passing evidence is mandatory; required pre-merge documentation can block. |
| Post-merge documentation reconciliation | CURRENTLY CORRECT | Exactly one merged PR plus matching merge evidence creates the due event; post-merge completion upgrades it idempotently. |
| Repository/project routing | DEFECT | Live `inventory(kis-mcp)` returned foreign repositories and preview `claim_work(kis-mcp, college#17)` resolved successfully under the wrong managed project. |
| Existing skill assumption: per-project inventory is intentionally shared | STALE ASSUMPTION | #317 requires repository-scoped managed-project projections while retaining explicit unbound portfolio visibility. |

## #317 implementation

- Repository-bound inventory now filters case-insensitively by the existing `ProjectBinding.repository` while scanning the shared Project page stream.
- `item_limit` counts only repository-matching records; foreign tail records no longer produce false truncation.
- `repository=None` remains an explicit cross-repository Project projection.
- CREATE/UPDATE reconciliation with an explicit foreign source repository now fails before provider I/O.
- No Work Management authority, schema, service-layer source of truth, or Project ownership was duplicated.
## Validation evidence

- TDD red: repository leakage, scoped-limit false truncation, and foreign CREATE/UPDATE routing all failed before production edits; explicit unbound visibility remained green.
- Focused defect tests: 7/7 passed after implementation.
- Provider/project-onboarding regressions: 29/29 passed.
- Work Management command/lifecycle/traceability/reconciliation/selection/binding regressions: 71/71 passed.
- Compile: affected production modules passed `compileall`.
- Ruff: affected production and test files passed.
- Governed scope: `scripts/change-workflow.ps1 check` passed with only declared paths.
- Existing unrelated limitation: `tests/workflows/project_management/test_documentation_tools.py` cannot collect because of the pre-existing `kis_mcp.workflows.project_management` circular import; this task does not modify that lane.

## Review

- First Codex CLI specialist invocation failed at the review process boundary (`CODEX_CLI_PROCESS_FAILED`) without findings; no code judgment was returned.
- Fallback independent code-quality review completed with no findings.
- Independent API-contract review completed with no findings.

## Git and merge

- Branch: `change/177-repository-scoped-work-management-projection`
- Worktree: `.work/worktrees/177-repository-scoped-work-management-projection`
- Base: `9adf1ca26a6a96a173605a7e5dd5c11216d6ec0e` / `refs/remotes/origin/main`, verified equal to GitHub default branch before the change.
- Commit: locally committed on the governed change branch; exact SHA is the branch HEAD reported at handoff.
- Merge: prohibited while canonical exact-head GitHub Actions is unavailable; no waiver is permitted.

## Residual items

- The running KIS runtime remains on the pre-fix code until this candidate is reviewed and eventually landed, so live runtime probes will continue to exhibit the #317 defect in the meantime.
- Exact-head GitHub Actions evidence and merge remain pending service availability.