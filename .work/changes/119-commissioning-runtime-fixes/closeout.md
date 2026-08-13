# Closeout

## Status
Implementation complete locally; publication and post-merge commissioning pending.

## Root-cause evidence
- Verification: `GitChangeReader` retained `_authority`/`_settings` privately while `InspectChangeService` only consumes public `authority`/`settings`, leaving `_analysis_service=None`.
- Serena: FastMCP 3.4.4 `ProxyTool.run()` invokes `call_tool_mcp`; `_SharedProviderClient` did not delegate that method.

## TDD and verification
- RED: both focused regressions failed for the exact reproduced defects.
- GREEN: both regressions pass after the minimal fixes.
- Affected pytest: 23 passed + 7 passed = 30 passed.
- `change-workflow.ps1 check`: passed.
- `git diff --check`: passed.
- Ruff: unavailable in the locked environment and not declared as a repository dev dependency; no package installation was attempted.

## Review
- NVIDIA `super` review timed out; `nano` retry failed with `AGENT_BACKEND_FAILED:NvidiaNimError`.
- Direct repository Review Contract found no blocking correctness, lifecycle, security, or scope finding.

## Operator hold
Issue #156 / SPEC-116 must remain open and non-Done until the operator explicitly verifies close-out. Issue #161 is the commissioning gate for this repair.