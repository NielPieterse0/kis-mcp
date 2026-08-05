# MCP SDK Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add five exact-revision, no-install integrations to the existing Tools and Providers foundations without editing concurrently owned central runtime files.

**Architecture:** A shared immutable stdio-command contract validates local executable invocation without executing it. Three Tool packages and two Provider packages each own settings loading, readiness, descriptor construction, and explicit builders. Checked-in JSON settings and schemas pin upstream identity and keep secrets and package acquisition outside runtime behavior.

**Tech Stack:** Python 3.11+, immutable dataclasses, JSON, pytest, existing `kis_mcp.tools` and `kis_mcp.providers` contracts.

## Global Constraints

- Write only beneath `C:\Projects`.
- Enforce exactly HR-001, HR-002, and HR-003; do not create another policy rule.
- Do not install, update, download, authenticate, invoke subprocesses, or call external services.
- Do not edit central runtime paths claimed by changes 040 or 043.
- Pin exact upstream commits and package versions; reject floating acquisition forms.
- Never read, store, serialize, or log credential values.

---

### Task 1: Shared stdio command contract

**Requirements:** R1, R2, R3, R6, R7

**Files:**
- Create: `src/kis_mcp/tools/mcp_stdio.py`
- Test: `tests/tools/test_mcp_sdk_integrations.py`

**Produces:**
- `StdioMcpCommand(executable: str, arguments: tuple[str, ...], environment_names: tuple[str, ...] = ())`
- `StdioMcpCommand.to_json_dict() -> dict[str, object]`

- [ ] Write failing tests for required executable text, deterministic tuple normalization, environment-name validation, duplicate rejection, and acquisition-flag rejection (`-y`, `--yes`, `@latest`, unpinned `uvx`).
- [ ] Run the focused test file and confirm failures are caused by missing implementation.
- [ ] Implement the immutable contract with no execution method and JSON-safe output containing environment names only.
- [ ] Rerun focused tests and commit the green task.

### Task 2: MCP Spec plugin Tool

**Requirements:** R1, R2, R3, R4, R7

**Files:**
- Create: `src/kis_mcp/tools/mcp_spec/__init__.py`
- Create: `src/kis_mcp/tools/mcp_spec/settings.py`
- Create: `src/kis_mcp/tools/mcp_spec/tool.py`
- Create: `settings/tools/mcp-spec.tool.json`
- Create: `contracts/tools/mcp-sdk-integrations/mcp-spec.schema.json`
- Test: `tests/tools/test_mcp_sdk_integrations.py`

**Produces:**
- `McpSpecSettings.load(path: Path) -> McpSpecSettings`
- `mcp_spec_tool_descriptor(settings: McpSpecSettings) -> ToolDescriptor`

- [ ] Write failing tests proving exact source pinning, plugin-kind truthfulness, optional local-checkout readiness, and metadata-only builder output.
- [ ] Implement strict JSON loading and descriptor construction as `ToolKind.PLATFORM_INTERNAL` / `ToolBoundary.LOCAL_READ_ONLY`.
- [ ] Validate the checked-in JSON against its schema and rerun focused tests.
- [ ] Commit the green task.

### Task 3: Fetch and Everything Tools

**Requirements:** R1, R2, R3, R4, R6, R7

**Files:**
- Create: `src/kis_mcp/tools/fetch/__init__.py`
- Create: `src/kis_mcp/tools/fetch/settings.py`
- Create: `src/kis_mcp/tools/fetch/tool.py`
- Create: `src/kis_mcp/tools/everything/__init__.py`
- Create: `src/kis_mcp/tools/everything/settings.py`
- Create: `src/kis_mcp/tools/everything/tool.py`
- Create: `settings/tools/fetch.tool.json`
- Create: `settings/tools/everything.tool.json`
- Create: `contracts/tools/mcp-sdk-integrations/fetch.schema.json`
- Create: `contracts/tools/mcp-sdk-integrations/everything.schema.json`
- Test: `tests/tools/test_mcp_sdk_integrations.py`

