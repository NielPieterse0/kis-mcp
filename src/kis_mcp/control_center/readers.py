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
        size = path.stat().st_size
    except OSError:
        diagnostics.append(Diagnostic(unavailable_code, f"Unable to read {path.name}."))
        return None
    if size > settings.max_json_bytes:
        diagnostics.append(
            Diagnostic(
                f"{invalid_code}_LIMIT_EXCEEDED",
                f"Refused {path.name} because it exceeds the configured byte limit.",
            )
        )
        return None
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        diagnostics.append(Diagnostic(invalid_code, f"Invalid JSON in {path.name}."))
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
            product=_nested_string(runtime, "product", "name", default="kis-mcp"),
            server=_nested_string(runtime, "fastmcp", "server_name", default="unknown"),
            desktop_commander_version=_nested_string(
                runtime, "desktop_commander", "version", default="unknown"
            ),
            desktop_commander_installed=installed,
            implementation_status=implementation_status,
        )

    @staticmethod
    def _desktop_commander_entry(desktop: dict[str, Any]) -> Path | None:
        raw = desktop.get("entry_point")
        launch = desktop.get("launch")
        cwd = launch.get("cwd") if isinstance(launch, dict) else None
        if not isinstance(raw, str) or not raw or not isinstance(cwd, str) or not cwd:
            return None
        return Path(cwd) / Path(raw)


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
            diagnostics.append(Diagnostic("CONTROL_CENTER_POLICY_INVALID", "Policy rules are unavailable."))
            return PolicySummary(status="invalid", closed_rule_set=False, rules=())
        rules: list[PolicyRuleSummary] = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                continue
            rule_id = raw.get("id")
            name = raw.get("name")
            prohibited = raw.get("prohibited_outcome")
            decision = raw.get("decision")
            if not all(isinstance(value, str) for value in (rule_id, name, prohibited, decision)):
                continue
            rules.append(
                PolicyRuleSummary(
                    rule_id=rule_id,
                    name=name,
                    prohibited_outcome=prohibited,
                    decision=decision,
                )
            )
        rule_ids = tuple(rule.rule_id for rule in rules)
        return PolicySummary(
            status="available",
            closed_rule_set=rule_ids == _EXPECTED_RULE_IDS,
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
            if not isinstance(raw, dict):
                continue
            provider_id = raw.get("provider_id")
            namespace = raw.get("namespace")
            enabled = raw.get("enabled")
            if not isinstance(provider_id, str) or not isinstance(namespace, str) or type(enabled) is not bool:
                continue
            providers.append(
                ProviderSummary(
                    provider_id=provider_id,
                    namespace=namespace,
                    enabled=enabled,
                    readiness="runtime_check_required" if enabled else "disabled",
                    action=(
                        "Authenticate or verify provider readiness before live use."
                        if enabled
                        else "Enable in provider runtime settings to expose this provider."
                    ),
                )
            )
        return tuple(sorted(providers, key=lambda item: item.provider_id))


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
        command = ["git", "status", "--short", "--branch", "--untracked-files=all"]
        environment = os.environ.copy()
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
            environment.pop(key, None)
        try:
            completed = subprocess.run(
                command,
                cwd=self.settings.project_path,
                env=environment,
                capture_output=True,
                text=True,
                timeout=self.settings.git_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return GitSummary("unavailable", None, None, None, "git executable not found")
        except subprocess.TimeoutExpired:
            return GitSummary("timeout", None, None, None, "git status timed out")
        except OSError:
            return GitSummary("unavailable", None, None, None, "git status failed to start")
        if completed.returncode != 0:
            detail = "not a Git repository" if "not a git repository" in completed.stderr.lower() else "git status failed"
            status = "not_repository" if detail == "not a Git repository" else "error"
            return GitSummary(status, None, None, None, detail)
        lines = completed.stdout.splitlines()
        branch = self._parse_branch(lines[0]) if lines and lines[0].startswith("##") else None
        changed = sum(1 for line in lines if not line.startswith("##"))
        return GitSummary(
            status="available",
            branch=branch,
            dirty=changed > 0,
            changed_files=changed,
            detail="Git status available.",
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
