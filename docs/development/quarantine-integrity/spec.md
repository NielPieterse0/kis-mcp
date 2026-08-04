# Quarantine Integrity and Transaction Safety Specification

## Outcome, actors, and current state

The HR-003 quarantine service must restore only the exact path and intact payload recorded by the original quarantine operation. Multi-target deletion transforms must not silently leave partially quarantined state when a later target fails.

The current implementation structurally validates payload location, but mutable `original_path` metadata can redirect restore to another in-boundary path with the same basename. Payload contents are not integrity-checked, corrupt records are silently omitted from listing, failed operations may leave residue, and middleware batches quarantine targets one at a time without service-owned rollback semantics.

The operator requested implementation of the attached F-04 and P1-05 audit findings on an isolated branch without merging the resulting pull request.

## Requirements and invariants

- **R1 — Canonical original-path binding:** Every new quarantine record must store a canonical path relative to `C:\Projects`. The absolute `original_path`, canonical relative path, operation ID, payload path, item type, timestamps, and payload digest must be bound by a cryptographic metadata integrity value. Restore must reject any changed field, including another valid in-boundary path with the same basename.
- **R2 — Payload content integrity:** Quarantine must compute a deterministic SHA-256 digest for the moved file or directory tree. Restore must recompute and compare the digest before moving the payload. A mismatch must fail closed without changing the original path or payload.
- **R3 — Strict record validation:** Metadata must use an explicit schema version and exact field set with type validation. Unknown, missing, legacy unsigned, malformed, path-inconsistent, or integrity-invalid records must not be restored.
- **R4 — Corrupt-record visibility:** Record listing must not silently omit corrupt metadata. It must raise a bounded `QuarantineError` identifying the affected operation or metadata path.
- **R5 — Batch compensation:** A service-owned `quarantine_many(paths)` operation must preflight all targets, reject duplicate or overlapping targets before mutation, quarantine them in order, and compensate in reverse order if a later target fails. If compensation is incomplete, the error must identify residual operation IDs for supervised recovery.
- **R6 — Failure residue cleanup:** When a single or batch quarantine attempt fails and rollback succeeds, generated metadata, payload directories, and operation directories created by that failed attempt must be removed when empty. User payloads must remain at their original paths.
- **R7 — Existing public behavior:** Single-path quarantine and restore remain available. Restore still refuses overwrite. Middleware direct-delete transforms use the service-owned batch operation and continue returning `HR-003_QUARANTINE_FAILED` on failure.
- **R8 — No new policy rule:** The change must enforce only HR-003 recoverability and integrity. It must not add approval tiers, deny tools, restrict reads, add network behavior, or alter HR-001/HR-002 resolution.
- **R9 — Error normalization:** Metadata read failures and payload-integrity calculation failures must be converted to bounded `QuarantineError` results so gateway restore and quarantine wrappers continue returning HR-003 corrective errors rather than leaking raw filesystem, JSON, or hashing exceptions.

## System, trust, data, compatibility, and operational boundaries

