# Closeout: MCP Inspector Bootstrap

## Implemented scope

- Added a pinned managed-install contract for `@modelcontextprotocol/inspector@2.0.0` with Node.js `>=22.19.0`.
- Added a supervised installer with `C:\Projects` containment, reparse-point rejection, exact package verification, CLI smoke-before-activation, previous-package quarantine, rollback, and bootstrap-home quarantine.
- Added a foreground launcher for the configured `operation` or `development` kis-mcp HTTP instance, fixed loopback binding, distinct UI ports, and managed runtime state.
- Added focused structural tests, reproducible CLI/web smoke helpers, independent review helper, and operator documentation.
- Added no gateway tool, provider registration, policy rule, startup behavior, automatic update, or arbitrary remote target surface.

## Validation evidence

- Baseline repository verification: passed before implementation at base `0d869f2`.
- Focused tests: `3 passed` after each final implementation change.
- Diff scope check: `scripts/change-workflow.ps1 check` passed; all changed paths are declared by change `042-mcp-inspector-bootstrap`.
- Repository verification: `scripts/verify.ps1` passed on implementation head `81be4ec`, including the full pytest suite, line endings, configuration, dependency, syntax, governance, and exact three-rule checks.
- Managed installation:
  - Node.js `v22.23.1` satisfied the upstream minimum.
  - First-time and replacement installs of exact version `2.0.0` succeeded.
  - Package identity and `--cli --help` smoke passed before each activation.
  - Replacement preserved the prior package under `C:\Projects\.kis-mcp\quarantine\mcp-inspector\20260805T1527247143251Z-04dfce912bcd45be817ac2cf6373c541\previous-package`.
  - The isolated bootstrap home was preserved under the same operation's `bootstrap-home`; no per-install `home-*` directories remain in the temp root.
- Live commissioning:
  - Inspector CLI connected to `http://127.0.0.1:8011/mcp` and returned the development kis-mcp tool catalogue.
  - The managed web launcher served HTTP 200 at `http://127.0.0.1:6275/` and was terminated after the smoke.
  - Ephemeral local Inspector auth tokens are redacted from retained smoke evidence.

## Review

- NVIDIA NIM independent review completed on the initial implementation head and reported no blocking findings.
- Its workflow concern was resolved by the passing registered change-workflow check; its enforcement-layer comment was outside this support-tooling slice.
- Manual final review found and resolved two issues:
  - misleading "read-only session" wording, corrected to state that Inspector can invoke mutation-capable kis-mcp tools subject to normal policy and approval;
  - successful-install bootstrap-home residue, fixed test-first by moving it into recoverable quarantine.
- Two independent blocking-only review attempts against final head `81be4ec` timed out. This is recorded as a review limitation, not as approval. Focused, full-suite, live CLI, live web, replacement, quarantine, and manual diff evidence remained green.
- Blocking findings remaining: none identified.

## Git and merge

- Branch: `change/042-mcp-inspector-bootstrap`
- Worktree: `.work/worktrees/042-mcp-inspector-bootstrap`
- Base: `0d869f2`
- Implementation head: `81be4ec`
- Closeout commit: pending.
- Pull request or merge: pending.
- Cleanup: pending.

## Residual items

- npm reports upstream peer-resolution and deprecated-transitive-package warnings during install. Installation and package smoke succeed; these dependencies are owned by upstream Inspector `2.0.0`, not modified in this slice.
- Inspector is intentionally not auto-started. The selected kis-mcp instance must be running before launch.
