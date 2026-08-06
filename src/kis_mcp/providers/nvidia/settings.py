from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
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


class NvidiaSettingsError(RuntimeError):
    """Raised when NVIDIA provider settings are invalid."""


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NvidiaSettingsError("nvidia must be an object")
    return value


def _exact_keys(value: Mapping[str, Any]) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - _NVIDIA_KEYS)
    missing = sorted(_NVIDIA_KEYS - actual)
    if unknown:
        raise NvidiaSettingsError(f"nvidia has unknown keys: {unknown}")
    if missing:
        raise NvidiaSettingsError(f"nvidia is missing required keys: {missing}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NvidiaSettingsError(f"{label} must be a non-empty string")
    return value.strip()


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise NvidiaSettingsError(f"{label} must be a boolean")
    return value


def _int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NvidiaSettingsError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise NvidiaSettingsError(f"{label} must be between {minimum} and {maximum}")
    return value


def _float(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NvidiaSettingsError(f"{label} must be a number")
    normalized = float(value)
    if normalized < minimum or normalized > maximum:
        raise NvidiaSettingsError(f"{label} must be between {minimum} and {maximum}")
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


def nvidia_settings_from_mapping(value: Any) -> NvidiaSettings:
    document = _mapping(value)
    _exact_keys(document)
    base_url = _text(document["base_url"], "nvidia.base_url").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise NvidiaSettingsError("nvidia.base_url must be an absolute https URL")
    api_key_env = _text(document["api_key_env"], "nvidia.api_key_env")
    if _ENV_NAME.fullmatch(api_key_env) is None:
        raise NvidiaSettingsError("nvidia.api_key_env must be an environment variable name")
    return NvidiaSettings(
        enabled=_bool(document["enabled"], "nvidia.enabled"),
        base_url=base_url,
        model=_text(document["model"], "nvidia.model"),
        api_key_env=api_key_env,
        timeout_seconds=_int(document["timeout_seconds"], "nvidia.timeout_seconds", 1, 600),
        temperature=_float(document["temperature"], "nvidia.temperature", 0, 2),
        max_tokens=_int(document["max_tokens"], "nvidia.max_tokens", 1, 32768),
    )


def disabled_nvidia_settings() -> NvidiaSettings:
    return NvidiaSettings(
        enabled=False,
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.3-70b-instruct",
        api_key_env="NVIDIA_API_KEY",
        timeout_seconds=90,
        temperature=0.1,
        max_tokens=4096,
    )


__all__ = [
    "NvidiaSettings",
    "NvidiaSettingsError",
    "disabled_nvidia_settings",
    "nvidia_settings_from_mapping",
]
