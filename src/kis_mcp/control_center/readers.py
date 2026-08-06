from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from kis_mcp.quarantine import QUARANTINE_SCHEMA_VERSION

from .contracts import (
    Diagnostic,
    GitSummary,
    PolicyRuleSummary,
    PolicySummary,
    ProviderSummary,
    QuarantineRecordSummary,
    QuarantineSummary,
    RuntimeSummary,
)
from .settings import ControlCenterSettings

_EXPECTED_RULE_IDS = ("HR-001", "HR-002", "HR-003")
_OPERATION_ID = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{12}")


def _read_json(
    path: Path,
    *,
    settings: ControlCenterSettings,
    diagnostics: list[Diagnostic],
    unavailable_code: str,
    invalid_code: str,
    schema_version: int = 1,
) -> dict[str, Any] | None:
    try:
        with path.open("rb") as handle:
            payload = handle.read(settings.max_json_bytes + 1)
    except OSError as exc:
        diagnostics.append(
            Diagnostic(unavailable_code, f"{path}: {type(exc).__name__}")
        )
        return None
    if len(payload) > settings.max_json_bytes:
        diagnostics.append(
            Diagnostic(
                f"{invalid_code}_LIMIT_EXCEEDED",
                (
                    f"{path}: JSON input exceeds the configured "
                    f"{settings.max_json_bytes}-byte limit"
                ),
            )
        )
        return None
    try:
        value: Any = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        diagnostics.append(
            Diagnostic(invalid_code, f"{path}: {type(exc).__name__}")
        )
        return None
    if not isinstance(value, dict):
        diagnostics.append(Diagnostic(invalid_code, f"Expected an object in {path.name}."))
        return None
    if type(value.get("schema_version")) is not int or value["schema_version"] != schema_version:
        diagnostics.append(
            Diagnostic(invalid_code, f"Unsupported or missing schema_version in {path.name}.")
        )
        return None
    return value


def _nested_string(value: dict[str, Any], *keys: str, default: str) -> str:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if isinstance(current, str) and current else default


class RuntimeStatusReader:
    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def read(self, diagnostics: list[Diagnostic]) -> RuntimeSummary:
        runtime = _read_json(
            self.settings.runtime_settings_path,
            settings=self.settings,
            diagnostics=diagnostics,
            unavailable_code="CONTROL_CENTER_RUNTIME_SETTINGS_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_RUNTIME_SETTINGS_INVALID",
        )
        if runtime is None:
            return RuntimeSummary(
                status="unavailable",
                product="unknown",
                server="unknown",
                desktop_commander_version="unknown",
                desktop_commander_installed=None,
                implementation_status=(),
            )
        implementation = runtime.get("implementation_status")
        implementation_status = (
            tuple(sorted((str(key), str(value)) for key, value in implementation.items()))
            if isinstance(implementation, dict)
            else ()
        )
        desktop = runtime.get("desktop_commander")
        desktop_value = desktop if isinstance(desktop, dict) else {}
        installed: bool | None = None
        entry = self._desktop_commander_entry(desktop_value)
        if entry is not None:
            installed = entry.is_file()
        return RuntimeSummary(
            status="available",
            product=_nested_string(runtime, "product", "name", default="unknown"),
            server=_nested_string(runtime, "fastmcp", "server_name", default="unknown"),
            desktop_commander_version=_nested_string(
                runtime, "desktop_commander", "version", default="unknown"
            ),
            desktop_commander_installed=installed,
            implementation_status=implementation_status,
        )

    @staticmethod
    def _desktop_commander_entry(desktop: dict[str, Any]) -> Path | None:
        launch = desktop.get("launch")
        if isinstance(launch, dict):
            args = launch.get("args")
            if (
                isinstance(args, list)
                and args
                and isinstance(args[0], str)
                and args[0]
            ):
                return Path(args[0])
        entry = desktop.get("entry_point")
        cwd = launch.get("cwd") if isinstance(launch, dict) else None
        if isinstance(entry, str) and entry and isinstance(cwd, str) and cwd:
            return Path(cwd) / entry
        return None


