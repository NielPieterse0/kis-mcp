# Live Proxy Commissioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable black-box commissioning harness for the real `kis-mcp` to Desktop Commander stdio proxy.

**Architecture:** A test-support module builds the locked subprocess environment and executes one ordered MCP scenario. A pytest integration test gates live execution behind `KIS_MCP_LIVE_COMMISSION=1`; a PowerShell script sets the flag and invokes the exact test through the locked interpreter.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4 client and stdio transport, pytest 8.4.2, PowerShell 7.

## Global Constraints

- Write only within `C:\Projects`.
- Do not modify `src/kis_mcp/**`, runtime settings, policy, or files owned by changes `002` and `003`.
- Keep generated state under `C:\Projects\.kis-mcp`.
- Never permanently delete artifacts.
- Preserve exact HR-001, HR-002, and HR-003 semantics.

---

### Task 1: Commissioning support contract

**Files:**
- Create: `tests/integration/test_live_proxy_commissioning.py`
- Create: `tests/support/live_proxy_commissioning.py`

**Interfaces:**
- Produces: `choose_unmounted_drive() -> str`, `build_gateway_environment(repository_root: Path) -> dict[str, str]`, `result_text(result: Any) -> str`, `validate_provider_state_bytes(content: bytes) -> None`, and `run_live_commissioning(repository_root: Path) -> dict[str, Any]`.

- [x] Write failing tests for drive selection, environment isolation, and result text extraction.
- [x] Run the targeted test and confirm failure because the support module does not exist.
- [x] Implement only the pure helper functions.
- [x] Run targeted tests and confirm they pass.

### Task 2: Real stdio commissioning scenario

**Files:**
- Modify: `tests/support/live_proxy_commissioning.py`
- Modify: `tests/integration/test_live_proxy_commissioning.py`

**Interfaces:**
- Consumes: helper functions from Task 1.
- Produces: ordered stage report containing `health`, `surface`, `read`, `write`, `hr001`, `quarantine`, `restore`, `process`, and `provider_state`.

- [x] Add the live integration test gated by `KIS_MCP_LIVE_COMMISSION=1`.
- [x] Run it with the flag and confirm failure before `run_live_commissioning` exists.
- [x] Implement the minimal async FastMCP stdio scenario against `python -m kis_mcp`.
- [x] Run the live test and fix only harness defects; record production defects without changing excluded files.
- [x] Add post-shutdown provider-state validation with atomic pre-run snapshot restoration.

### Task 3: Operator entry point and evidence

**Files:**
- Create: `scripts/commission-live-proxy.ps1`
- Create: `docs/development/live-proxy-commissioning/spec.md`
- Create: `docs/development/live-proxy-commissioning/plan.md`
- Modify: `.work/changes/004-live-proxy-commissioning/tasks.md`
- Modify: `.work/changes/004-live-proxy-commissioning/closeout.md`

**Interfaces:**
- Script invokes the locked interpreter with the exact live pytest node.

- [x] Add the PowerShell entry point with canonical-path validation and isolated environment variables.
- [x] Run the script and preserve its exact outcome.
- [x] Run normal repository verification and change-governance checks.
- [x] Review the diff for excluded-path or production changes.
- [ ] Commit the branch; do not merge.
