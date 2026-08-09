from __future__ import annotations

import importlib
from copy import deepcopy

import pytest


VALID_DISCOVER_SETTINGS = {
    "enabled": True,
    "limits": {
        "max_files": 5000,
        "max_directories": 1000,
        "max_total_bytes": 20_000_000,
        "max_file_bytes": 512_000,
        "max_evidence": 500,
        "max_output_chars": 1_000_000,
        "max_depth": 12,
        "max_visited_entries": 50_000,
        "traversal_timeout_seconds": 30,
        "git_timeout_seconds": 5,
        "git_max_output_bytes": 200_000,
        "git_history_limit": 20,
        "git_metadata_max_bytes": 4096,
        "python_max_nodes": 200_000,
        "python_max_records": 2_000,
    },
    "excluded_segments": [
        ".git",
        ".work",
        ".temp",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "build",
        "dist",
        "coverage",
    ],
    "allowed_extensions": [".py", ".toml", ".json", ".md", ".yml", ".yaml"],
    "allowed_filenames": ["Makefile", "Dockerfile", "CMakeLists.txt"],
    "text_encodings": ["utf-8", "utf-8-sig", "utf-16"],
    "reject_hard_links": True,
    "memory": {
        "schema_version": 1,
        "enabled": True,
        "state_root": r"C:\Projects\.kis-mcp\discover",
        "max_stored_bytes": 25_000_000,
        "max_files": 5_000,
        "max_modules": 5_000,
        "max_symbols": 10_000,
        "max_relationships": 20_000,
        "fingerprint_fields": [
            "git_revision",
            "dirty_tree",
            "settings",
            "provider_version",
        ],
        "provider_inclusion": ["serena"],
        "corruption_handling": "refresh_and_retain",
        "supersession_behavior": "retain_generations",
    },
}


def _settings_module():
    return importlib.import_module("kis_mcp.discover.settings")


def test_discover_settings_parse_exact_json_contract() -> None:
    settings_module = _settings_module()

    settings = settings_module.DiscoverSettings.from_mapping(VALID_DISCOVER_SETTINGS)

    assert settings.enabled is True
    assert settings.limits.max_files == 5000
    assert settings.limits.max_output_chars == 1_000_000
    assert settings.excluded_segments[0] == ".git"
    assert settings.allowed_extensions == (
        ".py",
        ".toml",
        ".json",
        ".md",
        ".yml",
        ".yaml",
    )
    assert settings.allowed_filenames == (
        "Makefile",
        "Dockerfile",
        "CMakeLists.txt",
    )
    assert settings.text_encodings == ("utf-8", "utf-8-sig", "utf-16")
    assert settings.reject_hard_links is True
    assert settings.memory.enabled is True
    assert settings.memory.state_root == r"C:\Projects\.kis-mcp\discover"
    assert settings.memory.provider_inclusion == ("serena",)


def test_checked_in_runtime_exposes_discover_settings() -> None:
    from pathlib import Path

    from kis_mcp.config import load_runtime_config

    repository_root = Path(__file__).resolve().parents[2]
    config = load_runtime_config(repository_root)

    assert config.discover_settings.enabled is True
    assert config.discover_settings.limits.max_files == 5000
    assert "discover" in config.raw_settings
    assert {".csproj", ".fsproj", ".vbproj", ".sln", ".gradle", ".lock"}.issubset(
        set(config.discover_settings.allowed_extensions)
    )
    assert ".kis-mcp" in config.discover_settings.excluded_segments


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"unknown": True}), "unsupported keys"),
        (lambda value: value.pop("limits"), "must contain exactly"),
        (
            lambda value: value["limits"].update({"unexpected": 1}),
            "must contain exactly",
        ),
        (lambda value: value["limits"].pop("max_files"), "must contain exactly"),
        (lambda value: value["limits"].update({"max_files": True}), "positive integer"),
        (lambda value: value["limits"].update({"max_files": 0}), "positive integer"),
        (lambda value: value.update({"enabled": "yes"}), "must be a boolean"),
        (
            lambda value: value.update({"allowed_extensions": ["PY"]}),
            "lowercase suffix",
        ),
        (
            lambda value: value.update({"text_encodings": ["not-an-encoding"]}),
            "Unsupported text encoding",
        ),
    ],
)
def test_discover_settings_reject_invalid_shapes(mutation, message: str) -> None:
    settings_module = _settings_module()
    value = deepcopy(VALID_DISCOVER_SETTINGS)
    mutation(value)

    with pytest.raises(ValueError, match=message):
        settings_module.DiscoverSettings.from_mapping(value)


def test_request_limits_may_narrow_but_not_broaden_configuration() -> None:
    settings_module = _settings_module()
    limits = settings_module.DiscoverSettings.from_mapping(
        VALID_DISCOVER_SETTINGS
    ).limits

    narrowed = limits.narrow(
        {
            "max_files": 50,
            "max_total_bytes": 100_000,
            "max_evidence": 20,
            "max_output_chars": 25_000,
            "max_depth": 4,
        }
    )

    assert narrowed.max_files == 50
    assert narrowed.max_total_bytes == 100_000
    assert narrowed.max_evidence == 20
    assert narrowed.max_output_chars == 25_000
    assert narrowed.max_depth == 4
    assert narrowed.max_file_bytes == limits.max_file_bytes

    with pytest.raises(ValueError, match="max_files.*between 1 and 5000"):
        limits.narrow({"max_files": 5001})
    with pytest.raises(ValueError, match="unsupported request limit"):
        limits.narrow({"git_timeout_seconds": 1})
