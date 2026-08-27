# Change Specification: Merge Queue Concurrency Safe

- **Change ID**: `251-merge-queue-concurrency-safe`
- **Status**: Active
- **Complexity**: Medium
- **Risk trigger**: `persistent_state`

## Outcome

Make merge-queue state mutation concurrency-safe for Work #549 without reducing liveness for disjoint queue identities.

## Authority and scope

- `AGENTS.md` and active Change 251 scope govern the implementation.
- Owned code: `src/kis_mcp/projects/github_merge_queue.py`.
- Owned tests: `tests/projects/test_github_merge_queue.py`.
- No shared paths or dependencies.

## Requirements

- **REQ-001**: Same `(project_id, target_branch)` mutations must serialize the full read-modify-write transaction across processes.
- **REQ-002**: Disjoint queue identities must remain independently concurrent.
- **REQ-003**: Atomic state publication and existing queue generation/FIFO semantics must remain unchanged.

## Acceptance

1. Concurrent accepted enqueues for one queue preserve both entries without temp-file collisions or lost updates.
2. Locks for disjoint queue identities can be held concurrently.
3. Existing merge-queue behavior remains green under the focused suite.

## Out of scope

- Global queue serialization, provider-authority changes, or merge-queue policy changes.
