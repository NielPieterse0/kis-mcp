from __future__ import annotations

import asyncio

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.capabilities import execution as execution_module
from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import capability_control_contribution


def runtime() -> CapabilityRuntimeState:
    contribution = capability_control_contribution()
    return CapabilityRuntimeState.build(
        CapabilityCatalogue((contribution,), ()),
        load_capability_settings(),
    )


def test_registered_acquisition_is_fixed_schema_approval_gated_virtual_operation() -> None:
    operation = next(
        item
        for item in capability_control_contribution().operations
        if item.name == "kis_acquire_registered_evidence"
    )
    assert operation.approval_required is True
    assert set(operation.tags) == {"registered-acquisition", "virtual"}
    assert set(operation.input_schema["properties"]) == {
        "project",
        "profile",
        "recipe",
        "recipe_hash",
        "parameters",
        "approved",
    }
    assert set(operation.input_schema["required"]) == set(operation.input_schema["properties"])
    assert "url" not in operation.input_schema["properties"]
    assert "target" not in operation.input_schema["properties"]
    parameter_value_schema = operation.input_schema["properties"]["parameters"]["additionalProperties"]
    assert parameter_value_schema["oneOf"][0]["type"] == ["string", "number", "boolean"]
    assert parameter_value_schema["oneOf"][1]["type"] == "array"
    assert parameter_value_schema["oneOf"][1]["minItems"] == 1
    assert parameter_value_schema["oneOf"][1]["maxItems"] == 64


def test_registered_acquisition_dispatch_requires_schema_bound_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def execute(arguments: dict[str, object]) -> dict[str, object]:
        calls.append(dict(arguments))
        return {"state": "success", "provider": "import-isolate"}

    monkeypatch.setattr(
        execution_module,
        "execute_registered_acquisition_operation",
        execute,
        raising=False,
    )
    router = CapabilityExecutionRouter(FastMCP("acquisition-dispatch-test"), runtime())
    arguments = {
        "project": "commodity",
        "profile": "firecrawl-web",
        "recipe": "commodity-news-search",
        "recipe_hash": "sha256:" + "0" * 64,
        "parameters": {"query": "natural gas news"},
        "approved": True,
    }

    denied = dict(arguments)
    denied["approved"] = False
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(router.execute_external("kis_acquire_registered_evidence", denied))

    result = asyncio.run(router.execute_external("kis_acquire_registered_evidence", arguments))
    assert result == {"state": "success", "provider": "import-isolate"}
    assert calls == [arguments]


def test_unrelated_virtual_family_cannot_gain_schema_bound_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contribution = capability_control_contribution()
    acquisition = next(item for item in contribution.operations if item.name == "kis_acquire_registered_evidence")
    from dataclasses import replace

    rogue = replace(
        acquisition,
        operation_id="capability-control.rogue",
        name="rogue_virtual",
        tags=("rogue-family", "virtual"),
    )
    rogue_contribution = replace(contribution, operations=(rogue,))
    state = CapabilityRuntimeState.build(
        CapabilityCatalogue((rogue_contribution,), ()),
        load_capability_settings(),
    )
    router = CapabilityExecutionRouter(FastMCP("rogue-virtual-test"), state)
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(router.execute_external("rogue_virtual", {"approved": True}))
