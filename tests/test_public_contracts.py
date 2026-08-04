from __future__ import annotations

import inspect
from dataclasses import asdict
from typing import Any

from pydantic import TypeAdapter

from kis_mcp.models import (
    HealthResponse,
    PolicyRuleResponse,
    QuarantineListResponse,
    QuarantineResponse,
)
from kis_mcp.quarantine import QuarantineRecord
from kis_mcp.server import _quarantine_response, build_server


def test_quarantine_response_is_explicit_and_versioned() -> None:
    internal = QuarantineRecord(
        schema_version=2,
        operation_id="20260804T000000000000Z-000000000000",
        original_path=r"C:\Projects\kis-mcp\old.txt",
        original_relative_path=r"kis-mcp\old.txt",
        payload_path=r"C:\Projects\.kis-mcp\quarantine\op\payload\old.txt",
        item_type="file",
        payload_digest="0" * 64,
        quarantined_at="2026-08-04T00:00:00+00:00",
        restored_at=None,
        integrity_digest="1" * 64,
    )

    public = _quarantine_response(internal)

    assert asdict(public) == {
        "operation_id": internal.operation_id,
        "original_path": internal.original_path,
        "payload_path": internal.payload_path,
        "item_type": internal.item_type,
        "quarantined_at": internal.quarantined_at,
        "restored_at": None,
        "schema_version": 1,
    }


def test_public_response_json_schemas_are_bounded() -> None:
    quarantine_schema = TypeAdapter(QuarantineResponse).json_schema()
    list_schema = TypeAdapter(QuarantineListResponse).json_schema()
    health_schema = TypeAdapter(HealthResponse).json_schema()

    assert set(quarantine_schema["properties"]) == {
        "operation_id",
        "original_path",
        "payload_path",
        "item_type",
        "quarantined_at",
        "restored_at",
        "schema_version",
    }
    assert set(list_schema["properties"]) == {"records", "schema_version"}
    assert set(health_schema["properties"]) == {
        "ready",
        "server",
        "project_boundary",
        "quarantine_root",
        "desktop_commander_entry",
        "desktop_commander_installed",
        "policy_rules",
        "policy_fingerprint",
        "implementation_status",
        "schema_version",
    }


def test_policy_rule_response_rejects_arbitrary_layout() -> None:
    schema = TypeAdapter(PolicyRuleResponse).json_schema()
    assert schema.get("additionalProperties") is not True
    assert set(schema["properties"]) == {
        "id",
        "name",
        "prohibited_outcome",
        "decision",
    }


def test_server_public_boundaries_do_not_use_internal_asdict() -> None:
    from kis_mcp import server

    source = inspect.getsource(server)
    assert "from dataclasses import asdict" not in source
    assert "asdict(quarantine" not in source
    assert "asdict(record)" not in source


def test_build_server_exposes_provider_runtime_injection_contract() -> None:
    parameters = inspect.signature(build_server).parameters

    assert list(parameters) == [
        "config",
        "validate_provider",
        "provider_service",
        "provider_runtime_settings",
    ]
    assert parameters["provider_service"].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        parameters["provider_runtime_settings"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
