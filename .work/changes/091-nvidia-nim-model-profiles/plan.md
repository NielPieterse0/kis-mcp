# NVIDIA NIM Model Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use the repository `develop-code` lifecycle with test-driven development and verification-before-completion. This plan is executed inline because no independent coding subagent is currently commissioned.

**Goal:** Configure and live-commission NVIDIA Nemotron 3 Nano, Super, and Ultra as selectable profiles for the bounded advisory reviewer, with Super as default and the NVIDIA key supplied only from the KIS encrypted vault to the selected runtime.

**Architecture:** Keep one `nvidia-nim` provider/backend. Replace the single model record with a strict three-profile configuration and make the client select a profile per review. Extend the advisory tool with an optional `model` alias and return non-secret provenance. Add a non-secret vault reference to configuration; the selected-instance launcher resolves that reference and injects `NVIDIA_API_KEY` only into the child KIS server process. Preserve ordinary NVIDIA→Codex fallback when no model is explicitly requested.

**Tech Stack:** Python 3.11+, FastMCP, stdlib `urllib`, JSON configuration, PowerShell launch scripts, pytest, existing KIS encrypted secret vault.

## Global Constraints

- Do not modify `policy/kis-mcp.policy.json`; HR-001, HR-002, and HR-003 remain the only Work prohibitions.
- Never write, print, log, stage, commit, or return the NVIDIA API key.
- Canonical secret reference: `secret://provider/nvidia-nim/api-key`; process environment name: `NVIDIA_API_KEY`.
- NVIDIA endpoint remains `https://integrate.api.nvidia.com/v1`.
- Profiles are exactly `nano`, `super`, and `ultra`; default is `super`.
- KIS uses non-streaming completions for all three profiles in this slice.
- A supplied `model` with `backend=codex-cli` is invalid. A supplied `model` with no backend explicitly selects NVIDIA and does not silently fall back to Codex.
- Keep the running `kis-op` instance untouched; candidate and final commissioning use only `kis-dev`.

---

### Task 1: Strict NVIDIA profile settings and canonical JSON

**Files:**
- Modify: `tests/providers/nvidia/test_nvidia.py`
- Modify: `tests/workflows/code_review/test_code_review_settings.py`
- Modify: `src/kis_mcp/providers/nvidia/settings.py`
- Modify: `src/kis_mcp/providers/nvidia/__init__.py`
- Modify: `settings/agents/code-review-agent.settings.json`

**Interfaces:**
- Produce `NvidiaModelProfile` with `model`, `guidance`, `temperature`, `top_p`, `max_tokens`, `reasoning_budget`, and `enable_thinking`.
- Produce `NvidiaSettings.profile(alias: str) -> NvidiaModelProfile` and fields `secret_ref`, `default_profile`, `profiles`.

- [ ] Write tests asserting exact aliases/model IDs, Super default, vault reference, per-profile parameters, strict alias/field rejection, and Nano `max_tokens=65536` acceptance.
- [ ] Run focused settings tests and confirm RED failures are due to the absent profile schema.
- [ ] Implement the minimal profile dataclasses/parser and canonical JSON values.
- [ ] Run focused settings tests and confirm GREEN.

### Task 2: Per-profile NVIDIA request construction and readiness guidance

**Files:**
- Modify: `tests/providers/nvidia/test_nvidia.py`
- Modify: `src/kis_mcp/providers/nvidia/client.py`
- Modify: `src/kis_mcp/providers/nvidia/provider.py`

**Interfaces:**
- `NvidiaNimClient.complete(prompt: str, model_profile: str | None = None) -> str`
- `NvidiaNimClient.review_with_model(project_path: object, prompt: str, model_profile: str) -> str`
- Provider readiness details expose only `default_profile` and bounded non-secret profile guidance/model metadata.

- [ ] Write tests for exact Nano/Super/Ultra payloads including `top_p`, `reasoning_budget`, `chat_template_kwargs.enable_thinking`, and `stream=false`.
- [ ] Write readiness tests proving guidance is visible and secret values are absent.
- [ ] Run focused provider tests and confirm RED.
- [ ] Implement minimal profile-aware client/readiness behavior.
- [ ] Run focused provider tests and confirm GREEN.

