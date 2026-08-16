# Work Management Programme Roadmap

## Programme boundary

This programme delivers one provider-neutral capability across multiple configured repositories. GitHub is the first backend, not the domain boundary.

Each implementation phase uses its own governed change, isolated worktree, bounded ownership claim, tests, review, verification, pull request, and safe cleanup.

## Delivery milestones

| Phase | Outcome | Integration boundary | Documentation milestone |
|---|---|---|---|
| P0 | Programme authority and provider-neutral foundation | No gateway or provider registration | Record working authority; reader docs remain unchanged |
| P1 | Read-only backend inventory and normalized contracts | GitHub adapter, no mutation | Document supported inventory and commissioning state |
| P2 | Intake, typed records, decisions, assumptions, risks, approvals, and holds | Bounded issue and Project mutations | Update operator workflow and record schemas |
| P3 | Change, branch, worktree, PR, verification, merge, and closeout traceability | Git and GitHub workflow integration | Enforce pre-merge and post-merge documentation reconciliation |
| P4 | Review runs, durable reports, triage, and finding extraction | Review and evidence workflows | Document evidence retention and finding lifecycle |
| P5 | Built-in automation, CLI, CI, reconciliation, and portfolio status | Platform composition after 047 | Reconcile README, operations, module specs, and implementation status |

## Documentation feedback routine

1. Classify documentation impact when the governed slice is created; initialize or reconcile its Work Management projection when the backend is available.
2. Retain any stable Work Management identity as operational linkage in the change scope, then name affected documents and authority owners in the plan.
3. Complete pre-merge updates or record an explicit no-impact decision.
4. Capture the PR number and merge commit when merge completes.
5. Reconcile merge-specific closeout, README, operations, architecture, product, and module documentation.
6. Keep the work item in `Documentation` until post-merge reconciliation is complete.

## Current implementation boundary

Changes 049 through 057 implement the provider-neutral P0-P5 capability; change 110 completes the approved Work Management/documentation integration boundary. The domain covers project identity and lifecycle, documentation-aware actionable intake, typed governance records, exact PR/verification/merge traceability, review evidence, atomic `.work/reviews/<review-id>/` persistence, deterministic reconciliation, portfolio status, Project schema drift, and an application service that isolates backend failures.

The GitHub adapter reads configured Projects and applies bounded issue/pull-request item updates through the official provider. A separate registered-Project commissioner owns only the checked-in manifest repair surface: create missing canonical fields/options/views, preserve existing option identities, update API-supported saved-view semantics in place, refuse incompatible/destructive drift, and re-read before success. No delete or unrestricted GraphQL/REST passthrough is exposed. The repository-owned projection is `settings/work-management/github-project-schema.json`: **25 managed fields and 12 saved views with executable layout/filter/display semantics**.

The platform exposes bounded Work Management reads and mutations for inventory, deterministic queueing, claims, lifecycle commands, schema status/plan, traceability, merge readiness, documentation reconciliation, review evidence, portfolio status, current work, and board projection. Exact-head GitHub Actions remains the landing verifier. `settings/work-management/github-projects.settings.json` uses the shared user Project #1 for all configured managed repositories; native/custom automation remains disabled unless separately commissioned.

Repository implementation is complete for the current Work Management command plane and semantic Project schema contract. Work Management is operational authority, not a prerequisite for establishing local governed-change authority; stable Work linkage may be reconciled after local change creation. Live Project readiness is dynamic evidence owned by `project_management_schema_status`, not a static roadmap claim: all managed fields/options and all declared view semantics must match the manifest, and `project_management_schema_plan` must be empty after commissioning. Detailed dated commissioning evidence remains in the applicable issue/change closeout records.
