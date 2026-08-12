from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner


def _write(root: Path, label: str, content: str) -> None:
    path = root / Path(label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _discover(project_root: Path, settings, *, max_candidates: int | None = None):
    from kis_mcp.discover.verification import VerificationDiscoveryService

    authority = ReadAuthority(Path(r"C:\Projects"), settings)
    snapshot = RepositoryScanner(authority, settings).snapshot(str(project_root))
    return VerificationDiscoveryService(
        authority=authority,
        settings=settings,
        max_candidates=max_candidates,
    ).discover(str(project_root), snapshot)


def test_discovers_python_node_powershell_and_ci_without_execution(
    project_root: Path,
    discover_settings,
) -> None:
    marker = project_root / "must-not-exist.txt"
    _write(
        project_root,
        "pyproject.toml",
        """
[project]
name = "verification-example"

[tool.pytest.ini_options]
addopts = "-q"
""".strip()
        + "\n",
    )
    _write(project_root, "uv.lock", "version = 1\n")
    _write(project_root, "tests/test_unit.py", "import pytest\n\ndef test_ok(): pass\n")
    _write(
        project_root,
        "package.json",
        json.dumps(
            {
                "scripts": {
                    "build": "python -c \"open('must-not-exist.txt','w').write('bad')\"",
                    "lint": "eslint .",
                    "test": "vitest run",
                    "test:e2e": "playwright test",
                    "typecheck": "tsc --noEmit",
                    "verify": "npm run lint && npm test",
                }
            }
        ),
    )
    _write(project_root, "repository.ps1", "Write-Host repository-check\n")
    _write(project_root, "scripts/verify.ps1", "Write-Host verified\n")
    _write(project_root, "scripts/verify.py", "print('verified')\n")
    _write(
        project_root,
        ".github/workflows/ci.yml",
        """
steps:
  - run: python -m pytest -q
  - run: npm run lint
  - run: |
      python -m unittest discover -s tests -v
      python -m pytest -q
""".strip()
        + "\n",
    )

    result = _discover(project_root, discover_settings)

    by_id = {item.id: item for item in result.declarations}
    assert {
        "node-script-build",
        "node-script-lint",
        "node-script-test",
        "node-script-test-e2e",
        "node-script-typecheck",
        "node-script-verify",
        "powershell-repository-check",
        "powershell-verify-script",
        "python-module-verify",
        "python-pytest",
        "python-unittest-discover",
        "python-uv-lock-check",
    }.issubset(by_id)
    assert by_id["python-pytest"].arguments == ("-m", "pytest", "-q")
    assert by_id["node-script-lint"].arguments == ("run", "lint")
    assert by_id["powershell-verify-script"].arguments == (
        "-NoProfile",
        "-File",
        ".\\scripts\\verify.ps1",
    )
    assert all(item.authority == "discovered_only" for item in result.declarations)
    assert all(item.execution_available is False for item in result.declarations)
    assert len({item.id for item in result.declarations}) == len(result.declarations)
    assert marker.exists() is False
    assert result.truncated is False
    assert result.diagnostics == ()
    assert set(result.evidence_sources) == {
        "github_actions",
        "package_json",
        "powershell",
        "pyproject",
        "python_tests",
        "uv",
    }


def test_discovers_declared_python_quality_tooling_without_execution(
    project_root: Path,
    discover_settings,
) -> None:
    _write(
        project_root,
        "pyproject.toml",
        """
[project]
name = "quality-example"
dependencies = ["LibCST>=1", "pyright>=1"]

[project.optional-dependencies]
quality = ["coverage>=7", "pytest-cov>=6"]

[dependency-groups]
dev = ["ruff>=0.12", "vulture>=2", "mypy>=1"]

[tool.ruff]
line-length = 100

[tool.coverage.run]
branch = true
""".strip()
        + "\n",
    )

    result = _discover(project_root, discover_settings)

    tooling = {item.id: item for item in result.quality_tools}
    assert list(tooling) == ["coverage", "libcst", "mypy", "pyright", "ruff", "vulture"]
    assert tooling["coverage"].package == "pytest-cov"
    assert tooling["coverage"].role == "coverage"
    assert tooling["coverage"].declared_via == "optional_dependency:quality"
    assert tooling["coverage"].confidence.value == "high"
    assert tooling["libcst"].role == "concrete_syntax"
    assert tooling["libcst"].verification_id is None
    assert tooling["pyright"].role == "typecheck"
    assert tooling["pyright"].verification_id == "python-pyright"
    assert tooling["ruff"].verification_id == "python-ruff-check"
    assert tooling["vulture"].verification_id == "python-vulture"
    assert tooling["mypy"].verification_id == "python-mypy"

    by_id = {item.id: item for item in result.declarations}
    assert by_id["python-ruff-check"].arguments == ("-m", "ruff", "check", ".")
    assert by_id["python-coverage-pytest"].arguments == (
        "-m",
        "coverage",
        "run",
        "-m",
        "pytest",
        "-q",
    )
    assert by_id["python-vulture"].arguments == (
        "-m",
        "vulture",
        ".",
        "--min-confidence",
        "80",
    )
    assert by_id["python-mypy"].arguments == ("-m", "mypy", ".")
    assert by_id["python-pyright"].arguments == ("-m", "pyright", ".")
    assert "python-libcst" not in by_id
    assert all(item.execution_available is False for item in result.declarations)
    assert "python_quality_tools" in result.evidence_sources


def test_config_only_quality_tooling_is_medium_confidence(
    project_root: Path,
    discover_settings,
) -> None:
    _write(
        project_root,
        "pyproject.toml",
        """
[project]
name = "config-only-quality"

[tool.ruff]
line-length = 88

[tool.vulture]
min_confidence = 90
""".strip()
        + "\n",
    )

    result = _discover(project_root, discover_settings)

    tooling = {item.id: item for item in result.quality_tools}
    assert list(tooling) == ["ruff", "vulture"]
    assert tooling["ruff"].declared_via == "tool_config:ruff"
    assert tooling["ruff"].confidence.value == "medium"
    assert tooling["vulture"].declared_via == "tool_config:vulture"
    assert tooling["vulture"].confidence.value == "medium"
    assert {item.id for item in result.declarations} == {
        "python-ruff-check",
        "python-vulture",
    }


def test_malformed_pyproject_returns_diagnostic_and_keeps_other_workflows(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "pyproject.toml", "[project\nname = 'broken'\n")
    _write(project_root, "scripts/verify.ps1", "Write-Host verified\n")

    result = _discover(project_root, discover_settings)

    assert result.quality_tools == ()
    assert [item.id for item in result.declarations] == ["powershell-verify-script"]
    assert [item.code for item in result.diagnostics] == ["WORKFLOW_PYPROJECT_INVALID"]
    assert result.diagnostics[0].path == "pyproject.toml"


def test_malformed_package_json_returns_diagnostic(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "package.json", "{not-json")
    _write(project_root, "scripts/verify.ps1", "Write-Host verified\n")

    result = _discover(project_root, discover_settings)

    assert [item.id for item in result.declarations] == ["powershell-verify-script"]
    assert [item.code for item in result.diagnostics] == [
        "WORKFLOW_PACKAGE_JSON_INVALID"
    ]
    assert result.diagnostics[0].path == "package.json"
    assert result.truncated is False


def test_candidate_limit_returns_deterministic_partial_result(
    project_root: Path,
    discover_settings,
) -> None:
    _write(
        project_root,
        "package.json",
        json.dumps(
            {
                "scripts": {
                    "verify": "echo verify",
                    "test": "echo test",
                    "lint": "echo lint",
                }
            }
        ),
    )

    first = _discover(project_root, discover_settings, max_candidates=2)
    second = _discover(project_root, discover_settings, max_candidates=2)

    assert [item.id for item in first.declarations] == [
        "node-script-lint",
        "node-script-test",
    ]
    assert first.to_json_dict() == second.to_json_dict()
    assert first.truncated is True
    assert [item.code for item in first.diagnostics] == [
        "WORKFLOW_DISCOVERY_LIMIT_REACHED"
    ]


def test_candidate_limit_may_narrow_but_not_broaden_settings(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.verification import VerificationDiscoveryService

    authority = ReadAuthority(Path(r"C:\Projects"), discover_settings)

    service = VerificationDiscoveryService(
        authority=authority,
        settings=discover_settings,
        max_candidates=discover_settings.limits.max_evidence + 100,
    )

    assert service.max_candidates == discover_settings.limits.max_evidence
