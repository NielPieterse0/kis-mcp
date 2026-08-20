# Change Specification: Non-SPEC Merge Readiness

- **Change ID**: `210-non-spec-merge-readiness`
- **Status**: Approved for implementation
- **Complexity**: medium
- **Risk trigger**: `public_contract`

## Outcome

Allow exact-head Work Management merge readiness and documentation lifecycle to use authoritative Defect, Task, and Specification Slice implementation identities without fabricated SPEC records.

## Authority and scope

- Authoritative sources: `AGENTS.md`, Work Management contracts, traceability implementation/tests, project-management parser/tool tests.
- Owned paths: `src/kis_mcp/work_management/**`, `src/kis_mcp/workflows/project_management/**`, corresponding tests, and this change record.
- Dependencies: none.

## Requirements

- **REQ-001**: An implementation trace has a generic implementation/source record identity that accepts valid `BUG-*`, `TASK-*`, and `SPEC-*` Work record IDs.
- **REQ-002**: Specification identity is optional and, when present, remains restricted to `SPEC-*`.
- **REQ-003**: Existing schema-v1 payloads containing only `specification_record_id` remain accepted and behave as before.
- **REQ-004**: Merge readiness matches the authoritative Work record against the generic implementation identity while preserving exact-head GitHub Actions and documentation gates.
- **REQ-005**: Documentation reconciliation events carry the same generic implementation identity and optional specification identity end-to-end.

## Acceptance

1. A `BUG-*` or `TASK-*` record can reach merge-ready with its own identity and no fabricated specification record.
2. A legacy `SPEC-*` trace/event payload still parses, serializes, evaluates, and reconciles unchanged in meaning.
3. A supplied `specification_record_id` with a non-`SPEC-*` prefix is still rejected.
4. Documentation event identity mismatch remains fail-closed.
5. Exact-head provider-native GitHub Actions verification remains mandatory.

## Risks and recovery

- Risk: schema-v1 consumers may rely on the existing field. Mitigation: additive generic identity plus legacy fallback; no schema-version bump.
- Recovery: revert the bounded contract/parser changes; no persisted migration is required.

## Out of scope

- Work record lifecycle redesign, new record types, or weakened verification/documentation policy.
- Historical Agent ownership-field reconciliation.
- Changes 172/195 or unrelated stale worktree cleanup.
