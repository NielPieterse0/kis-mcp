# Closeout

## Scope completed

- Closed stale merged claims:
  - `004-live-proxy-commissioning` — branch head `a645b26779d1ee41327cea7d67dc05ab0d3e7577`, merged by `bb8abaf6c2776febd19105bf24cc229a08122f1e`.
  - `010-provider-module` — branch head `1fc958e843f03e2bc41560daf52826a578e854cd`, merged by `fd9fe7907bcfafb8c71d28ead6bdc1ee3a0f3d0d`.
  - `017-p2-operational-hardening` — branch head `1621af0ef4c35e72718e12eb80daf971b8ef9508`, merged by `e9060038b941b62f61681224a15dccc882ae256a`.
  - `020-discover-change-inventory` — branch head `34f7ea5e8c2ea33a7ec34498166c8ce8911a916e`, merged by `bf989b75cb6aeae9c2ff4ad0e751f6de9c28478e`.
- Preserved the already-closed `006`, `009`, `015`, and `018` records unchanged.
- Changed claim discovery so the current checkout is authoritative; linked worktrees contribute only their own branch claim when that change ID is absent.
- Retained explicit underscore-prefixed template exclusion and added regression coverage for template and stale-snapshot handling.

## Verification

- `pytest tests/test_change_governance.py tests/test_repository_scope.py -q`: 27 passed.
- `change-workflow.ps1 check`: all changed paths were within the declared scope.
- `python -m py_compile scripts/change-governance.py`: passed.
- Changed scope JSON files parsed successfully.
- `git diff --check`: passed.
- Repository-wide `change-workflow.ps1 validate`: `{"active_changes": 4}`.
- Full `verify.ps1` was not run because integrated post-merge verification from clean updated `main` is point 8, outside this change.

## Recovery

Revert the resulting commit to restore the previous status records and claim-discovery behavior.

## Branch

- Branch: `change/021-governance-claim-reconciliation`
- Worktree: `.work/worktrees/021-governance-claim-reconciliation`
