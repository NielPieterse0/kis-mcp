# Quarantine Integrity and Transaction Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the registered isolated worktree. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close audit findings F-04 and P1-05 by authenticating quarantine metadata and payloads, reporting corrupt records, and making multi-target quarantine failure compensating and recoverable.

**Architecture:** Keep `QuarantineService` as the transaction owner. Add a focused `quarantine_integrity.py` module for deterministic payload hashing and canonical HMAC calculation, extend versioned record metadata in `quarantine.py`, and route middleware batches through a new `quarantine_many()` API. Preserve the closed HR-001/HR-002/HR-003 policy set and existing public single-path operations.

**Tech Stack:** Python 3.11+, standard-library `hashlib`, `hmac`, `json`, `os`, `pathlib`, `secrets`, `shutil`, `stat`; pytest 8.4.x; FastMCP 3.4.4; PowerShell verification entry point.

## Global Constraints

- Write only within `C:\Projects`.
- Never permanently delete user artifacts; failed-operation cleanup may remove only generated metadata and empty generated directories after payload rollback.
- Keep quarantine state beneath `C:\Projects\.kis-mcp\quarantine`.
- Enforce only HR-001, HR-002, and HR-003.
- Do not alter provider schemas, command parsing, Git remote resolution, governance, modularity contracts, or provider installation.
- New records use schema version 2; unsigned legacy records fail closed and remain recoverable for supervised manual handling.
- Every production behavior change must be preceded by a failing regression test.

---

## File map

- Create `src/kis_mcp/quarantine_integrity.py`: deterministic payload-tree SHA-256, canonical metadata bytes, HMAC signing, and constant-time verification.
- Modify `src/kis_mcp/quarantine.py`: schema-version-2 record, strict parsing/validation, canonical relative paths, integrity-key lifecycle, list corruption reporting, batch preflight/rollback, and failure cleanup.
- Modify `src/kis_mcp/server.py`: call `QuarantineService.quarantine_many()` for direct-delete batches.
- Modify `tests/test_quarantine.py`: metadata tamper, payload tamper, strict schema, corrupt listing, batch rollback, overlap, and residue tests.
- Modify `tests/test_middleware.py`: prove middleware invokes atomic batch behavior and keeps HR-003 error normalization.
- Update `docs/development/quarantine-integrity/spec.md` and this plan only when implementation evidence requires reconciliation.

---

### Task 1: Versioned metadata and original-path authentication

**Requirements:** R1, R3, R7, R8

**Files:**
- Create: `src/kis_mcp/quarantine_integrity.py`
- Modify: `src/kis_mcp/quarantine.py`
- Test: `tests/test_quarantine.py`

**Interfaces:**
- Produces `payload_sha256(path: Path) -> str`.
- Produces `metadata_bytes(fields: Mapping[str, object]) -> bytes`.
- Produces `sign_metadata(key: bytes, fields: Mapping[str, object]) -> str`.
- Produces `verify_metadata(key: bytes, fields: Mapping[str, object], digest: str) -> bool`.
- Extends `QuarantineRecord` with `schema_version: int`, `original_relative_path: str`, `payload_digest: str`, and `integrity_digest: str`.
- Adds `QuarantineService._integrity_key_path`, `_load_integrity_key(create: bool)`, `_record_fields(record)`, and `_canonical_original_relative(path)`.

- [ ] **Step 1: Add failing original-path tamper test**

