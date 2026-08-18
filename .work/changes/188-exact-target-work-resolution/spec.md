# Change Specification: Exact Target Work Resolution

- **Change ID**: `188-exact-target-work-resolution`
- **Status**: Active
- **Parent**: Change 186 / issue #356
- **Work item**: issue #358
- **Historical source**: Change 173 implementation `af501c9`

## Outcome

Restore bounded exact-target Work Management issue resolution beyond the default Project inventory window while remaining fail-closed on incomplete scans.

## Requirements

- Exact-target commands use a finite 1,000-item scan instead of the broad queue's 100-item bound.
- A still-truncated exact-target inventory fails closed even when one match is visible, because an unseen duplicate cannot be excluded.
- Visible duplicate exact matches remain ambiguous failures.
- `claim_work`, `release_work`, `transition_work`, `sync_change_classification`, and `complete_work` share the corrected resolver.
- `next_work` retains its existing 100-item fail-closed behavior.

## Scope

Only `src/kis_mcp/work_management/service.py`, `tests/work_management/test_command_service.py`, and this change record.

## Acceptance

Focused Work Management regressions pass; scope check passes; required review is clean; GitHub Actions passes on the frozen PR head.