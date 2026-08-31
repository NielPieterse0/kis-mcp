from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from threading import get_ident
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.transforms.visibility import Visibility

from ...discover.semantic import (
    SemanticEvidence,
    SemanticRelationship,
    SemanticSymbol,
)
from ..client_runtime import (
    PersistentClientProxyProvider,
    ProviderRuntimeToolState,
    ProviderStartupCall,
    ProviderStartupState,
)
from .settings import SerenaSettings

_PUBLIC_READ_TOOLS = frozenset(
    {
        "get_symbols_overview",
        "find_symbol",
        "find_referencing_symbols",
    }
)
_SUPPORTED_SUFFIXES = frozenset({".py", ".js", ".jsx", ".ts", ".tsx"})
_PYRIGHT_VERSION = "1.1.403"
_PYRIGHT_LAUNCHER_SHA256 = "11d890dd43a9729a13135f665faf8d41eb8b4c89b0e9e21d5e316058e0b8eaaf"
_PYRIGHT_METADATA_SHA256 = "1733517425e2e812cf12fcca6617d71233119797cf0b8bb138bab97424509933"
_LS_SETTINGS_EMPTY = re.compile(r"(?m)^ls_specific_settings:\s*\{\}\s*$")
_LS_SETTINGS_MANAGED = re.compile(
    r'(?m)^ls_specific_settings:[ \t]*\r?\n  python:[ \t]*\r?\n    ls_path:[ \t]*"[^"\r\n]+"[ \t]*$'
)


def _result_text(result: Any) -> str:
    texts = [
        text
        for block in getattr(result, "content", ())
        if isinstance((text := getattr(block, "text", None)), str)
    ]
    return "\n".join(texts).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_managed_pyright_launcher(settings: SerenaSettings) -> Path:
    cache_root = settings.home_root / "AppData" / "Local" / "uv" / "cache" / "archive-v0"
    matches: list[Path] = []
    if cache_root.is_dir():
        for archive in cache_root.iterdir():
            launcher = archive / "Scripts" / "pyright-langserver.exe"
            metadata = archive / "Lib" / "site-packages" / f"pyright-{_PYRIGHT_VERSION}.dist-info" / "METADATA"
            if not launcher.is_file() or not metadata.is_file():
                continue
            if launcher.is_symlink() or metadata.is_symlink():
                continue
            resolved_launcher = launcher.resolve()
            resolved_metadata = metadata.resolve()
            try:
                resolved_launcher.relative_to(archive.resolve())
                resolved_metadata.relative_to(archive.resolve())
            except ValueError:
                continue
            if _sha256(resolved_launcher) != _PYRIGHT_LAUNCHER_SHA256:
                continue
            if _sha256(resolved_metadata) != _PYRIGHT_METADATA_SHA256:
                continue
            matches.append(resolved_launcher)
    if len(matches) != 1:
        raise RuntimeError(
            "Serena requires exactly one content-verified managed Pyright "
            f"{_PYRIGHT_VERSION} launcher beneath {cache_root}; found {len(matches)}"
        )
    launcher = matches[0]
    try:
        launcher.relative_to(Path(settings.project_boundary))
    except ValueError as exc:
        raise RuntimeError("Serena Pyright launcher escaped the managed project boundary") from exc
    return launcher


def _managed_serena_path(source_path: str, settings: SerenaSettings) -> str:
    entries = [item for item in source_path.split(os.pathsep) if item]
    retained: list[str] = []
    for item in entries:
        lowered = item.casefold()
        if lowered.startswith("c:\\users\\"):
            continue
        retained.append(item)
    return os.pathsep.join(retained)


