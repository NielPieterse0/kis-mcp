# Modularity Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the currently actionable modularity violations without overlapping active worktrees or changing runtime policy.

**Architecture:** Move reusable settings ownership down into the NVIDIA provider and Codex tool packages, leaving the code-review workflow as the aggregate composer. Extract Control Center evidence interpretation into five typed read-only adapters. Make provider smoke routines accept application composition and move `build_server` usage to a supervised script. Remove the obsolete root registry alias and enforce all boundaries with static architecture tests.

**Tech Stack:** Python 3.13, dataclasses, FastMCP, pytest, PowerShell 7, repository change-governance scripts, Git/GitHub workflow tools.

## Global constraints

- Stay inside `scope.json`; do not edit `server.py`, `tools/__init__.py`, runtime settings, policy, or Discover.
- Preserve exactly HR-001, HR-002, and HR-003; introduce no new hard block or provider restriction.
- Add failing tests before each behavior or boundary change.
- Add no dependencies and perform no package installation.
- Preserve optional-agent failure containment, Control Center bounded degradation, and provider commissioning report shapes.
- Use frequent task commits and rerun affected tests after every review fix.

---

### Task 1: Correct provider/tool/workflow settings dependency direction

**Requirements:** R1, R2, R3

**Files:**
- Create: `src/kis_mcp/providers/nvidia/settings.py`
- Create: `src/kis_mcp/tools/codex_cli/settings.py`
- Modify: `src/kis_mcp/providers/nvidia/__init__.py`
- Modify: `src/kis_mcp/providers/nvidia/client.py`
- Modify: `src/kis_mcp/providers/nvidia/provider.py`
- Modify: `src/kis_mcp/providers/platform.py`
- Modify: `src/kis_mcp/tools/codex_cli/__init__.py`
- Modify: `src/kis_mcp/tools/codex_cli/adapter.py`
- Modify: `src/kis_mcp/tools/codex_cli/tool.py`
- Modify: `src/kis_mcp/workflows/code_review/__init__.py`
- Modify: `src/kis_mcp/workflows/code_review/settings.py`
- Modify: `tests/providers/nvidia/test_nvidia.py`
- Modify: `tests/providers/test_platform_composition.py`
- Modify: `tests/tools/codex_cli/test_adapter.py`
- Modify: `tests/workflows/code_review/test_code_review_settings.py`
- Modify: `tests/workflows/code_review/test_reviewer.py`
- Create: `tests/architecture/test_modularity_boundaries.py`

**Interfaces:**

- `NvidiaSettings(enabled: bool, base_url: str, model: str, api_key_env: str, timeout_seconds: int, temperature: float, max_tokens: int)`
- `nvidia_settings_from_mapping(value: Any) -> NvidiaSettings`
- `disabled_nvidia_settings() -> NvidiaSettings`
- `NvidiaSettingsError(RuntimeError)`
- `CodexSettings(enabled: bool, script_path: Path, executable: str, timeout_seconds: int, max_output_chars: int)`
- `codex_settings_from_mapping(value: Any, repository_root: Path) -> CodexSettings`
- `disabled_codex_settings(repository_root: Path) -> CodexSettings`
- `CodexSettingsError(RuntimeError)`
- `AgentSettings` continues to contain `nvidia: NvidiaSettings` and `codex: CodexSettings`.

- [ ] **Step 1: Write failing ownership and import-boundary tests**

  Update provider/tool tests to import their settings from `kis_mcp.providers.nvidia` and `kis_mcp.tools.codex_cli`. Add architecture assertions that Python files under `providers/nvidia`, `tools/codex_cli`, and `providers/platform.py` contain no import whose module starts with `kis_mcp.workflows.code_review` or the equivalent relative path.

- [ ] **Step 2: Run the focused tests and confirm failure**

  Run:

  ```powershell
  pwsh -NoProfile -Command "& 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe' -m pytest tests/providers/nvidia tests/providers/test_platform_composition.py tests/tools/codex_cli tests/workflows/code_review tests/architecture/test_modularity_boundaries.py -q"
  ```

  Expected: failure because module-owned settings files and exports do not exist and current imports cross into the workflow.

