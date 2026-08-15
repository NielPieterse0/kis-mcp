# Closeout: Review Agent Evidence Safety

## Implemented scope

- Bound advisory review to the same Discover source identity used by verification selection, including immutable resolved Git object IDs and content/evidence-byte fingerprints for mutable sources.
- Replaced blind review-evidence truncation with deterministic whole-section packaging and explicit included/omitted/completeness metadata.
- Enforced strict structured reviewer results and fail-closed source/evidence validation in change execution.
- Added one configured review deadline across attempts/retries/fallback plus an aggregate specialist-review deadline, with remaining-budget propagation into NVIDIA/Codex calls.
- Updated authoritative specification/operator documentation and focused regressions for #267 acceptance.

## Validation evidence

- Focused checks: 128 selected tests passed across Discover source identity, review evidence/result handling, change execution, verification selection, NVIDIA, and Codex adapters; `ruff check`, `compileall`, and `git diff --check` passed.
- Repository verification: `select_change_verification` identified repository-verifier and Python-test handoffs; local selector execution is unavailable and repository policy reserves the full canonical verifier for exact-head PR CI.
- Diff scope check: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed with exit code 0.

## Review

- Architecture: final Codex pass reported zero concrete findings after mutable-source evidence-byte binding and race fixes.
- API contracts: Codex hit its configured output limit; NVIDIA Nano completed the independent pass. Reported items were required/additive contract changes, not unresolved breaking defects, and are covered by focused compatibility tests.
- Code quality: Codex hit its configured output limit; NVIDIA Nano completed the independent pass. Its two reported items were validated as intentional fail-closed behavior (Git/I/O identity failure and missing immutable resolved refs) rather than defects.
- Resolutions: earlier concrete review findings were fixed: content/ref-bound source identity, immutable resolved-ref evidence extraction, mutable inventory/fingerprint race rejection, mutable evidence-byte fingerprint binding, aggregate deadline propagation, and implicit fallback after invalid preferred-backend output.

## Git and merge

- Branch: `change/156-review-agent-evidence-safety`
- Worktree: `.work/worktrees/156-review-agent-evidence-safety`
- Commit: pending publication.
- Pull request or merge: pending exact-head PR CI.
- Cleanup: pending merge.

## Residual items

- #261 remains open for false `CODEX_CLI_MUTATION_DETECTED`; this change does not claim Codex fallback reliability beyond the new timeout/source contract.
- #265 remains open for generic shared-editable-virtualenv/worktree source isolation; this change does not claim that broader execution defect is resolved.
- A pre-existing pytest collection/import-order issue reproduces on untouched `main`; synchronous focused verification used `-p no:asyncio` only when Discover package tests were combined. It is outside #267.
