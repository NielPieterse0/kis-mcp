from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .discover.settings import DiscoverSettings

from .paths import (
    PathValidationError,
    is_within_windows_boundary,
    normalize_windows_path,
    resolve_windows_effective_path,
)


EXPECTED_RULE_IDS = ("HR-001", "HR-002", "HR-003")
APPROVED_PROJECT_BOUNDARY = r"C:\Projects"
APPROVED_STATE_ROOT = r"C:\Projects\.kis-mcp"
GENERATED_PATH_KEYS = (
    "state_root",
    "desktop_commander_root",
    "desktop_commander_config_root",
    "quarantine_root",
    "temp_root",
    "log_root",
    "npm_cache_root",
    "python_environment_root",
    "uv_cache_root",
    "python_cache_root",
    "pytest_cache_root",
)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    raw_settings: dict[str, Any]
    raw_policy: dict[str, Any]

    @property
    def project_boundary(self) -> str:
        return str(self.raw_settings["paths"]["project_boundary"])

    @property
    def state_root(self) -> str:
        return str(self.raw_settings["paths"]["state_root"])

    @property
    def quarantine_root(self) -> str:
        return str(self.raw_settings["paths"]["quarantine_root"])

    @property
    def temp_root(self) -> str:
        return str(self.raw_settings["paths"]["temp_root"])

    @property
    def desktop_commander_root(self) -> str:
        return str(self.raw_settings["paths"]["desktop_commander_root"])

    @property
    def desktop_commander_config_root(self) -> str:
        return str(self.raw_settings["paths"]["desktop_commander_config_root"])

    @property
    def python_environment_root(self) -> str:
        return str(self.raw_settings["paths"]["python_environment_root"])

    @property
    def uv_cache_root(self) -> str:
        return str(self.raw_settings["paths"]["uv_cache_root"])

    @property
    def python_cache_root(self) -> str:
        return str(self.raw_settings["paths"]["python_cache_root"])

    @property
    def pytest_cache_root(self) -> str:
        return str(self.raw_settings["paths"]["pytest_cache_root"])

    @property
    def npm_cache_root(self) -> str:
        return str(self.raw_settings["paths"]["npm_cache_root"])

    @property
    def provider_state_file(self) -> str:
        return str(Path(self.desktop_commander_config_root) / "config.json")

    @property
    def puppeteer_cache_root(self) -> str:
        return str(Path(self.desktop_commander_config_root) / "puppeteer-cache")

    @property
    def require_local_chrome(self) -> bool:
        return bool(self.raw_settings["desktop_commander"].get("require_local_chrome", True))

    @property
    def server_name(self) -> str:
        return str(self.raw_settings["fastmcp"]["server_name"])

    @property
    def transport(self) -> str:
        return str(self.raw_settings["fastmcp"]["transport"])

    @property
    def desktop_commander_launch(self) -> dict[str, Any]:
        return dict(self.raw_settings["desktop_commander"]["launch"])

    @property
    def desktop_commander_package(self) -> str:
        return str(self.raw_settings["desktop_commander"]["package"])

    @property
    def desktop_commander_version(self) -> str:
        return str(self.raw_settings["desktop_commander"]["version"])

    @property
    def desktop_commander_entry(self) -> str:
        return str(self.raw_settings["desktop_commander"]["launch"]["args"][0])

    @property
    def desktop_commander_package_metadata(self) -> str:
        package_parts = self.desktop_commander_package.split("/")
        return str(
            Path(self.desktop_commander_root)
            / "node_modules"
            / Path(*package_parts)
            / "package.json"
        )

    @property
    def implementation_status(self) -> dict[str, str]:
        return {
            str(key): str(value)
            for key, value in self.raw_settings.get("implementation_status", {}).items()
        }

    @property
    def discover_settings(self) -> "DiscoverSettings":
        from .discover.settings import DiscoverSettings

        return DiscoverSettings.from_mapping(self.raw_settings.get("discover"))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required configuration is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Configuration root must be an object: {path}")
    return value


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{path} must be an object")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{path} must be a non-empty string")
    return value.strip()


def _validated_effective_path(value: Any, *, base: str, label: str) -> str:
    raw = _string(value, label)
    try:
        return resolve_windows_effective_path(raw, base=base, follow_final=False)
    except PathValidationError as exc:
        raise RuntimeError(f"{label} is not a valid Windows path: {raw}") from exc


