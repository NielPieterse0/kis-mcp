# Modularity Contract Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest executable contract layer required by the modularity assessment while preserving the current package layout and three-rule behavior.

**Architecture:** Keep existing implementation modules in place. Add one provider-neutral Python contract module, explicit versioned public response records, AST dependency tests, and machine-checked provider surface fixtures. FastMCP remains confined to transport/composition modules.

**Tech Stack:** Python 3.11+, dataclasses, `typing.Protocol`, FastMCP 3.4.4, pytest 8.4.x, JSON, SHA-256.

## Global Constraints

- Enforce exactly HR-001, HR-002, and HR-003; add no fourth runtime restriction.
- Preserve existing module layout except for `src/kis_mcp/contracts.py`.
- Provider contract checks are verification evidence, not runtime allowlisting.
- Write only beneath `C:\Projects`; never permanently delete artifacts.
- Use the canonical locked verifier before completion.

---

### Task 1: Structural contracts and substitutability

**Requirements:** R1, R2

**Files:**
- Create: `src/kis_mcp/contracts.py`
- Modify: `src/kis_mcp/desktop_commander.py`
- Modify: `src/kis_mcp/middleware.py`
- Create: `tests/test_contracts.py`
- Modify: `tests/test_middleware.py`

**Interfaces:**
- Produces: `ProviderCapabilities`, `ProviderEffectResolver`, `PolicyEvaluator`, `QuarantinePort`.
- Consumes: `InvocationEffects`, `PolicyDecision`, and `QuarantineRecord`.

- [ ] Write failing tests using resolver and policy fakes that satisfy protocols without inheriting concrete classes.
- [ ] Run targeted tests and confirm failure because contracts/capabilities do not exist and middleware still imports concrete classes.
- [ ] Implement immutable capability metadata and protocols.
- [ ] Adapt `DesktopCommanderEffectResolver` to expose `capabilities` and adapt middleware annotations/access.
- [ ] Run targeted tests and existing middleware/adapter/policy tests.
- [ ] Commit the independently reviewable task.

### Task 2: Versioned public response records

**Requirements:** R3

**Files:**
- Modify: `src/kis_mcp/models.py`
- Modify: `src/kis_mcp/server.py`
- Create: `tests/test_public_contracts.py`

**Interfaces:**
- Produces: explicit health, quarantine, quarantine-list, and restore response dataclasses with `schema_version=1`.
- Consumes: internal `QuarantineRecord` and runtime configuration.

- [ ] Write failing serialization and FastMCP schema tests proving public tools return explicit records and no longer mirror internal dataclass layout.
- [ ] Run targeted tests and confirm the current dictionary/asdict surface fails.
- [ ] Implement minimal response records and mapping helpers.
- [ ] Replace public `asdict()` boundaries while preserving external field values.
- [ ] Run targeted tests and server-adjacent tests.
- [ ] Commit the independently reviewable task.

### Task 3: Dependency-boundary enforcement

**Requirements:** R4

**Files:**
- Create: `tests/test_architecture_boundaries.py`

**Interfaces:**
- Consumes: Python source AST under `src/kis_mcp`.
- Produces: deterministic failures naming forbidden dependency edges or leaked provider constants.

- [ ] Write AST tests for framework imports, adapter imports, policy provider names, and middleware concrete imports.
- [ ] Run tests and confirm they fail against the pre-refactor dependency edges where applicable.
- [ ] Complete only the minimal source adjustments required by the tests.
- [ ] Run architecture and full unit tests.
- [ ] Commit the independently reviewable task.

### Task 4: Provider surface contract and fingerprint

**Requirements:** R5

**Files:**
- Create: `contracts/desktop-commander/0.2.46.tools.json`
- Create: `contracts/desktop-commander/0.2.46.schema.sha256`
- Create: `src/kis_mcp/provider_contract.py`
- Create: `tests/test_provider_contract.py`
- Modify: `tests/test_repository_scope.py`

**Interfaces:**
- Produces: normalized fixture loader, canonical JSON fingerprint calculation, and precise compatibility failure.
- Consumes: pinned provider version, adapter classifications, and checked-in fixture.

- [ ] Write failing tests for fixture completeness, classification agreement, and fingerprint mutation detection.
- [ ] Run targeted tests and confirm failure because artifacts/verification code do not exist.
- [ ] Add the minimal normalized provider surface fixture and fingerprint.
- [ ] Implement deterministic loading/fingerprinting and adapter-classification comparison.
- [ ] Integrate repository-scope checks so required artifacts cannot disappear.
- [ ] Run targeted and full tests.
- [ ] Commit the independently reviewable task.

### Task 5: Whole-change review and verification

**Requirements:** R1–R6

**Files:**
- Modify: `docs/development/modularity-contracts/spec.md`
- Modify: `docs/development/modularity-contracts/plan.md`
- Modify only other files needed to resolve review findings.

- [ ] Reconcile every requirement to code and test evidence.
- [ ] Review the complete diff for correctness, scope, security, public compatibility, unnecessary complexity, and three-rule preservation.
- [ ] Run `git diff --check`.
- [ ] Run `pwsh -NoProfile -File .\scripts\verify.ps1`.
- [ ] Record final evidence and residual risks in the PR body.
- [ ] Push `change/002-modularity-contracts` and open an unmerged PR against `main`.
