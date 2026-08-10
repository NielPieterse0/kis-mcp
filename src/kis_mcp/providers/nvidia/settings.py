from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from urllib.parse import urlparse

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PROFILE_ALIASES = ("nano", "super", "ultra")
_PROFILE_SET = frozenset(_PROFILE_ALIASES)
_CANONICAL_SECRET_REF = "secret://provider/nvidia-nim/api-key"
_NVIDIA_KEYS = frozenset(
    {
        "enabled",
        "base_url",
        "api_key_env",
        "secret_ref",
        "default_profile",
        "timeout_seconds",
        "profiles",
    }
)
_PROFILE_KEYS = frozenset(
    {
        "model",
        "guidance",
        "temperature",
        "top_p",
        "max_tokens",
        "reasoning_budget",
        "enable_thinking",
    }
)


class NvidiaSettingsError(RuntimeError):
    """Raised when NVIDIA provider settings are invalid."""


def _mapping(value: Any, label: str = "nvidia") -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NvidiaSettingsError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = {str(key) for key in value}
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise NvidiaSettingsError(f"{label} has unknown keys: {unknown}")
    if missing:
        raise NvidiaSettingsError(f"{label} is missing required keys: {missing}")


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
class NvidiaModelProfile:
    model: str
    guidance: str
    temperature: float
    top_p: float
    max_tokens: int
    reasoning_budget: int
    enable_thinking: bool


@dataclass(frozen=True, slots=True)
class NvidiaSettings:
    enabled: bool
    base_url: str
    api_key_env: str
    secret_ref: str
    default_profile: str
    timeout_seconds: int
    profiles: Mapping[str, NvidiaModelProfile]

    def profile(self, alias: str) -> NvidiaModelProfile:
        normalized = alias.strip() if isinstance(alias, str) else ""
        try:
            return self.profiles[normalized]
        except KeyError as exc:
            raise NvidiaSettingsError(
                f"nvidia model profile must be one of: {', '.join(_PROFILE_ALIASES)}"
            ) from exc


def _profile_from_mapping(alias: str, value: Any) -> NvidiaModelProfile:
    document = _mapping(value, f"nvidia.profiles.{alias}")
    _exact_keys(document, _PROFILE_KEYS, f"nvidia.profiles.{alias}")
    return NvidiaModelProfile(
        model=_text(document["model"], f"nvidia.profiles.{alias}.model"),
        guidance=_text(document["guidance"], f"nvidia.profiles.{alias}.guidance"),
        temperature=_float(
            document["temperature"], f"nvidia.profiles.{alias}.temperature", 0, 2
        ),
        top_p=_float(document["top_p"], f"nvidia.profiles.{alias}.top_p", 0, 1),
        max_tokens=_int(
            document["max_tokens"], f"nvidia.profiles.{alias}.max_tokens", 1, 65536
        ),
        reasoning_budget=_int(
            document["reasoning_budget"],
            f"nvidia.profiles.{alias}.reasoning_budget",
            0,
            65536,
        ),
        enable_thinking=_bool(
            document["enable_thinking"], f"nvidia.profiles.{alias}.enable_thinking"
        ),
    )


def nvidia_settings_from_mapping(value: Any) -> NvidiaSettings:
    document = _mapping(value)
    _exact_keys(document, _NVIDIA_KEYS, "nvidia")
    base_url = _text(document["base_url"], "nvidia.base_url").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise NvidiaSettingsError("nvidia.base_url must be an absolute https URL")
    api_key_env = _text(document["api_key_env"], "nvidia.api_key_env")
    if _ENV_NAME.fullmatch(api_key_env) is None:
        raise NvidiaSettingsError("nvidia.api_key_env must be an environment variable name")
    secret_ref = _text(document["secret_ref"], "nvidia.secret_ref")
    if secret_ref != _CANONICAL_SECRET_REF:
        raise NvidiaSettingsError(
            f"nvidia.secret_ref must be {_CANONICAL_SECRET_REF}"
        )
    profiles_document = _mapping(document["profiles"], "nvidia.profiles")
    profile_keys = {str(key) for key in profiles_document}
    if profile_keys != _PROFILE_SET:
        raise NvidiaSettingsError(
            "nvidia.profiles must contain exactly nano, super, and ultra"
        )
    profiles = {
        alias: _profile_from_mapping(alias, profiles_document[alias])
        for alias in _PROFILE_ALIASES
    }
    default_profile = _text(document["default_profile"], "nvidia.default_profile")
    if default_profile not in profiles:
        raise NvidiaSettingsError(
            "nvidia.default_profile must be nano, super, or ultra"
        )
    return NvidiaSettings(
        enabled=_bool(document["enabled"], "nvidia.enabled"),
        base_url=base_url,
        api_key_env=api_key_env,
        secret_ref=secret_ref,
        default_profile=default_profile,
        timeout_seconds=_int(document["timeout_seconds"], "nvidia.timeout_seconds", 1, 600),
        profiles=MappingProxyType(profiles),
    )


def _default_profiles() -> Mapping[str, NvidiaModelProfile]:
    return MappingProxyType(
        {
            "nano": NvidiaModelProfile(
                model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                guidance="Fast first-pass and focused iterative review.",
                temperature=0.6,
                top_p=0.95,
                max_tokens=65536,
                reasoning_budget=16384,
                enable_thinking=True,
            ),
            "super": NvidiaModelProfile(
                model="nvidia/nemotron-3-super-120b-a12b",
                guidance="Default substantive multi-file code review.",
                temperature=1.0,
                top_p=0.95,
                max_tokens=16384,
                reasoning_budget=16384,
                enable_thinking=True,
            ),
            "ultra": NvidiaModelProfile(
                model="nvidia/nemotron-3-ultra-550b-a55b",
                guidance="Deepest high-impact architecture and safety-sensitive review.",
                temperature=1.0,
                top_p=0.95,
                max_tokens=16384,
                reasoning_budget=16384,
                enable_thinking=True,
            ),
        }
    )


def disabled_nvidia_settings() -> NvidiaSettings:
    return NvidiaSettings(
        enabled=False,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        secret_ref=_CANONICAL_SECRET_REF,
        default_profile="super",
        timeout_seconds=90,
        profiles=_default_profiles(),
    )


__all__ = [
    "NvidiaModelProfile",
    "NvidiaSettings",
    "NvidiaSettingsError",
    "disabled_nvidia_settings",
    "nvidia_settings_from_mapping",
]
