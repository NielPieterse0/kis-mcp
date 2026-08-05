# KIS Control Center Implementation Plan

> **For agentic workers:** Execute this plan task-by-task, use test-driven development for behavior, and keep the declared scope current.

**Goal:** Add a separate read-only KIS Control Center MCP App without modifying or forking Desktop Commander.

**Architecture:** A focused package loads strict JSON settings, collects bounded local status into immutable data contracts, renders a self-contained HTML MCP App resource, and exposes a standalone FastMCP server with one model-visible entry tool. The implementation reads approved local configuration files but does not modify the main gateway or policy.

**Tech Stack:** Python 3.11–3.13, FastMCP 3.4.4, standard library HTML/JSON/subprocess/path utilities, pytest 8.4.

## Global constraints

- Stay inside `scope.json`.
- Add tests before production behavior.
- Perform no network access and add no dependencies.
- Do not alter Desktop Commander, the three-rule policy, or the main gateway integration surface.
- Keep the app read-only; operational changes continue through ordinary kis-mcp Work tools.

---

### Task 1: Settings and snapshot contracts

**Requirements:** REQ-003, REQ-004, REQ-007, REQ-008

**Files:**
- Create: `settings/control-center.settings.json`
- Create: `contracts/control-center/settings.schema.json`
- Create: `src/kis_mcp/control_center/contracts.py`
- Create: `src/kis_mcp/control_center/settings.py`
- Test: `tests/control_center/test_control_center_settings.py`

- [x] Write tests for valid settings, rejected unknown/missing fields, and schema agreement.
- [x] Run the focused tests and confirm failure because the package does not exist.
- [x] Implement immutable settings/contracts with exact field validation and bounded limits.
- [x] Run the focused tests and confirm pass.

**Evidence:** `pytest tests/control_center/test_control_center_settings.py -q`

### Task 2: Bounded local snapshot collection

**Requirements:** REQ-003, REQ-004, REQ-006

**Files:**
- Create: `src/kis_mcp/control_center/snapshot.py`
- Test: `tests/control_center/test_control_center_snapshot.py`

- [x] Write tests using temporary runtime, policy, provider, project, and quarantine fixtures.
- [x] Confirm failures because snapshot collection is absent.
- [x] Implement fixed-command local Git inspection, bounded provider/quarantine summaries, and explicit unknown verification state.
- [x] Confirm focused tests pass without network or mutation.

**Evidence:** `pytest tests/control_center/test_control_center_snapshot.py -q`

### Task 3: Self-contained MCP App renderer and server

**Requirements:** REQ-001, REQ-002, REQ-005, REQ-006, REQ-008

**Files:**
- Create: `src/kis_mcp/control_center/render.py`
- Create: `src/kis_mcp/control_center/app.py`
- Create: `src/kis_mcp/control_center/__init__.py`
- Create: `src/kis_mcp/control_center/__main__.py`
- Test: `tests/control_center/test_control_center_render.py`
- Test: `tests/control_center/test_control_center_app.py`

- [x] Write renderer tests for escaping, deterministic sections, host-theme variables, and absence of external resources.
- [x] Write FastMCP client tests for the entry tool, `ui://` resource, MIME type, and structured fallback result.
- [x] Confirm tests fail because renderer/server are absent.
- [x] Implement the smallest self-contained HTML renderer and standalone FastMCP server.
- [x] Confirm focused tests pass.

**Evidence:** `pytest tests/control_center/test_control_center_render.py tests/control_center/test_control_center_app.py -q`

### Task 4: Operator documentation and full verification

**Requirements:** REQ-009

**Files:**
- Create: `docs/development/control-center/README.md`
- Update: `.work/changes/036-kis-control-center/tasks.md`
- Update: `.work/changes/036-kis-control-center/closeout.md`

- [x] Document startup, current read-only boundary, host fallback behavior, and future additive gateway mount.
- [x] Review the complete diff against the specification and scope.
- [x] Run focused tests, change-workflow checks where the pre-existing governance conflict permits, whitespace validation, and full `scripts/verify.ps1`.
- [x] Record exact evidence and residual governance limitation.
- [ ] Commit, push, open the PR, review the exact head, merge, update local main, and remove the worktree and branch.

**Evidence:** focused pytest output, `git diff --check`, `scripts/verify.ps1`, PR checks, clean worktree/branch listing.
