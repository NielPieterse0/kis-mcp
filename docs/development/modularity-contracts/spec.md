# Modularity Contract Baseline Specification

## Status

Implemented on `change/002-modularity-contracts`; review and PR closure evidence are recorded below.

## Development level

Complex: this slice changes architectural contracts, public MCP response schemas, provider compatibility evidence, and repository enforcement tests.

## Outcome

Close the assessment's accepted near-term findings without restructuring the existing package or adding unapproved runtime policy.

## Requirements

### R1 — Structural component contracts

Add a focused `src/kis_mcp/contracts.py` containing provider-neutral structural protocols and immutable provider capability metadata. `ThreeRuleMiddleware` must depend on these contracts rather than concrete resolver or policy classes.

### R2 — Substitutability evidence

Add tests proving middleware accepts structurally compatible resolver and policy test doubles, and that the Desktop Commander resolver and three-rule policy return only provider-neutral domain records.

### R3 — Stable public MCP records

Define explicit typed records for health, quarantine, quarantine-list, and restore responses. Public tools must map internal service records to these records rather than exposing `asdict()` output from internal dataclasses.

Public contract versioning is minimal and explicit through a `schema_version` field with initial value `1`.

### R4 — Dependency direction

Add bounded AST tests enforcing these rules:

- `models.py`, `contracts.py`, `paths.py`, and `policy.py` do not import FastMCP;
- `models.py`, `contracts.py`, `paths.py`, and `policy.py` do not import the Desktop Commander adapter;
- `policy.py` contains no Desktop Commander tool names;
- `middleware.py` does not import concrete resolver or policy implementations;
- Desktop Commander tool-name constants remain limited to the adapter and provider contract fixtures/tests.

### R5 — Provider contract drift evidence

Add executable Desktop Commander `0.2.46` contract artifacts under `contracts/desktop-commander/`:

- a normalized provider surface JSON document covering every adapter-classified tool and exposed/unexposed capability relevant to enforcement;
- a SHA-256 fingerprint file;
- verification code and tests that detect fingerprint drift and identify the affected provider contract version.

This is repository/release verification evidence only. It must not add a fourth runtime rule or runtime allowlist.

### R6 — Verification integration

The canonical verifier must include the new contract artifacts and tests. Existing HR-001, HR-002, and HR-003 behavior must remain unchanged.

## Acceptance evidence

- A failing test is observed before each behavior implementation.
- Middleware tests pass with protocol-compatible fakes that do not inherit production classes.
- Public tool schemas expose explicit versioned response records.
- A deliberate provider contract fixture mutation fails fingerprint verification.
- Import-boundary tests fail on forbidden imports or provider names.
- `pwsh -NoProfile -File .\scripts\verify.ps1` passes on the final branch.

## Exclusions

- No `domain/application/ports/adapters` package tree.
- No generic multi-provider gateway.
- No separate application service.
- No Discover or Govern runtime packages.
- No new Work restriction, allowlist, denylist, approval tier, or policy rule.
- No provider upgrade or continuous runtime schema polling; live capture is limited to the installed pinned `0.2.46` provider during supervised contract maintenance.

## Requirement traceability

| Requirement | Implementation | Evidence |
|---|---|---|
| R1 | `contracts.py`, provider capabilities, middleware protocol dependencies | `tests/test_contracts.py`, `tests/test_architecture_boundaries.py` |
| R2 | Structural resolver, policy, and quarantine ports with non-inheriting fakes | `tests/test_contracts.py` |
| R3 | Explicit `HealthResponse`, `QuarantineResponse`, and `QuarantineListResponse` records | `tests/test_public_contracts.py` |
| R4 | Bounded AST import and provider-name checks | `tests/test_architecture_boundaries.py` |
| R5 | Live-captured 26-tool provider contract, adapter snapshot, classifications, and SHA-256 fingerprint | `tests/test_provider_contract.py`, `scripts/capture-provider-contract.ps1` |
| R6 | New tests run through the existing locked canonical verifier | `scripts/verify.ps1` |

## Review findings resolved

- Middleware no longer imports concrete resolver or policy implementations.
- Public MCP responses no longer mirror internal dataclasses through `asdict()`.
- Provider additions and removals fail contract capture until every changed tool receives explicit effect review.
- The provider contract remains release evidence and is not consulted as a runtime permission allowlist.
- Settings and operations documentation now reflect live provider-schema verification and the supervised recapture procedure.

## Compatibility and residual risk

- All `kis_*` response records now include `schema_version=1`.
- `kis_list_quarantine` changes from a bare list to the versioned `{records, schema_version}` envelope. This is an intentional public contract stabilization change and requires client review before merge.
- The installed provider was verified directly over local stdio. Full end-to-end live proxy behavior remains recorded as `not_verified` and is outside this slice.
- Full package decomposition remains deferred until the codebase grows enough to justify it.

## Recovery

All changes are isolated on `change/002-modularity-contracts`. Recovery is branch abandonment or PR closure; no persistent data migration is introduced. The worktree remains available for PR review fixes.
