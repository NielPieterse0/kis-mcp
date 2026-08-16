# Change Specification: Documentation Context Routing

- **Change ID**: `165-documentation-context-routing`
- **Status**: Approved for documentation-only execution
- **Documentation level**: Complex — this changes repository authority routing and target/current document boundaries.
- **Repository complexity**: Large — ownership/context routing is a repository-wide developer workflow boundary.

## Outcome

Reduce mandatory documentation context for ordinary governed slices while preserving the existing precedence of applicable authorities, canonical ownership, HR-001/HR-002/HR-003, change governance, review, verification, and historical evidence.

## Authority and scope

- Authoritative sources: operator instruction of 2026-08-16; GitHub issue #283; `AGENTS.md`; `docs/TRUST-MODEL.md`; `SPEC.md`; `docs/PLATFORM-CONCEPT.md`; `policy/kis-mcp.policy.json`; `docs/OPERATIONS.md`; `settings/change-governance.settings.json`.
- Owned paths: `AGENTS.md`, `docs/PLATFORM-CONCEPT.md`, and this change record.
- Excluded: `SPEC.md` (actively claimed by change 159), source code, tests, settings, policy, operations procedures, module specs, and historical development records.
- Dependency: none. This change must remain independently mergeable from active code lanes.
- Human approval: the operator explicitly requested urgent documentation-only simplification and supplied the target lifecycle/ownership model.

## Requirements

- **REQ-001**: Preserve the precedence order of applicable canonical authorities while replacing unconditional six-document traversal with task/path applicability routing.
- **REQ-002**: Keep `AGENTS.md` as a concise repository constitution containing authority, routing, skill access, governed-change mechanics, repository standards, verification ownership, and stop conditions.
- **REQ-003**: Route trust semantics to `docs/TRUST-MODEL.md`, current product truth to `SPEC.md`, target architecture to `docs/PLATFORM-CONCEPT.md`, machine rules to policy/settings/contracts, operations to `docs/OPERATIONS.md`, and change-local truth to `.work/changes/<id>/`.
- **REQ-004**: Remove current-implementation reconciliation/detail from `docs/PLATFORM-CONCEPT.md`; it must remain target-state architecture and link to `SPEC.md` for current implementation status.
- **REQ-005**: Do not weaken or reinterpret HR-001, HR-002, HR-003, provider boundaries, change claims, worktree isolation, exact-head verification, or closeout requirements.
- **REQ-006**: Do not create a new documentation authority, generated summary, machine-readable routing schema, or module contract in this slice.
- **REQ-007**: Preserve links to detailed operational/change-governance procedure instead of duplicating volatile implementation detail in the default agent entry document.

## Acceptance

1. **Given** an ordinary bounded implementation slice, **when** an agent reads repository instructions, **then** `AGENTS.md` requires only itself, the active change record, and context owners applicable to the affected paths/task rather than all six global documents.
2. **Given** a trust/policy, architecture/target, or operations-affecting slice, **when** applicability is evaluated, **then** the relevant canonical documents remain explicitly required and retain their existing precedence.
3. **Given** `docs/PLATFORM-CONCEPT.md`, **when** current implementation status is needed, **then** the document directs the reader to `SPEC.md` instead of maintaining a parallel current-state inventory.
4. `AGENTS.md` and `docs/PLATFORM-CONCEPT.md` contain no contradictory current/target ownership claims.
5. `pwsh -File scripts/change-workflow.ps1 check` passes and documentation review reports no blocking findings.
6. Repository-appropriate documentation/governance verification passes on the exact final change.

## Risks and recovery

- Risk: over-compression could hide a binding rule. Mitigation: retain unique operating rules in `AGENTS.md` and route detailed semantics to the existing canonical owner.
- Risk: target/current separation could remove target constraints accidentally. Mitigation: only delete current-state status/reconciliation prose from `PLATFORM-CONCEPT.md`; retain target architecture, non-goals, sequence, and success criteria.
- Recovery: revert this change commit. No runtime state, schema, migration, or product behavior is modified.

## Out of scope

- Rewriting or slimming `SPEC.md` while change 159 owns it.
- Rewriting `docs/OPERATIONS.md`; removing it from default implementation context provides the immediate context reduction without changing operator procedure.
- Creating automated path-to-context routing. That is a separate code/config slice if later justified.
- Deleting historical documentation or weakening slice/change evidence.
