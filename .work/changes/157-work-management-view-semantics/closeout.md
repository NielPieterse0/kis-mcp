# Closeout: Work Management View Semantics

## Implemented scope

- Extended the canonical Project manifest so all 12 views declare executable layout, filter, visible-field, sort/group, and board vertical-group semantics.
- Added provider-neutral semantic view observations and drift reporting; `views_ready` now fails for mismatched semantics rather than accepting a named shell.
- Distinguished missing views from name-only/unverified view evidence so repair planning cannot create a duplicate existing view.
- Added dimension-aware repair planning: filter/visible-field drift routes to the bounded commissioner; unsupported existing sort/group/vertical drift is explicit manual/provider limitation.
- Extended the registered-Project commissioner to observe full saved-view semantics, update supported existing semantics in place, create missing views with fixed current REST shapes, and require a semantic post-read before success.
- Added full refusal preflight before remote mutation and a second post-field-creation preflight before option/view updates, preserving idempotent recovery for additive field creation.

## Validation evidence

- Affected Work Management / GitHub Projects / Project Management tests: 236 passed.
- Exact changed-Python Ruff checks: passed.
- Python compilation for changed production modules: passed.
- `git diff --check`: passed.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: passed with every changed path inside change 157 ownership.
- Canonical full repository verification is intentionally deferred to provider-native exact-head pull-request CI per repository authority.

## Review

- Code-quality (Codex CLI): initial review found two blockers—late view refusal after earlier mutations and name-only evidence proposing duplicate view creation. Both were fixed with red regressions and the final re-review returned zero findings.
- Architecture (Codex CLI): initial review found the neutral repair plan recommended the commissioner for unsupported grouping drift. Repair dispositions are now dimension-aware; final re-review returned zero findings.
- Safety/security (Codex CLI): zero findings; fixed registered-target mutation, no delete/recreate path, preflight and post-read retained.
- API-contract automated review was unavailable/incomplete (Codex output/evidence limits; NVIDIA timeout), so the required exact-diff fallback was performed against current official GitHub Projects GraphQL, Project Views REST, filter, and `gh api` contracts.
- Manual API-contract fallback found and corrected one concrete defect: `ProjectV2FieldCommon` exposes the REST-compatible Project field identifier as `databaseId`, not `fullDatabaseId`. The query/parser/tests now match the current contract; no other blocking contract defect remained.

## Git and merge

- Branch: `change/157-work-management-view-semantics`
- Worktree: `.work/worktrees/157-work-management-view-semantics`
- Commit: pending exact reviewed-tree commit.
- Pull request / exact-head Actions / merge: pending.
- Cleanup: pending verified merge and live semantic commissioning.

## Residual items

- Publish and land the exact reviewed tree through the governed PR path.
- Restart a runtime on the landed revision; require semantic schema drift before repair, then recommission and prove all 12 views ready with an empty plan.
- Verify representative Inbox, Delivery Board, Holds/Deferred, and Completed semantics against live Project evidence.
- Complete #270, reconcile post-merge documentation evidence, annotate #142 with the corrected final acceptance, and safely clean the branch/worktree.
