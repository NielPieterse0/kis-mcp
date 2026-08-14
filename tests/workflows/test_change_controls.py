from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.work_management import ChangeComplexity, RiskTrigger
from kis_mcp.workflows.change_controls import (
    load_change_control_settings,
    select_change_controls,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = REPOSITORY_ROOT / "settings" / "change-governance.settings.json"


def test_small_change_uses_compact_execution_defaults() -> None:
    result = select_change_controls(complexity="small")
    assert result.max_verifications == 6
    assert result.review_types == ()


def test_medium_and_large_defaults() -> None:
    medium = select_change_controls(complexity="medium")
    large = select_change_controls(complexity="large")
    assert medium.max_verifications == 20
    assert large.max_verifications == 20
    assert medium.review_types == ("code-quality",)
    assert large.review_types == ("code-quality",)


def test_explicit_review_adds_to_base_review() -> None:
    result = select_change_controls(
        complexity="medium",
        review_types=("test-quality",),
    )
    assert result.review_types == ("code-quality", "test-quality")


def test_invalid_complexity_is_rejected() -> None:
    with pytest.raises(ValueError, match="complexity"):
        select_change_controls(complexity="heroic")


def test_change_controls_are_driven_by_repository_settings(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    document["complexities"]["small"]["max_verifications"] = 4
    document["risk_triggers"]["money"]["reviews"] = ["performance"]
    candidate = tmp_path / "change-governance.settings.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")

    settings = load_change_control_settings(candidate)
    result = select_change_controls(
        complexity="small",
        risk_triggers=("money",),
        settings=settings,
    )

    assert result.max_verifications == 4
    assert result.review_types == ("performance",)


def test_change_governance_settings_match_checked_in_schema() -> None:
    schema_path = (
        REPOSITORY_ROOT
        / "contracts"
        / "governance"
        / "change-governance.settings.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_change_classification_vocabulary_matches_settings_authority() -> None:
    settings = load_change_control_settings(SETTINGS_PATH)

    assert {item.value for item in ChangeComplexity} == {
        name for name, _controls in settings.complexities
    }
    assert {item.value for item in RiskTrigger} == {
        name for name, _reviews in settings.risk_reviews
    }
