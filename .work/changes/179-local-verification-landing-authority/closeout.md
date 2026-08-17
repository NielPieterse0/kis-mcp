# Closeout: Local Verification Landing Authority

## Implemented scope

- Replaced Actions-only merge readiness with referenced `source=local` verification for the exact current PR head; Actions-only, failed, stale, or unreferenced local evidence fails closed.
- Normal PR closeout now invokes `execute_change_workflow`; Actions read steps were removed from canonical completion descriptors.
- Removed `speculative-landing-queue` and `complete-work-managed-merge-queue` from canonical workflow discovery while retaining their dormant implementation/history.
- Reconciled `AGENTS.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and the verification runbook to the new authority boundary.
- Restored merged-baseline full-suite collection with `tests/execution/__init__.py` and the minimal project-management package import-order correction.

## Validation evidence

- TDD red confirmed the old gate rejected valid referenced local exact-head evidence and accepted Actions-only evidence.
- Former duplicate pytest module identities now collect cleanly; the project-management circular import is also cleared.
- Focused affected verification reached 71/71 passed; final Work Management authority regression set passed 39/39.
- Full repository `python -m pytest -q -x` completed 100%, exit 0, with two expected skips and existing warnings only.
- Full `pwsh -NoProfile -File scripts/verify.ps1` completed exit 0 on the frozen pre-commit candidate: line endings, configuration, interpreter, dependencies, syntax, change governance, pytest, and final verification all passed.
- `scripts/change-workflow.ps1 check` and `git diff --check` passed before closeout reconciliation.
- Test/cache/temp state was kept beneath `C:\Projects` (`C:\Projects\.kis-mcp`) throughout verification.

## Review

- API/contracts review completed successfully on frozen fingerprint `46d6b7df...` with zero findings.
- Code-quality review completed on the same fingerprint. Its five findings were resolved by exact repository evidence: the removed workflow IDs remain only in dormant queue diagnostics/tests; `OperationEffect.PROCESS` is used by the replacement Work Management closeout descriptor; `trace_json` is test-local with all callers updated; the reordered package imports clear the pre-existing cycle and the full suite passes; and `VerificationEvidence.reference` already rejects empty/whitespace values while merge readiness remains a provider-neutral pure evaluator over authoritative trace evidence, matching the pre-existing trust boundary rather than dereferencing provider receipts.
- Architecture specialist attempts timed out. Governed manual exact-diff fallback completed with no blocking finding: `execute_change_workflow` accepts `source="commit"` plus `commit_ref`, existing completion tests prove exact-commit routing, merge readiness separately requires that revision to equal the observed PR head, and exact landing still uses the registered GitHub merge primitive.
- Earlier Codex/NVIDIA reviewer failures are retained as reviewer-infrastructure evidence, not successful reviews.

## Git and merge

- Branch: `change/179-local-verification-landing-authority`
- Worktree: `.work/worktrees/179-local-verification-landing-authority`
- Commit: pending final review/freeze.
- Pull request or merge: pending exact-head bootstrap landing sequence.
- Cleanup: pending merge.

## Residual items

- The currently running `kis-dev` runtime still reflects pre-179 `main` until this change lands and the runtime is restarted.
- Exact committed-head verification, valid required review evidence, PR publication, reconciled PR-head local verification, exact-head merge, `main` refresh, and cleanup remain outstanding.
