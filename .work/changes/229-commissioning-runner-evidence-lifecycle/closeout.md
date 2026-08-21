# Closeout: Commissioning Runner Evidence Lifecycle

## Implemented scope

- Extended the Change 228 post-merge runtime with deterministic source classification projection and one explicit commissioning runner; no second scheduler was introduced.
- Added settings schema v2 with a required closed `probe_id` per live surface and six code-owned read-only probe profiles.
- Added strict generated-issue parsing, exact landed merge/scope/classifier revalidation, frozen obligation identity, and Work claim admission before a new/retry attempt is persisted.
- Added runtime-generation ancestry gating that blocks stale `kis-op` without self-restart, plus supervised explicit retry semantics.
- Added durable per-attempt execution state, content-addressed proof/aggregate receipts, interruption resume, terminal replay, and deterministic mutation idempotency.
- Added source aggregation across the complete obligation set and projection of only `Live Verification`, `Commissioning Key`, and `Live Verification Evidence`; source `Verification` is never written.
- Added canonical Work terminal behavior: Passed completes Work then closes only the commissioning issue; Failed remains open/Active; Blocked leaves the issue open and transitions Work to Blocked.
- Added approval-required external runner exposure plus read-only execution evidence, observer status, and receipt diagnostics.
- Reconciled Work `Commissioning Key` semantics, `SPEC.md`, `docs/OPERATIONS.md`, and the post-merge commissioning runbook.

## Validation evidence

- Focused commissioning suite: passed after the final manual-review fixes.
- Affected integration set passed: post-merge commissioning, canonical Work contracts, Discover tool registration, and gateway capability composition.
- Ruff: passed for changed commissioning source/tests and affected Discover registration test.
- `git diff --check`: passed.
- `pwsh -File scripts/change-workflow.ps1 check`: passed.
- Current pre-publication working-tree fingerprint: `50e8c900eecd93e690efb0b8bb4363badf368e2ce53e77e5147e4ea926925c57` before this closeout evidence update.
- Repository/full verification: canonical exact-head GitHub Actions remains required after PR publication.
## Review

Automated architecture, safety-security, API/contracts, test-quality, documentation, and code-quality review projectors each refused incomplete evidence before invoking a model because this 34-file Complex change exceeded the bounded projector size. Every result explicitly required `manual_fallback.mode = exact-diff`; no automated finding was produced from partial evidence.

The required exact-diff fallback found and resolved these material issues:

- Terminal Passed/Failed/Blocked replay initially re-required an Active claim before consulting durable state. Terminal replay now revalidates identity but returns from durable terminal state before Work-claim admission.
- Successful close itself made the generated issue closed, while the parser initially accepted only open issues. Identity parsing now accepts open/closed for replay; first/new execution separately requires the Project source issue to be open and Active/claimed.
- New/retry attempt state was initially created before Work claim admission. Claim rejection now creates no new local execution attempt; retry increments only after current Active/owner evidence succeeds.
- Observer source projection introduced `read`/`change` calls that were outside the original external-only budget wrapper. The same observer read/mutation budgets now cover all three dispatch planes.
- Aggregate receipts originally included wall-clock time in the content hash, making retry after a projection crash produce a new idempotency key. Aggregate evidence is now content-addressed only by deterministic frozen state.
- Crash windows after Work Blocked/Done mutations now re-read exact Work state and skip duplicate transitions/completion while safely continuing the next phase.
- Work completion and GitHub close responses are now positively validated before terminal state advances.
- Runtime source revisions are now validated as exact hexadecimal SHAs before ancestry checks.

Final exact-diff fallback found no remaining architecture, security, API-contract, lifecycle, or test-coverage blocker after those fixes.

## Git and merge

- Branch: `change/229-commissioning-runner-evidence-lifecycle`
- Worktree: `.work/worktrees/229-commissioning-runner-evidence-lifecycle`
- Commit: pending publication
- Pull request / exact-head CI / merge: pending publication
- Post-merge live commissioning: pending merge and refreshed `kis-op`
- Cleanup: pending post-merge closeout

## Residual items

- #455 remains the sole historical backfill owner and is intentionally outside Change 229.
- #453 remains open until the freshly merged Change 229 is independently observed by Change 228 and the resulting live commissioning obligations are proved through the landed runner.