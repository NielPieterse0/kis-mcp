# Closeout: MCP 2026 Workflow Prompts

## Implemented scope

- Added native thin MCP prompts for `start-change`, `resume-change`, `take-next-work`, and `explain-change`; each explicitly defers authority to Work Management and governed KIS operations.
- Added deterministic discovery ordering for tools, prompts, resources, and resource templates without enabling positive cache TTLs that could outlive dynamic catalogue/runtime identity changes.
- Evaluated `Mcp-Method` / `Mcp-Name` routing against the pinned FastMCP 4 / MCP 2026-07-28 runtime and rejected a duplicate KIS routing layer because the SDK already owns transport validation and KIS has no method/name-based multi-upstream dispatch requirement.

## Validation evidence

- Focused MCP 2026 suite: 11 tests passed (`tests/test_mcp2026_wire.py`, `tests/test_mcp2026_tasks.py`).
- Ruff on changed Python paths: passed.
- `scripts/change-workflow.ps1 check`: passed.
- Live candidate `WORK-589` on port `46047`: passed identity and governed scenario verification; candidate was then stopped after durable evidence.
- Canonical full repository verification remains provider-native GitHub Actions on the exact PR head per `AGENTS.md`; local full `verify.ps1` launch was not used as canonical merge evidence.
## Review

- Code-quality review: clean, zero findings.
- Architecture review: clean, zero findings after qualified fallback from one malformed provider response.
- API-contract review: no blocking findings; informational findings confirmed deterministic ordering and thin prompt boundaries.
- Safety/security review: clean, zero findings; HR-001/HR-002/HR-003 remain unchanged.

## Git and merge

- Branch: `change/635-mcp2026-workflow-prompts`
- Worktree: `.work/worktrees/635-mcp2026-workflow-prompts`
- Commit: pending pre-publication freeze.
- Pull request / exact-head Actions / merge: pending provider closeout.
- Cleanup: pending verified merge.

## Residual items

- Positive MCP list cache TTL remains intentionally disabled until the server can bind cache validity to changing catalogue/runtime fingerprints without stale discovery.
- No custom `Mcp-Method` / `Mcp-Name` router is warranted for the current gateway composition; the pinned SDK transport remains the protocol owner.
