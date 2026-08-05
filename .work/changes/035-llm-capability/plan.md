# LLM Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add NVIDIA NIM and Codex CLI as optional backends for one bounded advisory code-review agent.

**Architecture:** Keep provider, local tool, and workflow concerns separate. NVIDIA uses a stdlib HTTPS client; Codex is invoked only through a fixed PowerShell wrapper; the agent collects bounded local Git evidence and normalizes one backend result.

**Tech Stack:** Python 3.11 stdlib, FastMCP 3.4.4, PowerShell 7, pytest.

## Global Constraints

- Write only beneath `C:\Projects`.
- Preserve exactly HR-001, HR-002, and HR-003.
- Change `035-llm-capability` depends on `029-tools-code-tooling`; pause implementation until 029 is merged, then rebase 035 before continuing.
- Do not create or modify the generic `kis_mcp.tools` framework. Own only `tools/codex_cli/**` and its matching tests.
- No plaintext secrets in repository JSON, tool results, logs, or command arguments.
- One advisory agent role, delegation depth one, no mutation authority.
- All optional capability failures must leave the core gateway available.

---

### Task 1: Configuration and contracts

**Files:**
- Create: `settings/agents/code-review-agent.settings.json`
- Create: `contracts/agents/code-review-agent.settings.schema.json`
- Create: `src/kis_mcp/workflows/code_review/settings.py`
- Test: `tests/workflows/code_review/test_code_review_settings.py`

**Interfaces:**
- Produces: `AgentSettings`, `NvidiaSettings`, `CodexSettings`, `load_agent_settings(repository_root=None)`.

- [x] Write failing tests for exact keys, path/URL validation, backend order, and budgets.
- [x] Run the focused settings tests and confirm failure.
- [x] Implement immutable settings parsing and validation.
- [x] Run the focused settings tests and confirm pass.

### Task 2: NVIDIA NIM provider

**Files:**
- Create: `src/kis_mcp/providers/nvidia/__init__.py`
- Create: `src/kis_mcp/providers/nvidia/client.py`
- Create: `src/kis_mcp/providers/nvidia/provider.py`
- Modify: `src/kis_mcp/providers/platform.py`
- Test: `tests/providers/nvidia/test_nvidia.py`

**Interfaces:**
- Consumes: `NvidiaSettings`.
- Produces: `NvidiaNimClient.complete(prompt) -> str`, `register_nvidia_provider(registry, settings, environ=None)`.

- [x] Write failing request, response, error, redaction, readiness, and registry tests.
- [x] Run NVIDIA tests and confirm failure.
- [x] Implement stdlib HTTPS transport and provider descriptor.
- [x] Run NVIDIA tests and confirm pass.

### Task 3: Codex CLI script adapter

**Dependency gate:** Begin only after `029-tools-code-tooling` is merged and this branch is rebased onto its generic Tools foundation.

**Files:**
- Create: `scripts/invoke-codex-agent.ps1`
- Create: `src/kis_mcp/tools/codex_cli/__init__.py`
- Create: `src/kis_mcp/tools/codex_cli/adapter.py`
- Create: `src/kis_mcp/tools/codex_cli/tool.py`
- Test: `tests/tools/codex_cli/test_adapter.py`

**Interfaces:**
- Consumes: `CodexSettings`.
- Produces: `CodexCliAdapter.review(project_path, prompt) -> str`.

- [x] Write failing command-shape, JSONL parsing, timeout, process-failure, and script-contract tests.
- [x] Run Codex tests and confirm failure.
- [x] Implement the fixed PowerShell wrapper and Python adapter.
- [x] Run Codex tests and confirm pass.

### Task 4: One code-review agent

**Files:**
- Create: `src/kis_mcp/workflows/__init__.py`
- Create: `src/kis_mcp/workflows/code_review/__init__.py`
- Create: `src/kis_mcp/workflows/code_review/contracts.py`
- Create: `src/kis_mcp/workflows/code_review/evidence.py`
- Create: `src/kis_mcp/workflows/code_review/reviewer.py`
- Create: `src/kis_mcp/workflows/code_review/tools.py`
- Test: `tests/workflows/code_review/test_evidence.py`
- Test: `tests/workflows/code_review/test_reviewer.py`

**Interfaces:**
- Produces: `CodeReviewAgent.review(path, instructions="", backend=None) -> dict`, `register_agent_tools(server, agent)`.

- [x] Write failing tests for bounded evidence, backend selection, fallback, structured/unstructured normalization, and no-backend failure.
- [x] Run agent tests and confirm failure.
- [x] Implement the single advisory reviewer and tool registration.
- [x] Run agent tests and confirm pass.

### Task 5: Gateway integration and documentation

**Files:**
- Modify: `src/kis_mcp/server.py`
- Test: `tests/test_llm_agent_registration.py`
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`

**Interfaces:**
- `build_server()` registers `review_change_with_agent` additively and tolerates unavailable optional backends.

- [x] Write the failing additive-registration test.
- [x] Run the registration test and confirm failure.
- [x] Wire settings, backends, agent, and registration into the gateway.
- [x] Update current implementation and operating instructions without claiming live credentials or upstream verification.
- [x] Run all focused tests and confirm pass.

### Task 6: Review, verification, and integration

- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and `check` from the worktree.
- [x] Review the full diff for scope, secrets, policy, fallback, error handling, and unnecessary complexity.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1` with no concurrent verification process.
- [x] Commit, push, create PR #48, and inspect its exact file set and configured checks.
- [ ] Merge at the exact final verified head, update local main, and run workflow cleanup.