- [ ] **Step 3: Implement NVIDIA-owned settings**

  Move NVIDIA validation from the workflow into `providers/nvidia/settings.py`. Validate exact keys, HTTPS base URL, environment-variable syntax, integer and float bounds. Return the same disabled defaults currently used by `disabled_agent_settings`. Update NVIDIA client/provider imports and export the settings API from `providers/nvidia/__init__.py`.

- [ ] **Step 4: Implement Codex-owned settings**

  Move Codex validation into `tools/codex_cli/settings.py`. Resolve relative script paths against the repository root and reject paths outside that root. Return the same disabled defaults currently used by `disabled_agent_settings`. Update Codex adapter/tool imports and export the settings API from `tools/codex_cli/__init__.py`.

- [ ] **Step 5: Reduce workflow settings to aggregate composition**

  Import the module-owned settings/parser APIs into `workflows/code_review/settings.py`; retain only workflow root validation, backend selection, budgets, aggregate loading, and safe fallback. Catch `NvidiaSettingsError` and `CodexSettingsError` and re-raise `AgentSettingsError` with the bounded message. Remove NVIDIA/Codex settings from the workflow package public exports.

- [ ] **Step 6: Remove platform-to-workflow dependency and workflow-specific capability mapping**

  `providers.platform` imports `NvidiaSettings` and `disabled_nvidia_settings` from `.nvidia`. Its no-argument fallback uses the disabled provider-owned default. In `nvidia_provider_descriptor`, retain capability ID `llm.inference.nvidia-nim`, retain `effects=("external_network",)`, and set `tool_names=()`.

- [ ] **Step 7: Run focused tests**

  Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 8: Commit Task 1**

  ```powershell
  git add src/kis_mcp/providers/nvidia src/kis_mcp/providers/platform.py src/kis_mcp/tools/codex_cli src/kis_mcp/workflows/code_review tests/providers/nvidia tests/providers/test_platform_composition.py tests/tools/codex_cli tests/workflows/code_review tests/architecture/test_modularity_boundaries.py
  git commit -m "refactor: restore provider and tool settings ownership"
  ```

---

### Task 2: Add stable Control Center read adapters

**Requirements:** R4, R7

**Files:**
- Create: `src/kis_mcp/control_center/readers.py`
- Modify: `src/kis_mcp/control_center/snapshot.py`
- Modify: `src/kis_mcp/control_center/__init__.py`
- Modify: `tests/control_center/test_control_center_snapshot.py`
- Modify: `tests/control_center/test_control_center_snapshot_limits.py`
- Create: `tests/control_center/test_control_center_readers.py`
- Modify: `tests/architecture/test_modularity_boundaries.py`

**Interfaces:**

- `RuntimeStatusReader(settings: ControlCenterSettings).read(diagnostics: list[Diagnostic]) -> RuntimeSummary`
- `PolicyStatusReader(settings: ControlCenterSettings).read(diagnostics: list[Diagnostic]) -> PolicySummary`
- `ProviderStatusReader(settings: ControlCenterSettings).read(diagnostics: list[Diagnostic]) -> tuple[ProviderSummary, ...]`
- `QuarantineStatusReader(settings: ControlCenterSettings).read(diagnostics: list[Diagnostic]) -> tuple[QuarantineSummary, tuple[QuarantineRecordSummary, ...]]`
- `GitStatusReader(settings: ControlCenterSettings).read() -> GitSummary`
- Internal bounded JSON reader requires an exact integer schema version before any document-specific field access.

- [ ] **Step 1: Add failing schema-drift and adapter-boundary tests**

  Update valid fixture documents to include `schema_version`. Add tests for missing/unsupported runtime, policy, provider, and quarantine schema versions. Add a static assertion that `snapshot.py` contains no `json.loads`, `metadata.json`, `subprocess.run`, or canonical raw settings path interpretation.

