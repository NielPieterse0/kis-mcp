# Change Specification: Commissioning Runtime Fixes

- **Change ID**: `119-commissioning-runtime-fixes`
- **Status**: Approved for implementation by operator `go`
- **Risk Profile**: rigorous
- **Development level**: Complex — mounted provider/runtime integration

## Outcome
Fix the two post-merge runtime commissioning blockers for change 116, then prove the landed behavior with bounded live commissioning.

## Authority and scope
- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Work Management source: `SPEC-119` projected through issue #161, a sub-issue of #156.
- Only the four production/test paths in `scope.json` plus this change record are owned.
- No policy, public schema, dependency, provider version, or documentation architecture change.

## Requirements
- **REQ-001**: Exact commit/range verification selection MUST construct an analyzer-capable `GitChangeReader` and no longer fail because analysis is unavailable for that reader.
- **REQ-002**: Serena's shared persistent client wrapper MUST satisfy the FastMCP 3.4.4 proxy execution contract used by `ProxyTool.run`, including MCP tool-call delegation.
- **REQ-003**: Existing persistent-client nesting/lifecycle behavior MUST remain unchanged.
- **REQ-004**: Focused regression tests MUST fail before each production fix and pass after it.
- **REQ-005**: After merge/restart, bounded live smokes MUST prove clean-commit selection and Serena semantic execution; DBHub/DockerHub already-passed smokes need not be repeated unless runtime status regresses.

## Acceptance
1. Exact commit selection returns a verification selection on both restarted instances.
2. Mounted Serena semantic read succeeds on a registered Python project.
3. Focused tests, Ruff, scope check, diff check, and exact-head canonical CI pass.
4. Issue #161 records commissioning evidence; parent #156 remains open for operator verification.

## Risks and recovery
- Risk: changing shared provider proxy semantics could disturb lifecycle reuse. Mitigation: delegate only the missing FastMCP client method and retain nesting tests.
- Recovery: revert the bounded 119 merge; provider/runtime restarts return to the prior exact revision.

## Out of scope
- New provider features, FastMCP upgrade, policy changes, Work Management schema provisioning, and closing #156.