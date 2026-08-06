# Closeout: Multi-Project Work Management Foundation

## Current state

P0 is implemented and verified. Change 049 remains active and its worktree remains reserved because GitHub adapter, workflow composition, public exposure, remote commissioning, PR integration, and post-merge documentation reconciliation are later programme phases.

## Implemented scope

- Moved the working authority from `docs/development` to `.work/programmes/work-management`.
- Generalized the programme for multiple managed repositories and backend bindings.
- Added programme control, roadmap, modularity evidence, and ADR-001.
- Added configurable pre-merge and post-merge documentation milestones.
- Added immutable provider-neutral project and work-record contracts.
- Added deterministic lifecycle validation, including approval, documentation, and supersession behavior.
- Added deterministic project-scoped next-work selection with explicit exclusion reasons.
- Added architecture tests that keep P0 independent of FastMCP, gateway, Providers, Workflows, Capabilities, and GitHub-specific code.

## Test-first evidence

- Contracts red: `ModuleNotFoundError: No module named 'kis_mcp.work_management'`.
- Lifecycle red: `ImportError: cannot import name 'TransitionRejected'`.
- Selection red: `ImportError: cannot import name 'select_next_work'`.
- Identity review tests red for GitHub-specific repository shape, relative roots, and mismatched record prefixes.
- Supersession review test red with `transition_not_declared`.
- Cross-project dependency tests red because project B incorrectly satisfied project A.
- Current focused result: 22 work-management tests pass.

## Verification evidence

Passed on the current code state:

```powershell
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests\work_management -q
C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m compileall -q src\kis_mcp\work_management
git diff --check
pwsh -NoProfile -File .\scripts\change-workflow.ps1 check
pwsh -NoProfile -File .\scripts\verify.ps1
```

The canonical repository gate passed with Python syntax, change governance, the full pytest suite, locked dependencies, line endings, configuration, and the exact HR-001/HR-002/HR-003 implementation consistent.

## Review

The findings-first review identified and resolved:

1. GitHub-specific `owner/repo` validation inside the provider-neutral contract.
2. Relative local roots that could make project identity depend on process state.
3. Record identifiers whose prefixes did not match their record type.
4. A declared `Superseded` state with no valid incoming transition.
5. Cross-project dependency completion caused by record-ID-only matching.

No blocking findings remain in the P0 diff. Provider behavior, remote concurrency, GitHub API compatibility, persistence, migration, and live commissioning were not tested because they remain outside P0.

## Git and documentation milestone

- Branch: `change/049-github-project-management-spec`
- Worktree: `.work/worktrees/049-github-project-management-spec`
- Programme relocation commit: `b1e9ca4`
- Main reconciliation merge: `3e0adec`
- Contracts commit: `7d66e39`
- Lifecycle commit: `fbea96a`
- Selection commit: `188b519`
- Provider-neutral identity fix: `e27c0ed`
- Supersession fix: `bc3c482`
- Project-scoped dependency fix: `0cd1d1e`
- Documentation state: `pre_merge_complete` for P0 working authority.
- Reader-facing repository documentation: explicit no-impact for P0 because the package is unexposed and uncommissioned.
- Post-merge reconciliation: pending; the change MUST NOT become `Done` until merge evidence and closeout are reconciled.

## Recovery

P0 is additive and has no public composition, remote mutation, credentials, migration, or persisted operational state. Revert the P0 commits to remove the package and tests. Programme artifacts remain recoverable through Git history.

## Residual programme phases

- P1: read-only GitHub Project inventory and adapter contracts after change 047.
- P2: typed remote records, decisions, assumptions, risks, approvals, and holds.
- P3: change, PR, verification, merge, and documentation traceability.
- P4: review evidence, triage, and finding extraction.
- P5: CLI, CI, automation, reconciliation, public composition, and commissioning.
