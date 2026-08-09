from __future__ import annotations

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
    assert descriptor.readiness_probe().details["offline_enforced"] is True


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
