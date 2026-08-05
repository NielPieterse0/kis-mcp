from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_KEYS = {
    "schema_version",
    "enabled",
    "source_repository",
    "source_revision",
    "distribution_name",
    "module_name",
    "expected_version",
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PythonSdkSettings:
    enabled: bool
    source_repository: str
    source_revision: str
    distribution_name: str
    module_name: str
    expected_version: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        revision = _text(self.source_revision, "source_revision")
        version = _text(self.expected_version, "expected_version")
        module_name = _text(self.module_name, "module_name")
        if not _REVISION.fullmatch(revision):
            raise ValueError("source_revision must be a 40-character commit SHA")
        if not _VERSION.fullmatch(version):
            raise ValueError("expected_version must be exact semantic version")
        if not _MODULE.fullmatch(module_name):
            raise ValueError("module_name must be a dotted Python import name")
        object.__setattr__(
            self,
            "source_repository",
            _text(self.source_repository, "source_repository"),
        )
        object.__setattr__(self, "source_revision", revision)
        object.__setattr__(
            self,
            "distribution_name",
            _text(self.distribution_name, "distribution_name"),
        )
        object.__setattr__(self, "module_name", module_name)
        object.__setattr__(self, "expected_version", version)

    @classmethod
    def load(cls, path: Path) -> "PythonSdkSettings":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings must be a JSON object")
        unknown = sorted(set(data) - _KEYS)
        if unknown:
            raise ValueError(f"unknown settings keys: {', '.join(unknown)}")
        missing = sorted(_KEYS - set(data))
        if missing:
            raise ValueError(f"missing settings keys: {', '.join(missing)}")
        return cls(
            schema_version=data["schema_version"],
            enabled=data["enabled"],
            source_repository=data["source_repository"],
            source_revision=data["source_revision"],
            distribution_name=data["distribution_name"],
            module_name=data["module_name"],
            expected_version=data["expected_version"],
        )


__all__ = ["PythonSdkSettings"]
