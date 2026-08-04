from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from kis_mcp.discover.settings import DiscoverLimits, DiscoverSettings


@pytest.fixture
def discover_settings() -> DiscoverSettings:
    return DiscoverSettings(
        enabled=True,
        limits=DiscoverLimits(
            max_files=100,
            max_directories=100,
            max_total_bytes=1_000_000,
            max_file_bytes=1_000,
            max_evidence=100,
            max_output_chars=100_000,
            max_depth=8,
            max_visited_entries=1_000,
            traversal_timeout_seconds=30,
            git_timeout_seconds=5,
            git_max_output_bytes=20_000,
            git_history_limit=20,
            git_metadata_max_bytes=4096,
            python_max_nodes=10_000,
            python_max_records=1_000,
        ),
        excluded_segments=(
            ".git",
            ".work",
            ".temp",
            ".kis-mcp",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "build",
            "dist",
            "coverage",
        ),
        allowed_extensions=(
            ".c",
            ".cpp",
            ".cs",
            ".csproj",
            ".fsproj",
            ".go",
            ".gradle",
            ".graphql",
            ".java",
            ".json",
            ".kt",
            ".kts",
            ".lock",
            ".md",
            ".proto",
            ".ps1",
            ".py",
            ".rs",
            ".sh",
            ".sln",
            ".slnx",
            ".sql",
            ".toml",
            ".ts",
            ".txt",
            ".vbproj",
            ".xml",
            ".yaml",
            ".yml",
            ".properties",
        ),
        allowed_filenames=(
            "Makefile",
            "Dockerfile",
            "Procfile",
            "Justfile",
            "CMakeLists.txt",
            "go.mod",
            "go.sum",
            "Cargo.lock",
            "Pipfile",
            "Pipfile.lock",
            "poetry.lock",
            "uv.lock",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "gradlew",
            "gradlew.bat",
        ),
        text_encodings=("utf-8", "utf-8-sig", "utf-16"),
        reject_hard_links=True,
    )


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    return root


def with_limits(settings: DiscoverSettings, **overrides: int) -> DiscoverSettings:
    return replace(settings, limits=replace(settings.limits, **overrides))