**Produces:**
- `FetchToolSettings.load(path: Path) -> FetchToolSettings`
- `fetch_tool_descriptor(settings: FetchToolSettings) -> ToolDescriptor`
- `EverythingToolSettings.load(path: Path) -> EverythingToolSettings`
- `everything_tool_descriptor(settings: EverythingToolSettings) -> ToolDescriptor`

- [ ] Write failing tests for exact versions, fixed local commands, no `npx -y`/`uvx` acquisition, readiness states, and Fetch disabled/external-network-only metadata.
- [ ] Implement strict settings and descriptors; builders return `StdioMcpCommand` only.
- [ ] Validate JSON settings/schemas and rerun focused tests.
- [ ] Commit the green task.

### Task 4: Python SDK Provider

**Requirements:** R1, R2, R3, R7

**Files:**
- Create: `src/kis_mcp/providers/python_sdk/__init__.py`
- Create: `src/kis_mcp/providers/python_sdk/settings.py`
- Create: `src/kis_mcp/providers/python_sdk/provider.py`
- Create: `settings/providers/python-sdk.provider.json`
- Create: `contracts/providers/mcp-sdk-integrations/python-sdk.schema.json`
- Test: `tests/providers/test_mcp_sdk_providers.py`

**Produces:**
- `PythonSdkSettings.load(path: Path) -> PythonSdkSettings`
- `python_sdk_provider_descriptor(settings, *, version_lookup, importer) -> ProviderDescriptor`

- [ ] Write failing tests for installed/missing/version-mismatch readiness, injected importer behavior, exact source revision, and no dependency mutation.
- [ ] Implement strict settings, local-library descriptor, and explicit import builder.
- [ ] Validate JSON and rerun focused tests.
- [ ] Commit the green task.

### Task 5: Archived GitLab Provider

**Requirements:** R1, R2, R3, R5, R6, R7

**Files:**
- Create: `src/kis_mcp/providers/gitlab/__init__.py`
- Create: `src/kis_mcp/providers/gitlab/settings.py`
- Create: `src/kis_mcp/providers/gitlab/provider.py`
- Create: `settings/providers/gitlab.provider.json`
- Create: `contracts/providers/mcp-sdk-integrations/gitlab.schema.json`
- Test: `tests/providers/test_mcp_sdk_providers.py`

**Produces:**
- `GitLabProviderSettings.load(path: Path) -> GitLabProviderSettings`
- `gitlab_provider_descriptor(settings: GitLabProviderSettings) -> ProviderDescriptor`

- [ ] Write failing tests for archived status, fixed local Node command, PAT environment-name metadata, missing executable/entry-point/token readiness, and absence of token values.
- [ ] Implement strict settings and approved-external-connector descriptor; builder returns `StdioMcpCommand` only.
- [ ] Validate JSON and rerun focused tests.
- [ ] Commit the green task.

### Task 6: Documentation, review, and integration evidence

**Requirements:** R8, R9

**Files:**
- Create: `docs/development/mcp-sdk-integrations/README.md`
- Update: `.work/changes/044-mcp-sdk-integrations/tasks.md`
- Update: `.work/changes/044-mcp-sdk-integrations/closeout.md`

- [ ] Document exact pins, capability boundaries, installation/commissioning exclusions, and deferred central composition.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and `check` from the worktree.
- [ ] Run focused tests, JSON validation, compile/import checks, and `pwsh -NoProfile -File scripts/verify.ps1`.
- [ ] Review the full diff against the specification; fix blocking findings and rerun affected checks.
- [ ] Commit closeout evidence, push branch, open PR, review current PR head, merge with exact-head protection, update local main, and run safe cleanup/prune.

## Traceability

| Requirement | Tasks | Evidence |
|---|---|---|
| R1 | 1-5 | Package isolation and import tests |
| R2 | 2-5 | Exact JSON pins and descriptor assertions |
| R3 | 1-5 | No execution methods; injected probes/builders |
| R4 | 2-3 | Plugin truthfulness and Fetch disabled/external metadata tests |
| R5 | 5 | Archived/token-redaction tests |
| R6 | 1, 3, 5 | Command validation tests |
| R7 | 1-5 | JSON schema validation and deterministic serialization tests |
| R8 | 6 | Scope check and excluded central paths |
| R9 | 6 | Fresh focused/full verification and PR review evidence |
