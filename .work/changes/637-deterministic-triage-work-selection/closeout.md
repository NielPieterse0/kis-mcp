# Closeout: Deterministic Triage Work Selection

## Implemented scope

- Added canonical selection tiers: defect, material finding, unfinished, then new work.
- Preserved Priority, Effort, creation order, and stable identity ranking within the winning tier.
- Added tier explanation evidence to normalized and provider-backed selection.
- Classified findings as tier 2 only when canonical Severity is Critical/High/Medium; Low-severity cosmetic findings remain normal new work.
- Surfaced `Origin=Operator` as explicit `operator_directed` evidence without allowing it or prompt text to override deterministic next/take ranking; exact operator choice remains the exact-target claim path.
- Added deterministic Triage input fingerprinting and exact machine-readable attention reasons.
- Enforced canonical Ready metadata plus required issue sections.
- Added declared `Triage -> Approved -> Ready` progression and bounded public Triage operation.
- Made partial progression resumable from Approved with fingerprint-bound provider idempotency keys.
- Mounted Triage separately from the active #625-owned legacy Work tool bundle.

## Validation evidence

- Final focused tests passed across command service, Triage, canonical contracts, selection, project commands, and tool integration.
- Final Work Management plus project-management workflow suites passed after materiality/operator/fingerprint changes.
- Earlier repository verification passed configuration, interpreter, dependencies, Python syntax, change governance, full pytest, and three-rule consistency; exact-head GitHub Actions remains the canonical publication verification gate.
- `git diff --check` and `scripts/change-workflow.ps1 check` passed before closeout documentation reconciliation.

## Review

- Initial bounded code-quality review found one High issue: retry could not resume after Approved if Ready failed.
- Resolution: accept the declared Approved intermediate state, continue only the remaining Ready edge, and bind transition idempotency to the evaluation fingerprint.
- Added an injected partial-failure regression proving retry completes without reapplying Approved.
- First fixed-commit review then found one Medium issue: `apply=True` with the preview fingerprint could be suppressed as unchanged.
- Resolution: unchanged-fingerprint suppression now applies only to non-mutating polling/preview; apply continues through the fingerprint-bound idempotent transition path.
- The service regression covers preview fingerprint reuse during apply, non-Ready apply validation, and cross-issue target binding.
- Subsequent reviews found and resolved canonical Ready-semantics, normalized severity identity, target-fingerprint identity, and invalid Delivery Stage classification gaps.
- Final full-range code-quality review on `8192af837b4f52f97a54a30f62d7a1b6e16aaa5a`: zero actionable findings.

## Git and merge

- Branch: `change/637-deterministic-triage-work-selection`
- Worktree: `.work/worktrees/637-deterministic-triage-work-selection`
- Commit: pending final commit after this closeout reconciliation.
- Pull request or merge: pending exact-head publication and CI.
- Cleanup: pending verified merge and Work closeout.

## Residual items

- The qualified purpose-specific reviewer route failed closed with `EvidenceError`; explicit Codex review supplied the actionable pre-commit finding.
- Existing FastMCP `mimeType` deprecation warnings are unrelated and unchanged.
- #625 and downstream #544/#545/#547/#546 scopes were not absorbed.
