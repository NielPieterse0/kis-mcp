from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.skills.config import (
    APPROVED_SKILLS_ROOT,
    APPROVED_SKILLS_STAGING_ROOT,
    load_skills_config,
)


def _write_settings(root: Path, payload: dict[str, object]) -> None:
    settings = root / "settings"
    settings.mkdir(parents=True)
    (settings / "skills.settings.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "root": APPROVED_SKILLS_ROOT,
        "staging_root": APPROVED_SKILLS_STAGING_ROOT,
        "required_skills": ["kis-mcp"],
        "limits": {
            "max_file_bytes": 2_000_000,
            "max_skill_bytes": 3_000_000,
            "list_default_limit": 20,
            "list_max_limit": 100,
            "search_default_limit": 10,
            "search_max_limit": 50,
            "file_search_default_limit": 20,
            "file_search_max_limit": 100,
        },
        "validation": {
            "skill_id_pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
            "allowed_suffixes": [
                ".md",
                ".json",
                ".yaml",
                ".yml",
                ".py",
                ".ps1",
                ".sh",
                ".txt",
                ".toml",
                ".png",
                ".svg",
                ".css",
                ".html",
                ".js",
                ".ttl",
            ],
            "allowed_filenames": ["LICENSE"],
            "reject_links": True,
            "reject_reparse_points": True,
            "reject_hard_links": True,
            "reject_backslashes": True,
        },
    }


def test_load_skills_config_accepts_exact_approved_roots(tmp_path: Path) -> None:
    _write_settings(tmp_path, _valid_payload())

    config = load_skills_config(tmp_path)

    assert str(config.root) == APPROVED_SKILLS_ROOT
    assert str(config.staging_root) == APPROVED_SKILLS_STAGING_ROOT
    assert config.required_skills == ("kis-mcp",)
    assert config.limits.max_file_bytes == 2_000_000
    assert config.limits.max_skill_bytes == 3_000_000
    assert config.limits.search_max_limit == 50
    assert config.validation.allowed_suffixes[0] == ".md"
    assert ".svg" in config.validation.allowed_suffixes
    assert ".js" in config.validation.allowed_suffixes
    assert config.validation.allowed_filenames == ("LICENSE",)
    assert config.validation.skill_id_pattern.fullmatch("modularity-assessment")


@pytest.mark.parametrize(
    "required_skills",
    [[], ["kis-mcp", "kis-mcp"], ["KIS MCP"]],
)
def test_load_skills_config_rejects_invalid_required_skills(
    tmp_path: Path, required_skills: list[str]
) -> None:
    payload = _valid_payload()
    payload["required_skills"] = required_skills
    _write_settings(tmp_path, payload)

    with pytest.raises(RuntimeError, match="required_skills"):
        load_skills_config(tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("root", r"C:\Projects\noncanonical-skills"),
        ("staging_root", r"C:\Projects\kis-mcp\.temp\skills"),
    ],
)
def test_load_skills_config_rejects_noncanonical_roots(
    tmp_path: Path, field: str, value: str
) -> None:
    payload = _valid_payload()
    payload[field] = value
    _write_settings(tmp_path, payload)

    with pytest.raises(RuntimeError, match="approved Skills"):
        load_skills_config(tmp_path)


def test_load_skills_config_rejects_incoherent_limits(tmp_path: Path) -> None:
    payload = _valid_payload()
    limits = dict(payload["limits"])
    limits["max_skill_bytes"] = 10
    payload["limits"] = limits
    _write_settings(tmp_path, payload)

    with pytest.raises(RuntimeError, match="limits"):
        load_skills_config(tmp_path)


def test_load_skills_config_requires_closed_validation_shape(tmp_path: Path) -> None:
    payload = _valid_payload()
    validation = dict(payload["validation"])
    validation["unexpected"] = True
    payload["validation"] = validation
    _write_settings(tmp_path, payload)

    with pytest.raises(RuntimeError, match="unexpected"):
        load_skills_config(tmp_path)
