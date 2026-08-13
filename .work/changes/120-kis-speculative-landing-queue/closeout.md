# Closeout: KIS Speculative Landing Queue

## Implemented scope

- Added a bounded FIFO speculative landing queue for centrally registered GitHub repositories.
- Queue entries freeze exact PR heads; cumulative candidates are real two-parent merge commits and are published under generation-scoped `kis-readonly-queue/main/**` refs.
- Added exact candidate Actions reconciliation, 30-minute timeout handling, topology/base/head/review/conflict/failure invalidation, ALLGREEN prefix landing, and exact-base fast-forward CAS through the existing registered publication primitive.
- Added hard Work Management governance at the public enqueue and land boundaries: fresh record/trace evidence is parsed, exact-head-linked, and passed through the existing merge-readiness evaluator before mutation.
- Added strict v1 JSON configuration/schema, atomic generated state, capability/workflow exposure, canonical queue-ref verification trigger, tests, operations documentation, and commissioning smoke coverage.

## Validation evidence

- Focused checks: `24 passed` across queue core, registered backend, capability schema/dispatch, governed Work Management composition, platform workflow, and Work Management descriptor coverage.
- Ruff: changed Python/test surfaces pass repository Ruff invocation.
- Local commissioning: `scripts/smoke-github-merge-queue.ps1` passes bounded configuration/workflow checks and focused tests.
- Repository verification: branch-scoped canonical verification executed locally; the shared workstation Skills root currently injects `bayesian-modeler`, which this checkout does not define and causes unrelated composition failures. Exact clean-runner GitHub Actions evidence is required before merge and will be recorded here.
- Diff scope check: `scripts/change-workflow.ps1 check` and `git diff --check` pass.

## Review

- Specialist review backends were attempted but unavailable (`CodexCliError`, `NvidiaNimError`); no unavailable-backend result is counted as review evidence.
- Manual architecture review finding 1: Work Management readiness was initially only a workflow convention. Resolution: public enqueue/land now require fresh record+trace evidence and recompute exact-head merge readiness internally; live review/protection state is also revalidated.
- Manual architecture review finding 2: enqueue initially did not advance generation for a changed queue topology. Resolution: appending to a non-empty queue now advances generation and invalidates prior speculative evidence, with regression coverage.

## Git and merge

- Branch: `change/120-kis-speculative-landing-queue`
- Worktree: `.work/worktrees/120-kis-speculative-landing-queue`
- Commit: pending exact reviewed commit.
- Pull request or merge: pending exact-head PR verification/merge.
- Cleanup: pending verified merge and post-merge commissioning.

## Residual items

- Post-merge live commissioning must exercise the commissioned queue through a real registered PR: enqueue, candidate publication, exact candidate GitHub Actions success, governed ALLGREEN landing, GitHub-observed indirect PR merge, tracking refresh, and runtime smoke.
