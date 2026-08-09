from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REVISION = re.compile(r"^[0-9a-f]{40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_INTEGRITY = re.compile(r"^sha512-[A-Za-z0-9+/]+={0,2}$")
_ENVIRONMENT = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_KEYS = frozenset(
    {
        "schema_version",
        "enabled",
        "namespace",
        "source_repository",
        "source_revision",
        "package_name",
        "package_version",
        "package_integrity",
        "node_minimum_version",
        "install_root",
        "executable",
        "entry_point",
        "arguments",
        "environment_names",
    }
)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _tuple_text(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    items = tuple(_text(item, label) for item in value)
    if len(set(items)) != len(items):
        raise ValueError(f"{label} values must be unique")
    return items


@dataclass(frozen=True, slots=True)
class Context7Settings:
    enabled: bool
    namespace: str
    source_repository: str
    source_revision: str
    package_name: str
    package_version: str
    package_integrity: str
    node_minimum_version: str
    install_root: Path
    executable: str
    entry_point: Path
    arguments: tuple[str, ...]
    environment_names: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if self.namespace != "context7":
            raise ValueError("namespace must be context7")
        if self.source_repository != "https://github.com/upstash/context7":
            raise ValueError("source_repository must identify the official Context7 repository")
        if not _REVISION.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a 40-character commit SHA")
        if self.package_name != "@upstash/context7-mcp":
            raise ValueError("package_name must be @upstash/context7-mcp")
        if not _VERSION.fullmatch(self.package_version):
            raise ValueError("package_version must be an exact semantic version")
        if not _INTEGRITY.fullmatch(self.package_integrity):
            raise ValueError("package_integrity must be an npm sha512 integrity value")
        if not _VERSION.fullmatch(self.node_minimum_version):
            raise ValueError("node_minimum_version must be an exact semantic version")
        if self.arguments != ("--transport", "stdio"):
            raise ValueError("arguments must select the fixed stdio transport")
        if any(not _ENVIRONMENT.fullmatch(name) for name in self.environment_names):
            raise ValueError("environment_names must use upper-case shell syntax")
        if len(set(self.environment_names)) != len(self.environment_names):
            raise ValueError("environment_names must be unique")
        object.__setattr__(self, "install_root", Path(self.install_root))
        object.__setattr__(self, "entry_point", Path(self.entry_point))

    @classmethod
    def load(cls, path: Path) -> "Context7Settings":
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("settings must be a JSON object")
        actual = set(document)
        unknown = sorted(actual - _KEYS)
        if unknown:
            raise ValueError(f"unknown settings keys: {', '.join(unknown)}")
        missing = sorted(_KEYS - actual)
        if missing:
            raise ValueError(f"missing settings keys: {', '.join(missing)}")
        return cls(
            schema_version=document["schema_version"],
            enabled=document["enabled"],
            namespace=_text(document["namespace"], "namespace"),
            source_repository=_text(document["source_repository"], "source_repository"),
            source_revision=_text(document["source_revision"], "source_revision"),
            package_name=_text(document["package_name"], "package_name"),
            package_version=_text(document["package_version"], "package_version"),
            package_integrity=_text(document["package_integrity"], "package_integrity"),
            node_minimum_version=_text(document["node_minimum_version"], "node_minimum_version"),
            install_root=Path(_text(document["install_root"], "install_root")),
            executable=_text(document["executable"], "executable"),
            entry_point=Path(_text(document["entry_point"], "entry_point")),
            arguments=_tuple_text(document["arguments"], "arguments"),
            environment_names=_tuple_text(document["environment_names"], "environment_names"),
        )


__all__ = ["Context7Settings"]