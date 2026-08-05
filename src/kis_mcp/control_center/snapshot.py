from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kis_mcp.providers.runtime import latest_provider_runtime_composition
from kis_mcp.runtime_observability import (
    RuntimeObservability,
    RuntimeObservabilitySnapshot,
    get_runtime_observability,
)

from .contracts import (
    ApprovalSummary,
    AvailableAction,
    ControlCenterSnapshot,
    Diagnostic,
    DiscoverSummary,
    GitSummary,
    PolicyRuleSummary,
    PolicySummary,
    ProjectSummary,
    ProviderRuntimeSummary,
    ProviderSummary,
    QuarantineRecordSummary,
    QuarantineSummary,
    RuntimeSummary,
    VerificationSummary,
)
from .settings import ControlCenterSettings

_OPERATION_ID_PATTERN = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{12}")
_APPROVAL_HEADING_PATTERN = re.compile(
    r"^##\s+([A-Za-z0-9-]+)\s+(?:—|-)\s+(.+?)\s*$",
    re.MULTILINE,
)
_CLOSED_RULE_IDS = ("HR-001", "HR-002", "HR-003")

DiscoverSource = Callable[[], Mapping[str, Any]]
ProviderStatusSource = Callable[[], Mapping[str, Any]]


class ControlCenterSnapshotService:
    """Collect bounded local evidence without mutation or network access."""

    def __init__(
        self,
        settings: ControlCenterSettings,
        *,
        observability: RuntimeObservability | None = None,
        discover_source: DiscoverSource | None = None,
        provider_status_source: ProviderStatusSource | None = None,
    ) -> None:
        self.settings = settings
        self.observability = observability or get_runtime_observability()
        self.discover_source = discover_source or self._default_discover_source
        self.provider_status_source = (
            provider_status_source or self._default_provider_status_source
        )

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
        approvals = self._approval_summaries(diagnostics)
        discover = self._discover_summary(diagnostics)
        provider_runtime = self._provider_runtime_summaries(diagnostics)
        quarantine, quarantine_records = self._quarantine_evidence(diagnostics)
        verification = VerificationSummary(
            status="not_recorded",
            command=self.settings.verification_command,
            detail=(
                "No current verification result is inferred from configuration. Run the "
                "configured command through the supervised Work surface for fresh evidence."
            ),
        )
        return ControlCenterSnapshot(
            schema_version=1,
            generated_at=datetime.now(UTC).isoformat(),
            runtime=runtime,
            project=project,
            policy=policy,
            approvals=approvals,
            discover=discover,
            providers=providers,
            provider_runtime=provider_runtime,
            observability=self._bounded_observability(),
            quarantine=quarantine,
            quarantine_records=quarantine_records,
            actions=self._available_actions(),
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
        version = _nested_string(raw, "desktop_commander", "version") or "unknown"
        entry_path = self._desktop_commander_entry(raw)
        implementation = raw.get("implementation_status", {})
        implementation_status = (
            tuple(sorted((str(key), str(value)) for key, value in implementation.items()))
            if isinstance(implementation, Mapping)
            else ()
        )
        return RuntimeSummary(
            status="available",
            product=product,
            server=server,
            desktop_commander_version=version,
            desktop_commander_installed=(entry_path.is_file() if entry_path else None),
            implementation_status=implementation_status,
        )

    @staticmethod
    def _desktop_commander_entry(raw: Mapping[str, Any]) -> Path | None:
        section = raw.get("desktop_commander")
        if not isinstance(section, Mapping):
            return None
        launch = section.get("launch")
        if isinstance(launch, Mapping):
            args = launch.get("args")
            if isinstance(args, Sequence) and not isinstance(args, (str, bytes)):
                if args and type(args[0]) is str:
                    return Path(args[0])
        entry = section.get("entry_point")
        cwd = launch.get("cwd") if isinstance(launch, Mapping) else None
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
            if not isinstance(item, Mapping) or type(item.get("id")) is not str:
                continue
            rules.append(
                PolicyRuleSummary(
                    rule_id=item["id"],
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
                    message=(
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
            if not isinstance(item, Mapping) or type(item.get("provider_id")) is not str:
                continue
            summaries.append(
                ProviderSummary(
                    provider_id=item["provider_id"],
                    namespace=str(item.get("namespace", "unknown")),
                    enabled=item.get("enabled") is True,
                    readiness="runtime_check_required",
                    action=(
                        "Use kis_provider_status for current build, mount, authentication, "
                        "and commissioning evidence."
                    ),
                )
            )
        return tuple(summaries)

    def _approval_summaries(
        self, diagnostics: list[Diagnostic]
    ) -> tuple[ApprovalSummary, ...]:
        try:
            text = self.settings.approval_register_path.read_text(encoding="utf-8")
        except OSError as exc:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_APPROVAL_REGISTER_UNAVAILABLE",
                    message=f"Approval register is unavailable: {type(exc).__name__}.",
                )
            )
            return ()
        matches = list(_APPROVAL_HEADING_PATTERN.finditer(text))
        approvals: list[ApprovalSummary] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[start:end]
            decision_line = next(
                (line.strip() for line in body.splitlines() if "Operator decision:" in line),
                "",
            )
            if "[ ] Approve" not in decision_line:
                continue
            detail = next(
                (
                    line.split(":", 1)[1].strip()
                    for line in body.splitlines()
                    if line.strip().casefold().startswith("reason:") and ":" in line
                ),
                "Operator decision is pending.",
            )
            approvals.append(
                ApprovalSummary(
                    approval_id=match.group(1),
                    title=match.group(2).strip(),
                    status="pending",
                    detail=detail[:500],
                )
            )
            if len(approvals) >= self.settings.max_approval_entries:
                break
        return tuple(approvals)

    def _discover_summary(self, diagnostics: list[Diagnostic]) -> DiscoverSummary:
        if not self.settings.discover_enabled:
            return DiscoverSummary(
                status="disabled",
                project_id=None,
                languages=(),
                frameworks=(),
                module_count=0,
                finding_count=0,
                confidence="unknown",
                truncated=False,
                findings=(),
                detail="Discover collection is disabled in Control Center settings.",
            )
        try:
            raw = dict(self.discover_source())
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_DISCOVER_UNAVAILABLE",
                    message=f"Discover summary is unavailable: {type(exc).__name__}.",
                )
            )
            return DiscoverSummary(
                status="unavailable",
                project_id=None,
                languages=(),
                frameworks=(),
                module_count=0,
                finding_count=0,
                confidence="unknown",
                truncated=False,
                findings=(),
                detail="Discover failed independently; other dashboard evidence remains available.",
            )
        findings_raw = raw.get("findings", ())
        findings = tuple(
            _finding_text(item)
            for item in _sequence(findings_raw)[: self.settings.max_discover_findings]
        )
        return DiscoverSummary(
            status=str(raw.get("status", "available")),
            project_id=_optional_text(raw.get("project_id")),
            languages=tuple(str(item) for item in _sequence(raw.get("languages"))),
            frameworks=tuple(str(item) for item in _sequence(raw.get("frameworks"))),
            module_count=_non_negative_int(raw.get("module_count")),
            finding_count=_non_negative_int(raw.get("finding_count", len(findings))),
            confidence=str(raw.get("confidence", "unknown")),
            truncated=raw.get("truncated") is True,
            findings=findings,
            detail=str(raw.get("detail", "Bounded local Discover summary."))[:500],
        )

    def _provider_runtime_summaries(
        self, diagnostics: list[Diagnostic]
    ) -> tuple[ProviderRuntimeSummary, ...]:
        try:
            raw = self.provider_status_source()
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_PROVIDER_RUNTIME_UNAVAILABLE",
                    message=f"Provider runtime evidence is unavailable: {type(exc).__name__}.",
                )
            )
            return ()
        providers = raw.get("external_providers") if isinstance(raw, Mapping) else None
        if not isinstance(providers, Sequence) or isinstance(providers, (str, bytes)):
            return ()
        summaries: list[ProviderRuntimeSummary] = []
        for item in providers[: self.settings.max_provider_entries]:
            if not isinstance(item, Mapping) or type(item.get("provider_id")) is not str:
                continue
            readiness_raw = item.get("readiness")
            readiness = (
                str(readiness_raw.get("state", "unknown"))
                if isinstance(readiness_raw, Mapping)
                else "unknown"
            )
            user_status = item.get("user_status")
            action = (
                str(user_status.get("required_action"))
                if isinstance(user_status, Mapping) and user_status.get("required_action")
                else (
                    str(readiness_raw.get("summary"))
                    if isinstance(readiness_raw, Mapping) and readiness_raw.get("summary")
                    else "Inspect kis_provider_status for current provider evidence."
                )
            )
            commissioning_raw = item.get("commissioning")
            commissioning = (
                tuple(
                    sorted(
                        (str(key), str(value))
                        for key, value in commissioning_raw.items()
                    )
                )
                if isinstance(commissioning_raw, Mapping)
                else ()
            )
            summaries.append(
                ProviderRuntimeSummary(
                    provider_id=item["provider_id"],
                    namespace=str(item.get("namespace", "unknown")),
                    registered=item.get("registered") is True,
                    enabled=item.get("enabled") is True,
                    mounted=item.get("mounted") is True,
                    state=str(item.get("state", "unknown")),
                    readiness=readiness,
                    action=action[:500],
                    commissioning=commissioning,
                )
            )
        return tuple(summaries)

    def _quarantine_evidence(
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
                Diagnostic(
                    code="CONTROL_CENTER_QUARANTINE_UNAVAILABLE",
                    message="Configured quarantine root is not a directory.",
                )
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
        records: list[QuarantineRecordSummary] = []
        for operation_root in selected:
            metadata = self._read_json(
                operation_root / "metadata.json",
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
            records.append(
                QuarantineRecordSummary(
                    operation_id=str(metadata.get("operation_id", operation_root.name)),
                    original_path=str(metadata.get("original_path", "unknown")),
                    item_type=str(metadata.get("item_type", "unknown")),
                    restored=type(restored_at) is str,
                )
            )
        return (
            QuarantineSummary(
                root=str(root),
                status="available",
                total_records=len(entries),
                active_records=active,
                restored_records=restored,
                invalid_records=invalid,
                truncated=len(entries) > len(selected),
            ),
            tuple(records),
        )

    def _bounded_observability(self) -> RuntimeObservabilitySnapshot:
        snapshot = self.observability.snapshot()
        return RuntimeObservabilitySnapshot(
            recent_calls=snapshot.recent_calls[: self.settings.max_recent_calls],
            recent_policy_decisions=snapshot.recent_policy_decisions[
                : self.settings.max_policy_decisions
            ],
            active_processes=snapshot.active_processes[
                : self.settings.max_active_processes
            ],
            active_searches=snapshot.active_searches[: self.settings.max_active_searches],
        )

    @staticmethod
    def _available_actions() -> tuple[AvailableAction, ...]:
        return (
            AvailableAction("Refresh project evidence", "inspect_project", "read"),
            AvailableAction("Check provider status", "kis_provider_status", "read"),
            AvailableAction("List quarantine", "kis_list_quarantine", "read"),
            AvailableAction("Restore quarantine record", "kis_restore_quarantine", "mutation"),
            AvailableAction("Run repository verification", "scripts/verify.ps1", "command"),
        )

    def _default_provider_status_source(self) -> Mapping[str, Any]:
        composition = latest_provider_runtime_composition()
        return {
            "external_providers": [
                {
                    **item.to_json_dict(),
                    "readiness": None,
                    "user_status": None,
                    "commissioning": {},
                }
                for item in composition.results
            ]
        }

    def _default_discover_source(self) -> Mapping[str, Any]:
        from kis_mcp.config import load_runtime_config
        from kis_mcp.discover.contracts import InspectProjectRequest
        from kis_mcp.discover.service import InspectProjectService

        runtime = load_runtime_config()
        service = InspectProjectService(
            boundary=Path(runtime.project_boundary),
            settings=runtime.discover_settings,
        )
        response = service.inspect(InspectProjectRequest(path=str(self.settings.project_path)))
        document = response.to_json_dict()
        code_atlas = document.get("code_atlas", {})
        languages = _named_values(code_atlas, "languages")
        frameworks = _named_values(code_atlas, "frameworks")
        modules = _sequence(
            code_atlas.get("modules", ()) if isinstance(code_atlas, Mapping) else ()
        )
        return {
            "status": "available",
            "project_id": document.get("project", {}).get("project_id"),
            "languages": languages,
            "frameworks": frameworks,
            "module_count": len(modules),
            "finding_count": len(document.get("findings", ())),
            "confidence": document.get("confidence", "unknown"),
            "truncated": document.get("truncated") is True,
            "findings": document.get("findings", ()),
            "detail": "Bounded local inspect_project evidence.",
        }

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
                Diagnostic(
                    code=unavailable_code,
                    message=f"{path}: {type(exc).__name__}",
                )
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
            diagnostics.append(
                Diagnostic(code=invalid_code, message=f"{path}: {type(exc).__name__}")
            )
            return None
        if not isinstance(raw, dict):
            diagnostics.append(
                Diagnostic(code=invalid_code, message=f"{path}: root must be an object")
            )
            return None
        return raw


def _nested_string(raw: Mapping[str, Any], section: str, field: str) -> str | None:
    value = raw.get(section)
    if not isinstance(value, Mapping):
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


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


def _optional_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def _non_negative_int(value: Any) -> int:
    return value if type(value) is int and value >= 0 else 0


def _finding_text(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("title", "observation", "code", "id"):
            if value.get(key):
                return str(value[key])[:500]
    return str(value)[:500]


def _named_values(document: Any, key: str) -> tuple[str, ...]:
    if not isinstance(document, Mapping):
        return ()
    value = document.get(key)
    values: list[str] = []
    if isinstance(value, Mapping):
        values.extend(str(item) for item in value)
    else:
        for item in _sequence(value):
            if isinstance(item, Mapping):
                name = item.get("name") or item.get("id")
                if name:
                    values.append(str(name))
            else:
                values.append(str(item))
    return tuple(values)
