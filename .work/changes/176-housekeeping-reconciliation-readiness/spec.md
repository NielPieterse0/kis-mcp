# Change Specification: Housekeeping Reconciliation Readiness

- **Change ID**: `176-housekeeping-reconciliation-readiness`
- **Status**: Active
- **Risk Profile**: standard

## Outcome

Add provider-neutral deterministic housekeeping contracts plus the two highest-priority runners: Work Management reconciliation and backlog readiness/dependency recomputation.

## Authority and scope

- Authoritative sources: `AGENTS.md`, configured Work Management command-plane authority, GitHub issue state, governed `.work/changes/*/scope.json` bindings, existing KIS reconciliation/transition operations.
- Owned paths: `src/kis_mcp/housekeeping/**`, `tests/housekeeping/**`, `scripts/housekeeping.py`, this change record.
- Excluded paths: all disposable-Windows execution/verification paths, `.github/workflows/**`, `SPEC.md`, platform concept docs, coordinator change 150.
- Dependencies: exact-target Work Management repair already landed on `main`.
- Integration owner: none; no #324 wiring in this change.

## Requirements

- **REQ-001**: Every runner accepts a typed manual/scheduled-neutral trigger, defaults to preview, and requires an idempotency key for apply.
- **REQ-002**: Reconciliation must fail closed on truncated inventory and report semantic/lifecycle ambiguity rather than infer intent.
- **REQ-003**: Missing Project records may be auto-captured only from a unique governed exact source binding whose GitHub issue is open.
- **REQ-004**: Lifecycle/claim/projection conflicts are findings unless an existing KIS authority gate proves a bounded correction safe.
- **REQ-005**: Backlog readiness must reuse `project_management_next_work` for executable-leaf selection and `project_management_transition_work` for Ready transitions.
- **REQ-006**: Exact dependency references may be checked mechanically; free-form dependency text is a typed ambiguity and has no mutation path.
- **REQ-007**: No LLM receives mutation authority; this slice contains no LLM decision path.
- **REQ-008**: Receipts expose bounded findings, planned/applied actions, conflicts, completeness, and counters suitable for later observability work.
- **REQ-009**: The same runner code must execute under a normal Python process and therefore remain consumable by future local-process or disposable-Windows hosts without execution-specific code.

## Acceptance

1. **Given** truncated Project inventory, **when** either runner executes, **then** it returns an incomplete conflict receipt and performs no mutation.
2. **Given** a unique open governed source issue absent from the Project, **when** reconciliation previews/applies, **then** it composes existing Project reconciliation with exact source identity and no invented metadata.
3. **Given** closed source work still active/claimed or inconsistent Change ID projection, **when** reconciliation runs, **then** it reports typed evidence and does not guess terminal state or release ownership.
4. **Given** Blocked work with no dependency evidence, **when** backlog readiness runs, **then** Ready is planned/applied only when the existing transition gate accepts it.
5. **Given** exact closed dependency references or semantic dependency text, **when** backlog readiness runs, **then** it reports stale/ambiguous dependency findings without clearing evidence-owned fields.
6. **Given** manual or scheduled trigger metadata, **when** the CLI invokes a runner, **then** both use the same provider-neutral state machine and receipt contract.

## Risks and recovery

- Risk: stale/incomplete provider evidence could cause an unsafe lifecycle mutation.
- Mitigation: preview-first, revision-aware existing KIS operations, bounded reads/mutations, and fail-closed ambiguity/truncation handling.
- Recovery: repeat with the same idempotency key; no direct destructive repository operation exists in this slice.

## Out of scope

- PR merge/closeout, worktree cleanup, documentation semantic repair, issue deduplication, scheduler implementation, execution-provider implementation, and any #324 integration.
