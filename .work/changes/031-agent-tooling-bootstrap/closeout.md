# Closeout: Agent Tooling Bootstrap

## Implemented scope

- Added independent, exact-version installers for AgentSys `6.0.1` and agnix `0.45.0`.
- Installed AgentSys at `C:\Projects\.kis-mcp\tools\agentsys\6.0.1` and agnix at `C:\Projects\.kis-mcp\tools\agnix\0.45.0`.
- Processed all 25 upstream AgentSys catalogue entries; the commissioned state contains 21 valid Claude plugin packages, 25 OpenCode commands, 35 OpenCode agents, 39 OpenCode skills, and 25 Codex skills.
- Added staged package/profile validation, absolute-reference relocation, exact command-catalogue verification, reparse-ancestor rejection, and recoverable activation rollback before any live state is replaced.
- Added a managed host launcher for Claude Code, OpenCode, and Codex.
- Added strict JSON settings and schemas with default-deny future kis-mcp command exposure.
- Added bootstrap tests and operational documentation without modifying the active Tools module.

## Validation evidence

- Focused checks: `C:\Projects\.kis-mcp\python-env\Scripts\python.exe -m pytest tests\bootstrap -q` — 5 passed.
- PowerShell syntax parsing: both installers and the managed launcher passed.
- Relocation smoke: plain and escaped staged-path references were rewritten to final managed paths; the recoverable sample was retained beneath quarantine.
- Reparse smoke: both installers and the host launcher rejected managed paths traversing a junction; test harnesses were retained beneath quarantine.
- Repository verification: `pwsh -NoProfile -File scripts\verify.ps1` — passed on current `main`; full pytest suite passed with 2 expected skips, 125 Python files compiled, and configuration, dependencies, line endings, change governance, and the three-rule policy all valid.
- Diff scope check: `pwsh -NoProfile -File scripts\change-workflow.ps1 check` — passed with only declared paths.
- Whitespace check: `git diff --check` — passed.

## Review

- Blocking findings: the submitted installers moved active state before package/profile verification, so a failed upgrade could replace a working installation with partial state. Staging AgentSys also revealed generated Codex skill files with absolute managed-home references that would break after activation unless relocated. Lexical boundary checks did not reject an existing junction ancestor that could redirect managed writes or host state.
- Resolutions: both installers now complete package and smoke validation in temporary roots before live mutation. AgentSys rewrites and verifies staged absolute references, requires generated OpenCode commands and Codex skills to exactly match the JSON catalogue, and activates package plus profile with rollback. agnix activates only its verified staged package with rollback. Both installers and the launcher reject reparse traversal, and the launcher retains both managed binary directories on `PATH`.
- Product findings retained: AgentSys is a distribution and workflow installer, not an MCP server. The agnix npm distribution provides the CLI but not the separate native `agnix-mcp` binary, so status remains truthfully `not_in_npm_distribution` and runtime mounting remains deferred.
- Security and recovery: every explicit path is under `C:\Projects`; repository files contain no credentials; no AgentSys workflow is executed during installation; previous and failed-new states remain recoverable under quarantine.

## Git and merge

- Branch: `change/031-agent-tooling-bootstrap`
- Worktree: `.work/worktrees/031-agent-tooling-bootstrap`
- Commit: reviewed branch head includes the bootstrap implementation, current `main`, and PR-completion remediation.
- Pull request: `#38` — `Bootstrap AgentSys and agnix tooling`.
- Merge: explicitly authorized by the operator after exact-head review and fresh verification.
- Cleanup: required after merge; the primary worktree must be clean before the workflow can remove the change worktree and branch.

## Residual items

- Claude Code, OpenCode, and Codex executables were not found on the current process `PATH`. Their managed AgentSys profiles are installed and ready, but direct launch requires the corresponding host CLI installation or PATH configuration.
- The AgentSys marketplace attempted 25 entries; 21 produced valid Claude plugin packages. Four marketplace entries did not yield valid cached plugin packages in this run, while OpenCode and Codex still received 25 command/skill projections. This is upstream catalogue behavior and is recorded rather than hidden.
- Future kis-mcp integration should consume the now-merged generic Tools framework through a separate bounded slice. It should enable commands through JSON and must not add command-specific Python code when an existing generic execution contract is sufficient.
- A separate agnix MCP slice may install or build the native `agnix-mcp` binary after its release artifact and supply-chain verification are explicitly designed.