- Repository authority remains `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, policy JSON, and operations documentation.
- All generated state remains beneath `C:\Projects\.kis-mcp\quarantine`.
- The system is private, single-operator, and directly supervised. The integrity mechanism protects against accidental or metadata-only tampering; it is not a hostile-host security boundary against an actor that can also read the integrity key and rewrite code or all quarantine state.
- New records use schema version 2. Legacy unsigned records are list-visible as invalid and are not automatically upgraded or restored because their original path and payload contents cannot be authenticated retroactively.
- No provider schema, command parser, Git remote resolver, CI, worktree governance, or contracts-layer change is included.

## Explicit exclusions

- Permanent disposal of quarantine contents.
- Encryption of quarantined data.
- Cross-volume transactional filesystem guarantees.
- Automatic migration or restoration of legacy unsigned records.
- A new public quarantine inventory schema; `kis_list_quarantine` keeps returning valid records and fails clearly when corrupt records are present.
- Changes to the broader F-01/P0 process-containment decision, provider commissioning, installation integrity, or repository governance findings.

## Architecture and data flow

### Metadata integrity

`QuarantineService` owns a 32-byte local HMAC key at:

```text
<quarantine_root>\.metadata-integrity.key
```

The key is created lazily with exclusive creation for the first new quarantine operation. Existing restore or list operations require the key to exist and be exactly 32 bytes for schema-version-2 records.

Each record contains:

```text
schema_version
operation_id
original_path
original_relative_path
payload_path
item_type
payload_digest
quarantined_at
restored_at
integrity_digest
```

`integrity_digest` is HMAC-SHA-256 over canonical compact JSON containing every field except `integrity_digest`. Validation recomputes the canonical relative path and expected payload path, validates exact metadata types and fields, then verifies the HMAC with constant-time comparison.

### Payload digest

The payload digest is deterministic SHA-256 over a typed representation:

- regular file: file marker plus file bytes;
- symbolic link: link marker plus link target text;
- directory: directory marker plus sorted relative entry names, entry types, and recursive contents.

The implementation must not follow symbolic links while hashing.

### Batch transaction behavior

`quarantine_many(paths)` performs:

1. Resolve and validate every source without mutation.
2. Reject duplicates and ancestor/descendant overlaps.
3. Quarantine each source using the same single-path implementation.
4. On failure, roll back completed records in reverse order.
5. Remove generated operation residue after each successful rollback.
6. Raise one `QuarantineError` describing the original failure and any residual operation IDs if rollback was incomplete.

Middleware and server batch adapters call this method rather than a Python list comprehension.

## Security, privacy, failure, migration, and reversibility risks

- **Integrity key loss or corruption:** New signed records become unrestorable through the normal tool. Fail closed with an explicit error. Operator recovery remains manual and supervised.
- **Payload tampering:** Restore is blocked before any move. The quarantined payload remains available for inspection.
- **Rollback failure:** The error identifies residual operation IDs. No permanent delete is attempted; remaining payloads stay in quarantine for supervised recovery.
- **Legacy records:** They remain on disk and are reported as unsupported unsigned metadata. No destructive migration occurs.
- **Large directory hashing:** Digest computation is proportional to payload size and occurs after move and before restore. This is accepted for correctness; streaming reads bound memory usage.
- **Concurrent operations:** Exclusive operation IDs and atomic metadata replacement remain. Integrity-key creation uses exclusive file creation. Full multi-process transaction locking is excluded.

## Acceptance and release evidence

- A regression test changes `original_path` and `original_relative_path` to another valid in-boundary path with the same basename and restore rejects the record for metadata integrity.
- A regression test changes payload contents and restore rejects before moving.
- Tests reject unknown fields, missing integrity fields, invalid integrity key, and legacy unsigned metadata.
- Listing a corrupt record raises a clear `QuarantineError` instead of omitting it.
- A forced second-target failure restores the first target and leaves no new operation residue.
- Duplicate and overlapping batch targets fail before mutation.
- A forced rollback failure reports residual operation IDs and preserves recoverable quarantine state.
- Existing quarantine, restore, overwrite protection, relative path, payload-path tamper, middleware HR-003 transformation, and canonical repository verification tests pass.
- `pwsh -File .\scripts\verify.ps1` passes from the isolated worktree using the locked external interpreter.

## Rollback and recovery strategy

The branch can be reverted as one PR because new schema-version-2 metadata is additive to repository code but not backward-compatible with the old runtime. Before reverting after creating version-2 records, retain the branch or exported code required to restore those records. Failed batch operations expose residual operation IDs for `kis_restore_quarantine` or manual supervised recovery.

## Open decisions

No blocking product decision remains. The audit explicitly permits an integrity digest minimum, and the selected HMAC design is a bounded stronger implementation without adding a new policy rule.

## Specification review approval

Approved for implementation by the operator's instruction to plan and close the attached audit findings in an isolated worktree and raise an unmerged PR. Repository authority and the attached findings determine the bounded scope above.
