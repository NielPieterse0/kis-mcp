from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CODEX_KEYS = frozenset(
    {
        "enabled",
        "script_path",
        "executable",
        "home_path",
        "expected_version",
        "timeout_seconds",
        "max_output_chars",
    }
)


class CodexSettingsError(RuntimeError):
    """Raised when Codex CLI tool settings are invalid."""


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CodexSettingsError("codex must be an object")
    return value


def _exact_keys(value: Mapping[str, Any]) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - _CODEX_KEYS)
    missing = sorted(_CODEX_KEYS - actual)
    if unknown:
        raise CodexSettingsError(f"codex has unknown keys: {unknown}")
    if missing:
        raise CodexSettingsError(f"codex is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CodexSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise CodexSettingsError(f"{label} must be a boolean")
    return value


def _int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodexSettingsError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise CodexSettingsError(f"{label} must be between {minimum} and {maximum}")
    return value


def _project_path(value: Any, label: str) -> Path:
    path = Path(_text(value, label))
    if not path.is_absolute() or not str(path).casefold().startswith("c:\\projects\\"):
        raise CodexSettingsError(f"{label} must be an absolute path under C:\\Projects")
    return path


def _version(value: Any) -> str:
    version = _text(value, "codex.expected_version")
    parts = version.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise CodexSettingsError("codex.expected_version must be a semantic version")
    return version


@dataclass(frozen=True, slots=True)
class CodexSettings:
    enabled: bool
    script_path: Path
    executable: str
    home_path: Path
    expected_version: str
    timeout_seconds: int
    max_output_chars: int


def codex_settings_from_mapping(value: Any, repository_root: Path) -> CodexSettings:
    document = _mapping(value)
    _exact_keys(document)
    root = repository_root.resolve()
    raw_path = Path(_text(document["script_path"], "codex.script_path"))
    script_path = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    try:
        script_path.relative_to(root)
    except ValueError as exc:
        raise CodexSettingsError("codex.script_path must remain inside the repository") from exc
    executable = _project_path(document["executable"], "codex.executable")
    home_path = _project_path(document["home_path"], "codex.home_path")
    return CodexSettings(
        enabled=_bool(document["enabled"], "codex.enabled"),
        script_path=script_path,
        executable=str(executable),
        home_path=home_path,
        expected_version=_version(document["expected_version"]),
        timeout_seconds=_int(document["timeout_seconds"], "codex.timeout_seconds", 1, 1800),
        max_output_chars=_int(
            document["max_output_chars"], "codex.max_output_chars", 1000, 100000
        ),
    )


def disabled_codex_settings(repository_root: Path) -> CodexSettings:
    root = repository_root.resolve()
    return CodexSettings(
        enabled=False,
        script_path=(root / "scripts" / "invoke-codex-agent.ps1").resolve(),
        executable=r"C:\Projects\.kis-mcp\tools\codex\0.147.0\node_modules\.bin\codex.cmd",
        home_path=Path(r"C:\Projects\.kis-mcp\agent-hosts\codex-reviewer"),
        expected_version="0.147.0",
        timeout_seconds=180,
        max_output_chars=30000,
    )


__all__ = [
    "CodexSettings",
    "CodexSettingsError",
    "codex_settings_from_mapping",
    "disabled_codex_settings",
]
