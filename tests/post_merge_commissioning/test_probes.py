from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from kis_mcp.commissioning.runner import FrozenCommissioningExecution
from kis_mcp.commissioning_runtime.probes import (
    execute_probe,
    runtime_generation_gate,
)


class FakeInvoker:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((operation, dict(arguments)))
        return self.responses[operation]


def _frozen(probe_id: str, *, refresh_rule: str = "restart") -> FrozenCommissioningExecution:
    return FrozenCommissioningExecution(
        repository="NielPieterse0/kis-mcp",
        commissioning_issue=460,
        source_issue=454,
        source_pr=456,
        merge_sha="a" * 40,
        change_id="229-commissioning-runner-evidence-lifecycle",
        surface_id="work-management",
        commissioning_key="commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":work-management",
        runtime_instance="kis-op",
        refresh_rule=refresh_rule,
        probe_id=probe_id,
        verification_procedure="procedure",
        expected_invariant="invariant",
        evidence_target="target",
        terminal_success_criterion="criterion",
    )

def test_refresh_none_skips_generation_reads() -> None:
    invoker = FakeInvoker({})
    gate = asyncio.run(
        runtime_generation_gate(
            _frozen("work-management-contract", refresh_rule="none"),
            invoker,
            project_id="kis-mcp",
            ancestor_check=lambda _root, _merge, _source: True,
        )
    )
    assert gate.ready is True
    assert gate.code == "refresh_not_required"
    assert invoker.calls == []


def test_restart_gate_accepts_current_runtime_generation() -> None:
    invoker = FakeInvoker(
        {
            "kis_health": {
                "ready": True,
                "runtime_instance": "operation",
                "source_revision": "b" * 40,
            },
            "kis_project_status": {
                "project": {"local_root": "C:\\Projects\\kis-mcp"}
            },
        }
    )
    seen: list[tuple[Path, str, str]] = []
    gate = asyncio.run(
        runtime_generation_gate(
            _frozen("work-management-contract"),
            invoker,
            project_id="kis-mcp",
            ancestor_check=lambda root, merge, source: seen.append((root, merge, source)) or True,
        )
    )
    assert gate.ready is True
    assert gate.code == "runtime_generation_current"
    assert seen[0][1:] == ("a" * 40, "b" * 40)

def test_restart_gate_blocks_stale_runtime_without_probe() -> None:
    invoker = FakeInvoker(
        {
            "kis_health": {
                "ready": True,
                "runtime_instance": "operation",
                "source_revision": "b" * 40,
            },
            "kis_project_status": {"project": {"local_root": "C:\\Projects\\kis-mcp"}},
        }
    )
    gate = asyncio.run(
        runtime_generation_gate(
            _frozen("gateway-health"),
            invoker,
            project_id="kis-mcp",
            ancestor_check=lambda _root, _merge, _source: False,
        )
    )
    assert gate.ready is False
    assert gate.code == "runtime_refresh_required"


def test_work_contract_probe_uses_fixed_operation_and_predicate() -> None:
    invoker = FakeInvoker(
        {
            "project_management_contract": {
                "schema_version": 1,
                "canonical_contracts": {
                    "work_lifecycle_operations": {
                        "verification_domains": [
                            {"id": "source_verification", "field": "Verification"},
                            {"id": "live_verification", "field": "Live Verification"},
                        ]
                    }
                },
            }
        }
    )
    outcome = asyncio.run(
        execute_probe(
            _frozen("work-management-contract", refresh_rule="none"),
            invoker,
            project_id="kis-mcp",
            execution_owner="codex",
        )
    )
    assert outcome.passed is True
    assert outcome.operation == "project_management_contract"
    assert invoker.calls == [("project_management_contract", {})]

def test_provider_probe_fails_closed_on_degraded_platform() -> None:
    invoker = FakeInvoker(
        {
            "kis_provider_status": {
                "platform_health": {
                    "state": "degraded",
                    "unavailable_count": 1,
                }
            }
        }
    )
    outcome = asyncio.run(
        execute_probe(
            _frozen("provider-status", refresh_rule="none"),
            invoker,
            project_id="kis-mcp",
            execution_owner="codex",
        )
    )
    assert outcome.passed is False
    assert outcome.code == "provider_platform_not_ready"


def test_coordinator_board_probe_requires_exact_active_claim() -> None:
    invoker = FakeInvoker(
        {
            "project_management_board_data": {
                "provenance": {"complete": True},
                "result": {
                    "complete": True,
                    "truncated": False,
                    "cards": [
                        {
                            "number": 460,
                            "work_state": "active",
                            "execution_owner": "codex",
                        }
                    ],
                },
            }
        }
    )
    outcome = asyncio.run(
        execute_probe(
            _frozen("coordinator-work-board", refresh_rule="none"),
            invoker,
            project_id="kis-mcp",
            execution_owner="codex",
        )
    )
    assert outcome.passed is True
    assert invoker.calls[0][1]["query"] == "460"
    assert invoker.calls[0][1]["owner"] == "codex"


def test_restart_gate_rejects_non_hex_runtime_revision_before_ancestry() -> None:
    invoker = FakeInvoker(
        {
            "kis_health": {
                "ready": True,
                "runtime_instance": "operation",
                "source_revision": "z" * 40,
            }
        }
    )
    ancestry_calls: list[tuple[Path, str, str]] = []
    gate = asyncio.run(
        runtime_generation_gate(
            _frozen("work-management-contract"),
            invoker,
            project_id="kis-mcp",
            ancestor_check=lambda root, merge, source: ancestry_calls.append(
                (root, merge, source)
            )
            or True,
        )
    )
    assert gate.ready is False
    assert gate.code == "runtime_source_revision_invalid"
    assert ancestry_calls == []
    assert invoker.calls == [("kis_health", {})]