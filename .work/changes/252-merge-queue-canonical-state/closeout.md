# Closeout: Merge Queue Canonical State

## Implementation evidence
- Production queue state resolves through canonical `project-specific` ownership via `StateNamespaceResolver`.
- Branch identity is represented as a deterministic collision-resistant `state_key`; `project_id` remains the canonical required identity.
- Canonical state is read first. Valid legacy state is fallback-only until the next mutation publishes canonical state.
- Legacy state is preserved and cannot override an existing canonical file.
- Existing atomic publication and Change 251 per-queue locking remain unchanged.

## Verification evidence
- Merge-queue focused suite: 30 passed.
- Merge-queue + state-contract focused set: 61 passed.
- Ruff import-order check: passed.
- `git diff --check`: passed.

## Remaining gates
- Specialist review and scope validation.
- Exact commit, PR, exact-head GitHub Actions, governed merge.
- Post-merge commissioning and Work #552/#549 reconciliation.