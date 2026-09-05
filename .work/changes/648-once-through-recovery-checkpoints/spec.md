# Change Specification: Once Through Recovery Checkpoints

- **Change ID**: `648-once-through-recovery-checkpoints`
- **Status**: Implemented
- **Complexity**: medium
- **Risk trigger**: public_contract

## Outcome

Add generic reversible once-through checkpoints with retained evidence revalidation, safe abort/exit, and explicit irreversible-boundary handling without changing the normal forward path.

## Authority and scope

- `AGENTS.md` and issue #707 define the governing workflow and acceptance contract.
- Owned implementation is limited to recovery state, evidence applicability, lifecycle-tool exposure, persistence, and focused tests.
- Existing once-through forward-path logic and exact-head GitHub PR/CI/merge semantics remain unchanged.
- Change 646 retains ownership of `lifecycle.py` and `tools.py`; this slice integrates through `lifecycle_tools.py` instead of overlapping that stale claim.

## Requirements

- Rewind to prior reversible checkpoints without deleting evidence.
- Retained downstream evidence becomes pending revalidation for the new lineage.
- Reuse unchanged evidence, supersede changed evidence, and retain invalid evidence historically.
- Refuse rewind/abort across irreversible post-merge boundaries.
- Persist recovery state and serialize interrupted recovery for resume.
- Make recovery options visible from lifecycle decisions and expose one governed recovery tool.
- Serialize read-transform-write recovery updates under the per-Work evidence lock.

## Acceptance

1. Rewind one or multiple checkpoints retains evidence and creates a new lineage.
2. Revalidation reuses unchanged evidence without recomputation and marks changed evidence invalid or superseded.
3. Abort/resume is persisted and irreversible boundaries refuse false rollback.
4. Lifecycle tooling exposes supported recovery actions and rewind targets.
5. Existing once-through regressions remain green.

## Out of scope

- Rewriting the existing once-through happy path.
- Weakening GitHub exact-head CI, PR, merge-readiness, or post-merge boundaries.
- Scenario-specific repair commands as the primary recovery mechanism.
