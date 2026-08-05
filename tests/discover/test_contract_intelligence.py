from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.contract_intelligence import ContractIntelligenceService
from kis_mcp.discover.contract_intelligence_contracts import (
    ContractBudget,
    InspectContractsRequest,
)
from kis_mcp.discover.errors import DiscoverError

ROOT = Path(__file__).resolve().parents[2]


def _budget(**overrides: int) -> ContractBudget:
    values = {
        "max_documents": 10,
        "max_operations": 20,
        "max_schemas": 30,
        "max_relationships": 50,
    }
    values.update(overrides)
    return ContractBudget(**values)


def _service(project_root: Path, discover_settings) -> ContractIntelligenceService:
    return ContractIntelligenceService(boundary=project_root.parent, settings=discover_settings)


def _write_contracts(root: Path) -> None:
    contracts = root / "contracts"
    contracts.mkdir()
    (contracts / "openapi.json").write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {"title": "Pets", "version": "1.0.0"},
                "paths": {
                    "/pets": {
                        "get": {
                            "operationId": "listPets",
                            "summary": "List pets",
                            "responses": {
                                "200": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Pet"},
                                            }
                                        }
                                    }
                                }
                            },
                        },
                        "post": {
                            "operationId": "createPet",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                }
                            },
                            "responses": {
                                "201": {
                                    "content": {
                                        "application/json": {
                                            "schema": {"$ref": "#/components/schemas/Pet"}
                                        }
                                    }
                                }
                            },
                        },
                    }
                },
                "components": {
                    "schemas": {
                        "Pet": {
                            "type": "object",
                            "required": ["id", "name"],
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"},
                                "owner": {"$ref": "#/components/schemas/Owner"},
                            },
                        },
                        "Owner": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                    }
                },
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (contracts / "settings.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "settings.schema.json",
                "title": "Settings",
                "type": "object",
                "required": ["provider"],
                "properties": {
                    "provider": {"$ref": "#/$defs/provider"},
                },
                "$defs": {
                    "provider": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (contracts / "mcp-tool.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.invalid/mcp/tool.schema.json",
                "title": "MCP Tool Request",
                "type": "object",
                "required": ["name", "arguments"],
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"},
                },
            }
        ),
        encoding="utf-8",
    )


def test_extracts_openapi_json_schema_and_mcp_topology(
    project_root: Path,
    discover_settings,
) -> None:
    _write_contracts(project_root)
    response = _service(project_root, discover_settings).inspect(
        InspectContractsRequest(project=str(project_root), budget=_budget())
    )

    assert {item.kind for item in response.documents} == {
        "openapi",
        "json_schema",
        "mcp_contract",
    }
    assert {(item.method, item.path, item.operation_id) for item in response.operations} == {
        ("GET", "/pets", "listPets"),
        ("POST", "/pets", "createPet"),
    }
    assert {item.name for item in response.schemas}.issuperset(
        {"Pet", "Owner", "Settings", "provider", "MCP Tool Request"}
    )
    assert any(
        item.kind == "request_schema"
        and item.source == "createPet"
        and item.target == "#/components/schemas/Pet"
        for item in response.relationships
    )
    assert any(
        item.kind == "ref"
        and item.target == "#/$defs/provider"
        for item in response.relationships
    )
    assert response.confidence.value == "high"


def test_invalid_json_and_yaml_are_explicit_without_losing_valid_evidence(
    project_root: Path,
    discover_settings,
) -> None:
    contracts = project_root / "contracts"
    contracts.mkdir()
    (contracts / "valid.schema.json").write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}',
        encoding="utf-8",
    )
    (contracts / "broken.schema.json").write_text("{not-json", encoding="utf-8")
    (contracts / "openapi.yaml").write_text("openapi: 3.1.0\n", encoding="utf-8")

    response = _service(project_root, discover_settings).inspect(
        InspectContractsRequest(project=str(project_root), budget=_budget())
    )

    assert [item.path for item in response.documents] == ["contracts/valid.schema.json"]
    assert {item.code for item in response.unknowns}.issuperset(
        {"CONTRACT_JSON_INVALID", "YAML_CONTRACT_PARSING_UNAVAILABLE"}
    )
    assert response.confidence.value == "medium"


def test_budgets_apply_after_discovery_with_truthful_omissions(
    project_root: Path,
    discover_settings,
) -> None:
    _write_contracts(project_root)
    request = InspectContractsRequest(
        project=str(project_root),
        budget=_budget(
            max_documents=1,
            max_operations=1,
            max_schemas=1,
            max_relationships=1,
        ),
    )
    service = _service(project_root, discover_settings)

    first = service.inspect(request)
    second = service.inspect(request)

    assert first.to_json_dict() == second.to_json_dict()
    assert first.truncated is True
    assert first.omissions.documents == 2
    assert first.omissions.operations >= 1
    assert first.omissions.schemas >= 4
    assert first.omissions.relationships >= 2
    assert len(first.fingerprint) == 64


def test_budget_rejected_before_project_resolution(project_root: Path, discover_settings) -> None:
    constrained = replace(
        discover_settings,
        limits=replace(discover_settings.limits, max_evidence=2),
    )
    request = InspectContractsRequest(
        project=str(project_root / "missing"),
        budget=_budget(max_operations=3),
    )

    with pytest.raises(DiscoverError) as error:
        ContractIntelligenceService(
            boundary=project_root.parent,
            settings=constrained,
        ).inspect(request)

    assert error.value.code == "DISCOVER_CONTRACT_BUDGET_INVALID"
    assert error.value.field == "budget.max_operations"


def test_response_matches_checked_in_schema(project_root: Path, discover_settings) -> None:
    _write_contracts(project_root)
    response = _service(project_root, discover_settings).inspect(
        InspectContractsRequest(project=str(project_root), budget=_budget())
    )
    schema = json.loads(
        (ROOT / "contracts" / "discover" / "inspect-contracts-response.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(response.to_json_dict())) == []
