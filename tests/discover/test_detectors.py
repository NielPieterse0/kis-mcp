from __future__ import annotations

import json
from pathlib import Path

from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.scanner import RepositoryScanner


def _write(root: Path, label: str, content: str) -> None:
    path = root / Path(label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _detect(project_root: Path, settings):
    from kis_mcp.discover.detectors import RepositoryDetector

    authority = ReadAuthority(Path(r"C:\Projects"), settings)
    snapshot = RepositoryScanner(authority, settings).snapshot(str(project_root))
    return RepositoryDetector(authority, settings).detect(str(project_root), snapshot)


def test_detects_languages_manifests_frameworks_and_repository_artifacts(
    project_root: Path,
    discover_settings,
) -> None:
    _write(
        project_root,
        "pyproject.toml",
        """
[project]
name = "example-platform"
dependencies = ["fastmcp==3.4.4", "pytest>=8.4"]

[project.scripts]
example = "example.cli:main"

[build-system]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
addopts = "-q"

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
""".strip()
        + "\n",
    )
    _write(project_root, "uv.lock", "version = 1\n")
    _write(
        project_root,
        "package.json",
        json.dumps(
            {
                "name": "example-ui",
                "packageManager": "npm@11.0.0",
                "workspaces": ["packages/*"],
                "dependencies": {"react": "19.0.0"},
                "scripts": {
                    "test": "vitest run",
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "build": "vite build",
                },
            }
        ),
    )
    _write(project_root, "package-lock.json", "{}\n")
    _write(project_root, "Cargo.toml", "[package]\nname = \"rust-core\"\n")
    _write(project_root, "Cargo.lock", "version = 4\n")
    _write(project_root, "go.mod", "module example.com/project\n")
    _write(project_root, "pom.xml", "<project></project>\n")
    _write(project_root, "build.gradle.kts", "plugins { java }\n")
    _write(project_root, "src/App.csproj", "<Project Sdk=\"Microsoft.NET.Sdk\" />\n")
    _write(project_root, "example.sln", "Microsoft Visual Studio Solution File\n")
    _write(project_root, "CMakeLists.txt", "project(example)\n")
    _write(project_root, "Makefile", "test:\n\t@echo test\n")
    _write(project_root, "Dockerfile", "FROM scratch\n")

    for label, content in (
        ("src/example.py", "def main(): pass\n"),
        ("src/Program.cs", "class Program {}\n"),
        ("ui/index.ts", "export const value = 1\n"),
        ("rust/lib.rs", "pub fn value() {}\n"),
        ("go/main.go", "package main\n"),
        ("java/App.java", "class App {}\n"),
        ("kotlin/App.kt", "class App\n"),
        ("native/main.cpp", "int main() { return 0; }\n"),
        ("native/lib.c", "int value(void) { return 1; }\n"),
        ("scripts/verify.ps1", "Write-Host verified\n"),
        ("scripts/check.sh", "#!/bin/sh\nexit 0\n"),
        ("migrations/001.sql", "create table example(id int);\n"),
    ):
        _write(project_root, label, content)

    _write(project_root, "AGENTS.md", "# Repository instructions\n")
    _write(project_root, "docs/ARCHITECTURE.md", "# Architecture\n")
    _write(project_root, ".github/workflows/ci.yml", "steps:\n  - run: python -m pytest -q\n")
    _write(project_root, "openapi.yaml", "openapi: 3.1.0\ninfo: {title: Example, version: 1}\n")
    _write(project_root, "contracts/example.schema.json", '{"$schema":"https://json-schema.org/draft/2020-12/schema"}\n')
    _write(project_root, "schema.graphql", "type Query { value: Int }\n")
    _write(project_root, "api/example.proto", 'syntax = "proto3";\n')

    result = _detect(project_root, discover_settings)

    assert result.project_name == "example-platform"
    language_counts = {item.language: item.files for item in result.languages}
    assert language_counts["Python"] == 1
    assert language_counts["TypeScript"] == 1
    assert language_counts["Rust"] == 1
    assert language_counts["Go"] == 1
    assert language_counts["Java"] == 1
    assert language_counts["Kotlin"] == 1
    assert language_counts["C#"] == 1
    assert language_counts["C++"] == 1
    assert language_counts["C"] == 1
    assert language_counts["SQL"] == 1
    assert language_counts["PowerShell"] == 1
    assert language_counts["Shell"] == 1

    manifest_paths = {item.path for item in result.manifests}
    assert {
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle.kts",
        "src/App.csproj",
        "example.sln",
        "CMakeLists.txt",
        "Makefile",
        "Dockerfile",
    }.issubset(manifest_paths)
    assert {"FastMCP", "pytest", "React"}.issubset(set(result.frameworks))
    assert {
        "Hatchling",
        "Cargo",
        "Go modules",
        "Maven",
        "Gradle",
        ".NET/MSBuild",
        "CMake",
        "Make",
        "Docker",
    }.issubset(set(result.build_systems))
    assert {"uv", "npm", "Cargo", "Go modules", "Maven", "Gradle", "dotnet"}.issubset(
        set(result.package_managers)
    )
    assert [(item.pattern, item.source_path) for item in result.workspaces] == [
        ("packages/*", "package.json")
    ]
    assert [(item.name, item.target) for item in result.entry_points] == [
        ("example", "example.cli:main")
    ]
    assert result.instructions == ("AGENTS.md",)
    assert "docs/ARCHITECTURE.md" in result.documentation
    assert result.ci == (".github/workflows/ci.yml",)

    contracts = {(item.kind, item.path) for item in result.contract_artifacts}
    assert ("openapi", "openapi.yaml") in contracts
    assert ("json_schema", "contracts/example.schema.json") in contracts
    assert ("graphql", "schema.graphql") in contracts
    assert ("protobuf", "api/example.proto") in contracts
    assert ("database", "migrations/001.sql") in contracts
    assert result.diagnostics == ()
    assert len({item.id for item in result.evidence}) == len(result.evidence)


def test_malformed_manifests_return_diagnostics_and_partial_evidence(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "pyproject.toml", "[project\nname = broken\n")
    _write(project_root, "package.json", "{not-json")
    _write(project_root, "src/example.py", "x = 1\n")

    result = _detect(project_root, discover_settings)

    assert {item.path for item in result.manifests} == {"package.json", "pyproject.toml"}
    assert {item.path for item in result.diagnostics} == {"package.json", "pyproject.toml"}
    assert {item.code for item in result.diagnostics} == {"MANIFEST_PARSE_FAILED"}
    assert {item.language for item in result.languages} == {"Python"}
    assert result.project_name is None


def test_detector_output_is_deterministic(
    project_root: Path,
    discover_settings,
) -> None:
    _write(project_root, "b.py", "b = 1\n")
    _write(project_root, "a.py", "a = 1\n")
    _write(project_root, "AGENTS.md", "# Instructions\n")

    first = _detect(project_root, discover_settings).to_json_dict()
    second = _detect(project_root, discover_settings).to_json_dict()

    assert first == second
