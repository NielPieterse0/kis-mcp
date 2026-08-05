# MCP Inspector Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install pinned MCP Inspector `2.0.0` as recoverable operator-supervised support tooling and provide a loopback launcher for either kis-mcp HTTP instance.

**Architecture:** Follow the existing managed-bootstrap pattern used by AgentSys and agnix. Keep package installation, runtime state, and launch behavior outside the primary gateway; use a JSON contract, a staged/quarantine installer, and a web launcher that derives the selected local target from kis-mcp settings.

**Tech Stack:** PowerShell 7, Node.js `>=22.19.0`, npm, JSON, pytest, Git worktrees, MCP Inspector `2.0.0`.

## Global Constraints

- Work only within the paths declared by `.work/changes/042-mcp-inspector-bootstrap/scope.json`.
- Install only `@modelcontextprotocol/inspector@2.0.0`; never use `@latest` or an unpinned range.
- Keep every controlled write beneath `C:\Projects` and reject reparse-point traversal.
- Preserve replaced installations through move-based quarantine; never permanently delete artifacts.
- External network access is limited to the explicit operator-supervised installer run.
- Do not mount Inspector into the gateway, Tools registry, Provider module, startup path, or policy.
- Keep `settings/kis-mcp.settings.json`, `SPEC.md`, and `docs/OPERATIONS.md` unchanged because active change `041-dual-instance-commissioning` owns them.

---

### Task 1: Pin the managed installation contract

**Files:**
- Create: `settings/bootstrap/mcp-inspector.install.json`
- Create: `tests/bootstrap/test_mcp_inspector_install.py`

**Interfaces:**
- Consumes: repository bootstrap convention under `settings/bootstrap`.
- Produces: JSON fields `package`, `version`, `minimum_node_version`, `install_root`, `managed_home`, `npm_cache_root`, `temp_root`, `log_root`, `quarantine_root`, `launcher_entry_point`, `web_ports`, and `kis_mcp_exposure`.

- [ ] **Step 1: Write failing settings tests**

```python
def test_mcp_inspector_settings_pin_v2_and_managed_paths() -> None:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert data["package"] == "@modelcontextprotocol/inspector"
    assert data["version"] == "2.0.0"
    assert data["minimum_node_version"] == "22.19.0"
    assert data["install_root"] == r"C:\Projects\.kis-mcp\tools\mcp-inspector\2.0.0"
    assert data["launcher_entry_point"].endswith(r"clients\launcher\build\index.js")
    assert data["web_ports"] == {"operation": 6274, "development": 6275}
    assert data["kis_mcp_exposure"] == {"enabled": False, "namespace": "mcp-inspector"}
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
pwsh -NoProfile -Command "$env:UV_PROJECT_ENVIRONMENT='C:\Projects\.kis-mcp\python-env'; $env:UV_CACHE_DIR='C:\Projects\.kis-mcp\uv-cache'; uv run --offline --no-sync pytest tests/bootstrap/test_mcp_inspector_install.py -q"
```

Expected: FAIL because the settings file does not exist.

- [ ] **Step 3: Create the exact JSON contract**

Use schema version `1`, the exact package/version and paths from the specification, distinct loopback web ports, and disabled kis-mcp exposure.

- [ ] **Step 4: Run the focused test and verify GREEN**

Expected: the settings test passes.

- [ ] **Step 5: Commit the contract and test**

```powershell
git add settings/bootstrap/mcp-inspector.install.json tests/bootstrap/test_mcp_inspector_install.py
git commit -m "test(bootstrap): define MCP Inspector contract"
```

### Task 2: Implement staged and recoverable installation

**Files:**
- Modify: `tests/bootstrap/test_mcp_inspector_install.py`
- Create: `scripts/install-mcp-inspector.ps1`

**Interfaces:**
- Consumes: Task 1 JSON contract.
- Produces: an installed package at `install_root`, `installation.json`, and recoverable prior state under `quarantine_root`.

- [ ] **Step 1: Add failing installer structure tests**

Assert that the script:

```python
assert "version -ne '2.0.0'" in script
assert "minimum_node_version" in script
assert "--save-exact" in script
assert "--ignore-scripts" in script
assert "$StagingInstallRoot" in script
assert "clients\\launcher\\build\\index.js" in script
assert "--cli', '--help" in script or "--cli --help" in script
assert "MCP_INSPECTOR_ACTIVATION_FAILED" in script
assert "failed-new-package" in script
assert "ReparsePoint" in script
assert "Move-Item" in script
assert "Remove-Item" not in script
assert "@latest" not in script.lower()
assert script.index("& $Npm.Source install") < script.index("Move-Item -LiteralPath $InstallRoot")
assert script.index("MCP_INSPECTOR_SMOKE_FAILED") < script.index("Move-Item -LiteralPath $InstallRoot")
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: FAIL because the installer does not exist.

- [ ] **Step 3: Implement path and prerequisite validation**

Create `Assert-InProjects` with normalized descendant checks and existing-ancestor reparse checks. Validate package identity, exact version, minimum Node semantic version, npm presence, and all managed roots before creating staging state.

- [ ] **Step 4: Implement staged package verification**

Set `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `NPM_CONFIG_CACHE`, `TEMP`, and `TMP` to managed paths. Run:

```powershell
& $Npm.Source install --prefix $StagingInstallRoot $PackageSpec --save-exact --ignore-scripts --no-audit --no-fund
```

Then verify the installed `package.json`, launcher file, and:

```powershell
& $Node.Source $StagingLauncher --cli --help
```

Fail before activation on any mismatch or non-zero smoke exit.

