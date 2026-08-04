# Discover Local Change Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, bounded local Git change inventory as the first internal D2 Discover change-intelligence seam.

**Architecture:** Keep all subprocess execution inside the existing `GitReader` adapter. Define immutable provider-neutral records in a new contract module, parse fixed NUL-delimited Git outputs, merge observations by current path, and validate serialized responses against a checked-in JSON Schema. Do not add public tool registration in this slice.

**Tech Stack:** Python 3.11+, dataclasses, pathlib, subprocess through the existing bounded runner, pytest, jsonschema.

## Global Constraints

- Write only within `C:\Projects`.
- Discover remains read-only and must not execute repository code or use the network.
- Work policy remains exactly HR-001, HR-002, and HR-003.
- `GitReader` remains the only Discover module importing `subprocess`.
- Request-side executable paths, Git arguments, refs, environment maps, and network targets are prohibited.
- Retained change records are bounded by configured `settings.discover.limits.max_files`.
- Public `inspect_change` registration is excluded.

---

### Task 1: Immutable change response contracts and schema

**Files:**
- Create: `src/kis_mcp/discover/change_contracts.py`
- Create: `contracts/discover/local-change-inventory.schema.json`
- Test: `tests/discover/test_local_change_inventory.py`

**Interfaces:**
- Produces: `ChangePathRecord`, `ChangeSummary`, and `LocalChangeInventory` dataclasses with deterministic `to_json_dict()` methods.
- Status values: `added`, `copied`, `deleted`, `modified`, `renamed`, `type_changed`, `unmerged`, `unknown`.

- [x] **Step 1: Write failing contract and schema tests**

Add tests that construct a response, assert the exact serialized field set and ordering-independent values, and validate the payload against `contracts/discover/local-change-inventory.schema.json` using `jsonschema.Draft202012Validator`.

- [x] **Step 2: Run focused tests and confirm failure**

Run:

```powershell
& C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/discover/test_local_change_inventory.py -q
```

Expected: collection fails because `kis_mcp.discover.change_contracts` does not exist.

- [x] **Step 3: Implement minimal immutable contracts and schema**

Create frozen slotted dataclasses with explicit serialization. Ensure `LocalChangeInventory.to_json_dict()` emits `schema_version`, `source`, `project_path`, `repository_root`, `changes`, `summary`, `diagnostics`, and `truncated`.

- [x] **Step 4: Run focused tests**

Run the same focused command. Expected: contract and schema tests pass while reader tests remain absent.

### Task 2: Fixed-template Git change inspection

**Files:**
- Modify: `src/kis_mcp/discover/git_reader.py`
- Test: `tests/discover/test_local_change_inventory.py`

**Interfaces:**
- Consumes: `ChangePathRecord`, `ChangeSummary`, `LocalChangeInventory`.
- Produces: `GitReader.inspect_local_changes(project_path: str) -> LocalChangeInventory`.

- [x] **Step 1: Add failing clean and mixed-state repository tests**

Create temporary Git repositories and prove:

- clean repository returns zero changes;
- staged, unstaged, and untracked paths are represented independently;
- one path with staged and unstaged modifications is merged into one record;
- output order is deterministic.

- [x] **Step 2: Run focused tests and confirm behavioral failures**

Run:

```powershell
& C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/discover/test_local_change_inventory.py -q
```

Expected: failures because `inspect_local_changes` is missing.

- [x] **Step 3: Implement fixed Git commands and merge logic**

Inside `GitReader.inspect_local_changes()`:

1. Resolve the project and validate Git metadata.
2. Reuse the existing deadline and `_run()` boundary.
3. Run exact staged, unstaged, and untracked commands.
4. Parse only complete NUL-delimited records.
5. Normalize statuses and merge records by current path.
6. Sort deterministically and cap retained records at `max_files`.
7. Return corrective diagnostics for unavailable Git, non-repositories, command failure, timeout, output truncation, and record-limit truncation.

- [x] **Step 4: Run focused tests**

Expected: clean and mixed-state tests pass.

### Task 3: Rename/copy/error/truncation coverage and integration verification

**Files:**
- Modify: `tests/discover/test_local_change_inventory.py`
- Modify: `.work/changes/020-discover-change-inventory/tasks.md`
- Modify: `.work/changes/020-discover-change-inventory/closeout.md`

**Interfaces:**
- Consumes: `GitReader.inspect_local_changes()` and the serialized contract.
- Produces: complete acceptance evidence for the slice.

- [x] **Step 1: Add failing edge-case tests**

Cover rename and copy previous paths, deleted and type-changed files, conflict normalization, configured record limits, simulated bounded-output truncation with incomplete final records, and non-repository diagnostics.

- [x] **Step 2: Run focused tests and repair only demonstrated failures**

Run the focused test file until all cases pass. Do not add untested statuses or public API surface.

- [x] **Step 3: Run affected Discover tests**

```powershell
& C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/discover/test_git_reader.py tests/discover/test_git_hardening.py tests/discover/test_architecture.py tests/discover/test_local_change_inventory.py -q
```

Expected: all pass.

- [x] **Step 4: Run scope, whitespace, and full verification**

```powershell
pwsh -File .\scripts\change-workflow.ps1 check

git diff --check

pwsh -File .\scripts\verify.ps1
```

The governance check may reproduce the pre-existing recursive stale-claim defect; record that exact limitation while still verifying the actual changed paths against `scope.json`.

- [x] **Step 5: Review and commit**

Review specification, plan, final diff, tests, architecture boundaries, and verification evidence together. Stage only owned paths and commit with:

```text
feat(discover): add local change inventory foundation
```
