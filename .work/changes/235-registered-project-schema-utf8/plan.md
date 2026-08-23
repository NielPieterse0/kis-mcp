# Plan: Registered Project Schema UTF-8

## Task 1 — Add red regressions

- Add a schema-client runner test that requires explicit UTF-8 subprocess decoding.
- Add a registered-operation test proving production commissioning does not override the schema client's default runner.
- Preserve the existing custom-runner commissioning test.

## Task 2 — Implement the narrow fix

- Make the schema client's default subprocess runner capture raw bytes, then decode stdout/stderr explicitly as strict UTF-8.
- In `RegisteredGitHubOperations.commission_project_schema`, omit the runner argument when the operation itself uses the generic production default; continue passing any explicitly injected runner.
- Do not alter the generic registered Git/GitHub runner.

## Task 3 — Verify and review

- Run the two focused test files, then affected Work Management/Project schema tests.
- Run `git diff --check` and `scripts/change-workflow.ps1 check`.
- Review code quality and test quality; resolve blocking findings.
- Commit the exact reviewed scope and publish through the governed registered-repository path.

## Task 4 — Live closeout

- Require exact-head GitHub Actions and Work merge-readiness before merge.
- Land, refresh `main`, and let the post-land hook restart `kis-dev`.
- Rerun registered Project commissioning and require `views_ready=true` with an empty schema plan.
- Reconcile #409 documentation/verification, close it, and clean Change 235.
