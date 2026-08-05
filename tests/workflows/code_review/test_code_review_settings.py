from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.workflows.code_review.settings import (
    AgentSettingsError,
    load_agent_settings,
    load_agent_settings_or_disabled,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_load_agent_settings_reads_strict_checked_in_configuration() -> None:
    settings = load_agent_settings(REPOSITORY_ROOT)

    assert settings.enabled is True
    assert settings.agent_id == "code-reviewer"
    assert settings.preferred_backend == "nvidia-nim"
    assert settings.fallback_backend == "codex-cli"
    assert settings.max_evidence_chars == 120000
    assert settings.max_output_chars == 30000
    assert settings.nvidia.base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.nvidia.model == "meta/llama-3.3-70b-instruct"
    assert settings.nvidia.api_key_env == "NVIDIA_API_KEY"
    assert settings.codex.script_path == REPOSITORY_ROOT / "scripts" / "invoke-codex-agent.ps1"


def test_load_agent_settings_rejects_unknown_backend(tmp_path: Path) -> None:
    root = tmp_path
    settings_dir = root / "settings" / "agents"
    settings_dir.mkdir(parents=True)
    document = {
        "schema_version": 1,
        "enabled": True,
        "agent_id": "code-reviewer",
        "preferred_backend": "unknown",
        "fallback_backend": None,
        "max_evidence_chars": 1000,
        "max_output_chars": 1000,
        "nvidia": {
            "enabled": False,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "model": "model",
            "api_key_env": "NVIDIA_API_KEY",
            "timeout_seconds": 30,
            "temperature": 0.1,
            "max_tokens": 500,
        },
        "codex": {
            "enabled": False,
            "script_path": "scripts/invoke-codex-agent.ps1",
            "executable": "codex",
            "timeout_seconds": 30,
            "max_output_chars": 1000,
        },
    }
    (settings_dir / "code-review-agent.settings.json").write_text(
        json.dumps(document), encoding="utf-8"
    )

    with pytest.raises(AgentSettingsError, match="preferred_backend"):
        load_agent_settings(root)


def test_load_agent_settings_rejects_non_https_nvidia_url(tmp_path: Path) -> None:
    root = tmp_path
    settings_dir = root / "settings" / "agents"
    settings_dir.mkdir(parents=True)
    source = json.loads(
        (REPOSITORY_ROOT / "settings" / "agents" / "code-review-agent.settings.json").read_text(
            encoding="utf-8"
        )
    )
    source["nvidia"]["base_url"] = "http://example.invalid/v1"
    (settings_dir / "code-review-agent.settings.json").write_text(
        json.dumps(source), encoding="utf-8"
    )

    with pytest.raises(AgentSettingsError, match="https"):
        load_agent_settings(root)


def test_safe_loader_disables_optional_agent_when_settings_are_missing(
    tmp_path: Path,
) -> None:
    settings = load_agent_settings_or_disabled(tmp_path)

    assert settings.enabled is False
    assert settings.nvidia.enabled is False
    assert settings.codex.enabled is False
    assert settings.nvidia.model == "meta/llama-3.3-70b-instruct"
    assert settings.codex.script_path == (
        tmp_path / "scripts" / "invoke-codex-agent.ps1"
    ).resolve()
