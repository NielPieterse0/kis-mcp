# Change: Gateway Event Loop Safe

- **Change ID**: `243-gateway-event-loop-safe`
- **Risk Profile**: lean

## Outcome

Make synchronous gateway composition deterministic and safe when invoked from an already-running event loop without changing operator startup behavior or provider/tool discovery semantics.

## Scope and acceptance

- Keep `compose_gateway(...)` synchronous and preserve the existing CLI/startup contract.
- Permit synchronous composition when the caller already owns a running asyncio event loop.
- Keep provider/tool discovery results equivalent to the current synchronous path.
- Do not leak Python's generic `asyncio.run() cannot be called from a running event loop` failure.
- Use only the standard library; add no runtime dependency for loop bridging.
- Add a regression that fails on the current implementation when composition is invoked inside a running loop.

## Implementation and verification

- Plan: add the running-loop regression, replace nested `asyncio.run` with the smallest synchronous bridge, then review and verify the bounded gateway paths.
- Implementation notes: `_run_awaitable_sync` keeps the normal caller-thread `asyncio.run` path and uses one helper thread only when the caller already owns a running loop. The helper creates the awaitable in that thread and propagates the caller `contextvars` context.
- Focused checks: `uv run --frozen python -m pytest tests/capabilities/test_gateway_composition.py tests/gateway/test_project_context.py -q` passes 10/10; `pwsh -File scripts/change-workflow.ps1 check` passes before the context-propagation follow-up and will be rerun on the final diff.
- Review findings: architecture review identified missing context propagation across the helper-thread boundary; fixed with `copy_context()` and covered by regression. The follow-up automated architecture route failed to return evidence, so final architecture review is exact-diff/manual plus focused production-path tests.
- Residual risk: synchronous composition necessarily blocks its caller while discovery completes; when invoked under a running loop, discovery executes on a fresh helper-thread event loop. Current gateway/provider composition tests exercise the production provider path and remain green.
- Closeout state: implementation complete; final governance check and commit pending.
