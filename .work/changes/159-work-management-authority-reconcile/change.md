# Change: Work Management Authority Reconcile

- **Change ID**: `159-work-management-authority-reconcile`
- **Repository complexity**: `small`
- **Documentation level**: `Complex`
- **Risk trigger**: `public_contract`

## Outcome

Reconcile governing Work Management documentation to the corrected 25-managed-field / 12-canonical-view contract after change 166 live acceptance.

## Authority and sources

- `AGENTS.md` owns documentation routing and requires current product truth in `SPEC.md`.
- `settings/work-management/github-project-schema.json` owns executable field/view values.
- Change 166 and #270/#142 carry dated implementation and live commissioning evidence.
- Fresh live evidence on merge `1e51544b4d4e43ad90f890bfbb622f18c45519c7` proves pre-repair drift, six in-place view updates, all-12 behavioral verification, clean schema status/plan, and zero current `In Progress` legacy items.

## Plan and acceptance

1. Keep `SPEC.md` static/product-level: describe executable semantics, canonical Status-filter invariant, behavioral readback, and fail-closed readiness without embedding dated live success.
2. Mark the Work Management programme implementation/commissioning complete while keeping live readiness explicitly dynamic and owned by `project_management_schema_status`.
3. Reconcile change-166 closeout/tasks to its actual PR #301, CI, merge, live commissioning, legacy-state decision, issue evidence, branch deletion, and cleanup.
4. Preserve ambiguous legacy `Todo` backlog; document that canonical views exclude legacy lifecycle values rather than claiming a blind migration.
5. Verify scope, stale-text removal, Markdown/JSON validity, review the exact docs range, then update existing PR #282 at an exact reviewed head.

## Implementation and verification

- `SPEC.md` now describes the strict configured 12-view Status-filter invariant and bounded behavioral saved-view readback without embedding transient live success.
- Programme metadata now records implementation/commissioning complete, no current change, and dynamic live readiness ownership.
- Change-166 closeout/tasks now match PR #301, exact-head CI, merge, live 12-view verification, legacy-state decision, issue evidence, branch deletion, and cleanup.
- JSON parsing, `git diff --check`, governed scope check, and targeted stale-claim search pass on the current documentation set.
- Full-range documentation and API-contract reviews completed with zero findings; updating existing PR #282 at the exact reviewed final head is the remaining pre-merge gate.