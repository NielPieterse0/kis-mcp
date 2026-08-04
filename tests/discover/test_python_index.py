from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner


def _write(root: Path, label: str, content: str) -> None:
    path = root / Path(label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _index(project_root: Path, settings):
    from kis_mcp.discover.python_index import PythonProjectIndexer

    authority = ReadAuthority(Path(r"C:\Projects"), settings)
    snapshot = RepositoryScanner(authority, settings).snapshot(str(project_root))
    return PythonProjectIndexer(authority=authority, settings=settings).index(
        str(project_root), snapshot
    )


def _with_limits(settings, **overrides: int):
    return replace(settings, limits=replace(settings.limits, **overrides))


def test_python_index_never_executes_project_code(
    project_root: Path,
    discover_settings,
) -> None:
    marker = project_root / "executed.txt"
    _write(
        project_root,
        "src/pkg/danger.py",
        """
from pathlib import Path
Path('executed.txt').write_text('bad')
raise RuntimeError('must not execute')

def safe():
    return 1
""".strip()
        + "\n",
    )

    result = _index(project_root, discover_settings)

    assert marker.exists() is False
    assert [item.qualified_name for item in result.symbols] == ["pkg.danger.safe"]
    assert result.status == "completed"


def test_indexes_modules_symbols_imports_inheritance_calls_and_cycles(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "src/pkg/__init__.py", "from .service import Service\n")
    _write(
        project_root,
        "src/pkg/base.py",
        """
class Base:
    def run(self):
        return helper()

def helper():
    return 1
""".strip()
        + "\n",
    )
    _write(
        project_root,
        "src/pkg/service.py",
        """
from .base import Base as Parent
from . import cycle_a
import json as json_module

@decorator
class Service(Parent):
    @classmethod
    def build(cls):
        return cls()

    async def execute(self):
        return self.build()

def duplicate():
    return 1

def duplicate():
    return 2
""".strip()
        + "\n",
    )
    _write(project_root, "src/pkg/cycle_a.py", "from . import cycle_b\n")
    _write(project_root, "src/pkg/cycle_b.py", "from . import cycle_a\n")
    _write(project_root, "src/pkg/broken_relative.py", "from ...outside import value\n")

    result = _index(project_root, discover_settings)

    assert [(item.name, item.package) for item in result.modules] == [
        ("pkg", True),
        ("pkg.base", False),
        ("pkg.broken_relative", False),
        ("pkg.cycle_a", False),
        ("pkg.cycle_b", False),
        ("pkg.service", False),
    ]
    by_symbol = {item.qualified_name: item for item in result.symbols}
    assert by_symbol["pkg.base.Base"].kind == "class"
    assert by_symbol["pkg.base.Base.run"].kind == "method"
    assert by_symbol["pkg.service.Service"].bases == ("Parent",)
    assert by_symbol["pkg.service.Service"].decorators == ("decorator",)
    assert by_symbol["pkg.service.Service.build"].kind == "method"
    assert by_symbol["pkg.service.Service.execute"].kind == "async_method"

    imports = {
        (
            item.source_module,
            item.target_module,
            item.imported_name,
            item.alias,
            item.level,
            item.internal,
        )
        for item in result.imports
    }
    assert ("pkg.service", "pkg.base", "Base", "Parent", 1, True) in imports
    assert ("pkg.service", "json", None, "json_module", 0, False) in imports
    assert ("pkg.cycle_a", "pkg.cycle_b", "cycle_b", None, 1, True) in imports

    assert ("pkg.service.Service", "Parent") in {
        (item.symbol, item.base) for item in result.inheritance
    }
    assert ("pkg.service.Service.build", "cls") in {
        (item.caller, item.callee) for item in result.calls
    }
    assert ("pkg.service.Service.execute", "self.build") in {
        (item.caller, item.callee) for item in result.calls
    }
    assert {item.code for item in result.diagnostics} == {
        "PY_DUPLICATE_SYMBOL",
        "PY_IMPORT_CYCLE",
        "PY_RELATIVE_IMPORT_UNRESOLVED",
    }
    assert result.status == "completed"
    assert result.truncated is False


def test_syntax_error_returns_partial_result_without_source_excerpt(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "good.py", "def good(): return 1\n")
    _write(project_root, "broken.py", "def broken(:\n    secret = 'do-not-echo'\n")

    result = _index(project_root, discover_settings)

    assert [item.qualified_name for item in result.symbols] == ["good.good"]
    assert result.status == "partial"
    assert result.truncated is False
    assert [item.code for item in result.diagnostics] == ["PY_SYNTAX_ERROR"]
    assert "do-not-echo" not in result.diagnostics[0].message
    assert result.diagnostics[0].path == "broken.py"


def test_index_limits_return_bounded_partial_results(
    project_root: Path,
    discover_settings,
) -> None:
    _write(
        project_root,
        "a.py",
        "\n".join(f"def function_{index}(): return {index}" for index in range(10))
        + "\n",
    )
    _write(project_root, "b.py", "def b(): return 1\n")

    record_limited = _index(
        project_root,
        _with_limits(discover_settings, python_max_records=3),
    )
    node_limited = _index(
        project_root,
        _with_limits(discover_settings, python_max_nodes=5),
    )
    file_limited = _index(
        project_root,
        _with_limits(discover_settings, max_files=1),
    )

    assert len(record_limited.symbols) == 3
    assert record_limited.truncated is True
    assert "python_max_records" in record_limited.truncation_reasons
    assert node_limited.truncated is True
    assert node_limited.truncation_reasons == ("python_max_nodes",)
    assert [item.path for item in file_limited.modules] == ["a.py"]
    assert file_limited.truncated is True
    assert "max_files" in file_limited.truncation_reasons


def test_index_duration_limit_is_configured_and_deterministic(
    project_root: Path,
    discover_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(project_root, "a.py", "def a(): return 1\n")
    _write(project_root, "b.py", "def b(): return 2\n")
    settings = _with_limits(discover_settings, traversal_timeout_seconds=1)
    moments = iter((0.0, 0.1, 2.0, 2.0))
    monkeypatch.setattr(
        "kis_mcp.discover.python_index.monotonic",
        lambda: next(moments, 2.0),
    )

    result = _index(project_root, settings)

    assert [item.path for item in result.modules] == ["a.py", "b.py"]
    assert result.summary["files_indexed"] == 1
    assert result.truncated is True
    assert result.truncation_reasons == ("python_duration",)


def test_index_output_is_deterministic(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "b.py", "def b(): return a()\n")
    _write(project_root, "a.py", "def a(): return 1\n")

    first = _index(project_root, discover_settings).to_json_dict()
    second = _index(project_root, discover_settings).to_json_dict()

    assert first == second
