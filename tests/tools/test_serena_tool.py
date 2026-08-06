from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastmcp import FastMCP
from jsonschema import Draft202012Validator

from kis_mcp.models import InvocationEffects
from kis_mcp.tools import ToolBoundary, ToolKind, ToolState
from kis_mcp.tools.serena import (
    SerenaAdapter,
    SerenaEffectResolver,
    SerenaSettings,
    serena_tool_descriptor,
)

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "settings" / "tools" / "serena.tool.json"
SCHEMA_PATH = ROOT / "contracts" / "tools" / "serena" / "settings.schema.json"
CONTRACT_PATH = ROOT / "contracts" / "tools" / "serena" / "upstream-tools.json"


def _settings(**changes: object) -> SerenaSettings:
    return replace(SerenaSettings.load(SETTINGS_PATH), **changes)


def _resolver(project_root: str = r"C:\Projects\kis-mcp") -> SerenaEffectResolver:
    return SerenaEffectResolver(_settings(), project_root=project_root)


def _materialize_managed_roots(settings: SerenaSettings) -> None:
    for field in (
        "install_root",
        "home_root",
        "config_root",
        "cache_root",
        "log_root",
        "temp_root",
        "language_server_root",
        "global_memory_root",
    ):
        getattr(settings, field).mkdir(parents=True, exist_ok=True)


def test_checked_in_serena_settings_and_contract_are_exact() -> None:
    settings = SerenaSettings.load(SETTINGS_PATH)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert settings.source_revision == "bcac0969fb8685783ea6d0f2642468fcc47e6395"
    assert settings.package_version == "1.6.1"
    assert settings.package_sha256 == (
        "04ddd985bd3feb25598ab8732bf3a998f961d5b46dce271b816126c0a68a91e1"
    )
    assert contract["provider_schema_owner"] is True
    assert contract["memory_contract"]["delete_provider_behavior"] == (
        "unlink_exact_memory_file_only"
    )
    assert contract["effect_operations"]["delete_memory"]["complete_artifact_set"] == [
        "memory_markdown_file"
    ]


def test_serena_settings_match_schema() -> None:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(settings)


def test_serena_installer_requires_two_clean_scan_gates() -> None:
    source = (ROOT / "scripts" / "install-serena.ps1").read_text(encoding="utf-8")
    assert "-m pip download" in source
    assert "-3.11 -m venv" in source
    assert "--no-index" in source
    assert "proxy_tools-0.1.0.tar.gz" in source
    assert "setup.py' install" in source
    assert "operator-wheelhouse-scan-approved.json" in source
    assert "operator-candidate-scan-approved.json" in source
    assert source.count("provider_executed = $false") >= 2


def test_serena_settings_require_every_managed_root_inside_projects() -> None:
    settings = SerenaSettings.load(SETTINGS_PATH)
    for field in (
        "install_root",
        "home_root",
        "config_root",
        "cache_root",
        "log_root",
        "temp_root",
        "language_server_root",
        "global_memory_root",
    ):
        assert str(getattr(settings, field)).casefold().startswith(r"c:\projects".casefold())

    with pytest.raises(ValueError, match="inside project_boundary"):
        replace(settings, cache_root=Path(r"C:\Windows\Temp\serena"))


def test_serena_descriptor_uses_fixed_local_executable(tmp_path: Path) -> None:
    executable = tmp_path / "serena.exe"
    executable.write_text("fixture", encoding="utf-8")
    settings = _settings(executable=executable, install_root=tmp_path)
    _materialize_managed_roots(settings)
    descriptor = serena_tool_descriptor(settings)

    assert descriptor.tool_id == "serena-mcp"
    assert descriptor.tool_kind is ToolKind.MCP_ADAPTER
    assert descriptor.boundary is ToolBoundary.LOCAL_PROCESS
    assert descriptor.source_revision == settings.source_revision
    assert descriptor.readiness_probe().state is ToolState.READY
    adapter = descriptor.builder()
    assert isinstance(adapter, SerenaAdapter)
    assert adapter.command.executable == str(executable)
    assert adapter.command.arguments[0] == "start-mcp-server"
    assert "uvx" not in adapter.command.arguments
    assert "--enable-web-dashboard=false" in adapter.command.arguments
    assert "--open-web-dashboard=false" in adapter.command.arguments
    assert "--enable-gui-log-window=false" in adapter.command.arguments


def test_serena_readiness_failure_is_provider_local(tmp_path: Path) -> None:
    descriptor = serena_tool_descriptor(
        _settings(executable=tmp_path / "missing.exe", install_root=tmp_path)
    )
    readiness = descriptor.readiness_probe()
    assert readiness.state is ToolState.UNAVAILABLE
    assert readiness.details["provider_managed_storage_inside_boundary"] is True