def _validate_path_layout(
    settings: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    repository_root: Path,
) -> None:
    paths = _object(settings.get("paths"), "settings.paths")
    project_boundary = normalize_windows_path(
        _string(paths.get("project_boundary"), "settings.paths.project_boundary"),
        base=APPROVED_PROJECT_BOUNDARY,
    )
    if project_boundary.casefold() != APPROVED_PROJECT_BOUNDARY.casefold():
        raise RuntimeError(
            f"The approved project boundary is fixed at {APPROVED_PROJECT_BOUNDARY}"
        )
    if project_boundary.casefold() != _string(
        policy.get("project_boundary"), "policy.project_boundary"
    ).casefold():
        raise RuntimeError("Settings and policy project boundaries differ")

    effective_repository = resolve_windows_effective_path(
        str(repository_root.resolve()),
        base=project_boundary,
        follow_final=True,
    )
    state_root = _validated_effective_path(
        paths.get("state_root"),
        base=project_boundary,
        label="settings.paths.state_root",
    )
    approved_state_root = resolve_windows_effective_path(
        APPROVED_STATE_ROOT,
        base=project_boundary,
        follow_final=False,
    )
    if state_root.casefold() != approved_state_root.casefold():
        raise RuntimeError(f"settings.paths.state_root must be {APPROVED_STATE_ROOT}")
    if not is_within_windows_boundary(state_root, boundary=project_boundary):
        raise RuntimeError("settings.paths.state_root must resolve beneath C:\\Projects")
    if is_within_windows_boundary(state_root, boundary=effective_repository):
        raise RuntimeError("settings.paths.state_root must remain outside the repository")

    for key in GENERATED_PATH_KEYS:
        effective = _validated_effective_path(
            paths.get(key),
            base=project_boundary,
            label=f"settings.paths.{key}",
        )
        if not is_within_windows_boundary(effective, boundary=state_root):
            raise RuntimeError(f"settings.paths.{key} must resolve beneath state_root")
        if is_within_windows_boundary(effective, boundary=effective_repository):
            raise RuntimeError(f"settings.paths.{key} must remain outside the repository")

    quarantine_root = normalize_windows_path(
        _string(paths.get("quarantine_root"), "settings.paths.quarantine_root"),
        base=project_boundary,
    )
    if quarantine_root.casefold() != _string(
        policy.get("quarantine_root"), "policy.quarantine_root"
    ).casefold():
        raise RuntimeError("Settings and policy quarantine roots differ")


def _validate_provider(settings: Mapping[str, Any]) -> None:
    paths = _object(settings.get("paths"), "settings.paths")
    provider = _object(settings.get("desktop_commander"), "settings.desktop_commander")
    if _string(provider.get("package"), "settings.desktop_commander.package") != (
        "@wonderwhy-er/desktop-commander"
    ):
        raise RuntimeError("Desktop Commander must use the authoritative package")
    version = _string(provider.get("version"), "settings.desktop_commander.version")
    if re.fullmatch(r"\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.-]+)?", version) is None:
        raise RuntimeError("Desktop Commander version must be an exact pinned version")

    launch = _object(provider.get("launch"), "settings.desktop_commander.launch")
    command = _string(launch.get("command"), "settings.desktop_commander.launch.command")
    if Path(command).name.casefold() not in {"node", "node.exe"}:
        raise RuntimeError("Desktop Commander launch command must be node.exe")
    args = launch.get("args")
    if not isinstance(args, Sequence) or isinstance(args, (str, bytes)) or not args:
        raise RuntimeError("settings.desktop_commander.launch.args must be a non-empty array")

    project_boundary = _string(paths.get("project_boundary"), "settings.paths.project_boundary")
    provider_root = _validated_effective_path(
        paths.get("desktop_commander_root"),
        base=project_boundary,
        label="settings.paths.desktop_commander_root",
    )
    launch_cwd = _validated_effective_path(
        launch.get("cwd"),
        base=project_boundary,
        label="settings.desktop_commander.launch.cwd",
    )
    entry = _validated_effective_path(
        args[0],
        base=project_boundary,
        label="settings.desktop_commander.launch.args[0]",
    )
    if launch_cwd.casefold() != provider_root.casefold():
        raise RuntimeError("Desktop Commander launch cwd must equal desktop_commander_root")
    if not is_within_windows_boundary(entry, boundary=provider_root):
        raise RuntimeError("Desktop Commander entry point must remain beneath its install root")


def load_runtime_config(repository_root: Path | None = None) -> RuntimeConfig:
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    settings = _read_json(root / "settings" / "kis-mcp.settings.json")
    policy = _read_json(root / "policy" / "kis-mcp.policy.json")

    if settings.get("schema_version") != 1 or policy.get("schema_version") != 1:
        raise RuntimeError("Settings and policy schema_version must be 1")
    rule_ids = tuple(rule.get("id") for rule in policy.get("rules", []))
    if rule_ids != EXPECTED_RULE_IDS:
        raise RuntimeError(
            "Policy must contain exactly HR-001, HR-002, and HR-003 in order"
        )

    _validate_path_layout(settings, policy, repository_root=root)
    _validate_provider(settings)

    from .discover.settings import DiscoverSettings

    try:
        DiscoverSettings.from_mapping(settings.get("discover"))
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc

    fastmcp = _object(settings.get("fastmcp"), "settings.fastmcp")
    if _string(fastmcp.get("transport"), "settings.fastmcp.transport") != "stdio":
        raise RuntimeError("kis-mcp currently supports only the stdio transport")
    _string(fastmcp.get("version"), "settings.fastmcp.version")
    _string(fastmcp.get("server_name"), "settings.fastmcp.server_name")

    return RuntimeConfig(raw_settings=settings, raw_policy=policy)
