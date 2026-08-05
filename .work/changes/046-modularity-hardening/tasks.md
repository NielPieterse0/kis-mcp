# Tasks: Modularity Hardening

## Authority and scope

- [x] Read and follow `AGENTS.md`, `docs/TRUST-MODEL.md`, the development lifecycle skill, and the operator-supplied modularity assessment.
- [x] Classify the slice as Complex and create governed change `046-modularity-hardening` in an isolated worktree.
- [x] Confirm the primary worktree was clean and preserve unrelated active worktrees `040-context7-serena-adapters` and `041-dual-instance-commissioning`.
- [x] Exclude `src/kis_mcp/server.py`, `src/kis_mcp/tools/__init__.py`, runtime settings, policy, and Discover because they are outside this bounded slice or actively owned elsewhere.
- [x] Confirm the generic Tools foundation already exists on current `main`, closing the assessment's stale missing-029 finding.

## R1-R3: Provider, tool, and workflow dependency direction

- [x] Add failing tests proving NVIDIA and Codex settings are not module-owned and infrastructure imports the code-review workflow.
- [x] Move `NvidiaSettings` and NVIDIA validation/defaults into `providers/nvidia/settings.py`.
- [x] Move `CodexSettings` and Codex validation/defaults into `tools/codex_cli/settings.py`.
- [x] Reduce `workflows/code_review/settings.py` to aggregate workflow composition and error translation.
- [x] Remove the `providers.platform` dependency on code-review settings.
- [x] Change NVIDIA capability metadata to provider-native `llm.inference.nvidia-nim` without claiming the workflow tool.
- [x] Run focused ownership, workflow, platform, and capability tests.
- [x] Commit as `14461cd` (`refactor: restore provider and tool settings ownership`).

## R4: Control Center stable read seams

- [x] Add failing schema-version and snapshot-delegation tests.
- [x] Add `RuntimeStatusReader`, `PolicyStatusReader`, `ProviderStatusReader`, `QuarantineStatusReader`, and `GitStatusReader`.
- [x] Require schema version 1 for runtime, policy, and provider documents and the current quarantine schema for metadata.
- [x] Reduce `ControlCenterSnapshotService` to orchestration for these evidence sources.
- [x] Preserve bounded JSON reads, Git isolation, policy mismatch diagnostics, provider ordering/text, Desktop Commander entry resolution, and degraded-state contracts.
- [x] Add regression tests for each behavior-preservation review fix.
- [x] Run the complete Control Center and architecture test set.
- [x] Commit extraction as `19b59b3` and review hardening as `1d9a671`.

## R5: Provider smoke application independence

- [x] Add failing injected-server and import-boundary tests.
- [x] Remove `kis_mcp.server` imports from GitHub and Supabase smoke modules.
- [x] Require the caller to inject a server factory after provider-specific preconditions pass.
- [x] Add `scripts/run-provider-live-smoke.py` as the application composition boundary.
- [x] Update both supervised PowerShell smoke entry points and their static tests.
- [x] Run the complete GitHub, Supabase, and architecture test set.
- [x] Commit as `b916432` (`refactor: inject provider smoke application composition`).

## R6-R7: Compatibility retirement and boundary enforcement

- [x] Switch registry tests to the canonical `kis_mcp.providers` package.
- [x] Add an absence/import regression test for the root provider registry alias.
- [x] Remove `src/kis_mcp/provider_registry.py` through recoverable quarantine.
- [x] Replace text-only import checks with AST-resolved architecture checks that cover relative imports.
- [x] Narrow the application-server boundary to the provider smoke modules identified by the assessment, leaving unrelated Desktop Commander composition for its own approved slice.
- [x] Commit alias retirement as `682fa34` (`refactor: retire provider registry compatibility alias`).

## Review, verification, and integration

- [x] Review `main...HEAD` against `spec.md`, `plan.md`, and the modularity assessment.
- [x] Resolve all blocking review findings and rerun the affected tests.
- [x] Run the portable focused test artifact across all affected modules: 185 passed.
- [x] Run `git diff --check`: passed.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` on the final branch state: passed with 43 declared changed paths.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1` on the final branch state: passed with two expected skips, 161 Python files compiled, and all configuration, dependency, governance, line-ending, and exact three-rule checks valid.
- [x] Record the reviewed implementation head, verification evidence, review findings, and residual items in `closeout.md`.
- [ ] Push the branch and create a pull request to `main`.
- [ ] Review the exact remote PR head and required checks.
- [ ] Merge only if the exact reviewed head remains current and no blocking finding remains.
- [ ] Verify the merged `main` state.
- [ ] Run governed cleanup for change `046-modularity-hardening` without affecting worktrees `040` or `041`.
