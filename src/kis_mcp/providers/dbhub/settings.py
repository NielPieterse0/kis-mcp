from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

OFFICIAL_SOURCE = "https://github.com/bytebase/dbhub"
APPROVED_RELEASE = "v1.2.0"
APPROVED_REVISION = "1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0"
APPROVED_TOOLS = ("execute_sql", "search_objects")
_KEYS = {
    "schema_version", "provider_id", "authoritative_source", "release_tag",
    "source_revision", "transport", "node_executable", "entry_point",
    "runtime_root", "max_rows", "enabled_tools",
}
_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class DBHubSettings:
    schema_version: int
    provider_id: str
    authoritative_source: str
    release_tag: str
    source_revision: str
    transport: str
    node_executable: str
    entry_point: Path
    runtime_root: Path
    max_rows: int
    enabled_tools: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.provider_id != "dbhub":
            raise RuntimeError("DBHub settings identity is invalid")
        if self.authoritative_source != OFFICIAL_SOURCE:
            raise RuntimeError("DBHub authoritative source is invalid")
        if self.release_tag != APPROVED_RELEASE or self.source_revision != APPROVED_REVISION:
            raise RuntimeError("DBHub release/source identity is not the approved pin")
        if _SHA.fullmatch(self.source_revision) is None or self.transport != "stdio":
            raise RuntimeError("DBHub source revision or transport is invalid")
        if not self.node_executable.strip():
            raise RuntimeError("DBHub node executable is required")
        if not self.entry_point.is_absolute() or not self.runtime_root.is_absolute():
            raise RuntimeError("DBHub paths must be absolute")
        for path in (self.entry_point, self.runtime_root):
            if not str(path).casefold().startswith("c:\\projects\\"):
                raise RuntimeError("DBHub paths must remain beneath C:\\Projects")
        if type(self.max_rows) is not int or not 1 <= self.max_rows <= 10000:
            raise RuntimeError("DBHub max_rows must be 1-10000")
        if not self.enabled_tools or any(tool not in APPROVED_TOOLS for tool in self.enabled_tools):
            raise RuntimeError("DBHub enabled_tools contain an unapproved tool")
        if len(set(self.enabled_tools)) != len(self.enabled_tools):
            raise RuntimeError("DBHub enabled_tools must be unique")


def _document(root: Path) -> Mapping[str, Any]:
    path = root / "settings" / "providers" / "dbhub.provider.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"DBHub provider settings are unavailable: {type(exc).__name__}") from exc
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        raise RuntimeError("DBHub provider settings must contain exactly the approved keys")
    return value


def load_dbhub_settings(repository_root: Path | None = None) -> DBHubSettings:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    value = _document(root)
    tools = value["enabled_tools"]
    if not isinstance(tools, list) or any(not isinstance(item, str) for item in tools):
        raise RuntimeError("DBHub enabled_tools must be an array of strings")
    return DBHubSettings(
        schema_version=value["schema_version"],
        provider_id=value["provider_id"],
        authoritative_source=value["authoritative_source"],
        release_tag=value["release_tag"],
        source_revision=value["source_revision"],
        transport=value["transport"],
        node_executable=value["node_executable"],
        entry_point=Path(value["entry_point"]),
        runtime_root=Path(value["runtime_root"]),
        max_rows=value["max_rows"],
        enabled_tools=tuple(tools),
    )


__all__ = [
    "APPROVED_RELEASE",
    "APPROVED_REVISION",
    "APPROVED_TOOLS",
    "DBHubSettings",
    "OFFICIAL_SOURCE",
    "load_dbhub_settings",
]
