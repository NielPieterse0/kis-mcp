from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.discover.errors import DiscoverError
from kis_mcp.discover.project_catalog import (
    ProjectCatalogBudget,
    ProjectCatalogRequest,
    ProjectCatalogService,
)


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def _request(projects: list[Path], **overrides: int) -> ProjectCatalogRequest:
    budget = {
        "max_projects": 20,
        "max_manifests": 40,
        "max_relationships": 40,
        "max_unknowns": 40,
    }
    budget.update(overrides)
    return ProjectCatalogRequest(
        projects=tuple(str(path) for path in projects),
        budget=ProjectCatalogBudget(**budget),
    )


def test_catalog_detects_only_selected_static_relationships_and_is_deterministic(
    tmp_path: Path,
    discover_settings,
) -> None:
    app = tmp_path / "app"
    lib = tmp_path / "lib"
    shared = tmp_path / "shared"
    unselected = tmp_path / "unselected"
    for root in (app, lib, shared, unselected):
        root.mkdir()

    _write(
        app,
        "package.json",
        json.dumps(
            {
                "name": "app",
                "dependencies": {
                    "lib": "file:../lib",
                    "missing": "link:../unselected",
                    "registry": "^1.0.0",
                },
            }
        ),
    )
    _write(
        lib,
        "pyproject.toml",
        """
[project]
name = "lib"

[tool.poetry.dependencies]
shared = { path = "../shared", develop = true }

[tool.uv.sources]
shared-alt = { path = "../shared" }
""".strip(),
    )
    _write(shared, "shared.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>")
    _write(
        app,
        "app.csproj",
        """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="..\\shared\\shared.csproj" />
  </ItemGroup>
</Project>
""".strip(),
    )
    # This malformed sibling must remain invisible because it is not selected.
    _write(unselected, "package.json", "{not-json")

    service = ProjectCatalogService(boundary=tmp_path, settings=discover_settings)
    first = service.inspect(_request([app, lib, shared]))
    second = service.inspect(_request([app, lib, shared]))

    assert first == second
    assert tuple(Path(item.project.canonical_path).name for item in first.projects) == (
        "app",
        "lib",
        "shared",
    )
    assert tuple(
        (
            Path(item.source_project.canonical_path).name,
            Path(item.target_project.canonical_path).name,
            item.relationship_type,
            item.source_manifest,
            item.subject,
        )
        for item in first.relationships
    ) == (
        ("app", "lib", "npm_local_dependency", "package.json", "lib"),
        ("app", "shared", "dotnet_project_reference", "app.csproj", "shared"),
        ("lib", "shared", "python_path_dependency", "pyproject.toml", "shared"),
        ("lib", "shared", "python_path_dependency", "pyproject.toml", "shared-alt"),
    )
    assert {item.code for item in first.unknowns} == {
        "UNSELECTED_PROJECT_REFERENCE"
    }
    assert "unselected" in first.unknowns[0].candidate_path
    assert all("unselected/package.json" not in item.path for item in first.manifests)
    assert len(first.fingerprint) == 64


def test_catalog_adds_nested_selected_project_relationship(
    tmp_path: Path,
    discover_settings,
) -> None:
    parent = tmp_path / "workspace"
    child = parent / "packages" / "child"
    child.mkdir(parents=True)

    response = ProjectCatalogService(
        boundary=tmp_path,
        settings=discover_settings,
    ).inspect(_request([parent, child]))

    assert len(response.relationships) == 1
    relation = response.relationships[0]
    assert relation.relationship_type == "contains_selected_project"
    assert Path(relation.source_project.canonical_path) == parent
    assert Path(relation.target_project.canonical_path) == child
    assert relation.source_manifest is None
    assert relation.provenance == "explicit_selection"


