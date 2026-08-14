# Historical Slice / Commissioning Reconciliation

## Method

All available change closeouts from 001 through 111 were scanned in order. Their `Residual items` were extracted to `historical-residuals.txt`, then reconciled against later changes, current source/configuration, current authority documents, canonical verification, and live `kis-dev`/`kis-op` status. Raw unchecked/pending markers were not treated as debt without current corroboration because many old lifecycle records are intentionally historical or later superseded.

## Confirmed outstanding items

**SR-01 | Govern gateway/catalogue composition remains incomplete | Type: implementation.** Change 100 delivered settings, rules, evidence/service code, tests and four read-only tool contracts, explicitly deferring gateway composition. No later change registers those tools; live capability search contains no Govern operation. Current `SPEC.md` still labels Govern target-state. Follow-up should decide whether to complete the target-state integration or explicitly classify the foundation as staged.

**SR-02 | MCP Python SDK provider composition remains deferred | Type: implementation/configuration.** Change 044 delivered Python SDK and GitLab provider packages and deferred public composition. Tools from that slice are now composed, but the Python SDK provider is not; its checked-in setting remains `enabled=true`. GitLab is explicitly archived/disabled. Follow-up should resolve the Python SDK provider's intended lifecycle.

**SR-03 | Rich GitHub Project schema/view provisioning remains incomplete | Type: external commissioning limitation.** Change 110 completed the repository-owned 18-field/12-view schema manifest and drift/status logic, but current `OPERATIONS.md:258` still records only built-ins plus `Status = Todo/In Progress/Done`. The approved bounded GitHub MCP surface cannot create the missing custom fields, Status options, saved views or native workflow configuration. This remains a genuine external provisioning gap, not a code regression.

**SR-04 | Generated/code-derived module documentation architecture remains unimplemented | Type: planned future slice.** Change 110 explicitly kept generated module documentation out of scope and records it as the separate next documentation slice. It is not required by the current `SPEC.md`, so treat it as planned work rather than a current-contract defect.
**SR-05 | Docker Hub upstream search remains intentionally unavailable | Type: compatibility limitation.** Change 111 live-verified six public repository/tag reads but kept `search` hidden because the pinned upstream output schema rejects Docker Hub's current `search_after` field. Current `SPEC.md` documents the same limitation. This needs an approved provider update/compatibility slice, not a KIS policy change.

**SR-06 | Docker Hub pinned dependency advisories remain recorded risk | Type: security/dependency debt.** Change 111 records 13 production advisories, including 9 high, for the pinned upstream dependency tree. This audit did not use external network access and therefore did not refresh advisory data. The pin is unchanged and exposure remains constrained to public read-only stdio operations, so the historical risk should remain open until a local/approved dependency re-audit or provider upgrade supersedes it.

**SR-07 | DBHub/Docker commissioning status does not survive as truthful status evidence | Type: post-commissioning reporting defect.** Change 111 completed live commissioning and fresh restart smoke. Current readiness functions still hard-code commissioning fields to pending, so both live instances request commissioning again. This is a newly confirmed closeout/acceptance gap: successful commissioning exists, but the status model does not retain or derive it.

## Historical items confirmed superseded or closed

Early deferred Discover public integration, generalized change targets, context brokering, impact analysis, project cataloging, provider admission, Work Management P1-P5 implementation, GitHub/Supabase provider integration, dual-instance startup/reclaim, Control Center mounting, workflow exposure, verification selection/execution, and completion coordination all have later implementation/current-code evidence and are not reopened merely because older closeouts contain unchecked or pending text.

The change-013 long-session log-buffer concern is also no longer current: the launcher now drains owned stdout/stderr jobs repeatedly during readiness and steady-state loops. Change-109 DBHub/Docker “not commissioned” residual was superseded by change 111.

## Priority order for follow-up slices

1. Fix commissioning-state/reporting truth (SR-07 / CR-01 / DA-03).
2. Reconcile current document authority drift (DA-01/DA-02/DA-04).
3. Decide lifecycle/composition for Govern and Python SDK provider (SR-01/SR-02).
4. Handle external Project provisioning when a bounded mechanism is approved (SR-03).
5. Address Docker compatibility/dependency debt through an approved upstream/pin review (SR-05/SR-06).
6. Treat generated code-derived documentation as a separate planned architecture slice (SR-04).