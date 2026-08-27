# Change Specification: Merge Queue Canonical State

- **Change ID**: `252-merge-queue-canonical-state`
- **Status**: Implemented
- **Risk Profile**: standard

## Outcome
Migrate merge-queue durable state into the canonical project-specific KIS state namespace while preserving validated legacy state for compatibility recovery.

## Authority and scope
- Canonical authority: `contracts/state/state-ownership.contract.json` via `StateNamespaceResolver`.
- Owned implementation: `src/kis_mcp/projects/github_merge_queue.py`.
- Regression tests: `tests/projects/test_github_merge_queue.py` plus existing state-contract tests.
- Legacy queue files remain compatibility evidence only; GitHub/repository truth remains authoritative.

## Requirements
- **REQ-001**: Production queue state resolves through `project-specific` ownership with `project_id` identity.
- **REQ-002**: Target branch is represented only as the consumer `state_key`, using deterministic collision-resistant derivation.
- **REQ-003**: If canonical state is absent, validated legacy state may be read; the next mutation publishes canonical state without deleting legacy evidence.
- **REQ-004**: Once canonical state exists it always wins over stale legacy state.
- **REQ-005**: Existing atomic publication and per-queue mutation locking remain intact.

## Acceptance
1. Production construction uses the canonical state namespace resolver.
2. Legacy state is identity-validated before reuse and never overrides existing canonical state.
3. Focused queue/state suites and `git diff --check` pass.

## Risks and recovery
- Risk: stale legacy fallback after migration. Recovery: canonical-first reads and non-destructive legacy preservation.
- Rollback: revert Change 252; preserved legacy files remain available.