# Capability Workflow Mutations Implementation Plan

**Goal:** Restore executable `create_change_worktree` and `commit_change` operations with the smallest bounded capability-layer change.

**Architecture:** Add two discoverable virtual operation descriptors to capability control and route them through one governed local executor. Keep them hidden from the direct MCP surface. Reuse `scripts/change-workflow.ps1 new` for worktree creation and Git's normal commit machinery only inside a verified `change/*` worktree.

**Tech stack:** Python, FastMCP capability dispatcher, Git, PowerShell change workflow, pytest.

## Constraints
- Do not edit `workflows/platform.py`; active change #637 owns it.
- Do not touch or restart `kis-op`.
- Preserve HR-001/HR-002/HR-003 and the existing curated direct surface.

## Tasks
- [x] Reproduce missing operation discovery/dispatch.
- [x] Add discoverable operation contracts and governed execution routing.
- [x] Add focused dispatcher/discovery regression tests.
- [x] Run focused capability/composition tests.
- [x] Run governed scope check.
- [ ] Run applicable review and final verification.
- [ ] Commit, promote, land, restart only `kis-dev`, and live-smoke both operations.
