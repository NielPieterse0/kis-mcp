# Commissioning Closeout Hardening Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Eliminate the two commissioning defects observed during 099/101 delivery without widening Work or GitHub authority.

**Architecture:** Harden change-record creation at its authoritative generator, then extend the existing `RegisteredGitHubOperations` exact-ref service with one remote-default-rooted tree-equivalence publication primitive. Register only its virtual capability surface and keep PR merge/delete as separate existing exact operations.

**Tech Stack:** Python 3.11+, Git CLI, GitHub CLI through the existing registered external-operation boundary, FastMCP capability metadata, pytest, PowerShell verification wrapper.

## Global constraints

- Stay inside `scope.json`; do not touch active 103 paths or `policy/**`.
- Add regression tests before changing behavior.
- Preserve exact registered-project routing, process-scoped `GH_CONFIG_DIR`, token redaction, and fixed command arrays.
- No arbitrary commit messages, Git arguments, remote URLs, repositories, shell commands, or policy parameters.

### Task 1 — Reproduce both defects

- [ ] Add byte-level LF assertions for every generated change artifact.
- [ ] Add reconciliation tests for tree-equivalent divergent ancestry and failure cases.
- [ ] Extend capability tests to require the additive virtual operation.
- [ ] Run focused tests and retain the expected red evidence.

### Task 2 — Implement the narrow hardening

- [ ] Force LF at the change-governance write boundary.
- [ ] Implement exact registered remote-default reconciliation with tree equivalence, double remote-default verification, non-default target enforcement, and exact target lease.
- [ ] Add strict schema/dispatch and discoverable capability metadata without direct-profile expansion.
- [ ] Update only `SPEC.md` and `docs/OPERATIONS.md` for durable current behavior and procedure.

### Task 3 — Review, verify, and deliver

- [ ] Run focused regression tests, `scripts/change-workflow.ps1 check`, and `git diff --check`.
- [ ] Attempt bounded code-quality/security review; record backend failures without claiming passes.
- [ ] Run canonical `pwsh -NoProfile -File scripts/verify.ps1` on the exact final tree.
- [ ] Reconcile change artifacts and commit the verified local branch.
- [ ] Deliver a clean GitHub-main-rooted PR, exact-head merge, remote branch cleanup, local merge, and governed worktree cleanup.

## Recovery

Revert the slice. No persistent schema migration or credential migration exists; any published reconciliation branch is recoverable by its returned commit SHA until separately deleted through the existing exact-head operation.
