# 119 Commissioning Runtime Fixes Implementation Plan

**Goal:** Repair the two reproduced runtime blockers without widening public contracts or repeating canonical verification.

**Architecture:** Keep fixes at the adapter boundaries that dropped required metadata/methods. `GitChangeReader` will expose the same read-only `authority` and `settings` properties already provided by `GitReader`; Serena's shared wrapper will delegate the exact MCP proxy method FastMCP 3.4.4 calls.

**Tech stack:** Python 3.11+, FastMCP 3.4.4, pytest, PowerShell repository workflow.

## Global constraints
- Preserve HR-001/HR-002/HR-003 unchanged.
- No dependency/version/schema changes.
- TDD: observe focused RED before production edit, then GREEN.
- Run focused/affected verification locally; exact-head PR CI owns the single canonical full pass.
- Parent #156 must remain open/non-Done.

### Task 1: Exact-target analyzer capability
**Files:** `tests/workflows/verification/test_verification_platform.py`, `src/kis_mcp/discover/git_change_reader.py`.
- [ ] Add a regression asserting `_build_change_analyzer(...).analyze(...)` is actually available for an exact commit, not merely that the reader type is `GitChangeReader`.
- [ ] Run that test and confirm the current failure is the analyzer-unavailable defect.
- [ ] Add read-only `authority` and `settings` properties to `GitChangeReader`, matching `GitReader`.
- [ ] Re-run the focused verification-platform test and relevant change-target tests.

### Task 2: Serena FastMCP proxy contract
**Files:** `tests/providers/test_context7_serena_providers.py`, `src/kis_mcp/providers/serena/adapter.py`.
- [ ] Add a regression proving `_SharedProviderClient.call_tool_mcp(...)` delegates all arguments to the inner client and returns its result.
- [ ] Run the test and confirm failure is the missing method.
- [ ] Implement only the missing delegation method; retain existing context-depth/lifecycle behavior.
- [ ] Re-run Serena provider and memory-safety focused tests.

### Task 3: Review, publication, and commissioning
- [ ] Run Ruff on changed Python files, change scope check, and `git diff --check`.
- [ ] Review exact diff for lifecycle, error, security, and scope regressions.
- [ ] Commit the source tree, prepare exact reviewable PR, and rely on canonical GitHub Actions for the one full repository verification.
- [ ] Merge exact approved head, clean verified remote branch/worktree where current guards permit, and restart `kis-op`/`kis-dev` on landed main.
- [ ] Re-run clean exact-commit selection plus Serena semantic read; update/close #161 only if all commissioning checks pass. Keep #156 open for operator sign-off.