- [ ] **Step 2: Run Control Center tests and confirm failure**

  Run:

  ```powershell
  pwsh -NoProfile -Command "& 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe' -m pytest tests/control_center tests/architecture/test_modularity_boundaries.py -q"
  ```

  Expected: failure because the readers do not exist and current snapshot code directly parses the evidence.

- [ ] **Step 3: Implement bounded JSON and runtime/policy/provider readers**

  Centralize byte-bounded UTF-8 JSON loading in `readers.py`. Require `schema_version == 1`; preserve existing diagnostic codes and unavailable/invalid summary states. Keep provider entry and policy rule limits deterministic.

- [ ] **Step 4: Implement quarantine and Git readers**

  Move operation-ID matching, bounded directory enumeration, metadata reading, restored/active/invalid counting, Git environment sanitization, timeout handling, and branch parsing into their dedicated readers. Require quarantine `schema_version == QUARANTINE_SCHEMA_VERSION`, matching operation ID, string `original_path` and `item_type`, and `restored_at` as string or null.

- [ ] **Step 5: Reduce snapshot to orchestration**

  Construct default readers in `ControlCenterSnapshotService.__init__`, allow test injection, and replace raw-reader methods with adapter calls. Keep Discover, provider-runtime, approvals, observability, actions, and verification behavior in `snapshot.py`.

- [ ] **Step 6: Run Control Center tests**

  Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 7: Commit Task 2**

  ```powershell
  git add src/kis_mcp/control_center tests/control_center tests/architecture/test_modularity_boundaries.py
  git commit -m "refactor: isolate control center evidence readers"
  ```

---

### Task 3: Move live-smoke application composition out of providers

**Requirements:** R5, R7

**Files:**
- Modify: `src/kis_mcp/providers/github/smoke.py`
- Modify: `src/kis_mcp/providers/supabase/smoke.py`
- Create: `scripts/run-provider-live-smoke.py`
- Modify: `scripts/smoke-github-mcp.ps1`
- Modify: `scripts/smoke-supabase-mcp.ps1`
- Modify: `tests/providers/github/test_live_smoke.py`
- Modify: `tests/providers/github/test_scripts.py`
- Modify: `tests/providers/supabase/test_supabase_artifacts.py`
- Modify: `tests/providers/supabase/test_supabase_commissioning.py`
- Modify: `tests/architecture/test_modularity_boundaries.py`

**Interfaces:**

- `ServerFactory = Callable[[], FastMCP]`
- GitHub: `run_live_smoke(server_factory: ServerFactory, settings: GitHubProviderSettings | None = None, *, environ: Mapping[str, str] | None = None) -> dict[str, bool | str]`
- Supabase: `run_live_smoke(server_factory: ServerFactory, config: SupabaseProviderConfig | None = None, *, environ: Mapping[str, str] | None = None) -> dict[str, bool]`
- `scripts/run-provider-live-smoke.py {github|supabase}` imports `build_server`, invokes the selected provider-local routine, and prints sorted JSON.

- [ ] **Step 1: Write failing injected-factory and import-boundary tests**

  Update smoke tests to pass a fake server factory and verify it is invoked only after provider-specific preconditions pass. Add architecture assertions that provider packages do not import `kis_mcp.server`.

- [ ] **Step 2: Run focused smoke tests and confirm failure**

  Run:

  ```powershell
  pwsh -NoProfile -Command "& 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe' -m pytest tests/providers/github tests/providers/supabase tests/architecture/test_modularity_boundaries.py -q"
  ```

  Expected: failure because current provider smoke modules construct the application server internally.

- [ ] **Step 3: Inject application composition into provider smoke routines**

  Remove `from kis_mcp.server import build_server` and provider-module `main()` entry points. Accept the required server factory, execute existing precondition checks first, build once, then pass the server to the existing async client flow.

