from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from kis_mcp.capabilities import execution as execution_module
from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.contracts import (
    CapabilityContribution,
    CapabilityDomain,
    ExposureMode,
    ExposurePolicy,
    OperationDescriptor,
    OperationEffect,
    ReadinessSnapshot,
    ReadinessState,
)
from kis_mcp.capabilities.execution import CapabilityExecutionRouter
from kis_mcp.capabilities.exposure import ExposureMiddleware, ExposurePlanner
from kis_mcp.capabilities.normalization import default_quality
from kis_mcp.capabilities.result_resources import ResultResourceStore
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.surface import capability_control_contribution
from kis_mcp.capabilities.tools import register_capability_tools


def contribution(
    contribution_id: str,
    operation_name: str,
    effect: OperationEffect,
    *,
    readiness: ReadinessState = ReadinessState.READY,
    direct: bool = False,
    approval_required: bool = False,
) -> CapabilityContribution:
    operation = OperationDescriptor(
        operation_id=f"{contribution_id}.{operation_name}",
        name=operation_name,
        description=f"Run {operation_name}.",
        capabilities=(f"{contribution_id}.operate",),
        effects=(effect,),
        dependencies=(),
        exposure=ExposurePolicy(
            mode=ExposureMode.DIRECT if direct else ExposureMode.DISCOVERABLE,
            priority=90,
        ),
        quality=default_quality(),
        approval_required=approval_required,
    )
    return CapabilityContribution(
        contribution_id=contribution_id,
        domain=CapabilityDomain.TOOL,
        category="test-tool",
        capabilities=(f"{contribution_id}.operate",),
        operations=(operation,),
        dependencies=(),
        effects=(effect,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id=contribution_id,
            state=readiness,
            summary=readiness.value,
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )


def state(*contributions: CapabilityContribution) -> CapabilityRuntimeState:
    settings = load_capability_settings()
    return CapabilityRuntimeState.build(
        CapabilityCatalogue(contributions, ()),
        settings,
    )


def test_exposure_planner_filters_unavailable_and_long_tail() -> None:
    runtime = state(
        contribution("core", "read_file", OperationEffect.READ_ONLY, direct=True),
        contribution("long-tail", "rare_tool", OperationEffect.READ_ONLY),
        contribution(
            "offline",
            "inspect_project",
            OperationEffect.READ_ONLY,
            readiness=ReadinessState.UNAVAILABLE,
            direct=True,
        ),
    )

    plan = ExposurePlanner(runtime).plan()

    assert "read_file" in plan.direct_operations
    assert "rare_tool" not in plan.direct_operations
    assert "inspect_project" not in plan.direct_operations
    assert "rare_tool" in plan.discoverable_operations
    assert "inspect_project" in plan.status_only_operations


def test_explicit_valid_operation_can_be_exposed_without_overriding_readiness() -> None:
    runtime = state(
        contribution("ready", "rare_tool", OperationEffect.READ_ONLY),
        contribution(
            "offline",
            "offline_tool",
            OperationEffect.READ_ONLY,
            readiness=ReadinessState.UNAVAILABLE,
        ),
    )

    plan = ExposurePlanner(runtime).plan(explicit_operations={"rare_tool", "offline_tool"})

    assert "rare_tool" in plan.direct_operations
    assert "offline_tool" not in plan.direct_operations


def test_exposure_middleware_hides_long_tail_but_does_not_disable_calling() -> None:
    server = FastMCP("exposure-test")

    @server.tool
    def visible_tool() -> str:
        return "visible"

    @server.tool
    def hidden_tool() -> str:
        return "hidden"

    server.add_middleware(ExposureMiddleware({"visible_tool"}))

    async def run() -> tuple[set[str], str]:
        async with Client(server) as client:
            names = {item.name for item in await client.list_tools()}
            result = await client.call_tool("hidden_tool", {})
            return names, result.content[0].text

    names, result = asyncio.run(run())
    assert names == {"visible_tool"}
    assert result == "hidden"


def test_execution_router_preserves_original_schema_and_effect_boundary() -> None:
    server = FastMCP("execution-test")

    @server.tool
    def hidden_read(value: int) -> int:
        return value * 2

    runtime = state(contribution("hidden", "hidden_read", OperationEffect.READ_ONLY))
    router = CapabilityExecutionRouter(server, runtime)

    result = asyncio.run(router.execute_read("hidden_read", {"value": 4}))
    assert result.structured_content == {"result": 8}

    with pytest.raises(Exception, match="validation"):
        asyncio.run(router.execute_read("hidden_read", {"value": "bad"}))
    with pytest.raises(ToolError, match="EFFECT_MISMATCH"):
        asyncio.run(router.execute_change("hidden_read", {"value": 4}))


def test_generic_execution_budgets_oversized_provider_result() -> None:
    server = FastMCP("execution-budget-test")

    @server.tool
    def huge_external() -> dict[str, object]:
        return {
            "workflow_runs": [
                {
                    "id": index,
                    "repository": {
                        "name": "kis-mcp",
                        "description": "x" * 12_000,
                    },
                }
                for index in range(20)
            ]
        }

    runtime = state(contribution("github-like", "huge_external", OperationEffect.EXTERNAL))
    register_capability_tools(server, runtime)

    result = asyncio.run(
        server.call_tool(
            "execute_external_action",
            {"operation": "huge_external", "arguments": {}},
        )
    )
    payload = result.structured_content

    assert payload is not None
    assert not any(getattr(item, "type", None) == "resource_link" for item in result.content)
    assert payload["truncated"] is True
    assert payload["reason"] == "RESULT_BUDGET_EXCEEDED"
    assert payload["operation"] == "huge_external"
    assert payload["original_chars"] > payload["max_chars"]
    assert payload["preview"]["workflow_runs"]["omitted_items"] == 10
    assert len(json.dumps(payload, ensure_ascii=False)) < payload["max_chars"]


@pytest.mark.parametrize(
    ("control_tool", "effect"),
    [
        ("execute_read_action", OperationEffect.READ_ONLY),
        ("execute_change_action", OperationEffect.LOCAL_CHANGE),
        ("execute_external_action", OperationEffect.EXTERNAL),
    ],
)
def test_resource_persistence_failure_preserves_budget_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    control_tool: str,
    effect: OperationEffect,
) -> None:
    server = FastMCP("execution-resource-fallback-test")

    @server.tool
    def huge_operation() -> dict[str, object]:
        return {"items": [{"id": index, "payload": "x" * 12_000} for index in range(20)]}

    runtime = state(contribution("huge", "huge_operation", effect))
    register_capability_tools(server, runtime, state_root=tmp_path)
    monkeypatch.setattr(
        ResultResourceStore,
        "put",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    result = asyncio.run(
        server.call_tool(
            control_tool,
            {"operation": "huge_operation", "arguments": {}},
        )
    )
    payload = result.structured_content

    assert payload is not None
    assert set(payload) == {
        "truncated",
        "reason",
        "operation",
        "original_chars",
        "max_chars",
        "preview",
    }
    assert payload["reason"] == "RESULT_BUDGET_EXCEEDED"
    assert not any(getattr(item, "type", None) == "resource_link" for item in result.content)


def test_oversized_dispatch_result_exposes_exact_resource_link(tmp_path: Path) -> None:
    server = FastMCP("execution-resource-link-test")

    @server.tool
    def huge_read() -> dict[str, object]:
        return {"items": [{"id": index, "payload": "x" * 12_000} for index in range(20)]}

    runtime = state(contribution("huge", "huge_read", OperationEffect.READ_ONLY))
    register_capability_tools(server, runtime, state_root=tmp_path)

    async def run() -> tuple[dict[str, object], str]:
        async with Client(server) as client:
            result = await client.call_tool(
                "execute_read_action",
                {"operation": "huge_read", "arguments": {}},
            )
            payload = result.structured_content
            assert payload is not None
            links = [item for item in result.content if getattr(item, "type", None) == "resource_link"]
            assert len(links) == 1
            resource = await client.read_resource(str(links[0].uri))
            text = resource[0].text
            assert text is not None
            return payload, text

    payload, text = asyncio.run(run())
    restored = json.loads(text)
    assert payload["resource_uri"].startswith("kis-result:///")
    assert payload["resource_sha256"]
    assert payload["resource_uri"].rsplit("/", 1)[-1] != payload["resource_sha256"]
    assert restored["items"][19]["id"] == 19
    assert restored["items"][19]["payload"] == "x" * 12_000


def test_result_resource_store_accepts_exact_byte_limit(tmp_path: Path) -> None:
    budget = load_capability_settings().result_budget
    sample = {"value": "abc"}
    exact_bytes = len(ResultResourceStore.serialize(sample))
    store = ResultResourceStore(
        tmp_path,
        replace(budget, resource_max_bytes=exact_bytes),
    )

    stored = store.put("example_read", sample)

    assert stored is not None
    assert store.read(stored.grant_id) == ResultResourceStore.serialize(sample)
    assert stored.payload_sha256 == hashlib.sha256(ResultResourceStore.serialize(sample)).hexdigest()


def test_result_resource_grants_are_opaque_per_dispatch(tmp_path: Path) -> None:
    budget = load_capability_settings().result_budget
    store = ResultResourceStore(tmp_path, budget)
    sample = {"value": "same"}

    first = store.put("first_read", sample)
    second = store.put("second_read", sample)

    assert first is not None and second is not None
    assert first.grant_id != second.grant_id
    assert first.payload_sha256 == second.payload_sha256
    assert first.origin_operation == "first_read"
    assert second.origin_operation == "second_read"


def test_result_resource_store_expires_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = replace(load_capability_settings().result_budget, resource_ttl_seconds=60)
    store = ResultResourceStore(tmp_path, budget)
    monkeypatch.setattr("kis_mcp.capabilities.result_resources.time.time", lambda: 1_000)
    stored = store.put("example_read", {"value": "kept"})
    assert stored is not None
    resource_path = tmp_path / "capability-results" / f"{stored.grant_id}.json"
    monkeypatch.setattr("kis_mcp.capabilities.result_resources.time.time", lambda: 1_061)

    with pytest.raises(RuntimeError, match="RESULT_RESOURCE_EXPIRED_OR_UNKNOWN"):
        store.read(stored.grant_id)
    assert resource_path.is_file()


def test_expired_result_resources_use_recoverable_quarantine_on_next_put(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget = replace(load_capability_settings().result_budget, resource_ttl_seconds=60)
    quarantine_root = tmp_path / "quarantine"
    quarantine_root.mkdir()
    moved: list[Path] = []

    def quarantine_expired(path: str) -> None:
        source = Path(path)
        target = quarantine_root / source.name
        source.replace(target)
        moved.append(target)

    store = ResultResourceStore(
        tmp_path,
        budget,
        quarantine_expired=quarantine_expired,
    )
    monkeypatch.setattr("kis_mcp.capabilities.result_resources.time.time", lambda: 1_000)
    expired = store.put("old_read", {"value": "old"})
    assert expired is not None
    monkeypatch.setattr("kis_mcp.capabilities.result_resources.time.time", lambda: 1_061)

    current = store.put("new_read", {"value": "new"})

    assert current is not None
    assert moved
    assert not (tmp_path / "capability-results" / f"{expired.grant_id}.json").exists()
    assert moved[0].is_file()


def test_generic_execution_preserves_small_provider_result() -> None:
    server = FastMCP("execution-budget-small-test")

    @server.tool
    def small_external() -> dict[str, object]:
        return {"items": [{"id": 1, "name": "ok"}], "count": 1}

    runtime = state(contribution("github-like", "small_external", OperationEffect.EXTERNAL))
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "execute_external_action",
            {"operation": "small_external", "arguments": {}},
        )
    ).structured_content

    assert payload == {"items": [{"id": 1, "name": "ok"}], "count": 1}


