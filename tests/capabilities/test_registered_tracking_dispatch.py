from __future__ import annotations

import asyncio
from collections.abc import Mapping

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.capabilities import execution as execution_module
from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import capability_control_contribution

REFRESH = "kis_github_refresh_registered_default_branch"
SHA = "3333333333333333333333333333333333333333"


def runtime() -> CapabilityRuntimeState:
    contribution = capability_control_contribution()
    return CapabilityRuntimeState.build(
        CapabilityCatalogue((contribution,), ()),
        load_capability_settings(),
    )


def test_external_router_dispatches_registered_tracking_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def execute_tracking(
        name: str, arguments: Mapping[str, object]
    ) -> dict[str, object]:
        calls.append((name, dict(arguments)))
        return {"state": "refreshed"}

    monkeypatch.setattr(
        execution_module,
        "execute_registered_github_tracking_operation",
        execute_tracking,
    )
    router = CapabilityExecutionRouter(FastMCP("tracking-dispatch-test"), runtime())

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(
            router.execute_external(
                REFRESH,
                {
                    "project_id": "kis-mcp",
                    "expected_remote_default": SHA,
                    "approved": False,
                },
            )
        )

    result = asyncio.run(
        router.execute_external(
            REFRESH,
            {"project_id": "kis-mcp", "expected_remote_default": SHA, "approved": True},
        )
    )
    assert result == {"state": "refreshed"}
    assert calls == [
        (
            REFRESH,
            {
                "project_id": "kis-mcp",
                "expected_remote_default": SHA,
                "approved": True,
            },
        )
    ]