- [ ] **Step 4: Add the supervised application smoke script and update PowerShell callers**

  The script uses `argparse` with exact choices `github` and `supabase`, imports `build_server` at the application boundary, selects the provider routine, and prints sorted JSON. Update both PowerShell scripts to call this file through the existing offline `uv run --no-sync` command.

- [ ] **Step 5: Run focused smoke tests**

  Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 6: Commit Task 3**

  ```powershell
  git add src/kis_mcp/providers/github/smoke.py src/kis_mcp/providers/supabase/smoke.py scripts/run-provider-live-smoke.py scripts/smoke-github-mcp.ps1 scripts/smoke-supabase-mcp.ps1 tests/providers/github tests/providers/supabase tests/architecture/test_modularity_boundaries.py
  git commit -m "refactor: inject provider smoke application composition"
  ```

---

### Task 4: Retire the root provider registry alias and complete boundary checks

**Requirements:** R6, R7

**Files:**
- Remove: `src/kis_mcp/provider_registry.py`
- Modify: `tests/providers/github/test_registry.py`
- Modify: `tests/architecture/test_modularity_boundaries.py`

- [ ] **Step 1: Change the registry test to the canonical package and add a failing absence check**

  Import `ProviderDescriptor` and `ProviderRegistry` from `kis_mcp.providers`. Assert the root alias path does not exist and scan tracked Python source for imports of `kis_mcp.provider_registry` or `from kis_mcp import provider_registry`.

- [ ] **Step 2: Run tests and confirm failure while the alias remains**

  Run:

  ```powershell
  pwsh -NoProfile -Command "& 'C:\Projects\.kis-mcp\python-env\Scripts\python.exe' -m pytest tests/providers/github/test_registry.py tests/architecture/test_modularity_boundaries.py -q"
  ```

  Expected: failure because `src/kis_mcp/provider_registry.py` still exists.

- [ ] **Step 3: Remove the alias through the recoverable repository deletion path**

  Remove only `src/kis_mcp/provider_registry.py`. Do not alter provider contracts or registry implementation.

- [ ] **Step 4: Run focused tests**

  Run the command from Step 2. Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 4**

  ```powershell
  git add -A src/kis_mcp/provider_registry.py tests/providers/github/test_registry.py tests/architecture/test_modularity_boundaries.py
  git commit -m "refactor: retire provider registry compatibility alias"
  ```

---

### Task 5: Review, verify, publish, merge, and clean up

**Requirements:** R1–R7

**Files:**
- Modify: `.work/changes/046-modularity-hardening/tasks.md`
- Modify: `.work/changes/046-modularity-hardening/closeout.md`

- [ ] **Step 1: Run change scope validation**

  ```powershell
  pwsh -NoProfile -File scripts/change-workflow.ps1 check
  ```

- [ ] **Step 2: Review the complete diff against spec and plan**

  Inspect `git diff main...HEAD`, record findings by severity, fix all blocking findings, rerun affected focused tests, and re-review changed areas.

- [ ] **Step 3: Run full repository verification**

  ```powershell
  pwsh -NoProfile -File scripts/verify.ps1
  ```

  Expected: configuration, exact three-rule policy, syntax, dependencies, governance, and full pytest suite pass.

- [ ] **Step 4: Complete traceability and closeout artifacts**

  Record requirement-to-task-to-test evidence, commits, exact commands, outcomes, deferred items, recovery, and residual risks. Commit the artifacts.

- [ ] **Step 5: Push and create the PR**

  Push `change/046-modularity-hardening`, create a PR to `main`, and include scope, verification, risks, and explicit deferrals in the PR body.

- [ ] **Step 6: Perform final PR review and CI check**

  Review the remote PR files and checks independently. Merge only when the exact reviewed head is current, required checks pass, and no blocking review finding remains.

- [ ] **Step 7: Merge and clean up**

  Merge without force, update the clean primary worktree, run post-merge verification or repository report, then run:

  ```powershell
  pwsh -NoProfile -File scripts/change-workflow.ps1 cleanup 046-modularity-hardening
  ```

  Confirm the worktree and local change branch are removed without affecting active changes `040` or `041`.