def _provider_environment(
    settings: SerenaSettings,
    source: Mapping[str, str],
) -> dict[str, str]:
    environment = {
        key: source[key]
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if source.get(key)
    }
    if source.get("PATH"):
        environment["PATH"] = _managed_serena_path(source["PATH"], settings)
    environment.update(
        {
            "HOME": str(settings.home_root),
            "USERPROFILE": str(settings.home_root),
            "APPDATA": str(settings.home_root / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(settings.home_root / "AppData" / "Local"),
            "TEMP": str(settings.temp_root),
            "TMP": str(settings.temp_root),
            "SERENA_USAGE_REPORTING": "false",
            "UV_OFFLINE": "1",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return environment


_PROJECT_STATE_SETTING = re.compile(
    r"(?m)^project_serena_folder_location:\s*.*$"
)
_EMPTY_LANGUAGES_SETTING = re.compile(r"(?m)^languages:\s*\[\]\s*$")
_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "typescript",
    ".jsx": "typescript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


def _reconcile_registered_projects(config_path: Path) -> tuple[str, ...]:
    content = config_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    block_starts = [
        index
        for index, line in enumerate(lines)
        if line.rstrip("\r\n") == "projects:"
    ]
    inline_empty = [
        index
        for index, line in enumerate(lines)
        if line.rstrip("\r\n") == "projects: []"
    ]
    if len(block_starts) + len(inline_empty) != 1:
        raise RuntimeError(
            "Serena global configuration must contain exactly one projects registration block"
        )
    if inline_empty:
        return ()

    start = block_starts[0] + 1
    end = start
    while end < len(lines) and lines[end].startswith("- "):
        end += 1

    removed: list[str] = []
    retained: list[str] = []
    for line in lines[start:end]:
        raw_path = line[2:].strip()
        if len(raw_path) >= 2 and raw_path[0] == raw_path[-1] and raw_path[0] in {'"', "'"}:
            raw_path = raw_path[1:-1]
        if Path(raw_path).exists():
            retained.append(line)
        else:
            removed.append(raw_path)
    if removed:
        config_path.write_text(
            "".join((*lines[:start], *retained, *lines[end:])),
            encoding="utf-8",
            newline="",
        )
    return tuple(removed)


def _repair_empty_project_languages(
    settings: SerenaSettings,
    project_root: str,
    source_paths: tuple[str, ...],
) -> tuple[str, ...]:
    languages = tuple(
        dict.fromkeys(
            language
            for path in source_paths
            if (language := _LANGUAGE_BY_SUFFIX.get(Path(path).suffix.casefold()))
        )
    )
    if not languages:
        return ()
    config_path = settings.project_data_path(project_root) / "project.yml"
    if not config_path.is_file():
        return ()
    try:
        content = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ()
    if len(tuple(_EMPTY_LANGUAGES_SETTING.finditer(content))) != 1:
        return ()
    replacement = "languages:\n" + "\n".join(f"- {language}" for language in languages)
    config_path.write_text(
        _EMPTY_LANGUAGES_SETTING.sub(replacement, content, count=1),
        encoding="utf-8",
        newline="\n",
    )
    return languages


def _prepare_serena_project_state(
    settings: SerenaSettings,
    *,
    environment: Mapping[str, str],
    project_root: str,
    pyright_launcher: Path,
) -> Path:
    settings.project_data_root.mkdir(parents=True, exist_ok=True)
    settings.config_root.mkdir(parents=True, exist_ok=True)
    config_path = settings.config_root / "serena_config.yml"
    if not config_path.is_file():
        completed = subprocess.run(
            [
                str(settings.executable),
                "-c",
                (
                    "from serena.config.serena_config import SerenaConfig; "
                    "SerenaConfig.from_config_file()"
                ),
            ],
            cwd=settings.install_root,
            env=dict(environment),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0 or not config_path.is_file():
            raise RuntimeError("Serena global configuration bootstrap failed")

    content = config_path.read_text(encoding="utf-8")
    rendered_launcher = str(pyright_launcher).replace("\\", "/")
    managed_ls_settings = (
        "ls_specific_settings:\n"
        "  python:\n"
        f'    ls_path: "{rendered_launcher}"'
    )
    if _LS_SETTINGS_EMPTY.search(content):
        content = _LS_SETTINGS_EMPTY.sub(managed_ls_settings, content, count=1)
        config_path.write_text(content, encoding="utf-8")
    elif _LS_SETTINGS_MANAGED.search(content):
        updated = _LS_SETTINGS_MANAGED.sub(managed_ls_settings, content, count=1)
        if updated != content:
            content = updated
            config_path.write_text(content, encoding="utf-8")
    elif "ls_specific_settings:" in content:
        raise RuntimeError(
            "Serena language-server settings are not in the managed Pyright form"
        )

    matches = tuple(_PROJECT_STATE_SETTING.finditer(content))
    if len(matches) != 1:
        raise RuntimeError(
            "Serena global configuration must contain exactly one project state location"
        )
    template = settings.project_serena_folder_template.replace("\\", "/")
    expected = f'project_serena_folder_location: "{template}"'
    if matches[0].group(0) != expected:
        updated = _PROJECT_STATE_SETTING.sub(expected, content, count=1)
        config_path.write_text(updated, encoding="utf-8")

    _reconcile_registered_projects(config_path)
    return settings.ensure_project_data_path(project_root)


class _SharedProviderClient:
    def __init__(self, inner: Any, owner: "SerenaRuntimeAdapter") -> None:
        self._inner = inner
        self._owner = owner
        self._context_depth = 0

    async def __aenter__(self):
        outermost = self._context_depth == 0
        active = await self._inner.__aenter__()
        self._context_depth += 1
        self._owner._publish_active_client(active)
        if outermost:
            protocol_version = getattr(self._inner, "protocol_version", None)
            self._owner.startup_state.mark_protocol(
                mode="legacy_compatibility",
                version=str(protocol_version) if protocol_version is not None else None,
            )
        return self

    async def __aexit__(self, *args: object) -> None:
        try:
            await self._inner.__aexit__(*args)
        finally:
            self._context_depth -= 1
            if self._context_depth == 0:
                self._owner._clear_active_client()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        return await self._inner.call_tool(name, arguments)

    async def call_tool_mcp(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> object:
        return await self._inner.call_tool_mcp(name=name, arguments=arguments, meta=meta)

    async def list_tools(self) -> Sequence[Any]:
        return await self._inner.list_tools()


class SerenaRuntimeAdapter:
    provider_id = "serena-mcp"

    def __init__(
        self,
        settings: SerenaSettings,
        *,
        environment: Mapping[str, str] | None = None,
        default_project: str | None = None,
        client_factory=Client,
    ) -> None:
        self.settings = settings
        self.environment = os.environ if environment is None else environment
        self.default_project = default_project
        self.client_factory = client_factory
        self.startup_state = ProviderStartupState()
        self.runtime_tools = ProviderRuntimeToolState()
        self._managed_pyright_launcher: Path | None = None
        self._managed_pyright_error: str | None = None
        try:
            self._managed_pyright_launcher = resolve_managed_pyright_launcher(settings)
        except RuntimeError as exc:
            self._managed_pyright_error = str(exc)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread_id: int | None = None
        self._active_client: Any | None = None

    @property
    def provider_version(self) -> str:
        return self.settings.package_version

    @property
    def state_fingerprint(self) -> str:
        return f"{self.settings.source_revision}:{self.settings.package_sha256}:offline"

    @property
    def managed_pyright_launcher(self) -> Path | None:
        return self._managed_pyright_launcher

    @property
    def managed_pyright_error(self) -> str | None:
        return self._managed_pyright_error

    def public_runtime_tools(self) -> tuple[Any, ...]:
        """Project only the explicitly approved public Serena read surface."""

        return tuple(
            tool
            for tool in self.runtime_tools.snapshot()
            if str(getattr(tool, "name", "")).strip() in _PUBLIC_READ_TOOLS
        )

    def _publish_active_client(self, client: Any) -> None:
        self._active_client = client
        self._loop = asyncio.get_running_loop()
        self._loop_thread_id = get_ident()

    def _clear_active_client(self) -> None:
        self._active_client = None
        self._loop = None
        self._loop_thread_id = None

    def build_server(self) -> FastMCP:
        if not self.settings.executable.is_file():
            raise RuntimeError("Serena pinned venv interpreter is missing")
        try:
            verified_pyright = resolve_managed_pyright_launcher(self.settings)
        except RuntimeError as exc:
            self._managed_pyright_launcher = None
            self._managed_pyright_error = str(exc)
            raise
        self._managed_pyright_launcher = verified_pyright
        self._managed_pyright_error = None
        cwd = self.default_project or str(Path(__file__).resolve().parents[4])
        provider_environment = _provider_environment(self.settings, self.environment)
        _prepare_serena_project_state(
            self.settings,
            environment=provider_environment,
            project_root=cwd,
            pyright_launcher=verified_pyright,
        )
        transport = StdioTransport(
            command=str(self.settings.executable),
            args=list(self.settings.arguments),
            cwd=cwd,
            env=provider_environment,
        )
        shared_client = _SharedProviderClient(
            self.client_factory(transport, mode="legacy"),
            self,
        )
        startup_call = (
            ProviderStartupCall("activate_project", {"project": self.default_project})
            if self.default_project
            else None
        )
        provider = PersistentClientProxyProvider(
            shared_client,
            startup_call=startup_call,
            startup_state=self.startup_state,
            runtime_tools=self.runtime_tools,
        )
        server = FastMCP("kis-mcp-serena")
        server.add_provider(provider)
        server.add_transform(Visibility(False, match_all=True))
        server.add_transform(Visibility(True, names=set(_PUBLIC_READ_TOOLS)))
        return server

    def _call_sync(self, name: str, arguments: Mapping[str, Any]) -> Any:
        if self._active_client is None or self._loop is None:
            raise RuntimeError("Serena runtime client is not active")
        if self._loop_thread_id == get_ident():
            raise RuntimeError("Serena semantic read cannot block its provider event loop")
        future = asyncio.run_coroutine_threadsafe(
            self._active_client.call_tool(name, dict(arguments)),
            self._loop,
        )
        return future.result(timeout=90)

    @staticmethod
    def _json_result(result: Any) -> Any:
        if getattr(result, "is_error", False):
            raise RuntimeError("Serena semantic read returned an MCP error")
        text = _result_text(result)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Serena semantic read returned non-JSON evidence") from exc

    def read(
        self,
        project_path: str,
        source_paths: tuple[str, ...] = (),
    ) -> SemanticEvidence:
        self.settings.ensure_project_data_path(project_path)
        _repair_empty_project_languages(self.settings, project_path, source_paths)
        self._call_sync("activate_project", {"project": project_path})
        symbols: list[SemanticSymbol] = []
        relationships: list[SemanticRelationship] = []
        unknowns: list[str] = []
        selected_paths = tuple(
            path
            for path in source_paths
            if Path(path).suffix.casefold() in _SUPPORTED_SUFFIXES
        )[:64]

        for path in selected_paths:
            try:
                overview = self._json_result(
                    self._call_sync(
                        "get_symbols_overview",
                        {"relative_path": path, "depth": 0, "max_answer_chars": 8000},
                    )
                )
            except Exception as exc:
                unknowns.append(f"Serena overview unavailable for {path}: {type(exc).__name__}")
                continue
            if not isinstance(overview, dict):
                continue
            for kind, names in overview.items():
                if not isinstance(names, list):
                    continue
                for raw_name in names:
                    if not isinstance(raw_name, str) or not raw_name.strip():
                        continue
                    symbols.append(
                        SemanticSymbol(
                            qualified_name=f"{path}::{raw_name.strip()}",
                            name=raw_name.strip(),
                            kind=str(kind).casefold(),
                            path=path,
                            line=1,
                            language=Path(path).suffix.casefold().lstrip("."),
                        )
                    )
                    if len(symbols) >= 512:
                        break
                if len(symbols) >= 512:
                    break
            if len(symbols) >= 512:
                break

        refined: list[SemanticSymbol] = []
        for item in symbols[:64]:
            try:
                found = self._json_result(
                    self._call_sync(
                        "find_symbol",
                        {
                            "name_path_pattern": item.name,
                            "relative_path": item.path,
                            "include_body": False,
                            "depth": 0,
                            "max_matches": 2,
                            "max_answer_chars": 4000,
                        },
                    )
                )
            except Exception:
                refined.append(item)
                continue
            record = found[0] if isinstance(found, list) and found else None
            location = record.get("body_location") if isinstance(record, dict) else None
            if not isinstance(record, dict) or not isinstance(location, dict):
                refined.append(item)
                continue
            refined.append(
                SemanticSymbol(
                    qualified_name=f"{record.get('relative_path', item.path)}::{record.get('name_path', item.name)}",
                    name=str(record.get("name_path", item.name)).split("/")[-1],
                    kind=str(record.get("kind", item.kind)).casefold(),
                    path=str(record.get("relative_path", item.path)).replace("\\", "/"),
                    line=int(location.get("start_line", 0)) + 1,
                    end_line=int(location.get("end_line", 0)) + 1,
                    language=item.language,
                )
            )
        refined.extend(symbols[len(refined) :])
        symbols = refined

        for item in symbols[:8]:
            try:
                result = self._call_sync(
                    "find_referencing_symbols",
                    {
                        "name_path": item.name,
                        "relative_path": item.path,
                        "max_answer_chars": 12000,
                    },
                )
                text = _result_text(result)
                marker = "References without surrounding lines:\n"
                if marker in text:
                    text = text.split(marker, 1)[1]
                payload = json.loads(text)
            except Exception as exc:
                unknowns.append(
                    f"Serena references unavailable for {item.path}::{item.name}: {type(exc).__name__}"
                )
                continue
            if isinstance(payload, dict):
                for raw_path, by_kind in payload.items():
                    if not isinstance(by_kind, dict):
                        continue
                    for records in by_kind.values():
                        if not isinstance(records, list):
                            continue
                        for record in records:
                            if not isinstance(record, dict):
                                continue
                            relationships.append(
                                SemanticRelationship(
                                    kind="reference",
                                    source=str(record.get("name_path", raw_path)),
                                    target=item.qualified_name,
                                    path=str(raw_path).replace("\\", "/"),
                                    line=int(record.get("reference_line", 0)) + 1,
                                )
                            )
                            if len(relationships) >= 256:
                                break
                        if len(relationships) >= 256:
                            break
                    if len(relationships) >= 256:
                        break
            if len(relationships) >= 256:
                break

        status = "ready" if symbols else "partial"
        if not selected_paths:
            unknowns.append("Serena has no supported source files in this bounded snapshot.")
        elif not symbols:
            unknowns.append("Serena returned no semantic symbols; deterministic local parsing remains active.")
        return SemanticEvidence(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            status=status,
            symbols=tuple(symbols),
            relationships=tuple(relationships),
            unknowns=tuple(unknowns),
        )
