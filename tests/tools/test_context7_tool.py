from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastmcp import FastMCP
from jsonschema import Draft202012Validator

from kis_mcp.tools import ToolBoundary, ToolKind, ToolState
from kis_mcp.tools.context7 import (
    Context7Adapter,
    Context7Settings,
    context7_tool_descriptor,
)

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "settings" / "tools" / "context7.tool.json"
SCHEMA_PATH = ROOT / "contracts" / "tools" / "context7" / "settings.schema.json"
CONTRACT_PATH = ROOT / "contracts" / "tools" / "context7" / "upstream-tools.json"


def test_checked_in_context7_settings_and_contract_are_exact() -> None:
    settings = Context7Settings.load(SETTINGS_PATH)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert settings.source_revision == "b250c2515694eee4b6df4db82fa056df9ed3e306"
    assert settings.package_version == "3.2.5"
    assert settings.namespace == "context7"
    assert tuple(contract["operations"]) == ("resolve-library-id", "query-docs")
    assert contract["operations"]["resolve-library-id"]["required"] == [
        "query",
        "libraryName",
    ]
    assert contract["operations"]["query-docs"]["required"] == [
        "libraryId",
        "query",
    ]


def test_context7_settings_match_schema() -> None:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(settings)


def test_context7_installer_requires_scan_before_promotion() -> None:
    source = (ROOT / "scripts" / "install-context7.ps1").read_text(encoding="utf-8")
    assert "--ignore-scripts" in source
    assert "pending_operator_scan" in source
    assert "operator-scan-approved.json" in source
    assert "provider_executed = $false" in source


def test_context7_settings_reject_unknown_keys(tmp_path: Path) -> None:
    document = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    document["endpoint"] = "https://unapproved.example"
    path = tmp_path / "context7.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown settings keys"):
        Context7Settings.load(path)


def test_context7_descriptor_uses_fixed_local_entrypoint(tmp_path: Path) -> None:
    entry = tmp_path / "dist" / "index.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("// fixture", encoding="utf-8")
    settings = replace(
        Context7Settings.load(SETTINGS_PATH),
        entry_point=entry,
        install_root=tmp_path,
    )
    descriptor = context7_tool_descriptor(
        settings,
        which=lambda _: "C:/Program Files/nodejs/node.exe",
        node_version=lambda _: "22.18.0",
    )

    assert descriptor.tool_id == "context7-mcp"
    assert descriptor.tool_kind is ToolKind.MCP_ADAPTER
    assert descriptor.boundary is ToolBoundary.APPROVED_EXTERNAL_SERVICE
    assert descriptor.source_revision == settings.source_revision
    assert descriptor.enabled is True
    assert descriptor.capabilities[0].operation_names == (
        "query-docs",
        "resolve-library-id",
    )
    assert descriptor.readiness_probe().state is ToolState.READY

    adapter = descriptor.builder()
    assert isinstance(adapter, Context7Adapter)
    assert adapter.command.executable == "node"
    assert adapter.command.arguments == (str(entry), "--transport", "stdio")
    assert "npx" not in adapter.command.arguments
    assert "-y" not in adapter.command.arguments


def test_context7_readiness_is_contained_and_redacts_credentials(tmp_path: Path) -> None:
    settings = replace(
        Context7Settings.load(SETTINGS_PATH),
        entry_point=tmp_path / "missing.js",
        install_root=tmp_path,
    )
    descriptor = context7_tool_descriptor(
        settings,
        which=lambda _: None,
        node_version=lambda _: "",
    )
    readiness = descriptor.readiness_probe()

    assert readiness.state is ToolState.UNAVAILABLE
    rendered = json.dumps(readiness.to_json_dict(), sort_keys=True)
    assert "CONTEXT7_API_KEY" in rendered
    assert "secret-value" not in rendered
    assert "endpoint" not in rendered.casefold()


def test_context7_adapter_builds_proxy_without_exposing_environment_values(
    tmp_path: Path,
) -> None:
    entry = tmp_path / "index.js"
    entry.write_text("// fixture", encoding="utf-8")
    settings = replace(Context7Settings.load(SETTINGS_PATH), entry_point=entry)
    captured: dict[str, object] = {}

    def factory(command: str, arguments: tuple[str, ...], environment: dict[str, str]) -> FastMCP:
        captured.update(command=command, arguments=arguments, environment=environment)
        return FastMCP("context7-fixture")

    adapter = Context7Adapter(
        settings,
        environment={"CONTEXT7_API_KEY": "secret-value", "UNRELATED": "ignore"},
        proxy_factory=factory,
    )
    server = adapter.build_server()

    assert isinstance(server, FastMCP)
    assert captured["command"] == "node"
    assert captured["arguments"] == (str(entry), "--transport", "stdio")
    assert captured["environment"] == {"CONTEXT7_API_KEY": "secret-value"}
    assert "secret-value" not in repr(adapter)
