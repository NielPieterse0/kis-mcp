# Serena Registration Reconciliation Implementation Plan

**Goal:** Remove stale generated Serena project registrations before provider startup while preserving active registrations and repository authority.

**Architecture:** Keep reconciliation inside the Serena adapter where KIS already owns Serena generated-state bootstrap. Parse only the top-level `projects:` block in `serena_config.yml`, retain entries whose paths still exist, remove missing entries, and invoke this before the Serena transport starts. Do not couple generic governed cleanup to provider-specific state.

**Tech Stack:** Python 3.13, FastMCP 4 provider adapter, pytest, PowerShell change-governance scripts.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Generated Serena state is non-authoritative and recoverable.
- Do not alter HR-001/HR-002/HR-003 or Serena public capabilities.

### Task 1: Regression contract

- Add tests for mixed active/stale registrations, all-active idempotence, and startup ordering.
- Confirm the stale-registration case fails before implementation.

### Task 2: Reconcile generated registration state

- Add one bounded config reconciliation helper in `adapter.py`.
- Preserve existing lines/order for active projects.
- Reject ambiguous duplicate `projects:` sections without mutation.
- Run reconciliation before provider transport construction.

### Task 3: Verify and close

- Run focused Serena tests and Ruff on changed files.
- Run `pwsh -File scripts/change-workflow.ps1 check` and `git diff --check`.
- Review exact diff against Work #527 acceptance.
- Publish, require exact-head GitHub verification, merge, live-check Serena startup, complete Work #527, and clean the governed worktree.
