# Deterministic Triage Work Selection Implementation Plan

**Goal:** Deliver issue #543 only on top of the landed #542 canonical Work contract.

**Architecture:** Extend the canonical selection contract/parser and shared selection engine; add a bounded Triage evaluator/service operation; mount its public tool separately from #625-owned legacy tool files.

**Tech stack:** Python 3, FastMCP, JSON Work contracts, pytest, governed change workflow.

## Global constraints

- Stay inside `scope.json`; preserve all #625 exclusions.
- Keep one selection authority in `work-selection.json`.
- Use declared command-plane lifecycle edges rather than direct status edits.
- Keep Project mutation preview/apply and provider idempotency semantics.

### Task 1: Canonical selection policy

- [x] Add deterministic selection tiers to the canonical machine contract.
- [x] Project tier fields through the canonical parser.
- [x] Rank tier before existing Priority/Effort/age/stable identity keys.
- [x] Return tier evidence for normalized and provider-backed selection.

### Task 2: Deterministic Triage progression

- [x] Add stable relevant-input fingerprinting and exact attention reasons.
- [x] Enforce required Ready metadata and issue sections.
- [x] Progress valid items through `Triage -> Approved -> Ready`.
- [x] Make partial Approved progression safely resumable with fingerprint-bound idempotency.
- [x] Expose a bounded public Triage operation without expanding #625-owned tool files.

### Task 3: Verification and publication

- [x] Add focused selection, triage, command-service, platform, and architecture regressions.
- [x] Run focused/affected tests and governed scope check.
- [x] Run canonical local repository verification.
- [x] Resolve the blocking code-review finding and rerun affected tests.
- [ ] Commit the final governed tree and run fixed-commit review.
- [ ] Publish PR and require exact-head GitHub Actions plus merge-readiness evidence.
- [ ] Merge, reconcile Work/documentation state, close #543, and clean the worktree.
