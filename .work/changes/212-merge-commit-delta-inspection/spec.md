# Change Specification: Merge Commit Delta Inspection

- **Change ID**: `212-merge-commit-delta-inspection`
- **Status**: Implemented and verified; dependency `211-purpose-specific-reviewer` / #403 is landed and the bounded #407 lane is unblocked.
- **Complexity**: `medium`
- **Risk triggers**: `public_contract`

## Outcome

Retain the actual merged payload for normal two-parent merge commits across the existing Discover change-evidence pipeline, while preserving non-merge behavior and failing closed for unsupported multi-parent commits.

## Authority and scope

- Authority: `AGENTS.md`, `SPEC.md` current Discover/reviewer contracts, issue #407, and `scope.json`.
- Owned implementation: `src/kis_mcp/discover/change_targets.py`, `src/kis_mcp/discover/git_change_reader.py`.
- Owned tests: `tests/discover/test_change_targets.py` plus only consumer-regression paths added to `scope.json` before editing.
- Excluded: reviewer architecture #403/#395, Serena #408, unrelated cleanup.
- Dependency: none; existing inspect/analyze/review consumers must consume the corrected shared inventory unchanged.

## Requirements

- **REQ-001**: A non-merge commit uses its existing parent-to-commit/root delta semantics.
- **REQ-002**: A two-parent merge commit is inspected as `first-parent -> merge`, representing the payload introduced to the branch receiving the merge.
- **REQ-003**: A commit with more than two parents returns unavailable/fail-closed evidence rather than an empty successful delta.
- **REQ-004**: Inspect, analyze, verification selection, and review evidence derive from the same corrected change inventory.

## Acceptance

1. A representative two-parent merge with a real feature payload returns that payload from `source=commit` and no false empty result.
2. The Change 210-style merge shape is covered by regression evidence.
3. A synthetic three-parent octopus merge is rejected with a typed fatal diagnostic.
4. Existing ordinary commit/range/branch tests remain green.
5. Consumer-level tests prove the corrected inventory reaches analysis/verification/review evidence without a second merge rule.

## Risks and recovery

- Risk: choosing the wrong parent could report integration noise or omit the merged feature payload.
- Control: the rule is explicitly first-parent-to-merge for exactly two parents, with tests for content unique to the merged side.
- Recovery: revert the bounded Discover change; no persistent data migration is involved.

## Out of scope

- Redesigning reviewer routing, prompts, fallback, telemetry, or #395/#403 interfaces.
- Serena capability changes (#408).
- New merge-base semantics for range/branch inspection.
