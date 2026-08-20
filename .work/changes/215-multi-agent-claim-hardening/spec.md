# Change Specification: Multi-Agent Claim Hardening

- **Change ID**: `215-multi-agent-claim-hardening`
- **Status**: Approved for implementation by the active #412 execution route.
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `persistent_state`, `public_contract`

## Outcome

Prevent concurrent governed-change creators from entering repository mutation with duplicate numeric identities or intersecting path ownership, while preserving the historical duplicate `211-*` evidence. Bind admitted implementation to a coordinator-issued task/run envelope so workers cannot invent or widen project, worktree, objective, path, change, predecessor, or mutation authority.

## Authority and scope

- Authorities: `AGENTS.md`, issue #412, current `scripts/change-governance.py`, and `scope.json`.
- Owned implementation: `scripts/change-governance.py`, `scripts/change-workflow.ps1`, and the bounded coordinator task/run surfaces in `models.py`, `planner.py`, and `worker.py`.
- Contracts: coordinator work-packet, worker-execution, and worker-handoff schemas.
- Tests: governance admission plus coordinator planner/worker regressions.
- Documentation: `AGENTS.md`, `docs/OPERATIONS.md`, `docs/operations/verification-changes.md`.
- Excluded: Work Management lifecycle redesign, #253 live commissioning, renaming historical changes, unrelated stale-worktree cleanup, and coordinator features not required for #412 admission/task-run binding.

## Requirements

- **REQ-001 — Atomic admission:** serialize governed change creation per repository with an OS-backed lock under the configured KIS state root; re-read repository/worktree/claim truth while holding the lock immediately before mutation.
- **REQ-002 — Numeric identity uniqueness:** reject a new change when its three-digit prefix exists in any historical/current scope, local branch, remote-tracking branch, or governed worktree identity, even when the suffix differs.
- **REQ-003 — Collision-proof paths:** evaluate canonical bidirectional exact/recursive path intersections against every live claim after stale-claim projection, and fail before branch/worktree creation.
- **REQ-004 — Stale truth:** treat schema-v3/v4 active claims without their declared live `change/<id>` branch as closed for collision purposes; preserve historical records rather than rewriting them.
- **REQ-005 — Inspectable diagnostics:** collision errors identify both change owners/scopes and the intersecting path claims; numeric-prefix errors identify the conflicting repository identity.
- **REQ-006 — Agent binding:** when Work Management evidence is supplied, the governed scope may record the execution owner so issue, owner, branch/worktree, and path claims are inspectable together; existing schema-v4 records remain compatible.
- **REQ-007 — Safe failure:** a failed registration leaves no partially created governed worktree/branch and releases the admission lock.
- **REQ-008 — Task/run initialization:** before worker implementation, issue a bounded envelope with stable `task_id`, a generation-specific `run_id`, assigned executor/profile, registered project/change identity, exact governed worktree/root and base revision, objective/lifecycle phase, authority references, allowed path scope, and optional Work Management/predecessor/provenance evidence.
- **REQ-009 — Authority boundary:** task/run scope and external session provenance never grant Work authorization; agent-selected tools/skills remain subordinate to the issued envelope and mutating calls must match the exact current run, assignment generation, lease/fence, project/change, and path scope.
- **REQ-010 — Reassignment fencing:** reassignment preserves stable task/work-packet lineage, creates a new `run_id` and assignment generation, records predecessor lineage, and deterministically invalidates the prior assignment/run for mutation.

## Acceptance

1. Two concurrent creators cannot both register different `NNN-*` changes with the same numeric prefix.
2. A prefix already present only in historical scope data, a branch/ref, or a governed worktree still blocks reuse.
3. Exact-file vs recursive-directory and recursive-directory vs recursive-directory overlaps fail bidirectionally before mutation.
4. Stale schema-v3/v4 active records with no declared live branch do not create false ownership conflicts.
5. Three independently attempted registrations cannot enter mutation when any resolved scope intersects.
6. Collision diagnostics expose both IDs and both intersecting claims without leaking unrelated state.
7. Existing creation, validation, cleanup, schema-v3/v4 compatibility, and non-overlapping parallel behavior remain green.
8. Every issued implementation packet contains a stable task identity plus a generation-specific run identity and exact governed project/change/worktree/base/scope/authority envelope.
9. Reassignment keeps the same packet/task lineage, increments assignment generation, creates a distinct run identity, records predecessor lineage, and makes the old run fail closed for mutation.
10. External conversation/session provenance is retained only as bounded provenance and cannot widen mutation authority.

## Risks and recovery

- Risk: a global lock can deadlock or become machine-specific. Control: use the same cross-platform OS file-lock pattern already used by the coordinator; the file is durable but lock ownership is process-scoped.
- Risk: historical-prefix checks can incorrectly reserve unrelated three-digit text. Control: inspect only governed scope directory names and governed change branch/worktree identities matching the canonical change-ID grammar.
- Recovery: revert the bounded script/docs change. The lock file is generated state and contains no source authority or user data.

## Out of scope

- Renaming either historical `211-*` change.
- Repairing unrelated Work Management lifecycle inconsistencies such as #408.
- #253 live coordinator commissioning and unrelated coordinator features outside admission/task-run identity/fencing.
