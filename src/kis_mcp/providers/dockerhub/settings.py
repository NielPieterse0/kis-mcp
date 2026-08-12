from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from kis_mcp.secrets.references import SecretReference

OFFICIAL_SOURCE = "https://github.com/docker/hub-mcp"
APPROVED_REVISION = "ad806e2cab0489a296aec0f32f3d3eea807d65c2"
ALL_TOOLS = (
    "checkRepository", "checkRepositoryTag", "createRepository", "dockerHardenedImages",
    "getPersonalNamespace", "getRepositoryInfo", "getRepositoryTag",
    "listAllNamespacesMemberOf", "listNamespaces", "listRepositoriesByNamespace",
    "listRepositoryTags", "search", "updateRepositoryInfo",
)
PUBLIC_TOOLS = (
    "checkRepository", "checkRepositoryTag", "getRepositoryInfo", "getRepositoryTag",
    "listRepositoriesByNamespace", "listRepositoryTags", "search",
)
_KEYS = {"schema_version", "provider_id", "authoritative_source", "source_revision", "transport", "node_executable", "entry_point", "auth"}
_AUTH_KEYS = {"mode", "username", "secret_ref"}
_USERNAME = re.compile(r"^[A-Za-z0-9_.-]+$")

@dataclass(frozen=True, slots=True)
class DockerHubSettings:
    schema_version: int
    provider_id: str
    authoritative_source: str
    source_revision: str
    transport: str
    node_executable: str
    entry_point: Path
    auth_mode: str
    username: str | None
    secret_ref: str | None

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.provider_id != "dockerhub-mcp":
            raise RuntimeError("Docker Hub settings identity is invalid")
        if self.authoritative_source != OFFICIAL_SOURCE or self.source_revision != APPROVED_REVISION:
            raise RuntimeError("Docker Hub source identity is not the approved pin")
        if self.transport != "stdio" or not self.node_executable.strip():
            raise RuntimeError("Docker Hub transport/runtime is invalid")
        if not self.entry_point.is_absolute() or not str(self.entry_point).casefold().startswith("c:\\projects\\"):
            raise RuntimeError("Docker Hub entry point must remain beneath C:\\Projects")
        mode = self.auth_mode.casefold()
        if mode not in {"public", "pat"}:
            raise RuntimeError("Docker Hub auth mode must be public or pat")
        object.__setattr__(self, "auth_mode", mode)
        if mode == "public":
            if self.username is not None or self.secret_ref is not None:
                raise RuntimeError("Docker Hub public auth must not store username or secret_ref")
        else:
            if not isinstance(self.username, str) or _USERNAME.fullmatch(self.username) is None:
                raise RuntimeError("Docker Hub PAT auth requires a valid username")
            if not isinstance(self.secret_ref, str):
                raise RuntimeError("Docker Hub PAT auth requires a canonical secret_ref")
            try:
                reference = SecretReference.parse(self.secret_ref).uri
            except Exception as exc:
                raise RuntimeError("Docker Hub PAT auth requires a canonical secret_ref") from exc
            object.__setattr__(self, "secret_ref", reference)


def load_dockerhub_settings(repository_root: Path | None = None) -> DockerHubSettings:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    path = root / "settings" / "providers" / "dockerhub.provider.json"
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Docker Hub settings are unavailable: {type(exc).__name__}") from exc
    if not isinstance(value, Mapping) or set(value) != _KEYS:
        raise RuntimeError("Docker Hub settings must contain exactly the approved keys")
    auth = value["auth"]
    if not isinstance(auth, Mapping) or set(auth) != _AUTH_KEYS:
        raise RuntimeError("Docker Hub auth settings must contain exactly the approved keys")
    return DockerHubSettings(
        schema_version=value["schema_version"],
        provider_id=value["provider_id"],
        authoritative_source=value["authoritative_source"],
        source_revision=value["source_revision"],
        transport=value["transport"],
        node_executable=value["node_executable"],
        entry_point=Path(value["entry_point"]),
        auth_mode=auth["mode"],
        username=auth["username"],
        secret_ref=auth["secret_ref"],
    )


__all__ = [
    "ALL_TOOLS", "APPROVED_REVISION", "DockerHubSettings", "OFFICIAL_SOURCE",
    "PUBLIC_TOOLS", "load_dockerhub_settings",
]
