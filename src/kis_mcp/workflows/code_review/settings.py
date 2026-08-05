from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_BACKENDS = frozenset({"nvidia-nim", "codex-cli"})
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "agent_id",
        "preferred_backend",
        "fallback_backend",
        "max_evidence_chars",
        "max_output_chars",
        "nvidia",
        "codex",
    }
)
_NVIDIA_KEYS = frozenset(
    {
        "enabled",
        "base_url",
        "model",
        "api_key_env",
        "timeout_seconds",
        "temperature",
        "max_tokens",
    }
)
_CODEX_KEYS = frozenset(
    {"enabled", "script_path", "executable", "timeout_seconds", "max_output_chars"}
)


class AgentSettingsError(RuntimeError):
    """Raised when the code-review agent settings are invalid."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentSettingsError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise AgentSettingsError(f"{label} has unknown keys: {unknown}")
    if missing:
        raise AgentSettingsError(f"{label} is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AgentSettingsError(f"{label} must be a boolean")
    return value


def _int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentSettingsError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise AgentSettingsError(f"{label} must be between {minimum} and {maximum}")
    return value


def _float(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentSettingsError(f"{label} must be a number")
    normalized = float(value)
    if normalized < minimum or normalized > maximum:
        raise AgentSettingsError(f"{label} must be between {minimum} and {maximum}")
    return normalized


@dataclass(frozen=True, slots=True)
class NvidiaSettings:
    enabled: bool
    base_url: str
    model: str
    api_key_env: str
    timeout_seconds: int
    temperature: float
    max_tokens: int


@dataclass(frozen=True, slots=True)
class CodexSettings:
    enabled: bool
    script_path: Path
    executable: str
    timeout_seconds: int
    max_output_chars: int


@dataclass(frozen=True, slots=True)
class AgentSettings:
    enabled: bool
    agent_id: str
    preferred_backend: str
    fallback_backend: str | None
    max_evidence_chars: int
    max_output_chars: int
    nvidia: NvidiaSettings
    codex: CodexSettings


def _nvidia_settings(value: Any) -> NvidiaSettings:
    document = _mapping(value, "nvidia")
    _exact_keys(document, _NVIDIA_KEYS, "nvidia")
    base_url = _text(document["base_url"], "nvidia.base_url").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AgentSettingsError("nvidia.base_url must be an absolute https URL")
    api_key_env = _text(document["api_key_env"], "nvidia.api_key_env")
    if _ENV_NAME.fullmatch(api_key_env) is None:
        raise AgentSettingsError("nvidia.api_key_env must be an environment variable name")
    return NvidiaSettings(
        enabled=_bool(document["enabled"], "nvidia.enabled"),
        base_url=base_url,
        model=_text(document["model"], "nvidia.model"),
        api_key_env=api_key_env,
        timeout_seconds=_int(document["timeout_seconds"], "nvidia.timeout_seconds", 1, 600),
        temperature=_float(document["temperature"], "nvidia.temperature", 0, 2),
        max_tokens=_int(document["max_tokens"], "nvidia.max_tokens", 1, 32768),
    )


def _codex_settings(value: Any, root: Path) -> CodexSettings:
    document = _mapping(value, "codex")
    _exact_keys(document, _CODEX_KEYS, "codex")
    raw_path = Path(_text(document["script_path"], "codex.script_path"))
    script_path = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    try:
        script_path.relative_to(root.resolve())
    except ValueError as exc:
        raise AgentSettingsError("codex.script_path must remain inside the repository") from exc
    return CodexSettings(
        enabled=_bool(document["enabled"], "codex.enabled"),
        script_path=script_path,
        executable=_text(document["executable"], "codex.executable"),
        timeout_seconds=_int(document["timeout_seconds"], "codex.timeout_seconds", 1, 1800),
        max_output_chars=_int(document["max_output_chars"], "codex.max_output_chars", 1000, 100000),
    )


def disabled_agent_settings(repository_root: Path | None = None) -> AgentSettings:
    """Return a deterministic disabled configuration when optional settings fail."""

    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    return AgentSettings(
        enabled=False,
        agent_id="code-reviewer",
        preferred_backend="nvidia-nim",
        fallback_backend="codex-cli",
        max_evidence_chars=120000,
        max_output_chars=30000,
        nvidia=NvidiaSettings(
            enabled=False,
            base_url="https://integrate.api.nvidia.com/v1",
            model="meta/llama-3.3-70b-instruct",
            api_key_env="NVIDIA_API_KEY",
            timeout_seconds=90,
            temperature=0.1,
            max_tokens=4096,
        ),
        codex=CodexSettings(
            enabled=False,
            script_path=(root / "scripts" / "invoke-codex-agent.ps1").resolve(),
            executable="codex",
            timeout_seconds=180,
            max_output_chars=30000,
        ),
    )


def load_agent_settings(repository_root: Path | None = None) -> AgentSettings:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    path = root / "settings" / "agents" / "code-review-agent.settings.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AgentSettingsError(f"Code-review agent settings are missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AgentSettingsError(f"Invalid code-review agent settings JSON: {exc}") from exc
    document = _mapping(document, "root")
    _exact_keys(document, _ROOT_KEYS, "root")
    if document["schema_version"] != 1:
        raise AgentSettingsError("schema_version must be 1")
    agent_id = _text(document["agent_id"], "agent_id")
    if agent_id != "code-reviewer":
        raise AgentSettingsError("agent_id must be code-reviewer")
    preferred = _text(document["preferred_backend"], "preferred_backend")
    if preferred not in _BACKENDS:
        raise AgentSettingsError("preferred_backend must be nvidia-nim or codex-cli")
    raw_fallback = document["fallback_backend"]
    if raw_fallback is None:
        fallback = None
    else:
        fallback = _text(raw_fallback, "fallback_backend")
        if fallback not in _BACKENDS:
            raise AgentSettingsError("fallback_backend must be nvidia-nim, codex-cli, or null")
        if fallback == preferred:
            raise AgentSettingsError("fallback_backend must differ from preferred_backend")
    return AgentSettings(
        enabled=_bool(document["enabled"], "enabled"),
        agent_id=agent_id,
        preferred_backend=preferred,
        fallback_backend=fallback,
        max_evidence_chars=_int(document["max_evidence_chars"], "max_evidence_chars", 1000, 500000),
        max_output_chars=_int(document["max_output_chars"], "max_output_chars", 1000, 100000),
        nvidia=_nvidia_settings(document["nvidia"]),
        codex=_codex_settings(document["codex"], root),
    )


def load_agent_settings_or_disabled(
    repository_root: Path | None = None,
) -> AgentSettings:
    """Contain optional agent configuration failure without breaking the gateway."""

    try:
        return load_agent_settings(repository_root)
    except (AgentSettingsError, OSError, UnicodeError):
        return disabled_agent_settings(repository_root)


__all__ = [
    "AgentSettings",
    "AgentSettingsError",
    "CodexSettings",
    "NvidiaSettings",
    "disabled_agent_settings",
    "load_agent_settings",
    "load_agent_settings_or_disabled",
]
