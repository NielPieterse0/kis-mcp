# Closeout: Operations Document Routing

## Implemented scope

- `docs/OPERATIONS.md` remains the canonical operator entry/index and delegates detailed procedures to nine `docs/operations/**` runbooks.
- `AGENTS.md` preserves the existing authority order and now routes operator work through the root index plus only the needed scoped runbook.
- Detailed runbooks keep operator commands, prerequisites, commissioning, validation, recovery, and troubleshooting while routing current architecture, public contracts, machine-owned values, volatile inventories/status, and historical completion evidence to their existing owners.
- No source, tests, policy, settings, `SPEC.md`, trust semantics, module specs, or active implementation-lane files changed.

## Context reduction

- Baseline `docs/OPERATIONS.md`: 84,138 bytes.
- Final root index: 6,299 bytes / 97 lines — 92.5% smaller as the default Operations read.
- Final nine runbooks: 35,858 bytes.
- Combined operator documentation: 42,157 bytes — 49.9% smaller than the legacy monolith while retaining all 28 legacy H2/H3 operator headings.

## Validation evidence

- Heading audit: all 28 legacy H2/H3 operator headings retained; none missing.
- Script-reference audit: 28/29 legacy script references retained; the sole omission, `scripts\invoke-codex-agent.ps1`, was an internal gateway implementation reference rather than an operator action and is intentionally routed to source/tests.
- Command audit: 46/47 legacy executable command lines retained exactly; the sole replacement is the hardcoded NVIDIA secret-reference command, replaced by a settings-resolved equivalent.
- Troubleshooting audit: all 39 legacy operator error identifiers retained, including `KIS_MCP_SOURCE_CHECKOUT_REQUIRED`.
- Relative Markdown link audit: zero broken links across root and runbooks.
- Focused tests: `tests/test_repository_scope.py`, `tests/test_startup_scripts.py`, `tests/govern/test_governance_evidence.py`, and `tests/govern/test_governance_service.py` — 55 passed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with only declared change-167 paths.

## Review

The aggregate working-tree review package exceeded the reviewer evidence budget, so it was not counted as a pass. Acceptance composes bounded exact staged-source reviews with whole-set deterministic audits; the governance-record partition alone is not implementation-completion evidence.

- Nine-runbook base staged fingerprint `9f26dd119b27558ac6c5bdbac7b24951d60dc9106fa02f53ce44c16999464e35`: documentation review clean (Codex CLI); architecture review clean (NVIDIA super).
- Final incremental two-runbook fingerprint `ebc3ebbd91e076f9b48bb332e1e6f26a8eda58fbca2dcf36ef33184f5ad61e86`: documentation review clean (Codex CLI); architecture review clean (NVIDIA super). This covers the later restoration of the merge-queue smoke command, source-checkout troubleshooting, and governance-timing correction.
- Final root/authority fingerprint `9e45f24d28cb645bb92813067953629f1e989dfdac80ece8b822ca758f896a1d`: documentation review clean (Codex CLI); architecture review clean (NVIDIA super).
- Earlier incomplete, invalid-contract, and timeout attempts are not passes and are excluded from acceptance evidence.

Review-driven corrections also fixed stale legacy documentation: GitHub Project schema projection count was reconciled to the executable manifest, Desktop Commander upgrade inputs/cache order were completed, historical bootstrap docs were labeled non-authoritative, and governed-change semantics were routed back to `AGENTS.md`.

## Publication and recovery

- Branch: `change/167-operations-document-routing`.
- Worktree: `.work/worktrees/167-operations-document-routing`.
- Publication, exact-head Canonical Verification, merge, remote-branch deletion, and governed cleanup are recorded as external KIS/GitHub receipts after the reviewed source commit is frozen.
- Recovery: revert the landed documentation commit/PR; the legacy monolith remains available in Git history.

## Residual items

- README projection cleanup and the `docs/development/**` historical-boundary index are intentionally separate small governed changes in the approved documentation-drag tranche.