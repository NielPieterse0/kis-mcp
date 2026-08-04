from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from kis_mcp.config import load_runtime_config
from kis_mcp.provider_contract import (
    ProviderContractError,
    build_provider_contract,
    contract_fingerprint,
    load_provider_contract,
    verify_adapter_contract,
    verify_contract_fingerprint,
    verify_provider_identity,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = REPOSITORY_ROOT / "contracts" / "desktop-commander"
CONTRACT_PATH = CONTRACT_ROOT / "0.2.46.tools.json"
FINGERPRINT_PATH = CONTRACT_ROOT / "0.2.46.schema.sha256"


def test_provider_contract_matches_checked_fingerprint() -> None:
    document = verify_contract_fingerprint(CONTRACT_PATH, FINGERPRINT_PATH)
    assert document["provider"]["version"] == "0.2.46"


def test_provider_contract_matches_pinned_identity_and_adapter() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    document = load_provider_contract(CONTRACT_PATH)

    verify_provider_identity(
        document,
        package=str(config.raw_settings["desktop_commander"]["package"]),
        version=str(config.raw_settings["desktop_commander"]["version"]),
    )
    verify_adapter_contract(document)


def test_every_provider_tool_has_one_explicit_effect_classification() -> None:
    document = load_provider_contract(CONTRACT_PATH)
    tool_names = {tool["name"] for tool in document["tools"]}
    classifications = document["effect_classifications"]

    assert set(classifications) == tool_names
    assert all(isinstance(value, str) and value for value in classifications.values())


def test_provider_addition_requires_explicit_effect_review() -> None:
    document = load_provider_contract(CONTRACT_PATH)
    tools = deepcopy(document["tools"])
    tools.append(
        {
            "annotations": {"openWorldHint": True},
            "input_schema": {"properties": {}, "type": "object"},
            "name": "future_provider_tool",
        }
    )

    with pytest.raises(
        ProviderContractError,
        match=r"provider tool surface drift.*added: future_provider_tool",
    ):
        build_provider_contract(
            package=document["provider"]["package"],
            version=document["provider"]["version"],
            tools=tools,
        )


def test_provider_removal_requires_explicit_effect_review() -> None:
    document = load_provider_contract(CONTRACT_PATH)
    tools = [
        tool for tool in deepcopy(document["tools"]) if tool["name"] != "get_config"
    ]

    with pytest.raises(
        ProviderContractError,
        match=r"provider tool surface drift.*removed: get_config",
    ):
        build_provider_contract(
            package=document["provider"]["package"],
            version=document["provider"]["version"],
            tools=tools,
        )


def test_schema_mutation_changes_fingerprint_and_reports_provider_version() -> None:
    document = load_provider_contract(CONTRACT_PATH)
    mutated = deepcopy(document)
    first_tool = mutated["tools"][0]
    first_tool["input_schema"].setdefault("properties", {})["unexpected"] = {
        "type": "string"
    }

    assert contract_fingerprint(mutated) != contract_fingerprint(document)

    with pytest.raises(
        ProviderContractError,
        match=r"Desktop Commander 0\.2\.46 contract fingerprint mismatch",
    ):
        verify_contract_fingerprint(
            CONTRACT_PATH,
            FINGERPRINT_PATH,
            document=mutated,
        )
