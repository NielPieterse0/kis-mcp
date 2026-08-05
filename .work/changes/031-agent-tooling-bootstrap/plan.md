# Agent Tooling Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install complete pinned AgentSys and agnix distributions under `C:\Projects` and prepare isolated Claude Code, OpenCode, and Codex profiles.

**Architecture:** Two independent npm installations use versioned roots and a shared supervised-bootstrap pattern. AgentSys generates OpenCode and Codex profiles through its own installer and a Claude development profile from the downloaded plugin cache; a launcher reapplies the managed environment. Future kis-mcp exposure remains JSON-driven and outside this slice.

**Tech Stack:** PowerShell 7, Node.js 22, npm 10, Git, pytest, JSON and JSON Schema.

## Global Constraints

- Pin AgentSys `6.0.1` and agnix `0.45.0` exactly.
- Write only beneath `C:\Projects`.
- Never permanently delete existing installations or profiles; move them to quarantine before replacement.
- Keep AgentSys and agnix independently installable, testable, and recoverable.
- Do not modify active Tools-module paths or `src/kis_mcp/server.py`.
- Do not run any AgentSys workflow during installation.
- Keep future kis-mcp command exposure disabled by default and controlled through JSON.

---

### Task 1: Define strict bootstrap settings and schemas

**Files:**
- Create: `settings/bootstrap/agentsys.install.json`
- Create: `settings/bootstrap/agnix.install.json`
- Create: `contracts/bootstrap/agentsys.install.schema.json`
- Create: `contracts/bootstrap/agnix.install.schema.json`
- Test: `tests/bootstrap/test_agentsys_install.py`
- Test: `tests/bootstrap/test_agnix_install.py`

- [ ] Write tests for exact versions, independent roots, three AgentSys hosts, managed paths, and default-deny kis-mcp exposure.
- [ ] Run the tests and confirm missing-file failures.
- [ ] Add the strict JSON settings and schemas.
- [ ] Rerun the focused tests.

### Task 2: Implement independent supervised installers

**Files:**
- Create: `scripts/install-agentsys.ps1`
- Create: `scripts/install-agnix.ps1`
- Test: `tests/bootstrap/test_agentsys_install.py`
- Test: `tests/bootstrap/test_agnix_install.py`

- [ ] Extend tests to reject unpinned installs, outside paths, permanent deletion commands, and credential persistence.
- [ ] Implement staged npm installation with managed cache/temp/home paths and recoverable activation.
- [ ] Run AgentSys for OpenCode and Codex, then populate the managed Claude plugin profile from its complete fetched plugin cache.
- [ ] Verify package identity, versions, command inventory, host outputs, and agnix CLI/MCP entrypoints.
- [ ] Rerun focused tests.

### Task 3: Add managed host launcher and documentation

**Files:**
- Create: `scripts/start-agentsys-host.ps1`
- Create: `docs/development/bootstrap/agentsys.md`
- Create: `docs/development/bootstrap/agnix.md`
- Test: `tests/bootstrap/test_agent_host_profiles.py`

- [ ] Write tests for host enumeration, managed environment variables, and corrective missing-host behavior.
- [ ] Implement the launcher for `claude`, `opencode`, and `codex`.
- [ ] Document direct host use, future policy-driven kis-mcp exposure, upgrade, and recovery.
- [ ] Rerun focused tests.

### Task 4: Commission and verify

- [ ] Run both installers through the approved supervised command surface.
- [ ] Record installed package versions, paths, plugin/command counts, and unavailable host executables without claiming authentication.
- [ ] Run `python -m pytest tests/bootstrap -q`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run `pwsh -NoProfile -File scripts/verify.ps1` serially.
- [ ] Review the diff, update tasks and closeout, commit, push, and open a PR without merging.
