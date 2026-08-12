from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    ProjectSummary,
    ProviderRuntimeSummary,
    VerificationSummary,
)
from .readers import (
    GitStatusReader,
    PolicyStatusReader,
    ProviderStatusReader,
    QuarantineStatusReader,
    RuntimeStatusReader,
)
from .settings import ControlCenterSettings

_APPROVAL_HEADING_PATTERN = re.compile(
    r"^##\s+([A-Za-z0-9-]+)\s+(?:\u2014|-)\s+(.+?)\s*$",
    re.MULTILINE,
)

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
        runtime_reader: RuntimeStatusReader | None = None,
        policy_reader: PolicyStatusReader | None = None,
        provider_reader: ProviderStatusReader | None = None,
        quarantine_reader: QuarantineStatusReader | None = None,
        git_reader: GitStatusReader | None = None,
    ) -> None:
        self.settings = settings
        self.observability = observability or get_runtime_observability()
        self.discover_source = discover_source or self._default_discover_source
        self.provider_status_source = (
            provider_status_source or self._default_provider_status_source
        )
        self.runtime_reader = runtime_reader or RuntimeStatusReader(settings)
        self.policy_reader = policy_reader or PolicyStatusReader(settings)
        self.provider_reader = provider_reader or ProviderStatusReader(settings)
        self.quarantine_reader = quarantine_reader or QuarantineStatusReader(settings)
        self.git_reader = git_reader or GitStatusReader(settings)

    def collect(self) -> ControlCenterSnapshot:
        diagnostics: list[Diagnostic] = []
        runtime = self.runtime_reader.read(diagnostics)
        project = ProjectSummary(
            path=str(self.settings.project_path),
            exists=self.settings.project_path.exists(),
            git=self.git_reader.read(),
        )
        policy = self.policy_reader.read(diagnostics)
        providers = self.provider_reader.read(diagnostics)
        approvals = self._approval_summaries(diagnostics)
        discover = self._discover_summary(diagnostics)
        provider_runtime = self._provider_runtime_summaries(diagnostics)
        quarantine, quarantine_records = self.quarantine_reader.read(diagnostics)
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

    def _approval_summaries(
        self, diagnostics: list[Diagnostic]
    ) -> tuple[ApprovalSummary, ...]:
        try:
            with self.settings.approval_register_path.open("rb") as handle:
                payload = handle.read(self.settings.max_json_bytes + 1)
        except OSError as exc:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_APPROVAL_REGISTER_UNAVAILABLE",
                    message=f"Approval register is unavailable: {type(exc).__name__}.",
                )
            )
            return ()
        if len(payload) > self.settings.max_json_bytes:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_APPROVAL_REGISTER_LIMIT_EXCEEDED",
                    message=(
                        "Approval register exceeds the configured "
                        f"{self.settings.max_json_bytes}-byte limit."
                    ),
                )
            )
            return ()
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            diagnostics.append(
                Diagnostic(
                    code="CONTROL_CENTER_APPROVAL_REGISTER_INVALID",
                    message="Approval register is not valid UTF-8.",
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
            normalized_decision = decision_line.casefold()
            if "[ ] approve" not in normalized_decision or "[x]" in normalized_decision:
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

    def _bounded_observability(self) -> RuntimeObservabilitySnapshot:
        snapshot = self.observability.snapshot()
        return RuntimeObservabilitySnapshot(
            recent_calls=snapshot.recent_calls[: self.settings.max_recent_calls],
            recent_policy_decisions=snapshot.recent_policy_decisions[
                : self.settings.max_policy_decisions
            ],
            recent_boundary_requests=snapshot.recent_boundary_requests[
                : self.settings.max_recent_calls
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

    @staticmethod
    def _default_provider_status_source() -> Mapping[str, Any]:
        return {"external_providers": []}

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
