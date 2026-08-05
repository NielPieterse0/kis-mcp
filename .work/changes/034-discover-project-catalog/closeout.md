# Closeout: Discover Project Catalog

## Implemented scope

- Added immutable project-catalog request, budget, project, manifest, relationship, unknown, omission, and response contracts.
- Added strict Draft 2020-12 request and response schemas.
- Added explicit selected-project resolution through existing `ReadAuthority`, duplicate canonical selection rejection, and budgeted project retention.
- Added fixed manifest inventory for root `package.json`, root `pyproject.toml`, and root-level `*.csproj` files in retained selected projects only.
- Added static npm `file:`/`link:`, Poetry/uv path dependency, .NET `ProjectReference`, and nested selected-project relationship evidence.
- Added explicit unknowns for unselected, budget-omitted, outside-boundary, unreadable, and malformed manifest references without following or scanning target projects.
- Added deterministic ordering, global budgets, exact omissions, confidence, truncation reasons, content digests, and response fingerprint.
- Added developer documentation for trust boundaries, supported evidence, unknowns, budgets, and the final integration seam.

## Validation evidence

- Project-catalog tests: 8 passed.
- Discover regression suite: 191 passed, 1 expected skip.
- Full repository verification: passed; complete pytest suite passed with 2 expected skips, 105 Python files passed syntax validation, and configuration, dependency, governance, whitespace, line-ending, and exact HR-001/HR-002/HR-003 checks passed.
- Change scope check: passed against current `origin/main` and reported only declared 034 paths.
- Request and response validated against Draft 2020-12 schemas.

## Review

- Security: no subprocess, Git command, socket, HTTP client, provider runtime, credentials, package manager, target-code import, or network dependency.
- Selection boundary: only explicit paths are resolved; only budget-retained selected roots are scanned; repository references cannot expand the selection.
- Modularity: contracts and service are isolated under `discover.project_catalog`; public/server composition remains a later integration seam.
- Simplicity: only narrow static local relationship syntax is supported; ambiguous or unsupported references remain explicit unknowns.
- Determinism: project, manifest, relationship, unknown, omission, and fingerprint ordering is stable for identical inputs.
- Findings: no critical or important defects remain. The scope check initially compared against stale local `main`; the claim base was corrected to `origin/main` without touching the dirty primary checkout.

## Git and merge

- Branch: `change/034-discover-project-catalog`
- Worktree: `.work/worktrees/034-discover-project-catalog`
- Implementation commit: pending
- Pull request and merge: pending
- Cleanup: pending

## Residual items

- Public composition behind an explicit selected-project input remains in the final Discover integration change.
- Background indexes, semantic providers, forge evidence, package resolution, and cross-repository change impact remain outside this bounded local foundation.
