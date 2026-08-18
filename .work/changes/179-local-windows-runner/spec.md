# Change Specification: Local Windows Runner

- **Change ID**: `179-local-windows-runner`
- **Status**: Active
- **Complexity**: large
- **Risk triggers**: architecture_boundary, persistent_state, public_contract, security

## Outcome

Make governed local Windows execution the primary Actions-independent runner with process-tree containment, per-run isolation, exact-SHA canonical verification, durable receipts, and deterministic recovery.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, GitHub issue #338, and issue #331 for exact-head receipt requirements.
- Normal capacity target: two concurrent agents in independent governed worktrees; operator owns CPU/RAM admission.
- Existing coordinator lease/fencing/path-reservation and serialized integration authority remain unchanged.
- GitHub remains the issue/PR/review/merge control plane; GitHub Actions remains optional and non-authoritative for landing.
- VirtualBox/Hyper-V remain optional higher-isolation proof providers, not normal execution requirements.

## Requirements

- **REQ-001**: Local execution MUST retain the existing Work middleware boundary and MUST NOT add an adaptive CPU/RAM governor.
- **REQ-002**: Each exact execution MUST use a unique KIS-owned run namespace beneath `C:\Projects\.kis-mcp\execution\local`.
- **REQ-003**: Exact verification MUST materialize and re-check the requested Git commit in an isolated detached worktree before executing repository verification.
- **REQ-004**: Windows verification child processes MUST be assigned to a KIS-owned Job Object with kill-on-close semantics; timeout/cancel/parent-loss MUST terminate the full assigned process tree.
- **REQ-005**: Exact verification MUST emit an immutable receipt containing requested/resolved SHA, Git tree, source fingerprint, lock/verifier digests, runner/profile identity, timestamps, result, log digests, and receipt digest/reference.
- **REQ-006**: Stale non-terminal run state MUST be reconciled by requesting cancellation and MUST never be reported as authoritative evidence.
- **REQ-007**: `execute_change_workflow` commit verification MUST pass the selected commit into `run_verification`; a commit-source verification result lacking exact-source receipt identity MUST fail closed.
- **REQ-008**: Ordinary focused working-tree verification remains supported; canonical merge evidence requires exact-source execution.
- **REQ-009**: Concurrent exact executions MUST not share mutable run/workspace state.

## Acceptance

1. **Given** two exact local runs, **when** they execute concurrently, **then** each receives a distinct run namespace/workspace and produces independent evidence.
2. **Given** a verifier that spawns a descendant, **when** timeout/cancel/parent-loss occurs, **then** the Job Object terminates the complete process tree and records non-success state.
3. **Given** a requested commit, **when** canonical verification runs, **then** the detached workspace HEAD/tree are rechecked and the receipt binds the execution to that identity.
4. **Given** commit-source change execution, **when** verification returns mutable/stale evidence, **then** the workflow reports incomplete/error rather than passing.
5. **Given** GitHub Actions is unavailable, **when** the local exact-head path passes, **then** PR preparation and local merge-readiness evidence have no Actions dependency.
6. **Given** stale runtime state from a previous owner PID, **when** a new local runner reconciles state, **then** cancellation is requested and stale state is not promoted to a receipt.

## Risks and recovery

- Windows Job Object API misuse could leak children; fail closed if job creation/configuration/assignment fails.
- Interrupted exact worktrees may remain under KIS state; preserve them as recoverable evidence rather than permanently deleting them automatically.
- Exact materialization may fail because a ref is invalid or unavailable; return source-identity failure without falling back to a mutable tree.

## Out of scope

- Adaptive CPU/RAM admission, workload classes, throttling, or automatic host scheduling.
- Changes to coordinator lease/fencing/path-reservation/integration semantics.
- Making VirtualBox or Hyper-V a prerequisite for normal development.
- Removing GitHub Actions diagnostics/support or weakening HR-001/HR-002/HR-003.
