# Change: Work Management Authority Currentness

- **Change ID**: `168-work-management-authority-currentness`
- **Risk Profile**: lean

## Outcome

Reconcile the Work Management programme authority with completed change 166 and current live commissioning evidence without changing runtime behavior.

## Documentation plan

Documentation level: **Complex** because `target-spec.md` is the long-lived governing programme specification; the textual correction itself is bounded and reversible.

Sources:
- `programme.json`: programme `completed`, `current_change=null`, live readiness delegated to `project_management_schema_status`.
- Change 166 closeout: PR #301, exact-head CI, live 12-view recommissioning, zero mismatch/unverified, evidence-bounded legacy-state decision.
- Live Work Management: #270 and #142 are `Done` / `Complete`; both now project current change-166 evidence metadata.

Tasks:
1. Replace the stale reopened/pending status metadata with the completed programme boundary while keeping live readiness dynamic.
2. Reconcile the commissioning history to changes 157, 162, and 166 without freezing a live-success claim into this document.
3. Verify only the declared documentation/change-record paths changed; review the governing-document diff; run change governance checks.

Acceptance:
- No statement says #270 or saved-view commissioning is still reopened/pending.
- The commissioning history names the semantic, behavioral-readback, and final filter-invariant corrections.
- Runtime readiness remains owned by `project_management_schema_status` and an empty `project_management_schema_plan`, not static prose.
- No runtime/configuration behavior changes.

## Implementation and verification

- Implementation notes: reconciled the document-status metadata and commissioning history only; no runtime, settings, schema, policy, or source path changed.
- Focused checks: stale-claim scan passed; `git diff --check` passed; `scripts/change-workflow.ps1 check` passed with only the three declared paths.
- Review findings: documentation and architecture reviews completed with zero findings on working-tree fingerprint `7236cfb34b4528286e79957c6fd8487509f7d290d250b41a67ca23fb5466c795` before this evidence-only closeout edit; exact committed-source reviews remain required before publication.
- Residual risk: live readiness can drift after merge; static authority intentionally delegates current readiness to runtime schema status/plan.
- Closeout state: pre-publication verification in progress.
