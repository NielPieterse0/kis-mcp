# Change Specification: Runtime State Atomic Replace

- **Change ID**: `060-runtime-state-atomic-replace`
- **Status**: Approved
- **Development level**: Medium

## Outcome

Allow repeated selected-instance startup to atomically update an existing `current.json` lifecycle record without failing before preflight.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Owned implementation: `scripts/startup-instance-lifecycle.ps1`.
- Owned regression coverage: `tests/test_startup_scripts.py`.
- No policy, provider, tunnel, or work-management behavior changes.

## Requirements

- **REQ-001**: `Write-KisMcpAtomicJson` must create a missing JSON state file and replace an existing JSON state file on the same path without requiring a backup path.
- **REQ-002**: Replacement must remain a same-filesystem write/rename operation under `C:\Projects`; it must not introduce permanent-delete cleanup or external state.
- **REQ-003**: The selected-instance lifecycle contract from change 059 remains unchanged: repeated startup may progress from existing state to `restarting` and continue into preflight rather than failing in state persistence.

## Acceptance

1. **Given** a missing state path, **when** `Write-KisMcpAtomicJson` writes twice to that path, **then** both calls succeed and the second document is the persisted document.
2. **Given** an existing `development/current.json`, **when** the launcher begins selected-instance preflight, **then** writing `restarting` does not fail because the destination already exists.
3. Focused startup tests, change scope check, and canonical repository verification pass on the final state.
4. Live commissioning may restart `development` while leaving `operation` untouched.

## Root cause

`Write-KisMcpAtomicJson` used `[System.IO.File]::Replace($Temporary, $Path, $null)` when the destination existed. In the active PowerShell/.NET runtime, that call rejects the null backup-path argument with `The path is empty. (Parameter 'path')`.

## Risks and recovery

- Risk: changing the replacement primitive could weaken state replacement semantics or leave temporary files.
- Recovery: revert the focused implementation commit. Runtime state is generated operational evidence and can be rewritten by the next supervised startup.

## Out of scope

- Redesigning startup lifecycle state.
- Changing instance ownership/reclamation rules.
- Changing `start-chatgpt.ps1` orchestration.
- Changing HR-001, HR-002, or HR-003.
