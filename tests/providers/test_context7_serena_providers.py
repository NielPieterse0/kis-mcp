from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.providers.context7 import (
    context7_provider_descriptor,
    load_context7_settings,
)
from kis_mcp.providers.contracts import ProviderBoundary, ProviderKind
from kis_mcp.providers.serena import (
    SerenaRuntimeAdapter,
    load_serena_settings,
    serena_provider_descriptor,
)
from kis_mcp.providers.serena.adapter import (
    _SharedProviderClient,
    _provider_environment,
    _repair_empty_project_languages,
)

ROOT = Path(__file__).resolve().parents[2]


def _result(value: object, *, error: bool = False):
    text = value if isinstance(value, str) else json.dumps(value)
    return SimpleNamespace(is_error=error, content=(SimpleNamespace(text=text),))


def test_context7_descriptor_remains_external_documentation_only() -> None:
    settings = load_context7_settings(ROOT / "settings/providers/context7.provider.json")
    descriptor = context7_provider_descriptor(settings, environment={})
    capability = descriptor.capabilities[0]

    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert capability.tool_names == ("query-docs", "resolve-library-id")
    assert "semantic" not in capability.capability_id


def test_serena_project_state_is_centralized_outside_repository() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")

    assert str(settings.project_data_root) == r"C:\Projects\.kis-mcp\serena\projects"
    assert settings.project_serena_folder_template == (
        r"C:\Projects\.kis-mcp\serena\projects\$projectFolderName\.serena"
    )
    project_state = settings.project_data_path(str(ROOT))
    assert project_state == settings.project_data_root / ROOT.name / ".serena"
    assert project_state != ROOT / ".serena"


def test_serena_project_state_root_must_remain_inside_install_root(tmp_path: Path) -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")

    with pytest.raises(ValueError, match="project_data_root must remain inside install_root"):
        replace(settings, project_data_root=tmp_path / "outside-serena-state")


def test_serena_project_state_rejects_same_name_root_collisions(tmp_path: Path) -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    install_root = tmp_path / "serena"
    settings = replace(
        settings,
        install_root=install_root,
        project_data_root=install_root / "projects",
    )
    first = tmp_path / "first" / "shared-name"
    second = tmp_path / "second" / "shared-name"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    first_data = settings.ensure_project_data_path(str(first))
    canonical_path, canonical_identity = settings.canonical_project_identity(str(first))
    assert canonical_path.is_file()
    assert canonical_identity["project_id"] == "kis-mcp"
    assert "reconstructible" in canonical_path.parts
    assert "serena-project-data" in canonical_path.parts
    assert first_data.is_dir()

    with pytest.raises(ValueError, match="project state collision"):
        settings.ensure_project_data_path(str(second))


def test_serena_exact_legacy_identity_migrates_to_canonical_marker(tmp_path: Path) -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    install_root = tmp_path / "serena"
    settings = replace(
        settings,
        install_root=install_root,
        project_data_root=install_root / "projects",
    )
    project = tmp_path / "legacy-project"
    project.mkdir()
    legacy_path = settings.project_identity_path(str(project))
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        json.dumps({"schema_version": 1, "project_root": str(project)}) + "\n",
        encoding="utf-8",
    )

    settings.ensure_project_data_path(str(project))
    canonical_path, expected = settings.canonical_project_identity(str(project))
    assert json.loads(canonical_path.read_text(encoding="utf-8")) == expected
    assert json.loads(legacy_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "project_root": str(project),
    }


def test_serena_project_state_rejects_unmarked_legacy_data(tmp_path: Path) -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    install_root = tmp_path / "serena"
    settings = replace(
        settings,
        install_root=install_root,
        project_data_root=install_root / "projects",
    )
    project = tmp_path / "ambiguous-project"
    project.mkdir()
    legacy_data = settings.project_data_path(str(project))
    legacy_data.mkdir(parents=True)
    (legacy_data / "project.yml").write_text("project_name: ambiguous\n", encoding="utf-8")

    with pytest.raises(ValueError, match="identity is ambiguous"):
        settings.ensure_project_data_path(str(project))
    assert (legacy_data / "project.yml").is_file()


def test_serena_descriptor_is_local_read_only_and_offline() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))
    descriptor = serena_provider_descriptor(adapter)
    capability = descriptor.capabilities[0]

    assert settings.executable.name.casefold() == "python.exe"
    assert settings.arguments[:3] == (
        "-c",
        "from serena.cli import top_level; top_level()",
        "start-mcp-server",
    )
    assert descriptor.provider_kind is ProviderKind.SEMANTIC
    assert descriptor.boundary is ProviderBoundary.LOCAL_READ_ONLY
    assert capability.tool_names == (
        "find_referencing_symbols",
        "find_symbol",
        "get_symbols_overview",
    )
    assert "delete_memory" not in capability.tool_names
    assert descriptor.runtime_tools_probe is not None
    adapter.runtime_tools.publish((SimpleNamespace(name="find_symbol"),))
    assert [item.name for item in descriptor.runtime_tools_probe()] == ["find_symbol"]
    assert descriptor.readiness_probe().details["offline_enforced"] is True


