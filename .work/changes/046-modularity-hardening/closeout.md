# Closeout: Modularity Hardening

## Implemented scope

- Corrected the active NVIDIA/Codex dependency inversion by moving provider and tool settings ownership into `providers/nvidia` and `tools/codex_cli`; the code-review workflow now composes those module-owned contracts.
- Removed the code-review workflow dependency from `providers.platform` and changed NVIDIA capability metadata to the provider-native `llm.inference.nvidia-nim` capability without claiming a workflow-specific tool.
- Added stable read-only Control Center adapters for runtime, policy, provider, quarantine, and Git evidence, with explicit schema checks and bounded degradation.
- Reduced `ControlCenterSnapshotService` to orchestration for those evidence sources while preserving existing Git isolation, policy mismatch diagnostics, provider display behavior, Desktop Commander entry detection, and bounded JSON semantics.
- Removed application composition imports from GitHub and Supabase provider smoke modules. A supervised application script now injects `build_server` after provider-specific preconditions pass.
- Removed the stale root `provider_registry.py` compatibility alias and switched tests to `kis_mcp.providers`.
- Added AST-resolved modularity architecture tests for provider/tool-to-workflow dependencies, provider-smoke-to-application dependencies, the retired alias, and Control Center storage interpretation.
- Added no dependencies, hard blocks, policy changes, credentials, network calls, installations, or persistent-state migrations.

## Validation evidence

- Baseline verification before implementation: `pwsh -NoProfile -File scripts/verify.ps1` — passed on clean `main` at `cd19e86`; the full suite completed with two expected skips.
- TDD checkpoints:
  - settings ownership red phase failed on missing module-owned settings; green phase passed 34 focused tests;
  - Control Center red phase failed on missing readers; green phase passed the complete Control Center and architecture set;
  - provider smoke red phase failed on old signatures and upward imports; green phase passed 125 provider and architecture tests;
  - alias retirement red phase failed while the alias existed; green phase passed after recoverable removal.
- Review-fix verification: Control Center parity and AST boundary checks passed 30 tests.
- Final affected-module verification: `.work/changes/046-modularity-hardening/run-focused-tests.ps1` — 185 passed.
- Whitespace check: `git diff --check` — passed.
- Final change-governance check: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` — passed with 43 declared changed paths.
- Final repository verification: `pwsh -NoProfile -File scripts/verify.ps1` — passed; configuration, locked interpreter and dependencies, repository line endings, 161 Python syntax checks, change governance, pytest, and the exact HR-001–003 implementation were valid, with two expected skips.

## Review

- Initial review finding: the extracted Control Center readers changed several observable behaviors—Git command/environment isolation, policy rule-set mismatch diagnostics, provider ordering/action text, and Desktop Commander launch-argument resolution.
- Resolution: restored the original behavior inside the new adapters and added direct regression tests for each case. Bounded JSON reading was also restored to a single capped binary read rather than stat-then-read.
- Boundary-test review finding: text-fragment architecture checks could miss relative Python imports.
- Resolution: replaced those checks with AST parsing and relative-import resolution.
- Scope review finding: the stronger provider-wide application-import check exposed an unrelated existing Desktop Commander lazy import outside the assessed smoke finding and outside this change's ownership.
- Resolution: narrowed the regression to GitHub and Supabase provider smoke modules, matching the assessment and avoiding an unapproved cross-slice refactor.
- Remaining blocking review findings: none after focused reruns; final repository verification and remote PR review remain required before merge.

## Git and merge

- Branch: `change/046-modularity-hardening`.
- Worktree: `.work/worktrees/046-modularity-hardening`.
- Implementation commits:
  - `14461cd` — restore provider and tool settings ownership;
  - `19b59b3` — isolate Control Center evidence readers;
  - `b916432` — inject provider smoke application composition;
  - `682fa34` — retire provider registry compatibility alias;
  - `1d9a671` — preserve behavior and strengthen boundary tests.
- Exact reviewed PR head: `53cdebb71fb4ee521b59eba352fd7d6881053ed5`.
- Pull request: `#59` — `Harden module boundaries after modularity assessment`.
- Merge commit: `f4475961c44634b17327a934031f98bacc12d3d7`.
- Current repository evidence: the merge and reviewed head are ancestors of `main`; the local change branch and worktree are absent.
- Governance reconciliation: claim status corrected from stale `active` to `closed` by change `048-stale-change-cleanup-hardening`.
- Recovery: all tracked artifacts remain recoverable from Git history and merged `main`; no worktree reconstruction is required.

## Residual items

- `src/kis_mcp/server.py` composition thinning remains deferred because active change `040-context7-serena-adapters` owns that file exclusively. A coordinated post-040 slice should introduce module registration entry points without overlapping worktrees.
- Discover remains externally cohesive but internally flat. Its migration should continue incrementally by feature slice; no big-bang package move was attempted.
- Desktop Commander root-package consolidation and its existing lazy application import remain separate structural work requiring explicit ownership and scope.
- The assessment's missing `029-tools-code-tooling` dependency is already closed on current `main`; the generic Tools foundation is present and was not reimplemented.
- Recovery is a normal Git revert of the change or merge commit. No data migration or irreversible repository deletion is part of this slice.
