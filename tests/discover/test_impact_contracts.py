from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.impact_contracts import ImpactBudget, InspectImpactRequest

ROOT = Path(__file__).resolve().parents[2]


def test_request_normalizes_paths_and_requires_explicit_budget() -> None:
    request = InspectImpactRequest(
        project=r"C:\Projects\example",
        changed_paths=(r".\src\core.py", "src/core.py", "README.md"),
        budget=ImpactBudget(10, 20, 5, 4),
    )
    assert request.changed_paths == ("src/core.py", "README.md")
    assert request.to_json_dict()["budget"]["max_dependants"] == 20

    with pytest.raises(ValueError, match="changed_paths"):
        InspectImpactRequest(
            project=r"C:\Projects\example",
            changed_paths=(),
            budget=ImpactBudget(1, 1, 1, 1),
        )
    with pytest.raises(ValueError, match="repository-relative"):
        InspectImpactRequest(
            project=r"C:\Projects\example",
            changed_paths=("../outside.py",),
            budget=ImpactBudget(1, 1, 1, 1),
        )


def test_request_schema_is_strict() -> None:
    schema = json.loads(
        (ROOT / "contracts" / "discover" / "inspect-impact-request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    valid = {
        "project": r"C:\Projects\example",
        "changed_paths": ["src/core.py"],
        "budget": {
            "max_symbols": 10,
            "max_dependants": 20,
            "max_tests": 5,
            "max_verifications": 4,
        },
    }
    assert list(validator.iter_errors(valid)) == []
    assert list(validator.iter_errors({**valid, "unexpected": True}))
