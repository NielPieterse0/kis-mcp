# Closeout: Verification Selection Policy

## Implemented scope

- Added typed `verification-selection-v1` evidence for selected checks, skipped handoffs, source fingerprint, omissions, and truncation.
- Added deterministic reconciliation of Discover impact handoffs against the current project verification declarations.
- Added stable selection priority, 1–50 caller bounds, and explicit missing/stale/unsupported classifications.
- Added read-only `select_change_verification`; it accepts no command text and every selected item remains `execution_available=false`.
- Reused the exact Work executable-profile set from `run_verification` to prevent selector/executor drift.
- Preserved existing single-ID `run_verification` behavior and the three HR rules.

## Validation evidence

- TDD red: new selection tests initially failed collection because `verification.selection` did not exist.
- Focused selection/tool/platform tests: 9 passed after initial implementation.
- Broader verification workflow + gateway registration/provider-readiness regression set: 42 passed after adding the public tool to expected local registration.
- Post-review-fix broader regression set: 42 passed.
- `scripts/change-workflow.ps1 check`: passed; changes remain inside registered 099 ownership.
- `git diff --check`: passed.
- Initial canonical `scripts/verify.ps1`: passed; full pytest exit 0 with two expected skips, 254 Python files syntax checked, configuration/dependencies/change-governance and HR-001/2/3 checks green.

## Review

- Manual requirements/diff review found one drift risk: the selector initially duplicated Work's supported-profile set. Fixed by exporting and reusing `SUPPORTED_VERIFICATION_PROFILES` from the execution module; focused regressions were rerun green.
- NVIDIA NIM `super` review was attempted on the final state and failed before findings with `AGENT_BACKEND_FAILED:NvidiaNimError`; no NVIDIA pass is claimed.
- Codex CLI review was attempted on the final state and failed before findings with `AGENT_BACKEND_FAILED:CodexCliError`; no Codex pass is claimed.
- No remaining blocking correctness, scope, policy, or execution-authority issue was identified by bounded manual review.

## Git and merge

- Branch: `change/099-verification-selection-policy`.
- Worktree: `.work/worktrees/099-verification-selection-policy`.
- Implementation commit: pending.
- Pull request/merge: pending.
- Final closeout reconciliation and governed cleanup: pending implementation merge.

## Residual items

- Slice 4 selects but does not execute verification. Slice 5 owns bounded execution orchestration.
- Parallel 098 owns specialist review purposes and shared `SPEC.md`/`docs/OPERATIONS.md`; 099 did not modify those paths.
