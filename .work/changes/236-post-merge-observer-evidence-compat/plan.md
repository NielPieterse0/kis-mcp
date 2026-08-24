# Post-Merge Observer Evidence Compatibility Implementation Plan

> **For agentic workers:** Execute only after explicit Complex approval. Keep `scope.json` current and add failing tests before behavior changes.

**Goal:** Restore markerless governed PR observation using exact landed scope identity, and prevent deterministic evidence-invalid candidates from wedging later post-merge observation.

**Architecture:** Keep the existing observer/service/classifier/intake topology. Resolve source identity from the exact landed schema-v4 scope, then corroborate the same change through the provider-native governed PR head ref and the source Work card's canonical `Change ID`; PR-body text is non-authoritative and does not gate admission. Convert only an explicit immutable landed-governance error-code set into bounded `blocked_evidence`; re-raise provider/discovery/configuration/Work evidence errors so the runtime service preserves the checkpoint for retry.

**Tech stack:** Python 3.13, existing GitHub MCP operation dispatch, commissioning runtime/state contracts, pytest, Ruff, repository change governance.

## Global constraints

- Stay inside Change 236 `scope.json`.
- Do not modify `SPEC.md` while another active change owns it; after Change 232's orphan claim is safely retired, claim `SPEC.md` in Change 236 and make only the current-product reconciliation required by this change.
- Do not parse or gate on PR-body text for commissioning admission or source identity.
- Do not broaden mutation authority or increase configured read/mutation budgets. The approved provenance amendment may use the existing read-only Work board operation solely for change-ID corroboration, consuming the existing external-read budget.
- Do not change classifier, intake-key, runner, housekeeping, Project-schema, or source `Verification` semantics.
- Preserve exact merge SHA and exact-file evidence before any source identity is accepted.

## Traceability

| Task | Requirements | Primary files | Test/evidence |
| --- | --- | --- | --- |
| T1 | R1-R5,R10 | `commissioning/evidence.py`, `test_evidence.py` | exact-scope identity, PR-body non-authority, and fail-closed scope tests |
| T2 | R6-R8,R11 | `commissioning_runtime/processor.py`, `test_processor.py` | narrow `blocked_evidence` code set and retry propagation tests |
| T3 | R7-R9,R11 | `test_runtime_service.py` | accounted immutable defects vs retryable provider/discovery failures |
| T4 | R12 | operator docs | documentation review and terminology checks |
| T5 | all | change evidence | scope, Ruff, focused tests, specialist reviews, exact-head CI/live acceptance |
## T1 — Resolve source identity from exact landed scope

**Modify:** `src/kis_mcp/commissioning/evidence.py`
**Test:** `tests/post_merge_commissioning/test_evidence.py`

1. Add failing tests proving markerless, valid-marker, malformed-marker, partial-marker, duplicate-marker, and contradictory-marker PR bodies all resolve identically when the exact landed scope is valid.
2. Add failing tests for zero/multiple changed scope candidates; invalid/non-v4 landed scope; wrong repository/kind; and invalid risk-trigger content.
3. Remove PR-body marker parsing from admission/source-identity resolution; do not replace it with another text heuristic.
4. Exhaust the provider-native PR source-commit SHA list, exclude every such SHA from merge candidacy, then resolve the merge SHA from the registered default-branch commit stream only when the exact PR number/head branch pair, provider-native GitHub `web-flow` committer identity, and Git committer timestamp equal to PR `merged_at` all agree. Then require provider `changed_files` to be positive and within the 3,000-file GitHub commit ceiling, and page exact merge files only until that count is reached. Reject source-commit impersonation, provider identity disagreement, duplicate/non-progressing pages, early short pages, and count/shape disagreement as retryable provider evidence before selecting the scope path.
5. Select exactly one scope path only after completeness is proven; require the provider-native PR head ref to equal `change/<change-id>`, resolve the exact non-truncated merge-tree blob, read it at the exact SHA, require the returned bytes to hash to that blob, validate its own change/source identity, then require the exact source Work card (including history) to report the same canonical `Change ID` before accepting the evidence.
6. Bound filtered merge-tree entries, scope-wrapper depth, and encoded/decoded scope content size locally; boundary violations remain retryable `provider_evidence_invalid`.

## T2 — Account deterministic evidence failures per candidate

