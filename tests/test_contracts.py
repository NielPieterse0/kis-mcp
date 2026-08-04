from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

from fastmcp import Client, FastMCP

from kis_mcp.contracts import (
    PolicyEvaluator,
    ProviderCapabilities,
    ProviderEffectResolver,
    QuarantinePort,
)
from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.models import DecisionKind, InvocationEffects, PolicyDecision
from kis_mcp.policy import ThreeRulePolicy
from kis_mcp.quarantine import QuarantineRecord, QuarantineService


class FakeResolver:
    capabilities = ProviderCapabilities(
        network_only_tools=frozenset(),
        direct_delete_tools=frozenset(),
        unexposed_tool_arguments={},
        unexposed_config_keys=frozenset(),
        configuration_tool_name=None,
    )

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects:
        return InvocationEffects()


class FakePolicy:
    def evaluate(self, effects: InvocationEffects) -> PolicyDecision:
        return PolicyDecision(
            kind=DecisionKind.ALLOW,
            code="ALLOW",
            message="allowed by fake",
        )


class FakeQuarantine:
    def quarantine(self, path: str) -> QuarantineRecord:
        return QuarantineRecord(
            operation_id="20260804T000000000000Z-000000000000",
            original_path=path,
            payload_path=path + ".quarantine",
            item_type="file",
            quarantined_at="2026-08-04T00:00:00+00:00",
        )

    def restore(self, operation_id: str) -> QuarantineRecord:
        return self.quarantine(operation_id)

    def list_records(self, *, limit: int = 50) -> list[QuarantineRecord]:
        return []


def test_production_components_satisfy_structural_contracts(tmp_path: Any) -> None:
    resolver = DesktopCommanderEffectResolver(
        project_boundary=r"C:\Projects",
        provider_state_file=r"C:\Projects\.kis-mcp\provider.json",
    )
    policy = ThreeRulePolicy(
        project_boundary=r"C:\Projects",
        quarantine_root=r"C:\Projects\.kis-mcp\quarantine",
    )
    project = tmp_path / "project"
    quarantine = project / ".state" / "quarantine"
    project.mkdir()
    service = QuarantineService(
        project_boundary=str(project),
        quarantine_root=str(quarantine),
    )

    assert isinstance(resolver, ProviderEffectResolver)
    assert isinstance(policy, PolicyEvaluator)
    assert isinstance(service, QuarantinePort)


def test_middleware_accepts_structural_fakes() -> None:
    from kis_mcp.middleware import ThreeRuleMiddleware

    server = FastMCP("contract-fake-test")
    calls: list[str] = []

    @server.tool
    def ordinary_local_tool() -> str:
        calls.append("called")
        return "ok"

    def quarantine_paths(_paths: Sequence[str]) -> list[dict[str, Any]]:
        return []

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=FakeResolver(),
            policy=FakePolicy(),
            quarantine_paths=quarantine_paths,
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            result = await client.call_tool("ordinary_local_tool", {})
            assert "ok" in result.content[0].text

    asyncio.run(run())
    assert calls == ["called"]


def test_resolver_contract_is_provider_neutral_and_deterministic() -> None:
    resolver = DesktopCommanderEffectResolver(
        project_boundary=r"C:\Projects",
        provider_state_file=r"C:\Projects\.kis-mcp\provider.json",
    )

    first = resolver.resolve("unknown_tool", {"url": "https://example.com"})
    second = resolver.resolve("unknown_tool", {"url": "https://example.com"})

    assert isinstance(first, InvocationEffects)
    assert first == second == InvocationEffects()


def test_policy_contract_is_closed_and_deterministic() -> None:
    policy = ThreeRulePolicy(
        project_boundary=r"C:\Projects",
        quarantine_root=r"C:\Projects\.kis-mcp\quarantine",
    )
    effects = InvocationEffects()

    first = policy.evaluate(effects)
    second = policy.evaluate(effects)

    assert isinstance(first, PolicyDecision)
    assert first == second
    assert first.kind in set(DecisionKind)
