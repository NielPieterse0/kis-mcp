from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.tools import ToolBoundary, ToolKind, ToolState
from kis_mcp.tools.everything.settings import EverythingToolSettings
from kis_mcp.tools.everything.tool import everything_tool_descriptor
from kis_mcp.tools.fetch.settings import FetchToolSettings
from kis_mcp.tools.fetch.tool import fetch_tool_descriptor
from kis_mcp.tools.mcp_spec.settings import McpSpecSettings
from kis_mcp.tools.mcp_spec.tool import McpSpecPluginSource, mcp_spec_tool_descriptor
from kis_mcp.tools.mcp_stdio import StdioMcpCommand

ROOT = Path(__file__).resolve().parents[2]


def test_stdio_command_serializes_environment_names_without_values() -> None:
    command = StdioMcpCommand(
        executable="python.exe",
        arguments=("-m", "mcp_server_fetch"),
        environment_names=("PYTHONIOENCODING",),
    )

    assert command.to_json_dict() == {
        "executable": "python.exe",
        "arguments": ["-m", "mcp_server_fetch"],
        "environment_names": ["PYTHONIOENCODING"],
    }
    assert "secret-value" not in repr(command)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("-y", "package"), "package acquisition"),
        (("--yes", "package"), "package acquisition"),
        (("package@latest",), "floating package"),
        (("uvx", "mcp-server-fetch"), "package acquisition"),
    ],
)
def test_stdio_command_rejects_runtime_package_acquisition(
    arguments: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        StdioMcpCommand(executable="runner", arguments=arguments)


def test_stdio_command_rejects_invalid_or_duplicate_environment_names() -> None:
    with pytest.raises(ValueError, match="environment variable"):
        StdioMcpCommand(executable="python", environment_names=("bad-name",))
    with pytest.raises(ValueError, match="unique"):
        StdioMcpCommand(
            executable="python",
            environment_names=("TOKEN", "TOKEN"),
        )


def test_checked_in_tool_settings_pin_exact_upstreams() -> None:
    mcp_spec = McpSpecSettings.load(
        ROOT / "settings" / "tools" / "mcp-spec.tool.json"
    )
    fetch = FetchToolSettings.load(ROOT / "settings" / "tools" / "fetch.tool.json")
    everything = EverythingToolSettings.load(
        ROOT / "settings" / "tools" / "everything.tool.json"
    )

    assert mcp_spec.source_revision == "5c4f1768b97198a149d7db05f5026b30c6a3cb12"
    assert mcp_spec.plugin_path == "plugins/mcp-spec"
    assert fetch.source_revision == "76d64c822f5125032f89eb71dbdb94e42b434821"
    assert fetch.package_name == "mcp-server-fetch"
    assert fetch.package_version == "0.6.3"
    assert fetch.enabled is False
    assert everything.source_revision == "76d64c822f5125032f89eb71dbdb94e42b434821"
    assert everything.package_name == "@modelcontextprotocol/server-everything"
    assert everything.package_version == "2.0.0"


def test_mcp_spec_descriptor_is_plugin_metadata_not_an_mcp_server(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins" / "mcp-spec"
    plugin_root.mkdir(parents=True)
    settings = replace(
        McpSpecSettings.load(
            ROOT / "settings" / "tools" / "mcp-spec.tool.json"
        ),
        local_checkout=tmp_path,
    )

    descriptor = mcp_spec_tool_descriptor(settings)
    readiness = descriptor.readiness_probe()
    built = descriptor.builder()

    assert descriptor.tool_id == "mcp-spec-plugin"
    assert descriptor.tool_kind is ToolKind.PLATFORM_INTERNAL
    assert descriptor.boundary is ToolBoundary.LOCAL_READ_ONLY
    assert descriptor.source_revision == settings.source_revision
    assert descriptor.capabilities[0].capability_id == "mcp.spec.research"
    assert readiness.state is ToolState.READY
    assert isinstance(built, McpSpecPluginSource)
    assert built.plugin_root == plugin_root
    assert "command" not in built.to_json_dict()


def test_fetch_descriptor_is_disabled_external_network_only_without_probing() -> None:
    settings = FetchToolSettings.load(ROOT / "settings" / "tools" / "fetch.tool.json")

    def forbidden_probe(_: str) -> str | None:
        raise AssertionError("disabled Fetch must not probe executables")

    descriptor = fetch_tool_descriptor(settings, which=forbidden_probe)
    readiness = descriptor.readiness_probe()
    command = descriptor.builder()

    assert descriptor.enabled is False
    assert descriptor.tool_kind is ToolKind.MCP_ADAPTER
    assert descriptor.boundary is ToolBoundary.APPROVED_EXTERNAL_SERVICE
    assert descriptor.capabilities[0].effects == ("external_network",)
    assert readiness.state is ToolState.DISABLED
    assert command.arguments == ("-m", "mcp_server_fetch")
    assert all(item not in {"-y", "--yes"} for item in command.arguments)


def test_everything_builder_uses_fixed_local_node_entrypoint(tmp_path: Path) -> None:
    entry_point = tmp_path / "dist" / "index.js"
    entry_point.parent.mkdir()
    entry_point.write_text("// test", encoding="utf-8")
    settings = replace(
        EverythingToolSettings.load(
            ROOT / "settings" / "tools" / "everything.tool.json"
        ),
        enabled=True,
        executable="node",
        entry_point=entry_point,
    )

    descriptor = everything_tool_descriptor(
        settings,
        which=lambda executable: f"C:/bin/{executable}.exe",
    )

    assert descriptor.readiness_probe().state is ToolState.READY
    command = descriptor.builder()
    assert command.executable == "node"
    assert command.arguments == (str(entry_point), "stdio")
    assert "npx" not in command.arguments
    assert "-y" not in command.arguments


def test_tool_settings_reject_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "fetch.json"
    path.write_text(
        '{"schema_version":1,"enabled":false,"unexpected":true}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown settings keys"):
        FetchToolSettings.load(path)


@pytest.mark.parametrize(
    ("settings_path", "schema_path"),
    [
        (
            "settings/tools/mcp-spec.tool.json",
            "contracts/tools/mcp-sdk-integrations/mcp-spec.schema.json",
        ),
        (
            "settings/tools/fetch.tool.json",
            "contracts/tools/mcp-sdk-integrations/fetch.schema.json",
        ),
        (
            "settings/tools/everything.tool.json",
            "contracts/tools/mcp-sdk-integrations/everything.schema.json",
        ),
        (
            "settings/providers/python-sdk.provider.json",
            "contracts/providers/mcp-sdk-integrations/python-sdk.schema.json",
        ),
        (
            "settings/providers/gitlab.provider.json",
            "contracts/providers/mcp-sdk-integrations/gitlab.schema.json",
        ),
    ],
)
def test_checked_in_integration_settings_match_their_json_schemas(
    settings_path: str,
    schema_path: str,
) -> None:
    settings = json.loads((ROOT / settings_path).read_text(encoding="utf-8"))
    schema = json.loads((ROOT / schema_path).read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(settings)
