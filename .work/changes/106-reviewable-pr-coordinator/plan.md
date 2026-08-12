# Reviewable PR Coordinator Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Convert one exact verified local commit into one exact open reviewable PR while preserving all existing KIS verification, registered-repository, approval, and closeout boundaries.

**Architecture:** Add a focused `workflows/completion` package with immutable result contracts, a fixed-step coordinator service, and a thin FastMCP binder. The coordinator calls the existing `execute_change_workflow` first, then fixed `execute_external_action` operations for tree-equivalent remote-default reconciliation and exact registered PR creation. Extend `RegisteredGitHubOperations` only with bounded PR creation and post-create verification. Preserve both the verified source-commit SHA and generated reconciled PR-head SHA. Register the coordinator beside the existing verification workflow and expose its workflow metadata through Govern. Merge/delete/cleanup remain separate.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, existing registered Git/GitHub CLI boundary, pytest, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`; do not touch active change 105 or `policy/**`.
- Add tests before behavior changes and preserve red/green evidence.
- Every nested MCP call must use `run_middleware=True` and the original tool schemas.
- Caller input never chooses a nested tool/operation, repository URL, Git command, merge/delete action, or policy override.
- External mutation requires `approved=true` and only occurs after exact-commit change execution returns `passed`.
- Stop after exact open PR verification; never merge, delete the branch, or clean the worktree in this workflow.

### Task 1 — TDD exact registered PR creation

- [ ] Add failing tests for approval, SHA/branch/default checks, duplicate-open-PR rejection, fixed `gh pr create` shape, and post-create exact head/base/state verification.
- [ ] Extend registered-operation schema/capability tests to require discoverable PR creation without direct-profile expansion.
- [ ] Run focused tests and retain expected red evidence.
- [ ] Implement the minimal registered PR-create operation and dispatch schema.

### Task 2 — TDD completion coordinator

- [ ] Add failing service tests for verification-first order, exact source-commit/source-base pinning, mutation suppression on failed/incomplete verification, exact reconciliation inputs, reconciled-head PR-create inputs, and safe-stop result semantics.
- [ ] Add a public-tool schema test proving no command/tool/repository/merge/delete/cleanup authority is exposed.
- [ ] Implement contracts/service/tools with fixed internal operation names only.
- [ ] Register the coordinator from the existing verification platform seam using middleware-preserving structured invokers.

### Task 3 — Govern exposure and documentation

- [ ] Add one discoverable workflow descriptor for verified-change-to-reviewable-PR coordination with `prepare_reviewable_pull_request` as its only executable step.
- [ ] Update gateway/tool registration expectations and exact registered-operation capability metadata.
- [ ] Reconcile `SPEC.md` and `docs/OPERATIONS.md` only for durable current behavior and boundaries.

### Task 4 — Review, verification, and delivery

- [ ] Run focused completion/registered-GitHub/capability/registration tests.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and `git diff --check`.
- [ ] Attempt bounded specialist review; record any backend failure without claiming a pass.
- [ ] Run canonical `pwsh -NoProfile -File scripts/verify.ps1` on the exact final state.
- [ ] Reconcile lifecycle evidence and commit.
- [ ] Deliver a clean GitHub-main-rooted PR for Slice 7, exact-head merge it, delete its remote branch through the existing exact operation, and governed-clean the local Slice 7 worktree.
- [ ] Run final seven-slice programme reconciliation after Slice 7 lands; do not alter concurrent change 105.

## Recovery

Revert Slice 7. A branch or PR created before a later failure remains visible/recoverable and can be handled through the existing separate safe-closeout workflow; no automatic cleanup occurs here.
