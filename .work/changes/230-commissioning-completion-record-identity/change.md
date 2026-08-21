# Change: Commissioning Completion Record Identity

- **Change ID**: `230-commissioning-completion-record-identity`
- **Risk Profile**: lean

## Outcome

Fix commissioning runner terminal Work completion to emit a task-compatible record identity and prove the live Change 229 commissioning can resume to completion.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Emit a `TASK-<issue>` record identity when commissioning completes a task Work item.
- Exercise the real `WorkRecord` prefix/type contract in runner regression coverage.
- Preserve persisted passed-probe evidence so live #462 resumes from `source_projected` without duplicating the probe.

## Implementation and verification

- Implementation notes: terminal completion now uses a task-compatible Work record identity; the fake completion boundary validates the production `WorkRecord` contract.
- Focused checks: full `tests/post_merge_commissioning` passed 91/91; runner service passed 11/11 after the final explicit TASK identity assertion; Ruff, governance scope check, and `git diff --check` passed.
- Review findings: code-quality clean; API-contract review prompted an explicit `TASK-<issue>` assertion, now resolved.
- Residual risk: live proof remains required after landing because the defect occurs at the external Work completion boundary.
- Closeout state: implementation, focused verification, and review complete; publication/landing/live proof pending.