def test_execution_router_never_bypasses_approval_or_readiness() -> None:
    server = FastMCP("execution-gates-test")

    @server.tool
    def merge_tool() -> str:
        return "merged"

    approval_state = state(
        contribution(
            "approval",
            "merge_tool",
            OperationEffect.EXTERNAL,
            approval_required=True,
        )
    )
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(
            CapabilityExecutionRouter(server, approval_state).execute_external(
                "merge_tool", {}
            )
        )

    unavailable_state = state(
        contribution(
            "unavailable",
            "merge_tool",
            OperationEffect.EXTERNAL,
            readiness=ReadinessState.UNAVAILABLE,
        )
    )
    with pytest.raises(ToolError, match="OPERATION_INELIGIBLE"):
        asyncio.run(
            CapabilityExecutionRouter(server, unavailable_state).execute_external(
                "merge_tool", {}
            )
        )


def test_nonvirtual_approved_field_cannot_bypass_generic_approval_gate() -> None:
    server = FastMCP("approval-hardening-test")
    operation = OperationDescriptor(
        operation_id="provider.generic-approved",
        name="generic_approved_external",
        description="Generic approval-gated external operation.",
        capabilities=("generic.approved",),
        effects=(OperationEffect.EXTERNAL,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
        approval_required=True,
        input_schema={
            "type": "object",
            "properties": {"approved": {"type": "boolean"}},
            "required": ["approved"],
        },
    )
    generic = CapabilityContribution(
        contribution_id="provider.generic",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=("generic.approved",),
        operations=(operation,),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="provider.generic",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(
            CapabilityExecutionRouter(server, state(generic)).execute_external(
                "generic_approved_external",
                {"approved": True},
            )
        )


def test_schema_bound_approval_dispatches_only_registered_virtual_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = FastMCP("virtual-external-test")
    operation = OperationDescriptor(
        operation_id="projects.kis-github-publish",
        name="kis_github_publish_registered_commit",
        description="Publish an exact registered commit.",
        capabilities=("operation.kis_github_publish_registered_commit",),
        effects=(OperationEffect.EXTERNAL,),
        dependencies=(),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
        approval_required=True,
        tags=("registered-github", "virtual"),
        input_schema={
            "type": "object",
            "properties": {"approved": {"type": "boolean"}},
            "required": ["approved"],
        },
    )
    virtual = CapabilityContribution(
        contribution_id="projects",
        domain=CapabilityDomain.TOOL,
        category="project-context",
        capabilities=("operation.kis_github_publish_registered_commit",),
        operations=(operation,),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="projects",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )
    calls: list[tuple[str, dict[str, object]]] = []

    def execute_virtual(name: str, arguments: Mapping[str, object]) -> dict[str, object]:
        calls.append((name, dict(arguments)))
        return {"state": "published"}

    monkeypatch.setattr(
        execution_module,
        "execute_runtime_registered_github_operation",
        execute_virtual,
    )
    router = CapabilityExecutionRouter(server, state(virtual))

    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        asyncio.run(
            router.execute_external(
                "kis_github_publish_registered_commit",
                {"approved": False},
            )
        )

    result = asyncio.run(
        router.execute_external(
            "kis_github_publish_registered_commit",
            {"approved": True},
        )
    )
    assert result == {"state": "published"}
    assert calls == [
        ("kis_github_publish_registered_commit", {"approved": True})
    ]


def test_all_registered_virtual_mutations_use_schema_bound_supervised_approval() -> None:
    approval_operations = {
        operation.name: operation
        for operation in capability_control_contribution().operations
        if operation.approval_required
    }
    assert set(approval_operations) == {
        "kis_github_publish_registered_commit",
        "kis_github_reconcile_registered_commit",
        "kis_github_create_registered_pull_request",
        "kis_github_configure_registered_repository",
        "kis_github_commission_registered_project_schema",
        "kis_github_merge_registered_pull_request",
        "kis_github_refresh_registered_default_branch",
        "kis_acquire_registered_evidence",
        "kis_github_merge_queue_enqueue",
        "kis_github_merge_queue_reconcile",
        "kis_github_merge_queue_dequeue",
        "kis_github_merge_queue_land",
    }
    for operation in approval_operations.values():
        approved_schema = operation.input_schema["properties"]["approved"]
        assert approved_schema == {"type": "boolean"}
        assert "approved" in operation.input_schema["required"]
        assert execution_module._registered_virtual_approval(
            operation, {"approved": True}
        ) is True
        assert execution_module._registered_virtual_approval(
            operation, {"approved": False}
        ) is False


def test_execution_router_rejects_capability_control_recursion() -> None:
    server = FastMCP("execution-recursion-test")
    runtime = state(capability_control_contribution())
    router = CapabilityExecutionRouter(server, runtime)

    with pytest.raises(ToolError, match="DISPATCH_RECURSION_BLOCKED"):
        asyncio.run(
            router.execute_read(
                "execute_read_action",
                {"operation": "execute_read_action", "arguments": {}},
            )
        )


def test_runtime_capabilities_exclude_contributions_without_registered_operations() -> None:
    base = contribution("unregistered", "missing_tool", OperationEffect.READ_ONLY)
    from dataclasses import replace

    disabled_operation = replace(base.operations[0], enabled=False)
    unavailable_operation_contribution = replace(
        base, operations=(disabled_operation,)
    )
    skill_like = CapabilityContribution(
        contribution_id="skill-like",
        domain=CapabilityDomain.SKILL,
        category="analysis",
        capabilities=("analysis.skill",),
        operations=(),
        dependencies=(),
        effects=(OperationEffect.READ_ONLY,),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="skill-like",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )

    runtime = state(unavailable_operation_contribution, skill_like)

    assert "unregistered.operate" not in runtime.available_capabilities
    assert "analysis.skill" in runtime.available_capabilities


def test_capability_search_reports_per_category_truncation() -> None:
    def skill_like(contribution_id: str) -> CapabilityContribution:
        return CapabilityContribution(
            contribution_id=contribution_id,
            domain=CapabilityDomain.SKILL,
            category="alpha-analysis",
            capabilities=(f"{contribution_id}.alpha",),
            operations=(),
            dependencies=(),
            effects=(OperationEffect.READ_ONLY,),
            readiness_probe=lambda: ReadinessSnapshot(
                contribution_id=contribution_id,
                state=ReadinessState.READY,
                summary="ready",
            ),
            exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
            quality=default_quality(),
        )

    runtime = state(skill_like("alpha-one"), skill_like("alpha-two"))
    server = FastMCP("search-truncation-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool("search_capabilities", {"query": "alpha", "limit": 1})
    ).structured_content

    assert payload is not None
    assert len(payload["contributions"]) == 1
    assert payload["truncated"] is True


def test_describe_exact_operation_is_bounded_and_includes_invocation_schema() -> None:
    provider = CapabilityContribution(
        contribution_id="provider.github-mcp",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=(
            "operation.github_create_pull_request",
            "operation.github_get_gist",
            "repository.git",
        ),
        operations=(
            OperationDescriptor(
                operation_id="runtime.github_create_pull_request",
                name="github_create_pull_request",
                description="Create a pull request.",
                capabilities=("operation.github_create_pull_request", "repository.git"),
                effects=(OperationEffect.EXTERNAL,),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
                input_schema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"],
                },
            ),
            OperationDescriptor(
                operation_id="runtime.github_get_gist",
                name="github_get_gist",
                description="Read a gist.",
                capabilities=("operation.github_get_gist", "repository.git"),
                effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
        ),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="provider.github-mcp",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )
    runtime = state(provider)
    server = FastMCP("describe-exact-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "describe_capability",
            {"capability_id": "operation.github_create_pull_request"},
        )
    ).structured_content

    assert payload is not None
    assert payload["contributions"] == []
    assert [item["name"] for item in payload["operations"]] == [
        "github_create_pull_request"
    ]
    assert payload["operations"][0]["input_schema"]["required"] == ["title"]
    assert payload["operations"][0]["execution_surface"] == "execute_external_action"


def test_capability_search_ranks_exact_operation_before_generic_git_matches() -> None:
    provider = CapabilityContribution(
        contribution_id="provider.github-mcp",
        domain=CapabilityDomain.PROVIDER,
        category="connector",
        capabilities=("operation.github_merge_pull_request", "repository.git"),
        operations=(
            OperationDescriptor(
                operation_id="runtime.github_get_gist",
                name="github_get_gist",
                description="Read a gist.",
                capabilities=("operation.github_get_gist", "repository.git"),
                effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
            OperationDescriptor(
                operation_id="runtime.github_merge_pull_request",
                name="github_merge_pull_request",
                description="Merge a pull request.",
                capabilities=("operation.github_merge_pull_request", "repository.git"),
                effects=(OperationEffect.EXTERNAL,),
                dependencies=(),
                exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
                quality=default_quality(),
            ),
        ),
        dependencies=(),
        effects=(OperationEffect.EXTERNAL, OperationEffect.READ_ONLY),
        readiness_probe=lambda: ReadinessSnapshot(
            contribution_id="provider.github-mcp",
            state=ReadinessState.READY,
            summary="ready",
        ),
        exposure=ExposurePolicy(mode=ExposureMode.DISCOVERABLE),
        quality=default_quality(),
    )
    runtime = state(provider)
    server = FastMCP("search-ranking-test")
    register_capability_tools(server, runtime)

    payload = asyncio.run(
        server.call_tool(
            "search_capabilities",
            {"query": "github_merge_pull_request git", "limit": 10},
        )
    ).structured_content

    assert payload is not None
    assert payload["operations"][0]["operation_name"] == "github_merge_pull_request"
    assert payload["operations"][0]["match_score"] > payload["operations"][1]["match_score"]
