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

Changes 049 through 057 implement the provider-neutral P0-P5 capability. The domain now covers project identity and lifecycle, typed intake and governance records, implementation traceability, review evidence, atomic `.work/reviews/<review-id>/` persistence, deterministic reconciliation, portfolio status, and an application service that isolates backend failures.

The GitHub adapter reads configured Projects and applies only bounded issue or pull-request addition and Project-field updates. It preflights revisions, deduplicates source records across process restarts, requires explicit apply plus idempotency, and exposes no delete or unrestricted GraphQL operation.

P5 also supplies fixed-shape CLI commands, a reusable exact-revision CI workflow, and five task-level workflow descriptors composed through the platform. `settings/work-management/github-projects.settings.json` is disabled by default. Live GitHub OAuth and private-repository commissioning pass, but the previously approved user Project `#12` returned `404` on 2026-08-07; no stale Project binding was enabled or mutated.

Remaining work is limited to later optional enhancement: commissioning a valid Project binding, enabling selected automation, and organization-level or stronger-enforcement features that remain outside P5.