def test_serena_adapter_contains_environment_and_builds_proxy(tmp_path: Path) -> None:
    executable = tmp_path / "serena.exe"
    executable.write_text("fixture", encoding="utf-8")
    settings = _settings(executable=executable, install_root=tmp_path)
    captured: dict[str, object] = {}

    def factory(command: str, arguments: tuple[str, ...], environment: dict[str, str]) -> FastMCP:
        captured.update(command=command, arguments=arguments, environment=environment)
        return FastMCP("serena-fixture")

    adapter = SerenaAdapter(settings, environment={"PATH": "C:/bin"}, proxy_factory=factory)
    server = adapter.build_server()

    assert isinstance(server, FastMCP)
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["HOME"] == str(settings.home_root)
    assert environment["USERPROFILE"] == str(settings.home_root)
    assert environment["TEMP"] == str(settings.temp_root)
    assert environment["SERENA_USAGE_REPORTING"] == "false"


def test_serena_file_mutations_resolve_only_effective_project_paths() -> None:
    resolver = _resolver()
    for tool_name in (
        "serena_replace_symbol_body",
        "serena_insert_after_symbol",
        "serena_insert_before_symbol",
        "serena_rename_symbol",
        "serena_replace_content",
    ):
        effects = resolver.resolve(tool_name, {"relative_path": r"src\module.py"})
        assert effects.write_paths == (r"C:\Projects\kis-mcp\src\module.py",)
        assert effects.entry_paths == ()
        assert effects.external_network is False


def test_serena_memory_effects_are_exact_and_delete_is_complete() -> None:
    resolver = _resolver()
    memory = r"C:\Projects\kis-mcp\.serena\memories\design\boundary.md"

    assert resolver.resolve("serena_write_memory", {"memory_name": "design/boundary"}).write_paths == (memory,)
    assert resolver.resolve("serena_edit_memory", {"memory_name": "design/boundary"}).write_paths == (memory,)
    assert resolver.resolve("serena_delete_memory", {"memory_name": "design/boundary"}).delete_paths == (memory,)


def test_serena_global_memory_stays_in_configured_projects_root() -> None:
    resolver = _resolver()
    effects = resolver.resolve("serena_write_memory", {"memory_name": "global/shared"})
    assert effects.write_paths == (
        r"C:\Projects\.kis-mcp\serena\home\.serena\memories\shared.md",
    )


def test_serena_memory_names_reject_traversal_absolute_and_empty_segments() -> None:
    resolver = _resolver()
    for value in ("../escape", "segment//empty", r"C:\Windows\escape", "/absolute"):
        with pytest.raises(ValueError, match="memory_name"):
            resolver.resolve("serena_write_memory", {"memory_name": value})


def test_serena_rename_memory_reports_move_and_reference_update_scope() -> None:
    resolver = _resolver()
    effects = resolver.resolve(
        "serena_rename_memory",
        {"old_name": "old", "new_name": "new"},
    )
    assert effects.entry_paths == (
        r"C:\Projects\kis-mcp\.serena\memories\old.md",
        r"C:\Projects\kis-mcp\.serena\memories\new.md",
    )
    assert effects.write_paths == (r"C:\Projects\kis-mcp\.serena\memories",)


def test_serena_shell_delegates_unchanged_to_shared_resolver() -> None:
    resolver = _resolver()
    external = resolver.resolve(
        "serena_execute_shell_command",
        {"command": "curl --proxy https://proxy.example http://localhost", "cwd": r"C:\Projects\kis-mcp"},
    )
    local = resolver.resolve(
        "serena_execute_shell_command",
        {"command": 'Write-Output "https://example.com"', "cwd": r"C:\Projects\kis-mcp"},
    )
    dry_run_network = resolver.resolve(
        "serena_execute_shell_command",
        {"command": "curl --dry-run https://example.com", "cwd": r"C:\Projects\kis-mcp"},
    )

    assert external.external_network is True
    assert local.external_network is False
    assert dry_run_network.external_network is True


def test_serena_reads_unknown_tools_and_provider_storage_do_not_invent_effects() -> None:
    resolver = _resolver()
    for tool_name, arguments in (
        ("serena_read_file", {"relative_path": "README.md"}),
        ("serena_list_dir", {"relative_path": "."}),
        ("serena_future_tool", {"path": r"C:\Windows\data"}),
    ):
        assert resolver.resolve(tool_name, arguments) == InvocationEffects()


def test_serena_activate_project_updates_effect_resolution_after_success() -> None:
    resolver = _resolver()
    resolver.observe_success(
        "serena_activate_project",
        {"project": r"C:\Projects\other-project"},
        {"ok": True},
    )
    effects = resolver.resolve(
        "serena_replace_content",
        {"relative_path": "src/new.py"},
    )
    assert effects.write_paths == (r"C:\Projects\other-project\src\new.py",)
