# Discover Change Tool Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the merged working-tree change inspection service as one bounded read-only FastMCP tool.

**Architecture:** Add a focused `change_tools.py` adapter with an injected service protocol and deterministic structural error payload. Compose the existing `ReadAuthority`, `GitReader`, and `InspectChangeService` in `build_server()`, register the binder on a dedicated Discover change subserver, and mount it additively without modifying the active `inspect_project` implementation or binder.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, immutable Discover contracts, pytest.

## Global Constraints

- Write only within `C:\Projects`.
- Discover remains read-only and must not execute repository code or use the network.
- Work policy remains exactly HR-001, HR-002, and HR-003.
- Do not modify files owned by active changes `016-discover-response-hardening` or `022-supabase-oauth-commissioning`.
- Public support remains limited to the current working tree.
- Full `verify.ps1` runs must be serialized because the repository uses one shared editable Python environment.

---

### Task 1: Public change-tool binder

**Files:**
- Create: `src/kis_mcp/discover/change_tools.py`
- Test: `tests/discover/test_change_tool_registration.py`

**Interfaces:**
- Consumes: `InspectChangeRequest`, `InspectChangeResponse`, and an injected `InspectChangePort.inspect(request)` method.
- Produces: `register_change_tools(server: FastMCP, service: InspectChangePort) -> None`.

- [ ] **Step 1: Write failing tests for exact registration and delegation.**

Create a stub response whose `to_json_dict()` returns a representative `inspect_change` payload, register the binder on an empty `FastMCP`, assert the only local tool is `inspect_change`, run it with `path`, and assert the service received `InspectChangeRequest(path=...)`.

- [ ] **Step 2: Run the focused test and confirm the binder import fails.**

Run:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
& C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests\discover\test_change_tool_registration.py -q --no-header
```

Expected: collection fails because `kis_mcp.discover.change_tools` does not exist.

- [ ] **Step 3: Implement the minimal binder.**

Create `InspectChangePort` as a protocol and `register_change_tools()`. Register:

```python
@server.tool(
    name="inspect_change",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def inspect_change(path: str) -> dict[str, Any]:
    response = service.inspect(InspectChangeRequest(path=path))
    return response.to_json_dict()
```

Catch only request-construction `ValueError` and raise a JSON `ToolError` with:

```json
{
  "code": "DISCOVER_CHANGE_REQUEST_INVALID",
  "message": "The inspect_change request is invalid.",
  "reason": "<bounded validation message>",
  "field": "path",
  "corrective_actions": ["Provide a non-empty local project path beneath C:\\Projects."],
  "retryable": false
}
```

- [ ] **Step 4: Add and pass structural-error and annotation tests.**

Assert blank `path` raises `ToolError`, the parsed payload has the exact code and no `HR-` token, and the registered tool annotations match R4.

- [ ] **Step 5: Run the focused binder tests.**

Expected: all tests in `test_change_tool_registration.py` that do not require server composition pass.

### Task 2: Server composition

**Files:**
- Modify: `src/kis_mcp/server.py`
- Test: `tests/discover/test_change_tool_registration.py`

**Interfaces:**
- Consumes: `ReadAuthority`, `GitReader`, `InspectChangeService`, and `register_change_tools()`.
- Produces: a `build_server()` global catalogue containing both `inspect_project` and `inspect_change`, while preserving the existing local-provider catalogue.

- [ ] **Step 1: Write a failing server-catalogue test.**

Build the server with `validate_provider=False`, list the composed server tools, and assert `inspect_change` is present beside the existing gateway and Skills tools without removing `inspect_project`.

- [ ] **Step 2: Run the server-catalogue test and confirm it fails.**

Expected: `inspect_change` is absent.

- [ ] **Step 3: Compose the existing service in `build_server()`.**

Import the four additive dependencies, create a focused subserver, register the binder there, and mount it without a prefix:

```python
change_server = FastMCP("kis-mcp-discover-change")
register_change_tools(
    change_server,
    InspectChangeService(
        GitReader(
            authority=ReadAuthority(
                Path(runtime.project_boundary),
                runtime.discover_settings,
            ),
            settings=runtime.discover_settings,
        )
    ),
)
server.mount(change_server)
```

Keep existing `register_discover_tools()` behavior unchanged.

- [ ] **Step 4: Run focused registration and existing Discover registration tests.**

Run both `test_change_tool_registration.py` and `test_tool_registration.py`; update only the new test's expected catalogue. Existing tests may require a narrowly scoped expectation update later, but do not edit an actively owned file without explicit claim revision.

- [ ] **Step 5: Run affected Discover tests.**

Run the complete `tests\discover` suite with the worktree `PYTHONPATH` and `--no-sync` behavior where supported.

### Task 3: Governance, review, and verification

**Files:**
- Modify: `.work/changes/024-discover-change-tool-registration/tasks.md`
- Modify: `.work/changes/024-discover-change-tool-registration/closeout.md`
- Potential later integration after ownership release: `SPEC.md`, `docs/OPERATIONS.md`

**Interfaces:**
- Consumes: final diff, test evidence, active claim state, and authoritative public-interface documentation.
- Produces: merge-ready evidence only after documentation ownership is released and current claims are reconciled.

- [ ] **Step 1: Validate scope immediately after the first implementation edit.**

Run:

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 validate
pwsh -NoProfile -File .\scripts\change-workflow.ps1 check
```

- [ ] **Step 2: Review the specification, plan, code, tests, and diff together.**

Check exact request/response passthrough, annotations, exception boundaries, no policy or settings changes, no duplicate Git reader, and no overlap with active changes.

- [ ] **Step 3: Run whitespace and compilation checks.**

Run `git diff --check` and compile the changed Python modules with the locked interpreter.

- [ ] **Step 4: Reconcile current public-interface documentation after ownership release.**

Before merge, revise the scope claim and update `SPEC.md` and applicable operations documentation to state that working-tree `inspect_change` is public while other D2 targets remain unimplemented. Do not perform this step while change `022` owns those paths.

- [ ] **Step 5: Run serialized full verification and close out.**

Run `pwsh -NoProfile -File .\scripts\verify.ps1` only when no other worktree is synchronizing the shared environment. Record exact counts, unresolved non-blocking residuals, and rollback instructions in `closeout.md`.
