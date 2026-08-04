from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kis_mcp.paths import is_within_windows_boundary, normalize_windows_path

from .scope import normalize_repository


OFFICIAL_GITHUB_MCP_SOURCE = "https://github.com/github/github-mcp-server"
APPROVED_PROJECT_BOUNDARY = r"C:\Projects"
_SETTINGS_KEYS = {
    "schema_version",
    "provider_id",
    "authoritative_source",
    "source_revision",
    "transport",
    "executable",
    "token_env",
    "toolsets",
    "approved_repositories",
    "unscoped_tools",
}
_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_REVISION = re.compile(r"^[0-9a-fA-F]{40}$")
_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True, slots=True)
class GitHubProviderSettings:
    schema_version: int
    provider_id: str
    authoritative_source: str
    source_revision: str
    transport: str
    executable: str
    token_env: str
    toolsets: tuple[str, ...]
    approved_repositories: tuple[str, ...]
    unscoped_tools: tuple[str, ...]

    def launch_args(self) -> tuple[str, ...]:
        return ("stdio", f"--toolsets={','.join(self.toolsets)}")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a non-empty string")
    return value.strip()


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise RuntimeError(f"{label} must be a non-empty array")
    result = tuple(_string(item, f"{label}[]") for item in value)
    if len({item.casefold() for item in result}) != len(result):
        raise RuntimeError(f"{label} contains duplicate values")
    return result


def _load_document(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"GitHub provider settings are missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError("GitHub provider settings root must be an object")
    return value


def load_github_provider_settings(
    repository_root: Path | None = None,
) -> GitHubProviderSettings:
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve()
    document = _load_document(
        root / "settings" / "providers" / "github-mcp.provider.json"
    )
    unknown = sorted(set(document).difference(_SETTINGS_KEYS))
    missing = sorted(_SETTINGS_KEYS.difference(document))
    if unknown:
        raise RuntimeError(f"GitHub provider settings contain unknown keys: {unknown}")
    if missing:
        raise RuntimeError(f"GitHub provider settings are missing keys: {missing}")

    if document.get("schema_version") != 1:
        raise RuntimeError("GitHub provider schema_version must be 1")
    provider_id = _string(document.get("provider_id"), "provider_id")
    if provider_id != "github-mcp":
        raise RuntimeError("GitHub provider_id must be github-mcp")
    source = _string(document.get("authoritative_source"), "authoritative_source")
    if source != OFFICIAL_GITHUB_MCP_SOURCE:
        raise RuntimeError("Provider must use the official GitHub MCP source")
    revision = _string(document.get("source_revision"), "source_revision")
    if _REVISION.fullmatch(revision) is None:
        raise RuntimeError("source_revision must be a 40-character Git commit SHA")
    transport = _string(document.get("transport"), "transport")
    if transport != "stdio":
        raise RuntimeError("GitHub provider transport must be stdio")

    executable = normalize_windows_path(
        _string(document.get("executable"), "executable"),
        base=APPROVED_PROJECT_BOUNDARY,
    )
    if not is_within_windows_boundary(
        executable,
        boundary=APPROVED_PROJECT_BOUNDARY,
    ):
        raise RuntimeError("GitHub provider executable must remain beneath C:\\Projects")

    token_env = _string(document.get("token_env"), "token_env")
    if _ENV_NAME.fullmatch(token_env) is None:
        raise RuntimeError("token_env must be an uppercase environment-variable name")

    toolsets = _strings(document.get("toolsets"), "toolsets")
    if any(_NAME.fullmatch(value) is None for value in toolsets):
        raise RuntimeError("toolsets contain an invalid name")

    raw_repositories = _strings(
        document.get("approved_repositories"),
        "approved_repositories",
    )
    try:
        repositories = tuple(
            normalize_repository(value) for value in raw_repositories
        )
    except ValueError as exc:
        raise RuntimeError(
            "approved_repositories must contain owner/repo identities: "
            f"{exc}"
        ) from exc
    if len(set(repositories)) != len(repositories):
        raise RuntimeError("approved_repositories contains duplicate repositories")

    unscoped_tools = tuple(
        value.casefold()
        for value in _strings(document.get("unscoped_tools"), "unscoped_tools")
    )
    if any(_NAME.fullmatch(value) is None for value in unscoped_tools):
        raise RuntimeError("unscoped_tools contain an invalid tool name")

    return GitHubProviderSettings(
        schema_version=1,
        provider_id=provider_id,
        authoritative_source=source,
        source_revision=revision.casefold(),
        transport=transport,
        executable=executable,
        token_env=token_env,
        toolsets=toolsets,
        approved_repositories=repositories,
        unscoped_tools=unscoped_tools,
    )
