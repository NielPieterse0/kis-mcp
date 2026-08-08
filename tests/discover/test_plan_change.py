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