### Task 3: Advisory reviewer model selection and provenance

**Files:**
- Modify: `tests/workflows/code_review/test_reviewer.py`
- Modify: `src/kis_mcp/workflows/code_review/reviewer.py`
- Modify: `src/kis_mcp/workflows/code_review/tools.py`
- Modify: `src/kis_mcp/workflows/platform.py` only if construction needs adaptation.

**Interfaces:**
- `CodeReviewAgent.review(path, instructions="", backend=None, model=None) -> dict[str, Any]`
- Public `review_change_with_agent(path, instructions="", backend=None, model=None)`.
- NVIDIA success adds `model_profile` and `model`; non-NVIDIA results do not invent NVIDIA provenance.

- [ ] Write tests for default Super, explicit Nano/Super/Ultra, model-without-backend forcing NVIDIA, invalid alias, Codex+model rejection, and preservation of ordinary NVIDIA→Codex fallback when `model` is absent.
- [ ] Run focused reviewer tests and confirm RED.
- [ ] Implement minimal selection/provenance logic and tool signature/description.
- [ ] Run focused reviewer tests and confirm GREEN.

### Task 4: Vault-backed selected-instance startup and plaintext containment

**Files:**
- Modify: `tests/test_startup_scripts.py`
- Modify: `.gitignore`
- Modify: `scripts/start-chatgpt.ps1`

**Interfaces:**
- Launcher reads `settings/agents/code-review-agent.settings.json`, resolves only the configured `nvidia.secret_ref` through existing `secret-vault.ps1`, and sets the configured `api_key_env` in `$ServerEnvironment` only for the selected server child.
- The secret is cleared from local variables/environment maps after process creation.

- [ ] Write startup-script tests requiring `.env/` ignore, secret-vault use, canonical settings-driven reference/env-name lookup, child-only injection, and clearing/no retained-state disclosure.
- [ ] Run focused startup tests and confirm RED.
- [ ] Implement minimal launcher wiring; do not alter peer-instance lifecycle logic.
- [ ] Run focused startup tests and confirm GREEN.
- [ ] Migrate the operator key from `C:\Projects\.kis-mcp\temp\nvidia-nim-bootstrap-env\keys.env` into `secret://provider/nvidia-nim/api-key` without echoing plaintext; validate the reference exists; then move the plaintext bootstrap directory to recoverable quarantine.

### Task 5: Documentation, review, verification, commissioning, integration, and closeout

**Files:**
- Modify: `SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `.work/changes/091-nvidia-nim-model-profiles/tasks.md`
- Modify: `.work/changes/091-nvidia-nim-model-profiles/closeout.md`

- [ ] Document Nano = fast/focused iteration, Super = normal default substantive review, Ultra = deepest/high-impact analysis; explicitly note current review evidence is text-only.
- [ ] Document Codex as the next independent code/safety-review slice without claiming it is commissioned here.
- [ ] Run focused NVIDIA/reviewer/startup tests together.
- [ ] Run `scripts/change-workflow.ps1 check` in the change worktree.
- [ ] Review the complete diff against REQ-001 through REQ-015 and fix blocking findings.
- [ ] Run canonical `scripts/verify.ps1` on the exact change head and require exit 0.
- [ ] Start only candidate `kis-dev`; verify health and NVIDIA readiness; run bounded live Nano, Super, and Ultra review calls and record non-secret evidence.
- [ ] Commit the verified implementation/commissioning record.
- [ ] Merge `change/091-nvidia-nim-model-profiles` into clean local `main`, verify the merged exact head, and publish `main` using the repository's governed GitHub path if local main is ahead.
- [ ] Restart only `kis-dev` from final integrated `main`; recheck health/readiness and the default Super review path while confirming `kis-op` remains independently available.
- [ ] Complete `closeout.md`, run change-workflow cleanup for 091, and verify no 091 worktree/branch residue remains.
