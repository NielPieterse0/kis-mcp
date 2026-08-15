# Project Schema Commissioning Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Close `kis-mcp#142` by provisioning and verifying Project #1 through a bounded registered-GitHub commissioning path.

**Architecture:** Keep the official GitHub MCP adapter as the normal Work Management provider. Add a narrow schema commissioner behind the existing approval-gated registered-GitHub exact-operation family. The commissioner accepts only a registered project/binding plus the canonical manifest, emits fixed GitHub API operations, preserves existing option identity, and re-reads before success. A thin backend wrapper adds view inventory while delegating normal operations unchanged.

**Tech Stack:** Python 3.11+, FastMCP/KIS capability dispatch, GitHub CLI authenticated state, GitHub Projects API, pytest, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`; do not touch active change 148 ownership.
- Add failing tests before each behavior change.
- No arbitrary GraphQL/REST/API path or token surface.
- No destructive migration or delete operation.
- Preserve existing Project item content and single-select identities.
- Do not alter HR-001/HR-002/HR-003.

### Task 1: Specify exact schema commissioner behavior

**Files:** `tests/providers/github/projects/test_schema_commissioning.py`, `src/kis_mcp/providers/github/projects/schema_commissioning.py`

- [x] Test registered target/view/field snapshot parsing and strict failures.
- [x] Test missing field/view creation and post-mutation verification.
- [x] Test Status option extension retains existing option IDs.
- [x] Test incompatible field type fails before mutation.
- [x] Implement the smallest commissioner satisfying those tests.
### Task 2: Add strict registered-GitHub commissioning operation

**Files:** `src/kis_mcp/projects/github_exact.py`, `src/kis_mcp/capabilities/surface.py`, `tests/projects/test_github_exact.py`, `tests/capabilities/test_registered_commit_workflow.py`

- [x] Test approval, registered binding resolution, strict schema, and capability metadata.
- [x] Dispatch only `project_id`, `project_binding_id`, and `approved` to the commissioner.
- [x] Verify no caller-supplied query/path/schema values are accepted.

### Task 3: Make view readiness observable

**Files:** `src/kis_mcp/providers/platform.py`, `src/kis_mcp/work_management/service.py`, `tests/work_management/test_service.py`

- [x] Test `schema_status` reads views when available and remains explicit when unavailable.
- [x] Wrap the normal GitHub Project backend without replacing its normal read/update behavior.
- [x] Verify final status can become fully ready.

### Task 4: Reconcile current architecture/runbook

**Files:** `SPEC.md`, `docs/OPERATIONS.md`

- [x] Document the bounded schema commissioning exception and its approval/target contract.
- [x] Remove stale claims that views can never be observed/provisioned.
- [x] Keep unrestricted GraphQL and general Project administration explicitly out of surface.

### Task 5: Verify, review, land, and commission

- [x] Run focused tests and `change-workflow.ps1 check`.
- [x] Run required code-quality, safety-security, architecture, and API-contract reviews; resolve blockers.
- [ ] Commit and prepare exact-head PR through KIS; require GitHub Actions success.
- [ ] Merge through governed KIS GitHub path and refresh main.
- [ ] Commission Project #1 using the new exact operation, rerun schema status/plan and command-plane smoke operations.
- [ ] Record evidence on #142, close it, reconcile Project status, and clean the merged worktree.
