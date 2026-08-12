from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.context_broker import ContextBrokerService
from kis_mcp.discover.context_contracts import CodeContextBudget, GetCodeContextRequest
from kis_mcp.discover.errors import DiscoverError


ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def _initialize_git(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Context Tests")
    _git(root, "config", "user.email", "context@example.invalid")
    _git(root, "add", "--all")
    _git(root, "commit", "-m", "fixture")


def _write_fixture(root: Path) -> None:
    source = root / "src"
    tests = root / "tests"
    contracts = root / "contracts"
    source.mkdir()
    tests.mkdir()
    contracts.mkdir()
    (source / "context_ranking.py").write_text(
        "def rank_context(task):\n    return task.casefold()\n",
        encoding="utf-8",
    )
    (source / "context_broker.py").write_text(
        "from .context_ranking import rank_context\n\n"
        "class BaseBroker:\n    pass\n\n"
        "class ContextBroker(BaseBroker):\n"
        "    def assemble_context(self, task):\n"
        "        return rank_context(task)\n",
        encoding="utf-8",
    )
    (tests / "test_context_broker.py").write_text(
        "from src.context_broker import ContextBroker\n\n"
        "def test_assemble_context():\n"
        "    assert ContextBroker().assemble_context('Task') == 'task'\n",
        encoding="utf-8",
    )
    (contracts / "context.schema.json").write_text(
        '{"type":"object","properties":{"task":{"type":"string"}}}\n',
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "# Instructions\n\nUse deterministic context ranking.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")


def _budget(**overrides: int) -> CodeContextBudget:
    values = {
        "max_chars": 12_000,
        "max_files": 4,
        "max_symbols": 12,
        "max_relationships": 12,
    }
    values.update(overrides)
    return CodeContextBudget(**values)


def _service(project_root: Path, discover_settings) -> ContextBrokerService:
    return ContextBrokerService(
        boundary=project_root.parent,
        settings=discover_settings,
    )


def test_broker_returns_task_scoped_files_symbols_relationships_and_git(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    _initialize_git(project_root)
    request = GetCodeContextRequest(
        project=str(project_root),
        task="ContextBroker assemble_context rank_context",
        budget=_budget(max_files=3),
    )

    response = _service(project_root, discover_settings).get(request)
    payload = response.to_json_dict()

    assert payload["files"][0]["path"] == "src/context_broker.py"
    assert len(payload["files"]) <= 3
    assert {item["name"] for item in payload["symbols"]}.issuperset(
        {"ContextBroker", "assemble_context"}
    )
    assert any(
        item["kind"] == "call" and item["target"] == "rank_context"
        for item in payload["relationships"]
    )
    assert any(item["kind"] == "inheritance" for item in payload["relationships"])
    assert payload["git"]["available"] is True
    assert payload["git"]["branch"] == "main"
    assert any(item["code"] == "REMOTE_CONTEXT_UNAVAILABLE" for item in payload["unknowns"])
    assert len(json.dumps(payload, ensure_ascii=True, separators=(",", ":"))) <= request.budget.max_chars


def test_broker_prioritizes_tests_instructions_and_contracts_by_task(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    request = GetCodeContextRequest(
        project=str(project_root),
        task="verification tests AGENTS policy schema contract",
        budget=_budget(max_files=4),
    )

    response = _service(project_root, discover_settings).get(request)

    assert "tests/test_context_broker.py" in response.tests
    assert "AGENTS.md" in response.instructions
    assert "contracts/context.schema.json" in response.contracts
    assert {item.path for item in response.files}.issuperset(
        {
            "tests/test_context_broker.py",
            "AGENTS.md",
            "contracts/context.schema.json",
        }
    )


def test_broker_compacts_to_serialized_budget_and_reports_omissions(
    project_root: Path,
    discover_settings,
) -> None:
    source = project_root / "src"
    source.mkdir()
    for index in range(8):
        lines: list[str] = []
        for line in range(10):
            lines.extend(
                [
                    f"def service_{index}_{line}(request):",
                    f"    return 'service-{index}-{line}-' + request",
                    "",
                ]
            )
        (source / f"service_{index}.py").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )
    request = GetCodeContextRequest(
        project=str(project_root),
        task="service request functions",
        budget=_budget(
            max_chars=3_000,
            max_files=6,
            max_symbols=20,
            max_relationships=20,
        ),
    )

    response = _service(project_root, discover_settings).get(request)
    payload = response.to_json_dict()
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert len(serialized) <= 3_000
    assert response.truncated is True
    assert "max_chars" in response.truncation_reasons
    assert response.omissions.files > 0 or response.omissions.symbols > 0
    assert len(response.files) < 6


def test_git_changed_paths_are_narrowed_to_request_file_budget(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    _initialize_git(project_root)
    changes = project_root / "changes"
    changes.mkdir()
    for index in range(5):
        (changes / f"context_change_{index}.py").write_text(
            f"value_{index} = 'context change'\n",
            encoding="utf-8",
        )
    request = GetCodeContextRequest(
        project=str(project_root),
        task="context change",
        budget=_budget(max_files=2),
    )

    response = _service(project_root, discover_settings).get(request)

    assert len(response.git["changed_paths"]) == 2
    assert response.git["omitted_changed_paths"] >= 3
    assert response.git["truncated"] is True


def test_broker_is_deterministic_for_identical_inputs(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    request = GetCodeContextRequest(
        project=str(project_root),
        task="ContextBroker assemble context",
        budget=_budget(),
    )
    service = _service(project_root, discover_settings)

    first = service.get(request).to_json_dict()
    second = service.get(request).to_json_dict()

    assert first == second
    assert first["fingerprint"] == second["fingerprint"]


def test_budget_is_rejected_before_repository_resolution(
    project_root: Path,
    discover_settings,
) -> None:
    constrained = replace(
        discover_settings,
        limits=replace(discover_settings.limits, max_output_chars=5_000),
    )
    request = GetCodeContextRequest(
        project=str(project_root / "missing"),
        task="context",
        budget=_budget(max_chars=6_000),
    )

    with pytest.raises(DiscoverError) as error:
        _service(project_root, constrained).get(request)

    assert error.value.code == "DISCOVER_CONTEXT_BUDGET_INVALID"
    assert error.value.field == "budget.max_chars"


def test_non_python_repository_preserves_file_context_and_reports_semantic_unknown(
    project_root: Path,
    discover_settings,
) -> None:
    source = project_root / "src"
    source.mkdir()
    (source / "contextBroker.ts").write_text(
        "export function assembleContext(task: string) { return task; }\n",
        encoding="utf-8",
    )
    request = GetCodeContextRequest(
        project=str(project_root),
        task="assemble context broker",
        budget=_budget(),
    )

    response = _service(project_root, discover_settings).get(request)

    assert response.files[0].path == "src/contextBroker.ts"
    assert response.symbols == ()
    assert any(
        item.code == "SEMANTIC_CONTEXT_UNAVAILABLE" for item in response.unknowns
    )


def test_broker_response_matches_checked_in_schema(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    response = _service(project_root, discover_settings).get(
        GetCodeContextRequest(
            project=str(project_root),
            task="context broker",
            budget=_budget(),
        )
    )
    schema = json.loads(
        (ROOT / "contracts" / "discover" / "get-code-context-response.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert list(Draft202012Validator(schema).iter_errors(response.to_json_dict())) == []


def test_broker_retains_bounded_support_artifact_related_to_selected_source(
    project_root: Path,
    discover_settings,
) -> None:
    _write_fixture(project_root)
    docs = project_root / "docs"
    docs.mkdir()
    (docs / "context_broker-contract.md").write_text(
        "# Lifecycle notes\nThis file intentionally does not name the requested method.\n",
        encoding="utf-8",
    )
    request = GetCodeContextRequest(
        project=str(project_root),
        task="assemble behavior",
        budget=_budget(max_files=3),
    )

    response = _service(project_root, discover_settings).get(request)
    paths = tuple(item.path for item in response.files)

    assert "src/context_broker.py" in paths
    assert "docs/context_broker-contract.md" in paths
    support = next(item for item in response.files if item.path == "docs/context_broker-contract.md")
    assert support.category == "documentation"
