# Provider State Atomicity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the last valid Desktop Commander provider configuration when stdio shutdown interrupts a background state write.

**Architecture:** Bundle one CommonJS preload adapter inside `kis_mcp`. The gateway inserts Node's `--require` option before the existing Desktop Commander entry point and supplies the exact configured state path through an environment variable. The adapter passes every non-target write through unchanged and replaces only target writes with same-directory temporary writes followed by rename.

**Tech Stack:** Python 3.13, FastMCP 3.4.4, Node.js, CommonJS preload modules, pytest 8.4, PowerShell verification scripts.

## Global constraints

- Preserve exactly HR-001, HR-002, and HR-003; add no new block or restriction.
- Do not change Desktop Commander installation contents, provider package source, settings, or policy.
- Do not change PR #3 commissioning files or Discover-owned files.
- Modify `src/kis_mcp/server.py` only for launch integration coordinated through `005-discover-foundation`.
- Use the configured `RuntimeConfig.provider_state_file`; do not embed a machine-specific state path.
- Do not permanently delete incomplete temporary state files.
- Implement behavior test-first and retain red/green evidence in `tasks.md` and `closeout.md`.

---

### Task 1: Prove the adapter contract

**Files:**
- Create: `tests/test_provider_lifecycle.py`
- Create: `src/kis_mcp/provider_state_atomic.cjs`

**Interfaces:**
- Consumes: Node built-ins `node:fs/promises`, `node:path`, and `node:crypto`.
- Produces: `installAtomicStateWriter(options)` and `isSameStatePath(candidate, target)` from the CommonJS module.

- [ ] **Step 1: Write the failing adapter test**

Create a pytest test that locates `src/kis_mcp/provider_state_atomic.cjs`, executes Node with a fake promises filesystem, and asserts:

```python
assert adapter_path.is_file()
assert calls[0][0] == "writeFile"
assert Path(calls[0][1]).parent == target.parent
assert Path(calls[0][1]).name.startswith(f".{target.name}.41.")
assert calls[1] == ["rename", calls[0][1], str(target)]
assert passthrough_calls == [["writeFile", str(other), "other", "utf8"]]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/test_provider_lifecycle.py -q
```

Expected: failure because `provider_state_atomic.cjs` does not exist.

- [ ] **Step 3: Implement the minimal preload adapter**

Implement:

```javascript
function installAtomicStateWriter({
  fsPromises = require("node:fs/promises"),
  target = process.env.KIS_MCP_PROVIDER_STATE_FILE,
  processId = process.pid,
  randomId = randomUUID,
} = {}) {
  if (!target) return false;
  const originalWriteFile = fsPromises.writeFile.bind(fsPromises);
  const originalRename = fsPromises.rename.bind(fsPromises);
  fsPromises.writeFile = async function writeFile(file, data, options) {
    if (!isSameStatePath(file, target)) {
      return originalWriteFile(file, data, options);
    }
    const temp = path.join(
      path.dirname(path.resolve(target)),
      `.${path.basename(target)}.${processId}.${randomId()}.tmp`,
    );
    await originalWriteFile(temp, data, options);
    return originalRename(temp, path.resolve(target));
  };
  return true;
}
```

Auto-install it once at preload time and export the two testable functions.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same pytest command. Expected: adapter ordering and passthrough tests pass.

### Task 2: Shape the provider launch

**Files:**
- Create: `src/kis_mcp/provider_lifecycle.py`
- Modify: `tests/test_provider_lifecycle.py`
- Modify: `src/kis_mcp/server.py`

**Interfaces:**
- Consumes: existing provider launch arguments, provider environment mapping, and `RuntimeConfig.provider_state_file`.
- Produces: `prepare_provider_launch(*, args, environment, provider_state_file) -> tuple[list[str], dict[str, str]]`.

- [ ] **Step 1: Write the failing launch-shaping test**

Add a test that dynamically loads `kis_mcp.provider_lifecycle` and asserts:

```python
prepared_args, prepared_environment = prepare_provider_launch(
    args=["provider-entry.js", "--no-onboarding"],
    environment={"NO_UPDATE_NOTIFIER": "1"},
    provider_state_file=str(target),
)
assert prepared_args[0] == "--require"
assert Path(prepared_args[1]).name == "provider_state_atomic.cjs"
assert prepared_args[2:] == ["provider-entry.js", "--no-onboarding"]
assert prepared_environment["KIS_MCP_PROVIDER_STATE_FILE"] == str(target)
assert original_environment == {"NO_UPDATE_NOTIFIER": "1"}
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: failure because `kis_mcp.provider_lifecycle` does not exist.

- [ ] **Step 3: Implement launch shaping and server integration**

Create `provider_lifecycle.py` with:

```python
PROVIDER_STATE_ENV = "KIS_MCP_PROVIDER_STATE_FILE"


def prepare_provider_launch(*, args, environment, provider_state_file):
    adapter = Path(__file__).with_name("provider_state_atomic.cjs").resolve()
    if not adapter.is_file():
        raise RuntimeError(f"Provider state adapter is missing: {adapter}")
    prepared_environment = {str(key): str(value) for key, value in environment.items()}
    prepared_environment[PROVIDER_STATE_ENV] = str(provider_state_file)
    return ["--require", str(adapter), *[str(value) for value in args]], prepared_environment
```

In `build_server()`, call the helper after `_provider_environment(runtime)` and pass the returned arguments and environment to `StdioTransport`. Do not alter command, cwd, schemas, middleware, policy, or tools.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/test_provider_lifecycle.py tests/test_provider_readiness.py tests/test_provider_contract.py -q
```

Expected: all focused tests pass.

### Task 3: Verify real shutdown behavior and close the slice

**Files:**
- Modify: `.work/changes/006-provider-state-atomicity/tasks.md`
- Modify: `.work/changes/006-provider-state-atomicity/closeout.md`
- Create: `docs/development/provider-state-atomicity/plan.md`

**Interfaces:**
- Consumes: PR #3's unchanged `tests/support/live_proxy_commissioning.py` harness from its isolated worktree.
- Produces: current evidence that the 006 source tree passes live commissioning without restoration.

- [ ] **Step 1: Run the PR #3 harness against the 006 source tree**

Load the harness module from `004-live-proxy-commissioning` but call `run_live_commissioning()` with the 006 worktree root so the spawned gateway uses 006 source code.

Expected report:

```python
{
    "health": True,
    "surface": True,
    "read": True,
    "write": True,
    "hr001": True,
    "quarantine": True,
    "restore": True,
    "process": True,
    "provider_state": True,
}
```

- [ ] **Step 2: Run change-scope and repository verification**

Run:

```powershell
pwsh -File scripts/change-workflow.ps1 check
pwsh -File scripts/verify.ps1

git diff --check
```

Expected: scope check passes, repository verification passes, and no whitespace errors are reported.

- [ ] **Step 3: Review the final diff**

Confirm all requirements in `spec.md`, no changes outside declared paths, no hard-coded provider state path, no settings/policy/provider modifications, and no unexplained temporary or generated files.

- [ ] **Step 4: Commit and raise a draft PR**

Commit only declared paths with a focused message, push `change/006-provider-state-atomicity`, and create a draft PR against `main`. Do not merge without explicit confirmation for the current PR head.
