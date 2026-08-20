from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...providers.nvidia.settings import (
    NvidiaSettings,
    NvidiaSettingsError,
    disabled_nvidia_settings,
    nvidia_settings_from_mapping,
)
from ...tools.codex_cli.settings import (
    CodexSettings,
    CodexSettingsError,
    codex_settings_from_mapping,
    disabled_codex_settings,
)

_BACKENDS = frozenset({"nvidia-nim", "codex-cli"})
_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "agent_id",
        "preferred_backend",
        "fallback_backend",
        "max_evidence_chars",
        "max_output_chars",
        "max_backend_attempts",
        "review_deadline_seconds",
        "soft_stall_seconds",
        "hard_stall_seconds",
        "nvidia",
        "codex",
    }
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


@dataclass(frozen=True, slots=True)
class AgentSettings:
    enabled: bool
    agent_id: str
    preferred_backend: str
    fallback_backend: str | None
    max_evidence_chars: int
    max_output_chars: int
    max_backend_attempts: int
    review_deadline_seconds: int
    nvidia: NvidiaSettings
    codex: CodexSettings
    soft_stall_seconds: int = 10
    hard_stall_seconds: int = 30


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
        max_backend_attempts=2,
        review_deadline_seconds=120,
        soft_stall_seconds=10,
        hard_stall_seconds=30,
        nvidia=disabled_nvidia_settings(),
        codex=disabled_codex_settings(root),
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
    try:
        nvidia = nvidia_settings_from_mapping(document["nvidia"])
        codex = codex_settings_from_mapping(document["codex"], root)
    except (NvidiaSettingsError, CodexSettingsError) as exc:
        raise AgentSettingsError(str(exc)) from exc
    soft_stall_seconds = _int(document["soft_stall_seconds"], "soft_stall_seconds", 1, 120)
    hard_stall_seconds = _int(document["hard_stall_seconds"], "hard_stall_seconds", 2, 180)
    if hard_stall_seconds <= soft_stall_seconds:
        raise AgentSettingsError("hard_stall_seconds must be greater than soft_stall_seconds")
    return AgentSettings(
        enabled=_bool(document["enabled"], "enabled"),
        agent_id=agent_id,
        preferred_backend=preferred,
        fallback_backend=fallback,
        max_evidence_chars=_int(document["max_evidence_chars"], "max_evidence_chars", 1000, 500000),
        max_output_chars=_int(document["max_output_chars"], "max_output_chars", 1000, 100000),
        max_backend_attempts=_int(document["max_backend_attempts"], "max_backend_attempts", 1, 3),
        review_deadline_seconds=_int(document["review_deadline_seconds"], "review_deadline_seconds", 1, 300),
        soft_stall_seconds=soft_stall_seconds,
        hard_stall_seconds=hard_stall_seconds,
        nvidia=nvidia,
        codex=codex,
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
    "disabled_agent_settings",
    "load_agent_settings",
    "load_agent_settings_or_disabled",
]
