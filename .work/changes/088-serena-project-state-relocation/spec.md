# Change Specification: Serena Project State Relocation

- **Change ID**: `088-serena-project-state-relocation`
- **Status**: Approved
- **Risk Profile**: standard

## Outcome

Relocate all Serena per-project generated state out of repository worktrees into JSON-governed KIS state beneath `C:\Projects\.kis-mcp`, while preserving offline semantic reads and HR3-07 recoverable memory handling.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, `docs/TRUST-MODEL.md`, `docs/OPERATIONS.md`, canonical provider JSON, and pinned Serena 1.6.1 behavior.
- Owned paths: Serena provider settings/runtime/memory adapter, provider live smoke, focused Serena tests, authoritative spec/operations docs, and this change record.
- Shared paths: none.
- Excluded paths: `policy/**`.
- Dependencies: integrated 084 persistent-memory closeout and final 087 publication path.
- Integration owner: this 088 closeout.

## Requirements

- **REQ-001 — Central state:** canonical JSON SHALL define Serena per-project state beneath `C:\Projects\.kis-mcp\serena\projects`; repo-local `.serena` is not an allowed runtime state location.
- **REQ-002 — Provider reconciliation:** before Serena activation, KIS SHALL reconcile Serena's global `project_serena_folder_location` to the canonical central template and pre-create the configured path so Serena cannot fall back to a repository-local directory.
- **REQ-003 — Collision safety:** because Serena 1.6.1 central routing exposes `$projectFolderName`, KIS SHALL bind each central folder name to one normalized project root and fail closed on a different same-name root.
- **REQ-004 — Memory safety:** HR3-07 artifact resolution SHALL use the same centralized project-state path and preserve quarantine/restore semantics without forwarding permanent deletion.
- **REQ-005 — Offline containment:** Serena SHALL continue to run from the pinned relocatable interpreter with `UV_OFFLINE=1`; this change SHALL not add network access or provider mutation tools.
- **REQ-006 — Verification:** focused tests, live provider commissioning, governed scope validation, and canonical repository verification SHALL pass before integration.

## Acceptance

1. **Given** the primary or a governed worktree, **when** Serena starts or activates it, **then** generated Serena state resolves under the canonical external state root and no project-local `.serena` is created.
2. **Given** two distinct registered roots with the same leaf folder name, **when** both attempt to claim Serena state, **then** the second fails with a deterministic collision error rather than sharing data.
3. **Given** a Serena memory artifact, **when** HR3-07 removal is requested, **then** KIS quarantines and can restore the exact centralized artifact without permanent deletion.
4. **Given** final integrated `main`, **when** the development runtime is restarted, **then** Serena semantic reads remain ready and repository status stays clean.

## Risks and recovery

- Risk: central routing could collide for same-name project roots because Serena 1.6.1 exposes only `$projectFolderName` for this use case.
- Mitigation: KIS writes a JSON `project-root.json` identity marker beside the Serena directory and rejects mismatches.
- Risk: stale repo-local `.serena` may predate this fix.
- Recovery: move stale state to KIS recoverable quarantine; never permanently delete it. Restore by quarantine ID if required.

## Out of scope

- Changing Serena version, enabling Serena write tools, changing the three-rule policy, or treating Serena memory as authoritative KIS project memory.
