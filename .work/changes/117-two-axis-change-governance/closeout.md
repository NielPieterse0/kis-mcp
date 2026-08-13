# Closeout: Two Axis Change Governance

## Implemented scope

- Added schema-v4 change records with independent `small|medium|large` complexity and canonical additive risk triggers while preserving schema-v1-v3 stored-record compatibility.
- Updated change-governance CLI/lifecycle sizing, authority guidance, and the operational-only exception without changing HR-001/HR-002/HR-003.
- Expanded the desired Work Management Project schema from 18 to 20 fields with `Complexity` and `Risk Triggers`, and carried both through normalized work records/intake/parsing.
- Migrated change execution and completion from `risk_profile` to the v2 `complexity` + `risk_triggers` contract; complexity sizes base verification and risk triggers add narrow specialist review/selection controls.
- Left both operator-owned classification skill paths unchanged.

## Validation evidence

- Focused 117 regression suite covering change controls, change execution, completion, change governance, Work Management contracts/intake/schema, and Project-management parsing/tools exited `0` after the final migration.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check` exits `0` and reports only declared 117 paths.
- The branch was re-rooted onto current `main` only after proving source-side 116 commit `5ddd6963e31362319c0edcb6d5a037be6042f061` and landed `main` `4b9e80d4e1229818a0bbe122b5805318c5a13324` have the identical tree `c54eb2c6e16316c15e48af478e11423d88ddab71`.
- Canonical full repository verification is intentionally reserved for the exact published PR head.

## CI finding and correction

- The first reconciled PR #163 head `a3e463415837a9576a82e341e2bb434124136a59` failed canonical run `31741677453` only at change-governance conflict validation: historical merged schema-v3 records 115/116 still contain `active` in their committed scope files and were compared as live exclusive claims against 117.
- Local change-workflow validation already derives those merged/cleaned schema-v3+ records as closed, so the canonical verifier was inconsistent with the established schema-v3 lifecycle contract.
- Added a PR-validation projection that releases non-current schema-v3+ claims while preserving the exact `GITHUB_HEAD_REF` claim as active and leaving schema-v1/v2 explicit-status semantics unchanged; a focused red→green regression covers the rule.
- Reproducing only `verify_change_governance()` with `GITHUB_HEAD_REF=change/117-two-axis-change-governance` now returns `ok: true`; the subsequent exact-head run also confirmed canonical change governance passes.
- The next exact-head run reached the full pytest suite and exposed one stale CLI assertion that still expected the pre-117 18-field manifest. The manifest correctly contains 20 fields.
- Added that CLI regression file to 117 scope and updated it to require 20 fields plus `Complexity` and `Risk Triggers`. The focused regression now passes. The full canonical verifier remains delegated to the next exact PR head.

## Review

- The working-tree review helper returned no findings because the implementation was already committed and supplied no working-tree diff; that result is not counted as review evidence.
- A committed-range Codex review was attempted against `main...HEAD`; its local evidence/test commands were blocked by the reviewer sandbox, so no unsupported findings are recorded from that attempt.
- Focused tests and deterministic scope checks are the current valid pre-publication evidence; exact-head CI remains the merge gate.

## Git and merge

- Branch: `change/117-two-axis-change-governance`
- Worktree: `.work/worktrees/117-two-axis-change-governance`
- Current implementation head before this closeout update: `7554d49` (`Complete two-axis execution migration`).
- Pull request or merge: pending exact-head publication and canonical GitHub Actions.
- Cleanup: pending successful exact-head merge.

## Operator hold / residual items

- `SPEC-117` / issue #157 must remain open and Project status must remain `In Progress` until operator verification, even after repository implementation lands and cleans up.
- Live GitHub issue state was found closed during closeout and was reopened before publication.
- The repository-owned target is 20 fields / 12 views. Any live Project field/view drift that cannot be provisioned through the approved bounded provider surface must remain explicit rather than bypassed.
