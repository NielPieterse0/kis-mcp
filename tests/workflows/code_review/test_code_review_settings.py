from __future__ import annotations

import json
from pathlib import Path

import pytest

from kis_mcp.providers.nvidia import NvidiaSettings
from kis_mcp.tools.codex_cli import CodexSettings
from kis_mcp.workflows.code_review.settings import (
    AgentSettingsError,
    load_agent_settings,
    load_agent_settings_or_disabled,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = REPOSITORY_ROOT / "settings" / "agents" / "code-review-agent.settings.json"


def _checked_in_document() -> dict[str, object]:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def _write_settings(root: Path, document: dict[str, object]) -> None:
    settings_dir = root / "settings" / "agents"
    settings_dir.mkdir(parents=True)
    (settings_dir / "code-review-agent.settings.json").write_text(
        json.dumps(document), encoding="utf-8"
    )


def test_load_agent_settings_reads_strict_checked_in_configuration() -> None:
    settings = load_agent_settings(REPOSITORY_ROOT)

    assert settings.enabled is True
    assert settings.agent_id == "code-reviewer"
    assert settings.preferred_backend == "nvidia-nim"
    assert settings.fallback_backend == "codex-cli"
    assert settings.max_evidence_chars == 120000
    assert settings.max_output_chars == 30000
    assert isinstance(settings.nvidia, NvidiaSettings)
    assert isinstance(settings.codex, CodexSettings)
    assert settings.nvidia.base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.nvidia.api_key_env == "NVIDIA_API_KEY"
    assert settings.nvidia.secret_ref == "secret://provider/nvidia-nim/api-key"
    assert settings.nvidia.default_profile == "super"
    assert set(settings.nvidia.profiles) == {"nano", "super", "ultra"}
    assert settings.nvidia.benchmark.enabled is True
    assert settings.nvidia.benchmark.timeout_seconds == 40
    assert settings.nvidia.benchmark.latency_limit_seconds == 30
    assert settings.nvidia.benchmark.models["laguna-xs"] == "poolside/laguna-xs-2.1"
    assert "deepseek-flash" in settings.nvidia.benchmark.models
    assert "step-3.7-flash" in settings.nvidia.benchmark.models
    assert settings.nvidia.profile("nano").model == (
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    )
    assert settings.nvidia.profile("nano").max_tokens == 65536
    assert settings.nvidia.profile("nano").reasoning_budget == 16384
    assert settings.nvidia.profile("super").model == "nvidia/nemotron-3-super-120b-a12b"
    assert settings.nvidia.profile("super").temperature == 1.0
    assert settings.nvidia.profile("ultra").model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert settings.nvidia.profile("ultra").enable_thinking is True
    assert settings.codex.script_path == REPOSITORY_ROOT / "scripts" / "invoke-codex-agent.ps1"


def test_load_agent_settings_rejects_unknown_backend(tmp_path: Path) -> None:
    document = _checked_in_document()
    document["preferred_backend"] = "unknown"
    document["fallback_backend"] = None
    _write_settings(tmp_path, document)

    with pytest.raises(AgentSettingsError, match="preferred_backend"):
        load_agent_settings(tmp_path)


def test_load_agent_settings_rejects_non_https_nvidia_url(tmp_path: Path) -> None:
    document = _checked_in_document()
    document["nvidia"]["base_url"] = "http://example.invalid/v1"
    _write_settings(tmp_path, document)

    with pytest.raises(AgentSettingsError, match="https"):
        load_agent_settings(tmp_path)


def test_load_agent_settings_requires_exact_nvidia_profile_set(tmp_path: Path) -> None:
    missing = _checked_in_document()
    del missing["nvidia"]["profiles"]["ultra"]
    _write_settings(tmp_path, missing)

    with pytest.raises(AgentSettingsError, match="profiles"):
        load_agent_settings(tmp_path)

    extra_root = tmp_path / "extra"
    extra = _checked_in_document()
    extra["nvidia"]["profiles"]["other"] = dict(extra["nvidia"]["profiles"]["super"])
    _write_settings(extra_root, extra)

    with pytest.raises(AgentSettingsError, match="profiles"):
        load_agent_settings(extra_root)


def test_safe_loader_disables_optional_agent_when_settings_are_missing(
    tmp_path: Path,
) -> None:
    settings = load_agent_settings_or_disabled(tmp_path)

    assert settings.enabled is False
    assert settings.nvidia.enabled is False
    assert settings.codex.enabled is False
    assert settings.nvidia.default_profile == "super"
    assert settings.nvidia.profile("super").model == "nvidia/nemotron-3-super-120b-a12b"
    assert settings.codex.script_path == (
        tmp_path / "scripts" / "invoke-codex-agent.ps1"
    ).resolve()


def test_load_agent_settings_rejects_duplicate_benchmark_model_ids(tmp_path: Path) -> None:
    document = _checked_in_document()
    models = document["nvidia"]["benchmark"]["models"]
    models["duplicate-super"] = models["baseline-super"]
    _write_settings(tmp_path, document)

    with pytest.raises(AgentSettingsError, match="duplicate model IDs"):
        load_agent_settings(tmp_path)


def test_load_agent_settings_rejects_noncanonical_https_nvidia_url(tmp_path: Path) -> None:
    document = _checked_in_document()
    document["nvidia"]["base_url"] = "https://example.invalid/v1"
    _write_settings(tmp_path, document)

    with pytest.raises(AgentSettingsError, match="integrate.api.nvidia.com"):
        load_agent_settings(tmp_path)
