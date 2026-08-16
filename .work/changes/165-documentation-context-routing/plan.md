# Documentation Context Routing Implementation Plan

**Goal:** Reduce default repository documentation context while preserving applicable authority precedence and all existing quality/safety controls.

**Approved direction:** The operator approved documentation-only execution on 2026-08-16 and supplied the target model: rich slice records, sparse durable global docs, current/target/operations/history separation, and task/path-specific context routing.

**Baseline:** the current unconditional authority traversal is 191,748 bytes across `AGENTS.md`, `TRUST-MODEL.md`, `SPEC.md`, `PLATFORM-CONCEPT.md`, policy JSON, and `OPERATIONS.md`. `AGENTS.md` is 19,294 bytes and `PLATFORM-CONCEPT.md` is 27,329 bytes.

## Source-to-change traceability

| Requirement | Target | Source | Verification |
|---|---|---|---|
| REQ-001/002/003 | `AGENTS.md` | operator direction, #283, current authority owners | final diff + documentation review |
| REQ-004 | `docs/PLATFORM-CONCEPT.md` | operator direction, #283, `SPEC.md` ownership declaration | current-state phrase/section review |
| REQ-005 | both docs | `TRUST-MODEL.md`, policy JSON, change-governance settings | exact-rule and workflow checks |
| REQ-006/007 | both docs | documentation ownership rules | scope check + review |

## Constraints

- Stay inside `scope.json`; do not touch `SPEC.md` because change 159 owns it.
- Pure documentation work does not use TDD or modify executable behavior.
- Preserve current line-ending conventions and repository-relative links.
- Do not change HR rule semantics, policy JSON, Work Management implementation, source code, settings, or operator procedures.
- Keep `PLATFORM-CONCEPT.md` target-state only; current implementation belongs to `SPEC.md`.
## Tasks

### 1. Compress repository entry authority

- Rewrite `AGENTS.md` as the repository constitution.
- Preserve canonical identity, authority precedence, ownership/routing, Skills-module authority, governed-change/worktree/path-claim rules, repository standards, verification ownership, and stop rule.
- Replace unconditional global reading with an applicability table and minimum-context rule.
- Route detailed trust, architecture, provider/runtime, operations, and historical material to their existing owners.

### 2. Separate target architecture from current implementation

- Remove the current-capability inventory and implemented-provider/tool/status reconciliation from `docs/PLATFORM-CONCEPT.md`.
- Rewrite shared-kernel subsections as target responsibilities rather than current implementation claims where needed.
- Replace the status-heavy delivery table with target sequencing and an explicit pointer to `SPEC.md` for current status.
- Retain target capability planes, boundaries, non-goals, provider strategy, profiles, success criteria, and the three-rule constraint.

### 3. Review and verify

- Measure before/after sizes and default mandatory-context reduction.
- Search for stale unconditional traversal wording and current-state inventories remaining in the target document.
- Run `pwsh -File scripts/change-workflow.ps1 check`.
- Run the repository's applicable documentation/governance verification without duplicating canonical PR verification.
- Run a documentation specialist review and architecture review because this changes documentation authority routing.
- Reconcile all findings into the final diff and closeout evidence.

### 4. Delivery

- Commit only the owned documentation/change-record paths.
- Prepare an exact reviewable pull request through the registered KIS workflow.
- Stop before merge unless the normal exact-head merge/readiness gates are satisfied.
