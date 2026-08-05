from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_KEYS = {
    "schema_version", "enabled", "source_repository", "source_revision",
    "package_name", "package_version", "executable", "entry_point", "arguments",
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class EverythingToolSettings:
    enabled: bool
    source_repository: str
    source_revision: str
    package_name: str
    package_version: str
    executable: str
    entry_point: Path
    arguments: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        revision = _text(self.source_revision, "source_revision")
        version = _text(self.package_version, "package_version")
        if not _REVISION.fullmatch(revision):
            raise ValueError("source_revision must be a 40-character commit SHA")
        if not _VERSION.fullmatch(version):
            raise ValueError("package_version must be exact semantic version")
        object.__setattr__(self, "source_repository", _text(self.source_repository, "source_repository"))
        object.__setattr__(self, "source_revision", revision)
        object.__setattr__(self, "package_name", _text(self.package_name, "package_name"))
        object.__setattr__(self, "package_version", version)
        object.__setattr__(self, "executable", _text(self.executable, "executable"))
        if not isinstance(self.entry_point, Path):
            object.__setattr__(self, "entry_point", Path(self.entry_point))
        object.__setattr__(self, "arguments", tuple(_text(item, "argument") for item in self.arguments))

    @classmethod
    def load(cls, path: Path) -> "EverythingToolSettings":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings must be a JSON object")
        unknown = sorted(set(data) - _KEYS)
        if unknown:
            raise ValueError(f"unknown settings keys: {', '.join(unknown)}")
        missing = sorted(_KEYS - set(data))
        if missing:
            raise ValueError(f"missing settings keys: {', '.join(missing)}")
        if not isinstance(data["arguments"], list):
            raise ValueError("arguments must be an array")
        return cls(
            schema_version=data["schema_version"], enabled=data["enabled"],
            source_repository=data["source_repository"], source_revision=data["source_revision"],
            package_name=data["package_name"], package_version=data["package_version"],
            executable=data["executable"], entry_point=Path(data["entry_point"]),
            arguments=tuple(data["arguments"]),
        )


__all__ = ["EverythingToolSettings"]
