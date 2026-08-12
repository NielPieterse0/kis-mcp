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

1. Classify documentation impact when a slice is created.
2. Name affected documents and authority owners in the plan.
3. Complete pre-merge updates or record an explicit no-impact decision.
4. Capture the PR number and merge commit when merge completes.
5. Reconcile merge-specific closeout, README, operations, architecture, product, and module documentation.
6. Keep the work item in `Documentation` until post-merge reconciliation is complete.

## Current implementation boundary

Changes 049 through 057 implement the provider-neutral P0-P5 capability; change 110 completes the approved Work Management/documentation integration boundary. The domain covers project identity and lifecycle, documentation-aware actionable intake, typed governance records, exact PR/verification/merge traceability, review evidence, atomic `.work/reviews/<review-id>/` persistence, deterministic reconciliation, portfolio status, Project schema drift, and an application service that isolates backend failures.

The GitHub adapter reads configured Projects and field schema and applies only bounded issue or pull-request addition and explicit item-field updates. It preflights revisions, deduplicates source records across process restarts, requires explicit apply plus idempotency, and exposes no delete or unrestricted GraphQL operation. The repository-owned desired Project projection is `settings/work-management/github-project-schema.json`: 18 approved fields and 12 approved saved views.

The platform exposes eight bounded Work Management tools and seven task-level workflows, including Project schema status, pre-merge documentation readiness, and post-merge documentation reconciliation. The reusable exact-revision CI workflow validates settings, the Project schema manifest, governance claims, focused tests, and optionally the canonical verifier. `settings/work-management/github-projects.settings.json` is enabled for `kis-mcp` user Project #1; all native/custom automation remains disabled.

Repository implementation is complete for the approved schema/drift and documentation-lifecycle integration. Live rich Project schema/view commissioning remains incomplete at the current approved provider boundary. Current operator status and next actions are owned by `docs/OPERATIONS.md`; detailed dated evidence is retained in `docs/development/github-project-onboarding/commissioning.md` and change 110 rather than duplicated here.
