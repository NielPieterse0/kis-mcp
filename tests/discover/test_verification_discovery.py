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
