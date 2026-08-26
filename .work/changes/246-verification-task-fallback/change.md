# Change: Verification Task Fallback

- **Change ID**: `246-verification-task-fallback`
- **Risk Profile**: lean

## Outcome

Restore live repository verification execution by making run_verification execute synchronously instead of queueing into the non-consuming MCP Tasks worker.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- `run_verification` must not advertise MCP Tasks while the deployed worker path cannot consume queued work.
- Direct tool calls must continue to execute the existing verification service and preserve progress/error behavior.
- Other long-running tools keep their MCP Tasks configuration unchanged.
- Regression evidence must prove the verification tool is synchronous while the remaining selected long-running tools stay optional Tasks.

## Implementation and verification

- Implementation notes: Remove Tasks configuration only from `run_verification`; do not change verification execution semantics.
- Focused checks: Red/green regression proven; `tests/test_mcp2026_tasks.py` plus verification-tool tests pass 7/7.
- Review findings: Initial API-contract review requested explicit synchronous execution proof; added wire-level client regression. Re-review completed with zero findings.
- Residual risk: Background Tasks remain enabled for other long-running surfaces; their deployed worker lifecycle is outside this emergency fallback.
- Post-merge live finding: invalid project/path discovery errors escaped the tool boundary and FastMCP surfaced a misleading `super(type, obj)` class-identity failure. `run_verification` now translates `DiscoverError` into its stable typed ToolError envelope; regression coverage proves the original failure cannot recur at that boundary.
- Closeout state: Keep active until the follow-up commit is merged and live `kis-dev` proves both typed invalid-path handling and successful verification execution.
