from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kis_mcp.discover.contracts import InspectProjectRequest
from kis_mcp.discover.errors import DiscoverError


def _write(root: Path, label: str, content: str) -> None:
    path = root / Path(label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
    )


def _fixture(root: Path) -> None:
    _write(
        root,
        "pyproject.toml",
        """
[project]
name = "inspect-example"
dependencies = ["fastmcp==3.4.4", "pytest>=8.4"]

[project.scripts]
inspect-example = "example.cli:main"

[tool.pytest.ini_options]
addopts = "-q"
""".strip()
        + "\n",
    )
    _write(root, "uv.lock", "version = 1\n")
    _write(root, "src/example/__init__.py", "from .service import Service\n")
    _write(
        root,
        "src/example/service.py",
        """
class Service:
    def run(self):
        return helper()

def helper():
    return 1
""".strip()
        + "\n",
    )
    _write(root, "tests/test_service.py", "import pytest\n\ndef test_service(): pass\n")
    _write(root, "AGENTS.md", "# Repository instructions\n")
    _write(root, "docs/ARCHITECTURE.md", "# Architecture\n")
    _write(root, "scripts/verify.ps1", "Write-Host verified\n")
    _write(root, "openapi.yaml", "openapi: 3.1.0\ninfo: {title: Example, version: 1}\n")
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Discover Tests")
    _git(root, "config", "user.email", "discover@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")


def _service(settings):
    from kis_mcp.discover.service import InspectProjectService

    return InspectProjectService(boundary=Path(r"C:\Projects"), settings=settings)


def test_inspect_project_composes_local_repository_evidence(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)

    response = _service(discover_settings).inspect(
        InspectProjectRequest(path=str(project_root))
    )
    payload = response.to_json_dict()

    assert response.project.canonical_path == str(project_root.resolve())
    assert response.project.git_root == str(project_root.resolve())
    assert response.git.available is True
    assert response.git.branch == "main"
    assert response.repository_atlas["project_name"] == "inspect-example"
    assert response.repository_atlas["topology"]["file_count"] >= 9
    assert {
        item["language"]: item["files"]
        for item in response.repository_atlas["languages"]
    } == {"Python": 3, "PowerShell": 1}
    assert {item["path"] for item in response.repository_atlas["manifests"]} == {
        "pyproject.toml"
    }
    assert "FastMCP" in response.repository_atlas["frameworks"]
    assert response.code_atlas["language"] == "python"
    assert "example.service.Service" in {
        item["qualified_name"] for item in response.code_atlas["symbols"]
    }
    assert {
        item["id"] for item in response.verification["declarations"]
    }.issuperset({"python-pytest", "python-uv-lock-check", "powershell-verify-script"})
    assert response.contracts["artifacts"] == [
        {"kind": "openapi", "path": "openapi.yaml"}
    ]
    assert response.instructions[0]["path"] == "AGENTS.md"
    assert response.providers == {
        "filesystem": {"available": True, "provider": "local_filesystem"},
        "git": {"available": True, "provider": "local_git"},
        "remote": {"available": False, "reason": "not_configured"},
        "semantic": {"available": False, "reason": "not_configured"},
    }
    assert {item.code for item in response.unknowns} == {
        "REMOTE_EVIDENCE_UNAVAILABLE",
        "SEMANTIC_PROVIDER_UNAVAILABLE",
    }
    assert response.confidence.value == "high"
    assert response.truncated is False
    assert response.truncation_reasons == ()
    assert payload["schema_version"] == 1
    assert payload["tool"] == "inspect_project"

    evidence_ids = {item.id for item in response.evidence}
    for handoff in response.handoffs:
        assert set(handoff.evidence_ids).issubset(evidence_ids)
        assert handoff.target_plane == "work"
        assert handoff.workflow == "run_verification"


def test_request_limits_narrow_scanning_without_broadening_settings(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)

    response = _service(discover_settings).inspect(
        InspectProjectRequest(path=str(project_root), limits={"max_files": 3})
    )

    assert response.repository_atlas["topology"]["file_count"] == 3
    assert response.truncated is True
    assert "max_files" in response.truncation_reasons


def test_invalid_request_limits_return_structural_discover_error(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)

    with pytest.raises(DiscoverError) as raised:
        _service(discover_settings).inspect(
            InspectProjectRequest(
                path=str(project_root),
                limits={"max_files": discover_settings.limits.max_files + 1},
            )
        )

    assert raised.value.code == "DISCOVER_LIMIT_INVALID"
    assert raised.value.field == "limits.max_files"
    assert raised.value.retryable is False
    assert "HR-" not in raised.value.code