def test_catalog_applies_exact_global_budgets(
    tmp_path: Path,
    discover_settings,
) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    third = tmp_path / "c"
    for root in (first, second, third):
        root.mkdir()
    _write(
        first,
        "package.json",
        json.dumps(
            {
                "name": "a",
                "dependencies": {
                    "b": "file:../b",
                    "c": "file:../c",
                    "missing": "file:../missing",
                },
            }
        ),
    )
    _write(second, "package.json", json.dumps({"name": "b"}))
    _write(third, "package.json", json.dumps({"name": "c"}))

    response = ProjectCatalogService(
        boundary=tmp_path,
        settings=discover_settings,
    ).inspect(
        _request(
            [first, second, third],
            max_projects=2,
            max_manifests=1,
            max_relationships=1,
            max_unknowns=1,
        )
    )

    assert len(response.projects) == 2
    assert len(response.manifests) == 1
    assert len(response.relationships) <= 1
    assert len(response.unknowns) <= 1
    assert response.omissions.projects == 1
    assert response.omissions.manifests >= 1
    assert response.truncated is True
    assert "max_projects" in response.truncation_reasons
    assert "max_manifests" in response.truncation_reasons


def test_catalog_reports_malformed_selected_manifest_without_failing_other_projects(
    tmp_path: Path,
    discover_settings,
) -> None:
    broken = tmp_path / "broken"
    healthy = tmp_path / "healthy"
    broken.mkdir()
    healthy.mkdir()
    _write(broken, "package.json", "{not-json")
    _write(healthy, "package.json", json.dumps({"name": "healthy"}))

    response = ProjectCatalogService(
        boundary=tmp_path,
        settings=discover_settings,
    ).inspect(_request([broken, healthy]))

    assert len(response.projects) == 2
    assert {item.code for item in response.unknowns} == {"MANIFEST_PARSE_FAILED"}
    assert response.confidence.value == "medium"


def test_catalog_rejects_duplicate_canonical_selection(
    tmp_path: Path,
    discover_settings,
) -> None:
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(DiscoverError) as raised:
        ProjectCatalogService(boundary=tmp_path, settings=discover_settings).inspect(
            _request([project, project])
        )

    assert raised.value.code == "DISCOVER_PROJECT_CATALOG_DUPLICATE"


def test_catalog_rejects_empty_or_outside_selection(
    tmp_path: Path,
    discover_settings,
) -> None:
    with pytest.raises(ValueError):
        ProjectCatalogRequest(
            projects=(),
            budget=ProjectCatalogBudget(1, 1, 1, 1),
        )

    outside = tmp_path.parent / "outside-project-catalog"
    outside.mkdir(exist_ok=True)
    with pytest.raises(DiscoverError) as raised:
        ProjectCatalogService(boundary=tmp_path, settings=discover_settings).inspect(
            _request([outside])
        )
    assert raised.value.code == "DISCOVER_PATH_OUTSIDE_ROOT"


def test_catalog_request_and_response_are_schema_valid(
    tmp_path: Path,
    discover_settings,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "package.json", json.dumps({"name": "project"}))
    request = _request([project])
    response = ProjectCatalogService(
        boundary=tmp_path,
        settings=discover_settings,
    ).inspect(request)

    contracts = Path(__file__).parents[3] / "contracts" / "discover"
    request_schema = json.loads(
        (contracts / "project-catalog-request.schema.json").read_text(encoding="utf-8")
    )
    response_schema = json.loads(
        (contracts / "project-catalog-response.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(request_schema).validate(request.to_json_dict())
    Draft202012Validator(response_schema).validate(response.to_json_dict())


def test_project_catalog_package_has_no_execution_network_or_git_dependencies() -> None:
    package = Path(__file__).parents[3] / "src" / "kis_mcp" / "discover" / "project_catalog"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(package.glob("*.py"))
    ).casefold()
    for forbidden in (
        "import subprocess",
        "import socket",
        "import requests",
        "import httpx",
        "import urllib",
        "gitlocalinspector",
        "from github",
        "from kis_mcp.server",
    ):
        assert forbidden not in source
