from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from kis_mcp.discover.planning import PlanChangeService
from kis_mcp.discover.planning_contracts import PlanChangeRequest


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
    )


def _fixture(root: Path) -> None:
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "service.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (root / "tests" / "test_service.py").write_text(
        "from src.service import value\n\ndef test_value():\n    assert value() == 1\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text("# Agent instructions\nRun tests.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
        encoding="utf-8",
    )
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Plan Tests")
    _git(root, "config", "user.email", "plan@example.invalid")
    _git(root, "add", "--all")
    _git(root, "commit", "-m", "fixture")


def _claim(root: Path) -> None:
    claim = root / ".work" / "changes" / "001-other"
    claim.mkdir(parents=True)
    (claim / "scope.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "change_id": "001-other",
                "status": "active",
                "owned_paths": ["src/service.py"],
                "shared_paths": [],
                "excluded_paths": [],
            }
        ),
        encoding="utf-8",
    )


def test_plan_change_combines_context_impact_verification_and_claim_conflicts(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    _claim(project_root)
    (project_root / "src" / "service.py").write_text(
        "def value():\n    return 2\n",
        encoding="utf-8",
    )

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="change service value and verify tests",
        )
    )

    payload = result.to_json_dict()
    assert payload["tool"] == "plan_change"
    assert payload["change"]["changed_paths"] == ["src/service.py"]
    assert "AGENTS.md" in payload["authority"]["instructions"]
    assert "tests/test_service.py" in payload["affected"]["tests"]
    assert "python-pytest" in payload["verification"]["ids"]
    assert payload["governance"]["conflicts"][0]["change_id"] == "001-other"
    assert payload["governance"]["conflicts"][0]["paths"] == ["src/service.py"]
    assert payload["execution_performed"] is False


def test_plan_change_supports_pre_change_task_context(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="prepare a safe service change",
        )
    )

    assert result.change.changed_paths == ()
    assert result.affected.context_files
    assert result.execution_performed is False
    assert any(item.code == "NO_CURRENT_CHANGE" for item in result.unknowns)


def test_plan_change_bounds_active_claim_inventory(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    for index in range(5):
        claim = project_root / ".work" / "changes" / f"{index:03d}-other"
        claim.mkdir(parents=True)
        (claim / "scope.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "change_id": f"{index:03d}-other",
                    "status": "active",
                    "owned_paths": [f"src/path_{index}.py"],
                }
            ),
            encoding="utf-8",
        )
    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
        max_claims=2,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="inspect claims before editing",
        )
    )

    assert len(result.governance.active_claims) == 2
    assert result.truncated is True
    assert "active_claims" in result.truncation_reasons


def test_plan_change_classifies_existing_pre_change_source_as_reuse(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="change value behavior",
        )
    )

    assert "src/service.py" in result.change.planned_paths
    assert result.change.planned_impact_fingerprint
    pattern = next(item for item in result.patterns if item.path == "src/service.py")
    assert pattern.classification == "REUSE"


def test_plan_change_classifies_changed_source_as_extend_and_collects_support_surfaces(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    for directory, name in (
        ("docs", "service.md"),
        ("settings", "service.json"),
        ("contracts", "service.schema.json"),
        ("policy", "service.json"),
    ):
        target = project_root / directory
        target.mkdir(exist_ok=True)
        (target / name).write_text("{}\n", encoding="utf-8")
    (project_root / "src" / "service.py").write_text(
        "def value():\n    return 2\n",
        encoding="utf-8",
    )

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="change service value",
        )
    )

    pattern = next(item for item in result.patterns if item.path == "src/service.py")
    assert pattern.classification == "EXTEND"
    assert "docs/service.md" in result.affected.documentation
    assert "settings/service.json" in result.affected.configuration
    assert "contracts/service.schema.json" in result.affected.contracts
    assert "policy/service.json" in result.affected.policy


def test_plan_change_classifies_deleted_source_with_reference_evidence_as_replace(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    _git(project_root, "rm", "src/service.py")

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="replace service value implementation",
        )
    )

    pattern = next(item for item in result.patterns if item.path == "src/service.py")
    assert pattern.classification == "REPLACE"


def test_plan_change_classifies_absent_implementation_as_new(
    project_root: Path,
    discover_settings,
) -> None:
    (project_root / "README.md").write_text("# Empty fixture\n", encoding="utf-8")
    _git(project_root, "init", "-b", "main")
    _git(project_root, "config", "user.name", "Plan Tests")
    _git(project_root, "config", "user.email", "plan@example.invalid")
    _git(project_root, "add", "--all")
    _git(project_root, "commit", "-m", "fixture")

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="add event processor",
        )
    )

    assert result.patterns[0].classification == "NEW"
    assert result.patterns[0].path is None


def test_plan_change_classifies_added_source_as_new(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    (project_root / "src" / "event_processor.py").write_text(
        "def process():\n    return None\n",
        encoding="utf-8",
    )
    _git(project_root, "add", "src/event_processor.py")

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="add event processor",
        )
    )

    pattern = next(item for item in result.patterns if item.path == "src/event_processor.py")
    assert pattern.classification == "NEW"


def test_plan_change_preserves_staged_rename_when_destination_is_modified(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    _git(project_root, "mv", "src/service.py", "src/service_v2.py")
    (project_root / "src" / "service_v2.py").write_text(
        "def value():\n    return 2\n",
        encoding="utf-8",
    )

    result = PlanChangeService(
        boundary=project_root.parent,
        settings=discover_settings,
    ).plan(
        PlanChangeRequest(
            project=str(project_root),
            task="replace service value implementation",
        )
    )

    replacement = next(item for item in result.patterns if item.classification == "REPLACE")
    assert replacement.path == "src/service.py"
    assert not any(
        item.classification == "EXTEND" and item.path == "src/service_v2.py"
        for item in result.patterns
    )
