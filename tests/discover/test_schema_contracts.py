from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts" / "discover"


def _load(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))


def test_discover_portable_schemas_are_strict_and_versioned() -> None:
    evidence = _load("evidence.schema.json")
    request = _load("inspect-project-request.schema.json")
    response = _load("inspect-project-response.schema.json")

    for schema in (evidence, request, response):
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    assert set(evidence["required"]) == {
        "id",
        "kind",
        "subject",
        "source",
        "provenance",
        "location",
        "trust",
        "confidence",
        "freshness",
        "summary",
        "details",
        "truncated",
    }
    assert set(request["required"]) == {"path"}
    assert set(request["properties"]) == {"path", "limits"}
    assert set(response["required"]) == {
        "schema_version",
        "tool",
        "project",
        "repository_atlas",
        "code_atlas",
        "verification",
        "contracts",
        "instructions",
        "git",
        "remote",
        "providers",
        "evidence",
        "findings",
        "recommendations",
        "handoffs",
        "assumptions",
        "unknowns",
        "confidence",
        "truncated",
        "truncation_reasons",
    }
    assert response["properties"]["schema_version"] == {"const": 1}
    assert response["properties"]["tool"] == {"const": "inspect_project"}
    assert response["properties"]["evidence"]["items"] == {
        "$ref": "evidence.schema.json"
    }