class PolicyStatusReader:
    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def read(self, diagnostics: list[Diagnostic]) -> PolicySummary:
        policy = _read_json(
            self.settings.policy_path,
            settings=self.settings,
            diagnostics=diagnostics,
            unavailable_code="CONTROL_CENTER_POLICY_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_POLICY_INVALID",
        )
        if policy is None:
            return PolicySummary(status="unavailable", closed_rule_set=False, rules=())
        raw_rules = policy.get("rules")
        if not isinstance(raw_rules, list):
            diagnostics.append(
                Diagnostic(
                    "CONTROL_CENTER_POLICY_INVALID",
                    "Policy rules must be an array.",
                )
            )
            return PolicySummary(status="invalid", closed_rule_set=False, rules=())
        rules: list[PolicyRuleSummary] = []
        for raw in raw_rules:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                continue
            rules.append(
                PolicyRuleSummary(
                    rule_id=raw["id"],
                    name=str(raw.get("name", "unknown")),
                    prohibited_outcome=str(
                        raw.get("prohibited_outcome", "unknown")
                    ),
                    decision=str(raw.get("decision", "unknown")),
                )
            )
        closed = tuple(rule.rule_id for rule in rules) == _EXPECTED_RULE_IDS
        if not closed:
            diagnostics.append(
                Diagnostic(
                    "CONTROL_CENTER_POLICY_RULE_SET_MISMATCH",
                    (
                        "Policy does not contain exactly HR-001, HR-002, and HR-003 "
                        "in canonical order."
                    ),
                )
            )
        return PolicySummary(
            status="available" if rules else "invalid",
            closed_rule_set=closed,
            rules=tuple(rules),
        )


class ProviderStatusReader:
    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def read(self, diagnostics: list[Diagnostic]) -> tuple[ProviderSummary, ...]:
        provider_document = _read_json(
            self.settings.provider_settings_path,
            settings=self.settings,
            diagnostics=diagnostics,
            unavailable_code="CONTROL_CENTER_PROVIDER_SETTINGS_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_PROVIDER_SETTINGS_INVALID",
        )
        if provider_document is None:
            return ()
        raw_providers = provider_document.get("providers")
        if not isinstance(raw_providers, list):
            diagnostics.append(
                Diagnostic("CONTROL_CENTER_PROVIDER_SETTINGS_INVALID", "Provider entries are unavailable.")
            )
            return ()
        providers: list[ProviderSummary] = []
        for raw in raw_providers[: self.settings.max_provider_entries]:
            if not isinstance(raw, dict) or not isinstance(raw.get("provider_id"), str):
                continue
            providers.append(
                ProviderSummary(
                    provider_id=raw["provider_id"],
                    namespace=str(raw.get("namespace", "unknown")),
                    enabled=raw.get("enabled") is True,
                    readiness="runtime_check_required",
                    action=(
                        "Use kis_provider_status for current build, mount, authentication, "
                        "and commissioning evidence."
                    ),
                )
            )
        return tuple(providers)


