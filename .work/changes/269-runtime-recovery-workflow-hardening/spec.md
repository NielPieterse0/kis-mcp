# Change Specification: Runtime Recovery Workflow Hardening

- **Change ID**: `269-runtime-recovery-workflow-hardening`
- **Status**: Active
- **Complexity**: large
- **Risk triggers**: architecture_boundary, deployment, public_contract

## Outcome

Harden `kis-dev` runtime recovery, process execution, Serena/Skills reliability, and once-through workflow behavior using defects reproduced during this implementation run.

## Requirements

- **REQ-001**: selected-instance process execution must preserve exact argument/source binding and reject ambiguous invocation state.
- **REQ-002**: post-land `kis-dev` refresh must be idempotent for a live same-SHA worker and retry bounded transient launcher failure without touching `kis-op`.
- **REQ-003**: `kis-dev` must have an independent local-shell recovery surface that remains hard-bound to the development instance.
- **REQ-004**: Serena must remove user-profile launcher provenance and use exactly one managed Pyright 1.1.403 launcher beneath `C:\Projects`.
- **REQ-005**: Serena configuration rendering must preserve managed Pyright and canonical project-state settings together.
- **REQ-006**: Skills tool descriptions must make the canonical `skill_id` invocation contract explicit for load/read calls.
- **REQ-007**: once-through promotion must suppress immediate no-progress replay after a failed stage while retaining telemetry/evidence.
