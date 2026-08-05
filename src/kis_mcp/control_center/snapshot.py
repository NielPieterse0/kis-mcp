from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import (
    ControlCenterSnapshot,
    Diagnostic,
    GitSummary,
    PolicyRuleSummary,
    PolicySummary,
    ProjectSummary,
    ProviderSummary,
    QuarantineSummary,
    RuntimeSummary,
    VerificationSummary,
)
from .settings import ControlCenterSettings

_OPERATION_ID_PATTERN = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{12}")
_CLOSED_RULE_IDS = ("HR-001", "HR-002", "HR-003")


class ControlCenterSnapshotService:
    """Collect bounded local evidence without mutation or network access."""

    def __init__(self, settings: ControlCenterSettings) -> None:
        self.settings = settings

    def collect(self) -> ControlCenterSnapshot:
        diagnostics: list[Diagnostic] = []
        runtime = self._runtime_summary(diagnostics)
        project = ProjectSummary(
            path=str(self.settings.project_path),
            exists=self.settings.project_path.exists(),
            git=self._git_summary(),
        )
        policy = self._policy_summary(diagnostics)
        providers = self._provider_summaries(diagnostics)
        quarantine = self._quarantine_summary(diagnostics)
        verification = VerificationSummary(
            status="not_recorded",
            command=self.settings.verification_command,
            detail=(
                "No verification result is inferred from configuration. Run the "
                "configured command through the supervised Work surface for current evidence."
            ),
        )
        return ControlCenterSnapshot(
            schema_version=1,
            generated_at=datetime.now(UTC).isoformat(),
            runtime=runtime,
            project=project,
            policy=policy,
            providers=providers,
            quarantine=quarantine,
            verification=verification,
            diagnostics=tuple(diagnostics),
        )

    def _runtime_summary(self, diagnostics: list[Diagnostic]) -> RuntimeSummary:
        raw = self._read_json(
            self.settings.runtime_settings_path,
            unavailable_code="CONTROL_CENTER_RUNTIME_SETTINGS_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_RUNTIME_SETTINGS_INVALID",
            diagnostics=diagnostics,
        )
        if raw is None:
            return RuntimeSummary(
                status="unavailable",
                product="unknown",
                server="unknown",
                desktop_commander_version="unknown",
                desktop_commander_installed=None,
                implementation_status=(),
            )

        product = _nested_string(raw, "product", "name") or "unknown"
        server = _nested_string(raw, "fastmcp", "server_name") or "unknown"
        desktop_commander_version = (
            _nested_string(raw, "desktop_commander", "version") or "unknown"
        )
        entry_path = self._desktop_commander_entry(raw)
        implementation = raw.get("implementation_status", {})
        implementation_status = (
            tuple(
                sorted(
                    (str(key), str(value))
                    for key, value in implementation.items()
                )
            )
            if isinstance(implementation, dict)
            else ()
        )
        return RuntimeSummary(
            status="available",
            product=product,
            server=server,
            desktop_commander_version=desktop_commander_version,
            desktop_commander_installed=(entry_path.is_file() if entry_path else None),
            implementation_status=implementation_status,
        )

    @staticmethod
    def _desktop_commander_entry(raw: dict[str, Any]) -> Path | None:
        section = raw.get("desktop_commander")
        if not isinstance(section, dict):
            return None
        launch = section.get("launch")
        if isinstance(launch, dict):
            args = launch.get("args")
            if isinstance(args, list) and args and type(args[0]) is str:
                return Path(args[0])
        entry = section.get("entry_point")
        cwd = launch.get("cwd") if isinstance(launch, dict) else None
        if type(entry) is str and type(cwd) is str:
            return Path(cwd) / entry
        return None

    def _git_summary(self) -> GitSummary:
        if not self.settings.project_path.is_dir():
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
                "GIT_CEILING_DIRECTORIES": str(self.settings.project_path.parent),
            }
        )
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.settings.project_path),
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
                detail=f"Local Git status is unavailable: {exc}",
            )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            status = "not_repository" if "not a git repository" in detail.lower() else "unavailable"
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
            branch=_parse_branch(header),
            dirty=bool(changes),
            changed_files=len(changes),
            detail="Local fixed-template Git status collected without remote access.",
        )

    def _policy_summary(self, diagnostics: list[Diagnostic]) -> PolicySummary:
        raw = self._read_json(
            self.settings.policy_path,
            unavailable_code="CONTROL_CENTER_POLICY_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_POLICY_INVALID",
            diagnostics=diagnostics,
        )
        if raw is None:
            return PolicySummary(status="unavailable", closed_rule_set=False, rules=())
        rules_raw = raw.get("rules")
        if not isinstance(rules_raw, list):
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_POLICY_INVALID",
                    message="Policy rules must be an array.",
                )
            )
            return PolicySummary(status="invalid", closed_rule_set=False, rules=())

        rules: list[PolicyRuleSummary] = []
        for item in rules_raw:
            if not isinstance(item, dict):
                continue
            rule_id = item.get("id")
            if type(rule_id) is not str:
                continue
            rules.append(
                PolicyRuleSummary(
                    rule_id=rule_id,
                    name=str(item.get("name", "unknown")),
                    prohibited_outcome=str(item.get("prohibited_outcome", "unknown")),
                    decision=str(item.get("decision", "unknown")),
                )
            )
        closed = tuple(rule.rule_id for rule in rules) == _CLOSED_RULE_IDS
        if not closed:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_POLICY_RULE_SET_MISMATCH",
                    message="Policy does not contain exactly HR-001, HR-002, and HR-003 in canonical order.",
                )
            )
        return PolicySummary(
            status="available" if rules else "invalid",
            closed_rule_set=closed,
            rules=tuple(rules),
        )

    def _provider_summaries(
        self, diagnostics: list[Diagnostic]
    ) -> tuple[ProviderSummary, ...]:
        raw = self._read_json(
            self.settings.provider_settings_path,
            unavailable_code="CONTROL_CENTER_PROVIDER_SETTINGS_UNAVAILABLE",
            invalid_code="CONTROL_CENTER_PROVIDER_SETTINGS_INVALID",
            diagnostics=diagnostics,
        )
        if raw is None:
            return ()
        providers = raw.get("providers")
        if not isinstance(providers, list):
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_PROVIDER_SETTINGS_INVALID",
                    message="Provider settings providers field must be an array.",
                )
            )
            return ()

        summaries: list[ProviderSummary] = []
        for item in providers[: self.settings.max_provider_entries]:
            if not isinstance(item, dict) or type(item.get("provider_id")) is not str:
                continue
            summaries.append(
                ProviderSummary(
                    provider_id=item["provider_id"],
                    namespace=str(item.get("namespace", "unknown")),
                    enabled=item.get("enabled") is True,
                    readiness="runtime_check_required",
                    action="Use kis_provider_status for current build, mount, authentication, and commissioning evidence.",
                )
            )
        return tuple(summaries)

    def _quarantine_summary(
        self, diagnostics: list[Diagnostic]
    ) -> QuarantineSummary:
        root = self.settings.quarantine_root
        if not root.exists():
            return QuarantineSummary(
                root=str(root),
                status="empty",
                total_records=0,
                active_records=0,
                restored_records=0,
                invalid_records=0,
                truncated=False,
            )
        if not root.is_dir():
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_QUARANTINE_UNAVAILABLE",
                    message="Configured quarantine root is not a directory.",
                )
            )
            return QuarantineSummary(
                root=str(root),
                status="unavailable",
                total_records=0,
                active_records=0,
                restored_records=0,
                invalid_records=0,
                truncated=False,
            )

        entries = sorted(
            (
                path
                for path in root.iterdir()
                if _OPERATION_ID_PATTERN.fullmatch(path.name) is not None
            ),
            key=lambda path: path.name,
            reverse=True,
        )
        selected = entries[: self.settings.max_quarantine_records]
        active = restored = invalid = 0
        for operation_root in selected:
            metadata_path = operation_root / "metadata.json"
            metadata = self._read_json(
                metadata_path,
                unavailable_code="CONTROL_CENTER_QUARANTINE_METADATA_UNAVAILABLE",
                invalid_code="CONTROL_CENTER_QUARANTINE_METADATA_INVALID",
                diagnostics=diagnostics,
            )
            if metadata is None:
                invalid += 1
                continue
            restored_at = metadata.get("restored_at")
            if restored_at is None:
                active += 1
            elif type(restored_at) is str:
                restored += 1
            else:
                invalid += 1
        return QuarantineSummary(
            root=str(root),
            status="available",
            total_records=len(entries),
            active_records=active,
            restored_records=restored,
            invalid_records=invalid,
            truncated=len(entries) > len(selected),
        )

    def _read_json(
        self,
        path: Path,
        *,
        unavailable_code: str,
        invalid_code: str,
        diagnostics: list[Diagnostic],
    ) -> dict[str, Any] | None:
        try:
            with path.open("rb") as handle:
                payload = handle.read(self.settings.max_json_bytes + 1)
        except OSError as exc:
            diagnostics.append(
                Diagnostic(code=unavailable_code, message=f"{path}: {exc}")
            )
            return None
        if len(payload) > self.settings.max_json_bytes:
            diagnostics.append(
                Diagnostic(
                    code=f"{invalid_code}_LIMIT_EXCEEDED",
                    message=(
                        f"{path}: JSON input exceeds the configured "
                        f"{self.settings.max_json_bytes}-byte limit"
                    ),
                )
            )
            return None
        try:
            raw: Any = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            diagnostics.append(Diagnostic(code=invalid_code, message=f"{path}: {exc}"))
            return None
        if not isinstance(raw, dict):
            diagnostics.append(
                Diagnostic(code=invalid_code, message=f"{path}: root must be an object")
            )
            return None
        return raw


def _nested_string(raw: dict[str, Any], section: str, field: str) -> str | None:
    value = raw.get(section)
    if not isinstance(value, dict):
        return None
    nested = value.get(field)
    return nested if type(nested) is str else None


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
