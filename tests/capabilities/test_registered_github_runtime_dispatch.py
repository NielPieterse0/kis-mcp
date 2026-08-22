from __future__ import annotations

import asyncio
from collections.abc import Mapping

import pytest
from fastmcp import FastMCP

from kis_mcp.capabilities import execution as execution_module
from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import capability_control_contribution

MERGE = "kis_github_merge_registered_pull_request"
HEAD = "1" * 40


def runtime() -> CapabilityRuntimeState:
    contribution = capability_control_contribution()
    return CapabilityRuntimeState.build(
        CapabilityCatalogue((contribution,), ()),
        load_capability_settings(),
    )


def test_external_router_uses_runtime_registered_github_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def execute_runtime(
        name: str, arguments: Mapping[str, object]
    ) -> dict[str, object]:
        calls.append((name, dict(arguments)))
        return {"state": "merged"}

    monkeypatch.setattr(
        execution_module,
        "execute_runtime_registered_github_operation",
        execute_runtime,
    )
    router = CapabilityExecutionRouter(FastMCP("registered-github-runtime"), runtime())
    arguments = {
        "project_id": "kis-mcp",
        "pull_number": 7,
        "expected_head": HEAD,
        "merge_method": "merge",
        "approved": True,
    }
    result = asyncio.run(router.execute_external(MERGE, arguments))

    assert result == {"state": "merged"}
    assert calls == [(MERGE, arguments)]
