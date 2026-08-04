from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .desktop_commander import (
    COMMAND_TOOLS,
    CONDITIONAL_WRITE_PATH_KEYS,
    CONFIGURATION_TOOL_NAME,
    DELETE_PATH_KEYS,
    ENTRY_PATH_KEYS,
    NETWORK_ONLY_TOOLS,
    UNEXPOSED_CONFIG_KEYS,
    UNEXPOSED_TOOL_ARGUMENTS,
    WRITE_PATH_KEYS,
)


CONTRACT_SCHEMA_VERSION = 1
ALLOWED_EFFECT_CLASSIFICATIONS = frozenset(
    {
        "command_execution",
        "conditional_write",
        "direct_delete",
        "direct_write",
        "entry_mutation",
        "mixed_network_argument",
        "network_only",
        "no_proven_prohibited_effect",
        "provider_configuration",
    }
)


class ProviderContractError(RuntimeError):
    pass


def _canonical_mapping(
    values: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    return {
        str(name): sorted(str(value) for value in arguments)
        for name, arguments in sorted(values.items())
    }


def adapter_contract_snapshot() -> dict[str, Any]:
    return {
        "command_tools": sorted(COMMAND_TOOLS),
        "conditional_write_path_keys": _canonical_mapping(
            CONDITIONAL_WRITE_PATH_KEYS
        ),
        "configuration_tool": {
            "name": CONFIGURATION_TOOL_NAME,
            "unexposed_keys": sorted(UNEXPOSED_CONFIG_KEYS),
        },
        "delete_path_keys": _canonical_mapping(DELETE_PATH_KEYS),
        "entry_path_keys": _canonical_mapping(ENTRY_PATH_KEYS),
        "network_only_tools": sorted(NETWORK_ONLY_TOOLS),
        "unexposed_tool_arguments": _canonical_mapping(
            UNEXPOSED_TOOL_ARGUMENTS
        ),
        "write_path_keys": _canonical_mapping(WRITE_PATH_KEYS),
    }


def classify_provider_tool(tool_name: str) -> str:
    normalized = tool_name.casefold()
    if normalized in NETWORK_ONLY_TOOLS:
        return "network_only"
    if normalized in UNEXPOSED_TOOL_ARGUMENTS:
        return "mixed_network_argument"
    if normalized == CONFIGURATION_TOOL_NAME:
        return "provider_configuration"
    if normalized in COMMAND_TOOLS:
        return "command_execution"
    if normalized in CONDITIONAL_WRITE_PATH_KEYS:
        return "conditional_write"
    if normalized in ENTRY_PATH_KEYS:
        return "entry_mutation"
    if normalized in WRITE_PATH_KEYS:
        return "direct_write"
    if normalized in DELETE_PATH_KEYS:
        return "direct_delete"
    return "no_proven_prohibited_effect"


def build_provider_contract(
    *,
    package: str,
    version: str,
    tools: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_tools = sorted(
        (
            {
                "annotations": dict(tool.get("annotations") or {}),
                "input_schema": dict(tool.get("input_schema") or {}),
                "name": str(tool["name"]),
                **(
                    {"output_schema": dict(tool["output_schema"])}
                    if isinstance(tool.get("output_schema"), Mapping)
                    else {}
                ),
            }
            for tool in tools
        ),
        key=lambda tool: tool["name"],
    )
    names = [tool["name"] for tool in normalized_tools]
    if len(names) != len(set(names)):
        raise ProviderContractError("Provider contract contains duplicate tool names")
    return {
        "adapter_contract": adapter_contract_snapshot(),
        "effect_classifications": {
            name: classify_provider_tool(name) for name in names
        },
        "provider": {
            "package": package,
            "version": version,
        },
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "tools": normalized_tools,
    }


def canonical_contract_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def contract_fingerprint(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_contract_bytes(document)).hexdigest()


def load_provider_contract(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderContractError(f"Provider contract is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderContractError(f"Provider contract is invalid JSON: {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ProviderContractError("Provider contract root must be an object")
    if document.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ProviderContractError(
            f"Provider contract schema_version must be {CONTRACT_SCHEMA_VERSION}"
        )
    return document


def verify_provider_identity(
    document: Mapping[str, Any],
    *,
    package: str,
    version: str,
) -> None:
    provider = document.get("provider")
    if not isinstance(provider, Mapping):
        raise ProviderContractError("Provider contract provider identity is missing")
    actual_package = str(provider.get("package", ""))
    actual_version = str(provider.get("version", ""))
    if actual_package != package or actual_version != version:
        raise ProviderContractError(
            "Provider contract identity mismatch: "
            f"expected {package}@{version}, found {actual_package}@{actual_version}"
        )


def _tool_properties(tool: Mapping[str, Any]) -> set[str]:
    schema = tool.get("input_schema")
    if not isinstance(schema, Mapping):
        return set()
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return set()
    return {str(name) for name in properties}


def verify_adapter_contract(document: Mapping[str, Any]) -> None:
    expected_adapter = adapter_contract_snapshot()
    if document.get("adapter_contract") != expected_adapter:
        raise ProviderContractError(
            "Desktop Commander adapter contract drifted from the checked provider contract"
        )

    raw_tools = document.get("tools")
    if not isinstance(raw_tools, list) or not all(
        isinstance(tool, Mapping) for tool in raw_tools
    ):
        raise ProviderContractError("Provider contract tools must be an array of objects")
    tools = {str(tool.get("name", "")): tool for tool in raw_tools}
    if "" in tools or len(tools) != len(raw_tools):
        raise ProviderContractError("Provider contract tool names must be unique and non-empty")

    classifications = document.get("effect_classifications")
    if not isinstance(classifications, Mapping):
        raise ProviderContractError("Provider effect classifications are missing")
    if set(classifications) != set(tools):
        raise ProviderContractError(
            "Every provider tool must have exactly one effect classification"
        )
    for name, classification in classifications.items():
        expected = classify_provider_tool(str(name))
        if classification != expected or classification not in ALLOWED_EFFECT_CLASSIFICATIONS:
            raise ProviderContractError(
                f"Provider tool {name} has invalid effect classification {classification!r}"
            )

    required_argument_contracts: dict[str, Sequence[str]] = {
        **UNEXPOSED_TOOL_ARGUMENTS,
        **ENTRY_PATH_KEYS,
        **CONDITIONAL_WRITE_PATH_KEYS,
    }
    for tool_name, arguments in required_argument_contracts.items():
        tool = tools.get(tool_name)
        if tool is None:
            continue
        missing = set(arguments) - _tool_properties(tool)
        if missing:
            raise ProviderContractError(
                f"Provider tool {tool_name} is missing contracted arguments: "
                f"{', '.join(sorted(missing))}"
            )

    alternative_argument_contracts: dict[str, Sequence[str]] = {
        **WRITE_PATH_KEYS,
        **DELETE_PATH_KEYS,
    }
    for tool_name, alternatives in alternative_argument_contracts.items():
        tool = tools.get(tool_name)
        if tool is None:
            continue
        if not (set(alternatives) & _tool_properties(tool)):
            raise ProviderContractError(
                f"Provider tool {tool_name} has none of the contracted arguments: "
                f"{', '.join(sorted(alternatives))}"
            )

    required_surface = {
        *NETWORK_ONLY_TOOLS,
        *UNEXPOSED_TOOL_ARGUMENTS,
        CONFIGURATION_TOOL_NAME,
    }
    missing_surface = required_surface - set(tools)
    if missing_surface:
        raise ProviderContractError(
            "Provider contract is missing gateway-shaped tools: "
            f"{', '.join(sorted(missing_surface))}"
        )


def verify_contract_fingerprint(
    contract_path: Path,
    fingerprint_path: Path,
    *,
    document: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = load_provider_contract(contract_path) if document is None else dict(document)
    provider = loaded.get("provider")
    version = (
        str(provider.get("version", "unknown"))
        if isinstance(provider, Mapping)
        else "unknown"
    )
    try:
        expected = fingerprint_path.read_text(encoding="utf-8").strip().casefold()
    except FileNotFoundError as exc:
        raise ProviderContractError(
            f"Desktop Commander {version} contract fingerprint is missing: {fingerprint_path}"
        ) from exc
    actual = contract_fingerprint(loaded)
    if expected != actual:
        raise ProviderContractError(
            f"Desktop Commander {version} contract fingerprint mismatch: "
            f"expected {expected}, calculated {actual}"
        )
    return loaded