def test_shared_serena_client_records_protocol_once_per_connection_generation() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))

    class LegacyClient:
        protocol_version = "2025-11-25"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            del args

    inner = LegacyClient()
    shared = _SharedProviderClient(inner, adapter)

    async def scenario() -> None:
        async with shared:
            assert adapter.startup_state.protocol_mode == "legacy_compatibility"
            assert adapter.startup_state.protocol_version == "2025-11-25"
            inner.protocol_version = "nested-must-not-republish"
            async with shared:
                assert adapter.startup_state.protocol_version == "2025-11-25"
        inner.protocol_version = "2025-06-18"
        async with shared:
            assert adapter.startup_state.protocol_version == "2025-06-18"

    asyncio.run(scenario())


def test_shared_serena_client_propagates_unexpected_connection_failure() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))

    class FailingClient:
        async def __aenter__(self):
            raise RuntimeError("discover transport failed")

        async def __aexit__(self, *args: object) -> None:
            del args

    shared = _SharedProviderClient(FailingClient(), adapter)

    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="discover transport failed"):
            async with shared:
                raise AssertionError("unreachable")

    asyncio.run(scenario())
    assert adapter.startup_state.protocol_mode is None
    assert adapter.startup_state.protocol_version is None


def test_shared_serena_client_survives_nested_proxy_context_exit() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))

    class ReentrantClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            del args

        async def call_tool(self, name: str, arguments: dict[str, object]):
            del name, arguments
            return _result("ok")

        async def list_tools(self):
            return ()

    inner = ReentrantClient()
    shared = _SharedProviderClient(inner, adapter)

    async def scenario() -> None:
        async with shared:
            outer_loop = adapter._loop
            assert adapter._active_client is inner
            assert outer_loop is not None
            async with shared:
                assert adapter._active_client is inner
            assert adapter._active_client is inner
            assert adapter._loop is outer_loop
        assert adapter._active_client is None
        assert adapter._loop is None

    asyncio.run(scenario())


def test_shared_serena_client_delegates_fastmcp_proxy_tool_calls() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))

    class ProxyClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object], object]] = []

        async def call_tool_mcp(
            self,
            name: str,
            arguments: dict[str, object],
            *,
            meta: object = None,
        ):
            self.calls.append((name, arguments, meta))
            return _result("proxy-ok")

    inner = ProxyClient()
    shared = _SharedProviderClient(inner, adapter)
    result = asyncio.run(shared.call_tool_mcp("find_symbol", {"name_path_pattern": "Demo"}, meta={"request": "current"}))

    assert result == _result("proxy-ok")
    assert inner.calls == [
        ("find_symbol", {"name_path_pattern": "Demo"}, {"request": "current"})
    ]


def test_serena_normalizes_symbols_and_references_without_schema_leakage() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    adapter = SerenaRuntimeAdapter(settings, environment={}, default_project=str(ROOT))

    def call(name: str, arguments: dict[str, object]):
        if name == "activate_project":
            return _result("ok")
        if name == "get_symbols_overview":
            return _result({"Class": ["Demo"], "Function": ["run"]})
        if name == "find_symbol":
            symbol = str(arguments["name_path_pattern"])
            return _result(
                [
                    {
                        "name_path": symbol,
                        "kind": "Class" if symbol == "Demo" else "Function",
                        "relative_path": "src/demo.py",
                        "body_location": {"start_line": 4, "end_line": 8},
                    }
                ]
            )
        if name == "find_referencing_symbols":
            return _result(
                {
                    "src/use.py": {
                        "Function": [
                            {"name_path": "use_demo", "reference_line": 10}
                        ]
                    }
                }
            )
        raise AssertionError(name)

    adapter._call_sync = call  # type: ignore[method-assign]
    evidence = adapter.read(str(ROOT), ("src/demo.py",))

    assert evidence.status == "ready"
    assert {item.name for item in evidence.symbols} == {"Demo", "run"}
    assert evidence.symbols[0].path == "src/demo.py"
    assert evidence.relationships[0].kind == "reference"
    assert not hasattr(evidence.symbols[0], "name_path")


def test_serena_child_environment_forces_utf8_text_streams() -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    environment = _provider_environment(settings, {"PATH": "python-path"})

    assert environment["PYTHONUTF8"] == "1"
    assert environment["PYTHONIOENCODING"] == "utf-8"


def test_serena_repairs_persisted_empty_language_state(tmp_path: Path) -> None:
    settings = load_serena_settings(ROOT / "settings/providers/serena.provider.json")
    install_root = tmp_path / "serena"
    settings = replace(
        settings,
        install_root=install_root,
        project_data_root=install_root / "projects",
    )
    project = tmp_path / "commodity"
    project.mkdir()
    project_data = settings.ensure_project_data_path(str(project))
    config = project_data / "project.yml"
    config.write_text(
        'project_name: "commodity"\nlanguages: []\nencoding: "utf-8"\n',
        encoding="utf-8",
    )
    repaired = _repair_empty_project_languages(
        settings,
        str(project),
        ("src/feed.py", "web/app.ts"),
    )
    assert repaired == ("python", "typescript")
    content = config.read_text(encoding="utf-8")
    assert "languages:\n- python\n- typescript\n" in content
    config.write_text(
        'project_name: "commodity"\nlanguages:\n- python\n',
        encoding="utf-8",
    )
    assert _repair_empty_project_languages(
        settings,
        str(project),
        ("web/app.ts",),
    ) == ()
    assert config.read_text(encoding="utf-8").endswith("languages:\n- python\n")
