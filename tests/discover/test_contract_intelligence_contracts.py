from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.contract_intelligence_contracts import (
    ContractBudget,
    InspectContractsRequest,
)

ROOT = Path(__file__).resolve().parents[2]


def test_request_requires_project_and_explicit_positive_budget() -> None:
    request = InspectContractsRequest(
        project=r"C:\Projects\example",
        budget=ContractBudget(4, 20, 20, 40),
    )
    assert request.to_json_dict()["budget"]["max_documents"] == 4

    with pytest.raises(ValueError, match="project"):
        InspectContractsRequest(project=" ", budget=ContractBudget(1, 1, 1, 1))
    with pytest.raises(ValueError, match="positive"):
        ContractBudget(0, 1, 1, 1)


def test_request_schema_is_strict() -> None:
    schema = json.loads(
        (ROOT / "contracts" / "discover" / "inspect-contracts-request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    valid = {
        "project": r"C:\Projects\example",
        "budget": {
            "max_documents": 4,
            "max_operations": 20,
            "max_schemas": 20,
            "max_relationships": 40,
        },
    }
    assert list(validator.iter_errors(valid)) == []
    assert list(validator.iter_errors({**valid, "unexpected": True}))