**Modify:** `src/kis_mcp/commissioning_runtime/processor.py`
**Test:** `tests/post_merge_commissioning/test_processor.py`

1. Define the explicit immutable landed-governance code set (`scope_path_missing`, `scope_path_ambiguous`, `scope_invalid`, `scope_identity_mismatch`) and add table-driven processor tests for it.
2. Return bounded `blocked_evidence` only for that code set with `pull_number`, `error_code`, and empty commissioning/issue lists; assert no intake, Project read, or Project mutation occurs.
3. Re-raise all other `MergeEvidenceError` values, including provider/discovery/configuration/Work evidence codes, so the runtime service preserves retry semantics.
4. Reclassify unreadable/invalid provider response content in `_scope_content` as provider evidence and require exact merge-tree blob-hash agreement before decoded JSON/schema-v4 validation may produce `scope_invalid`.
5. Do not include exception text/detail or provider bodies in any returned/persisted outcome.

## T3 — Prove checkpoint semantics

**Modify:** tests only unless implementation evidence requires a service adjustment.
**Test:** `tests/post_merge_commissioning/test_runtime_service.py`

1. Add a test with an immutable-scope `blocked_evidence` candidate followed by a successful candidate; assert both outcomes persist and the checkpoint advances.
2. Add resolver/processor/service tests proving provider-evidence, source Work corroboration, and merge-discovery `MergeEvidenceError` values propagate into an incomplete run with checkpoint unchanged.
3. Preserve existing raw `RuntimeError`, provider/search, and budget failure coverage.
4. Add replay coverage showing a previously blocked immutable-governance candidate can later resolve if rediscovered, without duplicate identity side effects.
5. If service code requires no change, do not add one merely for symmetry.
## T4 — Reconcile operator documentation

**Modify:** `docs/OPERATIONS.md`, `docs/operations/post-merge-commissioning.md`

1. Document the implemented authority order: exact merge -> complete changed-file evidence -> unique landed schema-v4 scope -> exact governed PR-head corroboration -> exact source Work `Change ID` corroboration; PR-body text is non-authoritative and does not gate admission.
2. Document `blocked_evidence` as an accounted fail-closed outcome only for immutable landed-governance defects, with no commissioning mutation.
3. Distinguish those immutable defects from provider/discovery/configuration/Work evidence failures that remain retryable and preserve the checkpoint.
4. Keep current-product architecture in `SPEC.md`, not operator docs. After Change 232's orphan ownership is safely released, minimally reconcile `SPEC.md` to the implemented source-identity, evidence-typing, and checkpoint semantics.

## T5 — Review, verify, land, and live-commission

1. Run focused evidence/processor/runtime tests and Ruff on changed Python.
2. Run `git diff --check` and `pwsh -File scripts/change-workflow.ps1 check` from the Change 236 worktree.
3. Review the exact diff for architecture, API/contracts, safety/security, code quality, test quality, and documentation. Fix blocking findings and rerun affected evidence.
4. Confirm Change 232 ownership is released, add `SPEC.md` to Change 236 ownership, and complete the minimal current-product reconciliation before publication.
5. Prepare/publish the exact commit through governed KIS paths; require exact-head canonical GitHub Actions success and Work merge-readiness.
6. Merge only the approved head. Allow the existing landing hook to refresh `kis-dev`; do not restart or mutate `kis-op` automatically.
7. Refresh `kis-op` only through the existing supervised lifecycle when live observer acceptance requires the landed code image.
8. Verify the observer accounts the six currently wedging markerless merged PRs without an unhandled `MergeEvidenceError`, with bounded outcomes and checkpoint progress.
9. Produce one fresh governed runtime-affecting merge and verify exact landed-scope resolution, deterministic classification/intake, and normal source live-verification projection.
10. Record live receipts, merge SHA, source/change identity, outcome/key/issue references, and checkpoint evidence; then complete Work #474 and clean Change 236 from synced `main`.

## Recovery

Before merge, abandon or amend Change 236 normally. After merge, repository revert plus supervised runtime refresh restores prior behavior; retained checkpoints/receipts remain evidence. The change does not delete or rewrite existing commissioning issues or historical receipts.

## Approval gate

Because this plan implements a Complex change that revises the approved Change 228 source-linkage contract and observer checkpoint semantics, implementation begins only after explicit human approval of this finalized specification and plan.