class QuarantineStatusReader:
    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def read(
        self, diagnostics: list[Diagnostic]
    ) -> tuple[QuarantineSummary, tuple[QuarantineRecordSummary, ...]]:
        root = self.settings.quarantine_root
        if not root.exists():
            return (
                QuarantineSummary(
                    root=str(root),
                    status="empty",
                    total_records=0,
                    active_records=0,
                    restored_records=0,
                    invalid_records=0,
                    truncated=False,
                ),
                (),
            )
        if not root.is_dir():
            diagnostics.append(
                Diagnostic("CONTROL_CENTER_QUARANTINE_UNAVAILABLE", "Quarantine root is not a directory.")
            )
            return (
                QuarantineSummary(
                    root=str(root),
                    status="unavailable",
                    total_records=0,
                    active_records=0,
                    restored_records=0,
                    invalid_records=0,
                    truncated=False,
                ),
                (),
            )
        try:
            operation_roots = sorted(
                (
                    path
                    for path in root.iterdir()
                    if path.is_dir() and not path.is_symlink() and _OPERATION_ID.fullmatch(path.name)
                ),
                key=lambda path: path.name,
                reverse=True,
            )
        except OSError:
            diagnostics.append(
                Diagnostic("CONTROL_CENTER_QUARANTINE_UNAVAILABLE", "Unable to enumerate quarantine records.")
            )
            return (
                QuarantineSummary(
                    root=str(root),
                    status="unavailable",
                    total_records=0,
                    active_records=0,
                    restored_records=0,
                    invalid_records=0,
                    truncated=False,
                ),
                (),
            )
        active = restored = invalid = 0
        records: list[QuarantineRecordSummary] = []
        for operation_root in operation_roots[: self.settings.max_quarantine_records]:
            metadata = _read_json(
                operation_root / "metadata.json",
                settings=self.settings,
                diagnostics=diagnostics,
                unavailable_code="CONTROL_CENTER_QUARANTINE_METADATA_UNAVAILABLE",
                invalid_code="CONTROL_CENTER_QUARANTINE_METADATA_INVALID",
                schema_version=QUARANTINE_SCHEMA_VERSION,
            )
            if metadata is None:
                invalid += 1
                continue
            operation_id = metadata.get("operation_id")
            original_path = metadata.get("original_path")
            item_type = metadata.get("item_type")
            restored_at = metadata.get("restored_at")
            if (
                operation_id != operation_root.name
                or not isinstance(original_path, str)
                or not isinstance(item_type, str)
                or (restored_at is not None and not isinstance(restored_at, str))
            ):
                invalid += 1
                diagnostics.append(
                    Diagnostic(
                        "CONTROL_CENTER_QUARANTINE_METADATA_INVALID",
                        f"Invalid quarantine metadata for {operation_root.name}.",
                    )
                )
                continue
            is_restored = restored_at is not None
            if is_restored:
                restored += 1
            else:
                active += 1
            records.append(
                QuarantineRecordSummary(
                    operation_id=operation_id,
                    original_path=original_path,
                    item_type=item_type,
                    restored=is_restored,
                )
            )
        return (
            QuarantineSummary(
                root=str(root),
                status="available",
                total_records=len(operation_roots),
                active_records=active,
                restored_records=restored,
                invalid_records=invalid,
                truncated=len(operation_roots) > self.settings.max_quarantine_records,
            ),
            tuple(records),
        )


class GitStatusReader:
    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def read(self) -> GitSummary:
        project_path = self.settings.project_path
        if not project_path.is_dir():
            return GitSummary(
                status="path_unavailable",
                branch=None,
                dirty=None,
                changed_files=None,
                detail="Configured project path is not an available directory.",
            )
        environment = dict(os.environ)
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ):
            environment.pop(key, None)
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_CEILING_DIRECTORIES": str(project_path.parent),
            }
        )
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(project_path),
                    "status",
                    "--short",
                    "--branch",
                    "--untracked-files=normal",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.git_timeout_seconds,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return GitSummary(
                status="unavailable",
                branch=None,
                dirty=None,
                changed_files=None,
                detail=f"Local Git status is unavailable: {type(exc).__name__}.",
            )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            status = (
                "not_repository"
                if "not a git repository" in detail.casefold()
                else "unavailable"
            )
            return GitSummary(
                status=status,
                branch=None,
                dirty=None,
                changed_files=None,
                detail=detail or "Local Git status returned a non-zero exit code.",
            )
        lines = completed.stdout.splitlines()
        header = lines[0] if lines and lines[0].startswith("## ") else ""
        changes = lines[1:] if header else lines
        return GitSummary(
            status="available",
            branch=self._parse_branch(header),
            dirty=bool(changes),
            changed_files=len(changes),
            detail="Local fixed-template Git status collected without remote access.",
        )

    @staticmethod
    def _parse_branch(header: str) -> str | None:
        if not header.startswith("## "):
            return None
        value = header[3:].strip()
        marker = "No commits yet on "
        if value.startswith(marker):
            return value[len(marker) :]
        if value.startswith("HEAD (no branch)"):
            return None
        return value.split("...", 1)[0].split(" ", 1)[0] or None


__all__ = [
    "GitStatusReader",
    "PolicyStatusReader",
    "ProviderStatusReader",
    "QuarantineStatusReader",
    "RuntimeStatusReader",
]
