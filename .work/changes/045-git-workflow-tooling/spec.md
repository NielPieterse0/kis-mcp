# Change Specification: Git Workflow Tooling

- **Change ID**: `045-git-workflow-tooling`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Add bounded repository-local Git workflow commands for structured specialized diffs, PR readiness, and safe merged-worktree cleanup, including recoverable Windows long-path failure handling, without installing packages or duplicating Tool/Provider capabilities.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and the operator request in this slice.
- Owned implementation: `scripts/git-workflow.py`, `scripts/git-workflow.ps1`, and targeted cleanup hardening in `scripts/change-governance.py`.
- Owned tests: `tests/test_git_workflow.py` and targeted additions to `tests/test_change_governance.py`.
- Owned documentation: `docs/development/git-workflow-tooling/**`.
- Tool, Provider, server, policy, and settings implementation paths are excluded.

## Requirements

- **REQ-001**: Provide a fixed-shape `diff-summary` command that compares two validated Git refs and returns deterministic bounded JSON with merge base, commits, file statuses, rename/copy provenance, numstat, and aggregate counts.
- **REQ-002**: Provide a read-only `pr-readiness` command that reports branch/base/head, clean/detached state, ahead/behind counts, governed change identity, scope-check result, blockers, and recommended next actions without contacting a remote forge.
- **REQ-003**: Provide a read-only `cleanup-preview` command that classifies managed change worktrees as eligible or blocked based on registration, cleanliness, merge ancestry, and path-length risk.
- **REQ-004**: Validate repository paths and Git refs; reject leading-option, whitespace, traversal-like, or missing refs as structural errors rather than shell input.
- **REQ-005**: Use fixed Git subprocess shapes with `shell=False`, isolated output bounds, deterministic ordering, and JSON-only stdout.
- **REQ-006**: Harden `cleanup_change_worktree` with `core.longpaths=true` and a recoverable fallback when Git removes registration but Windows cannot remove the directory.
- **REQ-007**: Cleanup fallback must move intact remnants beneath `C:\Projects\.backup`, never force-delete, never branch-delete while registration remains, and report the recovery path.
- **REQ-008**: Preserve existing `change-workflow.ps1 cleanup` behavior for ordinary clean merged worktrees.
- **REQ-009**: Add a PowerShell wrapper that invokes the repository Python implementation and propagates its exit code without package installation.
- **REQ-010**: Remote PR creation, review, and merge remain GitHub connector responsibilities; local commands only produce readiness evidence and recommended actions.

## Acceptance

1. `diff-summary` returns stable structured output for additions, deletions, modifications, renames, copies, binary files, and optional path filtering.
2. `pr-readiness` identifies clean ready branches and blocks dirty, detached, unscoped, scope-violating, or non-ahead branches with explicit reasons.
3. `cleanup-preview` lists managed worktrees without mutation and identifies dirty or unmerged blockers.
4. A simulated Windows filename-too-long cleanup failure moves an unregistered remnant intact to the shared backup root and completes branch/prune cleanup.
5. A cleanup failure that leaves Git registration intact stops without moving the directory or deleting the branch.
6. Existing governance tests and full repository verification remain green.
7. No package, provider, runtime composition, policy, or settings file changes occur.

## Risks and recovery

- Risk: cleanup recovery could hide a partially removed worktree.
- Mitigation: verify registration state after failure, move only an unregistered clean merged remnant, use an exclusive timestamped backup destination, and return recovery metadata.
- Risk: diff/readiness commands could permit argument injection.
- Mitigation: strict ref/path validation, fixed argument arrays, and `shell=False`.
- Risk: large repositories could produce excessive output.
- Mitigation: configurable hard bounds with explicit truncation and omission counts.
- Recovery: revert this repository-only change. Any cleanup fallback artifact remains intact under the shared recoverable backup root.

## Out of scope

- Installing Git extensions, diff viewers, GitHub CLI plugins, Tool packages, or Provider packages.
- Creating, approving, merging, or closing remote PRs.
- Replacing the GitHub connector or underlying fixed `git_*` capability tools.
- Force deletion, force push, branch rewriting, or automatic cleanup of unrelated active worktrees.
