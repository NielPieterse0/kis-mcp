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

Changes 049 through 055 implement the internal provider-neutral P0-P4 foundation under `src/kis_mcp/work_management`: project identity and lifecycle, read-only Project inventory contracts, typed intake and governance records, implementation traceability, exact-revision merge readiness, documentation milestones, and review-run evidence with explicit coverage, observation triage, deterministic child-record extraction, and finding lifecycle management.

P4 confirms `.work/reviews/<review-id>/` as the canonical evidence namespace and models its request, report, result, coverage, optional SARIF, and closeout artifact manifest. It does not create those files or implement a generic persistence service.

These contracts are not publicly composed or remotely commissioned. P5 provider workflows, persistence, CLI, CI, automation, reconciliation, portfolio status, and stable reader-facing operating documentation remain future governed work.