- [ ] **Step 5: Implement quarantine activation and rollback**

Move the current install to `<quarantine_root>/<operation-id>/previous-package`, activate the staged directory, and on failure move the failed new package to quarantine and restore the previous package. Write `installation.json` only for verified staged content.

- [ ] **Step 6: Run focused tests and verify GREEN**

Expected: all installer structure tests pass.

- [ ] **Step 7: Commit the installer**

```powershell
git add scripts/install-mcp-inspector.ps1 tests/bootstrap/test_mcp_inspector_install.py
git commit -m "feat(bootstrap): install MCP Inspector recoverably"
```

### Task 3: Implement the local-instance web launcher

**Files:**
- Modify: `tests/bootstrap/test_mcp_inspector_install.py`
- Create: `scripts/start-mcp-inspector.ps1`

**Interfaces:**
- Consumes: Task 1 settings plus `settings/kis-mcp.settings.json` fields `remote_mcp.host`, `remote_mcp.path`, and `remote_mcp.instances.<instance>.port/configured`.
- Produces: one foreground Inspector web process bound to the configured loopback UI port and targeting the selected local kis-mcp endpoint.

- [ ] **Step 1: Add failing launcher tests**

Assert that the launcher contains:

```python
assert "ValidateSet('operation', 'development')" in launcher
assert "settings\\kis-mcp.settings.json" in launcher
assert "remote_mcp.instances" in launcher
assert "MCP_INSPECTOR_INSTANCE_NOT_CONFIGURED" in launcher
assert "$env:HOST = '127.0.0.1'" in launcher
assert "$env:CLIENT_PORT" in launcher
assert "$env:MCP_STORAGE_DIR" in launcher
assert "$env:MCP_LOG_FILE" in launcher
assert "--server-url" in launcher
assert "--transport" in launcher
assert "'http'" in launcher
assert "& $Node.Source $LauncherPath --web" in launcher
assert "npm install" not in launcher.lower()
assert "Remove-Item" not in launcher
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: FAIL because the launcher does not exist.

- [ ] **Step 3: Implement settings and installation resolution**

Validate the selected instance, installation metadata, exact package version, launcher file, configured target, loopback host, and configured Inspector web port.

- [ ] **Step 4: Implement contained environment and launch**

Set Inspector home, storage, logs, cache, temp, fixed loopback host, fixed UI port, and browser-open flag beneath managed roots. Start:

```powershell
& $Node.Source $LauncherPath --web --server-url $ServerUrl --transport http
```

Return Inspector’s exit code without installing, updating, deleting, or terminating another process.

- [ ] **Step 5: Run focused tests and verify GREEN**

Expected: all settings, installer, and launcher tests pass.

- [ ] **Step 6: Commit the launcher**

```powershell
git add scripts/start-mcp-inspector.ps1 tests/bootstrap/test_mcp_inspector_install.py
git commit -m "feat(bootstrap): launch Inspector for local instances"
```

### Task 4: Document, verify, install, and close the slice

**Files:**
- Create: `docs/development/tools/mcp-inspector.md`
- Modify: `.work/changes/042-mcp-inspector-bootstrap/tasks.md`
- Modify: `.work/changes/042-mcp-inspector-bootstrap/closeout.md`

**Interfaces:**
- Consumes: completed installer/launcher and fresh verification evidence.
- Produces: operator commands, architecture status, recovery instructions, merged PR, and cleaned worktree.

- [ ] **Step 1: Document the operator workflow**

Document exact commands:

```powershell
pwsh -NoProfile -File .\scripts\install-mcp-inspector.ps1
pwsh -NoProfile -File .\scripts\start-mcp-inspector.ps1 -Instance development
pwsh -NoProfile -File .\scripts\start-mcp-inspector.ps1 -Instance operation -NoBrowser
```

State that Inspector is support tooling, not gateway-mounted; the selected kis-mcp instance must already be running; installation may access npm; launch binds loopback; and prior installs are quarantined.

- [ ] **Step 2: Run focused tests**

```powershell
pwsh -NoProfile -Command "$env:UV_PROJECT_ENVIRONMENT='C:\Projects\.kis-mcp\python-env'; $env:UV_CACHE_DIR='C:\Projects\.kis-mcp\uv-cache'; uv run --offline --no-sync pytest tests/bootstrap/test_mcp_inspector_install.py -q"
```

Expected: PASS.

- [ ] **Step 3: Run scope and repository verification**

```powershell
pwsh -NoProfile -File scripts/change-workflow.ps1 check
pwsh -NoProfile -File scripts/verify.ps1
```

Expected: both pass on the current branch.

- [ ] **Step 4: Run the supervised installer**

```powershell
pwsh -NoProfile -File scripts/install-mcp-inspector.ps1
```

Verify returned JSON reports package `@modelcontextprotocol/inspector`, version `2.0.0`, the managed install path, and a successful launcher smoke.

- [ ] **Step 5: Run a non-server launcher validation**

Use `-NoBrowser` only after confirming the selected kis-mcp instance is running. If it is not running, verify installation and launcher structure without claiming a live Inspector-to-gateway connection.

- [ ] **Step 6: Review the final diff**

Check specification coverage, no unclaimed files, no permanent delete command, no unpinned dependency, no gateway/policy edits, truthful docs, and fresh evidence after the last edit.

- [ ] **Step 7: Complete closeout, commit, push, create PR, merge, and clean**

Use the repository Git/GitHub helpers, merge only after checks pass, update main, run `scripts/change-workflow.ps1 cleanup 042-mcp-inspector-bootstrap`, and verify the primary worktree is clean.