Add a test that quarantines `first/same.txt`, rewrites both `original_path` and `original_relative_path` to `second/same.txt` without changing `integrity_digest`, and expects `service.restore()` to raise `QuarantineError` matching `metadata integrity` while the payload remains in quarantine and neither destination exists.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/test_quarantine.py::test_restore_rejects_tampered_original_path_with_same_basename -q
```

Expected: FAIL because current metadata has no authenticated canonical relative path and restore accepts the redirect.

- [ ] **Step 3: Add strict-schema failing tests**

Add separate tests that mutate a valid metadata document by adding an unknown field, removing `integrity_digest`, setting `schema_version` to `1`, and corrupting the local integrity key. Each test must expect a bounded `QuarantineError`; no source or payload move may occur.

- [ ] **Step 4: Run strict-schema tests and confirm RED**

Run the new test node IDs together. Expected: FAIL because current parsing coerces values, ignores unknown fields, and has no schema or key validation.

- [ ] **Step 5: Implement canonical metadata and HMAC helpers**

Create `quarantine_integrity.py` with compact sorted JSON serialization and HMAC-SHA-256 signing/verification. Use `hmac.compare_digest`. Do not include `integrity_digest` itself in signed fields.

- [ ] **Step 6: Implement schema-version-2 records and integrity-key lifecycle**

In `quarantine.py`:

- define `QUARANTINE_SCHEMA_VERSION = 2`, exact metadata field names, key filename `.metadata-integrity.key`, and key length 32;
- create the key lazily for new quarantine operations using exclusive creation and 32 random bytes;
- require the key for reading/restoring signed records;
- store canonical `original_relative_path` and verify it reconstructs exactly `original_path` beneath the project boundary;
- parse exact field sets and exact scalar types rather than coercing arbitrary values to strings;
- sign all immutable and mutable record fields except `integrity_digest`;
- re-sign metadata after successful restore.

- [ ] **Step 7: Run Task 1 tests and confirm GREEN**

Run all metadata tests plus existing quarantine tests. Expected: PASS.

- [ ] **Step 8: Refactor without behavior expansion**

Keep metadata serialization in `quarantine_integrity.py`; keep path and transaction ownership in `QuarantineService`. Re-run Task 1 tests after refactoring.

- [ ] **Step 9: Commit Task 1**

Stage the new module, `quarantine.py`, and metadata tests. Commit:

```text
fix: bind quarantine restore metadata
```

---

### Task 2: Payload content integrity and corrupt-record visibility

**Requirements:** R2, R3, R4, R7, R9

**Files:**
- Modify: `src/kis_mcp/quarantine_integrity.py`
- Modify: `src/kis_mcp/quarantine.py`
- Test: `tests/test_quarantine.py`

**Interfaces:**
- `payload_sha256(path)` hashes regular files, symbolic links without following them, and sorted directory trees using streaming reads.
- `QuarantineService.list_records(limit=50)` retains its list return type when all records are valid but raises `QuarantineError` identifying invalid metadata instead of skipping it.

- [ ] **Step 1: Add failing payload-tamper tests**

Add one file test and one nested-directory test. After quarantine, change file contents inside the payload and expect restore to raise `QuarantineError` matching `payload integrity`; assert the original remains absent and the payload remains present.

- [ ] **Step 2: Run payload tests and confirm RED**

Expected: FAIL because current restore does not hash payload contents.

- [ ] **Step 3: Add failing corrupt-list test**

Create a valid record, corrupt its JSON or integrity digest, call `list_records()`, and expect `QuarantineError` containing the operation ID or metadata path. Confirm the test fails because current code silently continues.

- [ ] **Step 4: Implement deterministic payload hashing**

Hash typed records so files, directories, and symlinks cannot collide by content alone. Sort directory entries by exact name, include relative names and entry types, stream regular files in bounded chunks, and never follow symlinks.

- [ ] **Step 5: Validate payload digest before restore**

Compute and store the digest after the move and before metadata commit. During restore, compare the current payload digest to the signed expected value before creating the original parent or moving anything.

- [ ] **Step 6: Report corrupt records from listing**

Accumulate bounded invalid-record identifiers while scanning. If any invalid record is encountered within the scan window, raise one `QuarantineError` naming up to a small fixed number of affected operation IDs or metadata paths. Do not silently omit them.

- [ ] **Step 7: Run Task 2 tests and confirm GREEN**

Run all payload, list, and existing quarantine tests. Expected: PASS with no warnings.

- [ ] **Step 8: Commit Task 2**

Commit:

```text
fix: verify quarantined payload integrity
```

---

### Task 3: Atomic multi-target quarantine compensation

**Requirements:** R5, R6, R7, R8

**Files:**
- Modify: `src/kis_mcp/quarantine.py`
- Modify: `src/kis_mcp/server.py`
- Test: `tests/test_quarantine.py`
- Test: `tests/test_middleware.py`

**Interfaces:**
- Adds `QuarantineService.quarantine_many(paths: Sequence[str]) -> list[QuarantineRecord]`.
- Adds internal preflight source normalization and overlap checks.
- Adds internal rollback that moves payloads back in reverse order and removes only generated metadata and empty operation directories.
- `server.py` batch adapter returns `[asdict(record) for record in quarantine.quarantine_many(paths)]`.

- [ ] **Step 1: Add failing second-target rollback test**

Create two source files. Monkeypatch the move dependency so the first quarantine move succeeds, the second quarantine move fails, and the reverse compensation move succeeds. Expect `quarantine_many()` to raise, both originals to exist with original contents, and no new operation directories or metadata to remain.

- [ ] **Step 2: Run rollback test and confirm RED**

Expected: FAIL because `quarantine_many()` does not exist and server batches with a list comprehension.

- [ ] **Step 3: Add failing duplicate and overlap preflight tests**

Test duplicate identical paths and a parent directory plus its child. Expect failure before any target is moved and before any operation directory is created.

- [ ] **Step 4: Add failing rollback-residual test**

Force the second forward move to fail and the compensation move for the first target to fail. Expect the raised error to contain the residual operation ID, the first payload to remain in quarantine, and the second original to remain untouched.

- [ ] **Step 5: Add failing single-operation residue test**

Force metadata writing to fail after a payload move. Expect the source to be restored and the newly created operation directory to be absent.

- [ ] **Step 6: Implement preflight and compensation**

Resolve every source using the same path rules as `quarantine()`. Reject duplicates and ancestor/descendant overlaps before mutation. Quarantine sequentially; on failure, roll back completed records in reverse. If all rollback succeeds, remove generated operation metadata and empty directories. If rollback fails, retain recoverable payloads and report residual operation IDs.

- [ ] **Step 7: Route server and middleware batches through the service transaction**

Replace the server list comprehension with `quarantine.quarantine_many(paths)`. Keep middleware's `HR-003_QUARANTINE_FAILED` normalization unchanged.

- [ ] **Step 8: Add or update middleware assertion**

Use a batch callback that records the full path sequence once. Confirm direct-delete middleware invokes one batch transaction and returns all record dictionaries. Preserve the existing failure normalization test.

- [ ] **Step 9: Run Task 3 tests and confirm GREEN**

Run focused quarantine and middleware tests. Expected: PASS.

- [ ] **Step 10: Commit Task 3**

Commit:

```text
fix: compensate multi-target quarantine failures
```

---

### Task 4: Review, verification, and PR delivery

**Requirements:** R1-R9

**Files:**
- Review all changed files.
- Reconcile `docs/development/quarantine-integrity/spec.md` and `plan.md` if implementation differs.

- [ ] **Step 1: Run focused tests**

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests/test_quarantine.py tests/test_middleware.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run canonical verification**

```powershell
pwsh -File .\scripts\verify.ps1
```

Expected: locked interpreter, dependency, syntax, configuration, and complete pytest checks pass.

- [ ] **Step 3: Run diff and whitespace review**

Inspect working-tree and staged diffs, verify only the registered scope changed, and run Git whitespace validation.

- [ ] **Step 4: Perform code review**

Review requirement-to-change-to-test traceability, path canonicalization, integrity-key handling, payload hashing, rollback failure behavior, error messages, compatibility, and unnecessary complexity. Fix blocking findings and rerun affected tests.

- [ ] **Step 5: Run completion verification again after final edits**

Re-run focused tests and `scripts\verify.ps1` on the final commit candidate.

- [ ] **Step 6: Commit final artifact reconciliation if needed**

Use a separate documentation-only commit only when spec or plan evidence changed.

- [ ] **Step 7: Push the branch**

Push `change/003-quarantine-integrity` to `origin` without force.

- [ ] **Step 8: Open an unmerged pull request**

Base: `main`.

Title:

```text
fix: harden quarantine integrity and rollback
```

Body must include scope, attached audit finding IDs, design summary, test evidence, rollback/recovery notes, residual risks, and an explicit statement that the PR is not merged.

## Plan review approval

The operator explicitly instructed this agent to plan and implement the attached audit findings autonomously in a unique worktree and raise an unmerged PR. This plan is the bounded execution interpretation of that approval.

## Completion and stop conditions

Stop after the PR is open and unmerged, the branch is clean, canonical verification is green, blocking review findings are closed, and remaining audit findings outside F-04/P1-05 are explicitly out of scope.
