# Closeout: Agent Tooling Bootstrap

## Implemented scope

- Added independent, exact-version installers for AgentSys `6.0.1` and agnix `0.45.0`.
- Installed AgentSys at `C:\Projects\.kis-mcp\tools\agentsys\6.0.1` and agnix at `C:\Projects\.kis-mcp\tools\agnix\0.45.0`.
- Fetched the complete AgentSys catalogue: 25 upstream plugins were processed; 21 valid Claude plugin packages were installed into the managed profile.
- Created isolated managed host profiles with 25 OpenCode commands, 35 OpenCode agents, 39 OpenCode skills, and 25 Codex skills.
- Added a managed host launcher for Claude Code, OpenCode, and Codex.
- Added strict JSON settings and schemas with default-deny future kis-mcp command exposure.
- Added bootstrap tests and operational documentation without modifying the active Tools module.

## Validation evidence

- Focused checks: `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests\bootstrap -q` — 5 passed.
- JSON parsing: both settings documents and both schemas validated successfully.
- Repository verification: `pwsh -NoProfile -File scripts\verify.ps1` — passed; 579 tests passed, 2 expected skips, 85 Python files compiled.
- Diff scope check: `pwsh -NoProfile -File scripts\change-workflow.ps1 check` — passed with only declared paths.
- Whitespace check: `git diff --check` — passed.

## Review

- Findings: AgentSys is a distribution and workflow installer, not an MCP server. agnix's npm distribution provides the CLI but does not include the separate native `agnix-mcp` binary. Review also found that the first launcher revision did not prepend the managed agnix binary directory, which would make the AgentSys agnix workflow unable to resolve its companion CLI.
- Resolutions: kept both installations independent; recorded agnix MCP status truthfully as `not_in_npm_distribution`; prepended both managed binary directories in the host launcher; added the discovered 25-command catalogue to default-deny JSON; deferred runtime mounting to a later Tools integration slice.
- Security and recovery: every explicit path is under `C:\Projects`; prior managed state is moved to quarantine before replacement; repository files contain no credentials; installers run no AgentSys workflow.

## Git and merge

- Branch: `change/031-agent-tooling-bootstrap`
- Worktree: `.work/worktrees/031-agent-tooling-bootstrap`
- Commit: current branch HEAD (`feat(tools): bootstrap agentsys and agnix`).
- Pull request or merge: pending publication; merge is not authorized by this closeout.
- Cleanup: pending approved merge.

## Residual items

- Claude Code, OpenCode, and Codex executables were not found on the current process `PATH`. Their managed AgentSys profiles are installed and ready, but direct launch requires the corresponding host CLI installation or PATH configuration.
- The AgentSys marketplace attempted 25 entries; 21 produced valid Claude plugin packages. Four marketplace entries did not yield valid cached plugin packages in this run, while OpenCode and Codex still received 25 command/skill projections. This is upstream catalogue behavior and is recorded rather than hidden.
- Future kis-mcp integration should use the generic Tools command catalogue after change `029-tools-code-tooling` merges. It should enable commands through JSON and must not add command-specific Python code when an existing generic execution contract is sufficient.
- A separate agnix MCP slice may install or build the native `agnix-mcp` binary after its release artifact and supply-chain verification are explicitly designed.
