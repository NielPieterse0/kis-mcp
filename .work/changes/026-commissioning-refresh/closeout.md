# Closeout: Commissioning Refresh

## Implemented scope

- Added provider-owned, bounded `user_status` and commissioning metadata for GitHub and Supabase.
- GitHub now reports `Ready — authentication required` when its pinned executable and OAuth configuration are ready.
- GitHub reports installation-required or PAT/OAuth configuration-conflict states only for genuine local faults.
- Supabase now reports `Ready — project initialization required` when no project reference is present and `Ready — authentication required` after project scope and local OAuth prerequisites are ready.
- Supabase mounts a local health-only FastMCP surface without constructing upstream transport until project scope, Windows credential storage, and PAT-conflict checks pass.
- Shared `kis_provider_status` preserves validated provider-owned action states, keeps registration/build/mount/readiness/live-verification evidence separate, bounds promoted values, and removes duplicated action metadata from nested platform health.
- Updated the gateway tool description, authoritative specification, operations guidance, and existing GitHub/Supabase provider documentation.
- Preserved OAuth implementation, credential storage, provider versions, namespaces, tool surfaces, HR-001, HR-002, HR-003, and all Discover paths.

## Requirement evidence

- **R1 / R2 — Supabase onboarding and authentication states**: `tests/providers/supabase/test_supabase_server.py` covers project-initialization-required, authentication-required, credential-storage failure, PAT conflict, redaction, and health-only mounting; `tests/providers/supabase/test_supabase_cli.py` covers standalone health-only startup.
- **R3 — GitHub authentication state**: `tests/providers/github/test_server.py` covers executable missing, OAuth authentication required, PAT conflict, and redaction.
- **R4 — Shared actionable status**: `tests/providers/test_runtime_composition.py` proves validated provider-owned status survives composition, generic fallback remains available, and promoted metadata is not duplicated in platform health.
- **R5 / R6 — Genuine faults, bounded output, and redaction**: provider tests cover missing executable, unavailable credential storage, both legacy PAT conflicts, builder containment, fixed-key validation, bounded promoted values, and absence of supplied secret values.
- **R7 — Guidance alignment**: `SPEC.md`, `docs/OPERATIONS.md`, and both existing provider README files define the same onboarding states and next actions.
- **R8 — Boundary preservation**: scope validation reports only declared provider, test, documentation, gateway-description, and change-record paths; Discover and policy paths are unchanged.

## Validation evidence

- TDD red/green cycles were observed for GitHub action metadata, Supabase readiness mapping, Supabase health-only mounting, shared status preservation, GitHub PAT conflict handling, and platform-health de-duplication.
- Focused provider suite: `tests/providers` passed with **170 tests** and no failures.
- Change-scope validation: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed and listed only declared paths.
- Whitespace validation: `git diff --check` passed with no output.
- Canonical repository verification: `pwsh -NoProfile -File .\scripts\verify.ps1` passed with the locked interpreter, FastMCP `3.4.4`, pytest `8.4.2`, 76 Python files, 24 governance claims, the full pytest suite, and two expected skips.
- Temporary focused-test runners were moved to recoverable quarantine:
  - `30be6567a171450fa529e80a6077fdf8`
  - `f4ef2eff659849329c3c9daeb4e027c2`

## Review

- Review boundary: working-tree diff for change `026-commissioning-refresh` against local `main` at `a73a19c6efbaf15b651cb05243f894e2a7623590`.
- Governing review sources: repository authority, change specification, local `code-review` skill, MCP server design guidance, and the operator-supplied commissioning report.
- Finding resolved: GitHub PAT override was initially still presented as ready; it now produces a degraded configuration-conflict state with a removal action and regression coverage.
- Finding resolved: promoted action metadata was initially duplicated inside `platform_health`; status extraction now emits it once, validates fixed keys, and bounds each promoted value to 256 characters.
- Finding resolved during PR completion: provider-owned onboarding status could still say ready when runtime composition had failed to build or mount the provider. Runtime build and mount failures now override onboarding status with an actionable unavailable state; regression tests observed both failures before the repair and passed afterward.
- Remaining findings: none identified in the final reviewed diff.

## Git and integration

- Branch: `change/026-commissioning-refresh`
- Worktree: `.work/worktrees/026-commissioning-refresh`
- Base: local `main` at `a73a19c6efbaf15b651cb05243f894e2a7623590`
- Implementation commit: `b15f49e9c26b25d81ac6c3192397d9481e552a41`.
- Pull request: `#34 — Clarify provider commissioning readiness` is open for review; no merge is authorized by this closeout.
- Cleanup: retain the branch/worktree until review and merge; remove them safely from clean `main` after integration.

## Residual items

- GitHub and Supabase authentication, upstream connectivity, discovered tools, and live verification remain explicit runtime actions; this slice does not claim or perform them.
- Discover Git-index handling, Windows `list_processes`, gateway-wide telemetry coverage, and stopped-search lifecycle reporting remain outside this slice and are not modified.
- Repository verification uses a shared editable Python environment and must remain serialized across worktrees. This run synchronized that environment to change 026; other active worktrees must run their own verification before relying on it.
