# Codex Independent Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commission pinned local Codex as an independent code-quality and safety/security reviewer and eliminate interactive vault prompts from ordinary KIS startup.

**Architecture:** Preserve the existing single reviewer/workflow and make review purpose explicit rather than adding duplicate agents. Keep Codex pinned and project-contained with a managed home. Reuse the established Windows Credential Manager boundary to persist a cryptographically verified runtime vault unlock while retaining interactive unlock for vault mutations.

**Tech Stack:** Python 3.13, FastMCP, PowerShell 7, Windows Credential Manager, Node/npm bootstrap, OpenAI Codex CLI 0.147.0, pytest.

## Global Constraints

- Write only beneath `C:\Projects`.
- Preserve HR-001, HR-002, and HR-003 unchanged.
- External network is permitted only for explicit supervised Codex bootstrap/authentication, not ordinary Work execution.
- All new non-secret settings are JSON; no plaintext credentials are committed or logged.
- TDD is mandatory for behavior changes.
- Codex remains advisory, ephemeral, read-only, and mutation-detected.

---

### Task 1: Runtime vault credential and non-interactive startup

**Files:**
- Modify: `settings/secrets.settings.json`
- Modify: `scripts/secret-vault.ps1`
- Modify: `scripts/windows-credential.ps1`
- Create: `scripts/configure-secret-runtime-unlock.ps1`
- Modify: `scripts/initialize-secret-vault.ps1`
- Modify: `scripts/rotate-secret.ps1`
- Modify: `scripts/start-chatgpt.ps1`
- Test: `tests/secret_vault/test_scripts.py`
- Test: `tests/test_startup_scripts.py`
- Test: `tests/test_tunnel_scripts.py`

**Interfaces:**
- Produces: `Get-KisMcpRuntimeUnlockCredentialTarget`, `Get-KisMcpRuntimeUnlockCredential`, `Set-KisMcpRuntimeUnlockCredential` and one explicit existing-vault migration script.

- [ ] Add RED tests proving startup contains no `Get-KisMcpUnlockPayload`, uses the configured Windows credential target, migration verifies before write, and rotation synchronizes only after success.
- [ ] Run focused secret/startup tests and confirm intended failures.
- [ ] Implement the smallest credential/settings/script changes.
- [ ] Re-run focused tests to GREEN and inspect scripts for plaintext/log/argument leakage.

### Task 2: Pinned Codex bootstrap and managed authentication state

**Files:**
- Create: `settings/bootstrap/codex.install.json`
- Create: `contracts/bootstrap/codex.install.schema.json`
- Create: `scripts/install-codex.ps1`
- Create: `scripts/auth-codex.ps1`
- Modify: `settings/agents/code-review-agent.settings.json`
- Modify: `contracts/agents/code-review-agent.settings.schema.json`
- Modify: `src/kis_mcp/tools/codex_cli/settings.py`
- Modify: `src/kis_mcp/tools/codex_cli/tool.py`
- Modify: `scripts/invoke-codex-agent.ps1`
- Test: `tests/bootstrap/test_codex_install.py`
- Test: `tests/tools/codex_cli/test_adapter.py`

**Interfaces:**
- Produces: exact stable `0.147.0` install metadata, project-contained executable/home paths, version-aware readiness, and wrapper `CODEX_HOME` isolation.

- [ ] Add RED tests for exact pin, project-contained paths, no floating acquisition, managed `CODEX_HOME`, version mismatch, and wrapper argument/environment contract.
- [ ] Run focused Codex tests and confirm intended failures.
- [ ] Implement JSON settings/schema, bootstrap/auth scripts, settings model, readiness, and wrapper changes.
- [ ] Re-run focused tests to GREEN.

### Task 3: Independent code-quality and safety/security review purposes

**Files:**
- Modify: `src/kis_mcp/workflows/code_review/reviewer.py`
- Modify: `src/kis_mcp/workflows/code_review/tools.py`
- Test: `tests/workflows/code_review/test_reviewer.py`
- Test: `tests/test_llm_agent_registration.py`

**Interfaces:**
- Produces: `CodeReviewAgent.review(..., review_type="code-quality")` with strict `code-quality|safety-security` validation and purpose-specific prompt framing.

- [ ] Add RED tests proving strict review-type validation before collection/backend calls, Codex direct selection with no fallback, purpose-specific prompt criteria, and backward-compatible code-quality default.
- [ ] Run focused reviewer/registration tests and confirm intended failures.
- [ ] Implement minimal validation/prompt/tool signature changes.
- [ ] Re-run focused tests to GREEN.

### Task 4: Documentation, review, and repository verification

**Files:**
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `.work/changes/092-codex-independent-review/tasks.md`
- Modify: `.work/changes/092-codex-independent-review/closeout.md`

- [ ] Document Codex use guidance: code-quality for correctness/regressions and safety-security for trust/secrets/effects; explain explicit `backend=codex-cli` independence and NVIDIA alternatives.
- [ ] Document one-time existing-vault runtime-credential migration and the rule that ordinary startup is non-interactive while vault mutation remains interactive.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and `validate`.
- [ ] Perform full-diff code/security review, fix blocking findings, and re-run affected tests.
- [ ] Run fresh `pwsh -NoProfile -File scripts/verify.ps1` on the exact head.

### Task 5: Bootstrap and commissioning

- [ ] Install exact Codex `0.147.0` through the supervised bootstrap script if not already present; never use a global install outside `C:\Projects`.
- [ ] Authenticate the managed Codex home through **Sign in with ChatGPT**; do not configure an API key.
- [ ] Verify `codex --version` and authenticated non-mutating `codex exec` under the managed home.
- [ ] Run one bounded Codex `code-quality` review and one bounded `safety-security` review through KIS, proving normalized output and unchanged repository fingerprint.
- [ ] Migrate the existing vault runtime unlock once, restart only `kis-dev`, and prove startup no longer prompts for vault unlock while NVIDIA remains ready.
- [ ] Integrate only after exact-head verification; safely clean the governed worktree and record any unavoidable operator-interactive commissioning step as explicit residual evidence rather than claiming it passed.
