from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_KEYS = {
    "schema_version",
    "enabled",
    "source_repository",
    "source_revision",
    "plugin_path",
    "local_checkout",
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class McpSpecSettings:
    enabled: bool
    source_repository: str
    source_revision: str
    plugin_path: str
    local_checkout: Path | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        repository = _text(self.source_repository, "source_repository")
        revision = _text(self.source_revision, "source_revision")
        plugin_path = _text(self.plugin_path, "plugin_path").replace("\\", "/")
        if not _REVISION.fullmatch(revision):
            raise ValueError("source_revision must be a 40-character commit SHA")
        if plugin_path.startswith("/") or ".." in Path(plugin_path).parts:
            raise ValueError("plugin_path must be a repository-relative path")
        if self.local_checkout is not None and not isinstance(self.local_checkout, Path):
            object.__setattr__(self, "local_checkout", Path(self.local_checkout))
        object.__setattr__(self, "source_repository", repository)
        object.__setattr__(self, "source_revision", revision)
        object.__setattr__(self, "plugin_path", plugin_path)

    @classmethod
    def load(cls, path: Path) -> "McpSpecSettings":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings must be a JSON object")
        unknown = sorted(set(data) - _KEYS)
        if unknown:
            raise ValueError(f"unknown settings keys: {', '.join(unknown)}")
        missing = sorted(_KEYS - set(data))
        if missing:
            raise ValueError(f"missing settings keys: {', '.join(missing)}")
        checkout = data["local_checkout"]
        if checkout is not None:
            checkout = Path(_text(checkout, "local_checkout"))
        return cls(
            schema_version=data["schema_version"],
            enabled=data["enabled"],
            source_repository=data["source_repository"],
            source_revision=data["source_revision"],
            plugin_path=data["plugin_path"],
            local_checkout=checkout,
        )


__all__ = ["McpSpecSettings"]
