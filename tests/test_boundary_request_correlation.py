from __future__ import annotations

import asyncio

from fastmcp import Client, FastMCP

from kis_mcp.middleware import BoundaryObservabilityMiddleware
from kis_mcp.runtime_observability import RuntimeObservability, current_request_id


def test_boundary_request_id_is_visible_only_during_dispatch() -> None:
    server = FastMCP("boundary-correlation-test")
    registry = RuntimeObservability(max_boundary_requests=10)

    @server.tool
    def correlation_probe() -> str:
        return current_request_id() or "missing"

    server.add_middleware(BoundaryObservabilityMiddleware(registry))

    async def run() -> str:
        async with Client(server) as client:
            result = await client.call_tool("correlation_probe", {})
            return result.content[0].text

    observed = asyncio.run(run())
    calls = [
        item for item in registry.snapshot().recent_boundary_requests
        if item.method == "tools/call" and item.tool_name == "correlation_probe"
    ]
    assert len(calls) == 1
    assert observed == calls[0].request_id
    assert current_request_id() is None
