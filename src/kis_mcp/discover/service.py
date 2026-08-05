from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from .budgeting import ResultBudgeter
from .context_broker import ContextBrokerService
from .context_contracts import GetCodeContextRequest, GetCodeContextResponse
from .contracts import (
    Confidence,
    EvidenceItem,
    EvidenceSource,
    Finding,
    Freshness,
    Handoff,
    InspectProjectRequest,
    InspectProjectResponse,
    ProjectIdentity,
    Provenance,
    ProvenanceKind,
    Recommendation,
    Severity,
    TrustState,
    Unknown,
)
from .detectors import RepositoryDetector
from .errors import DiscoverError
from .git_reader import GitReader
from .python_index import PythonProjectIndexer
from .read_authority import ReadAuthority
from .scanner import RepositoryScanner
from .settings import DiscoverSettings
from .verification import VerificationDiscoveryService


class InspectProjectService:
    def __init__(self, *, boundary: Path, settings: DiscoverSettings) -> None:
        self._boundary = boundary
        self._settings = settings

    def get_code_context(
        self,
        request: GetCodeContextRequest,
    ) -> GetCodeContextResponse:
        """Delegate bounded task context assembly through the Discover facade."""

        return ContextBrokerService(
            boundary=self._boundary,
            settings=self._settings,
        ).get(request)

    def inspect(self, request: InspectProjectRequest) -> InspectProjectResponse:
        if not self._settings.enabled:
            raise DiscoverError(
                code="DISCOVER_DISABLED",
                message="Discover is disabled by runtime settings.",
                reason="settings.discover.enabled is false.",
                field="settings.discover.enabled",
            )
        try:
            limits = self._settings.limits.narrow(request.limits)
        except ValueError as exc:
            field = "limits"
            if request.limits:
                field = f"limits.{sorted(request.limits)[0]}"
            raise DiscoverError(
                code="DISCOVER_LIMIT_INVALID",
                message="The requested Discover limits are invalid.",
                reason=str(exc),
                field=field,
                accepted="Positive supported values that do not exceed configured maxima.",
                corrective_actions=(
                    "Remove unsupported limit fields or lower the requested values.",
                ),
            ) from exc
        settings = replace(self._settings, limits=limits)
        authority = ReadAuthority(self._boundary, settings)
        scanner = RepositoryScanner(authority, settings)
        snapshot = scanner.snapshot(request.path)
        detection = RepositoryDetector(authority, settings).detect(request.path, snapshot)
        python_index = PythonProjectIndexer(
            authority=authority,
            settings=settings,
        ).index(request.path, snapshot)
        verification = VerificationDiscoveryService(
            authority=authority,
            settings=settings,
        ).discover(request.path, snapshot)
        git = GitReader(authority=authority, settings=settings).inspect(request.path)

        project = replace(
            snapshot.project,
            git_root=snapshot.project.canonical_path if git.repository else None,
            remote_identity=git.remote,
        )
        evidence = list(detection.evidence)
        normalized_declarations = []
        handoffs: list[Handoff] = []
        for declaration in verification.declarations:
            evidence_id = _stable_id("ev-verification", declaration.id)
            evidence.append(
                EvidenceItem(
                    id=evidence_id,
                    kind="verification",
                    subject=project.project_id,
                    source=EvidenceSource(
                        kind="file",
                        provider="local_filesystem",
                        identifier=declaration.source_path,
                    ),
                    provenance=Provenance(
                        kind=declaration.provenance,
                        source_id=declaration.source_path,
                    ),
                    location={"path": declaration.source_path},
                    trust=TrustState.TRUSTED,
                    confidence=declaration.confidence,
                    freshness=Freshness.CURRENT,
                    summary=f"Discovered verification declaration {declaration.id}.",
                    details={
                        "category": declaration.category,
                        "profile": declaration.profile,
                        "arguments": list(declaration.arguments),
                        "authority": declaration.authority,
                        "execution_available": declaration.execution_available,
                    },
                )
            )
            normalized = replace(declaration, evidence_ids=(evidence_id,))
            normalized_declarations.append(normalized)
            handoffs.append(
                Handoff(
                    handoff_id=_stable_id("handoff-verification", declaration.id),
                    target_plane="work",
                    workflow="run_verification",
                    reason="A repository verification declaration was discovered but not executed.",
                    inputs={"verification_id": declaration.id},
                    evidence_ids=(evidence_id,),
                    required_authority=("verification.execution",),
                    expected_result_contract="verification-result-v1",
                )
            )

        if git.available:
            evidence.append(
                EvidenceItem(
                    id="ev-git-summary",
                    kind="git",
                    subject=project.project_id,
                    source=EvidenceSource(
                        kind="repository",
                        provider="local_git",
                        identifier="local_repository",
                        revision=git.head,
                    ),
                    provenance=Provenance(
                        kind=ProvenanceKind.OBSERVED,
                        source_id="local_git",
                    ),
                    location={"path": "."},
                    trust=TrustState.TRUSTED,
                    confidence=Confidence.HIGH,
                    freshness=Freshness.CURRENT,
                    summary="Read bounded local Git repository state.",
                    details=git.to_json_dict(),
                    truncated=git.truncated,
                )
            )

        evidence.sort(key=lambda item: item.id)
        path_to_evidence: dict[str, str] = {}
        for item in evidence:
            path = item.location.get("path")
            if isinstance(path, str):
                path_to_evidence.setdefault(path, item.id)

        diagnostics = [
            *detection.diagnostics,
            *python_index.diagnostics,
            *verification.diagnostics,
        ]
        diagnostics.sort(key=lambda item: (item.code, (item.path or "").casefold()))
        findings: list[Finding] = []
        recommendations: list[Recommendation] = []
        for index, diagnostic in enumerate(diagnostics):
            evidence_ids = (
                (path_to_evidence[diagnostic.path],)
                if diagnostic.path in path_to_evidence
                else ()
            )
            finding_id = _stable_id(
                "finding",
                f"{diagnostic.code}:{diagnostic.path or '.'}:{index}",
            )
            findings.append(
                Finding(
                    id=finding_id,
                    code=diagnostic.code,
                    title=diagnostic.code.replace("_", " ").title(),
                    severity=diagnostic.severity,
                    scope=diagnostic.path or ".",
                    observation=diagnostic.message,
                    impact="Repository evidence is incomplete or requires review.",
                    evidence_ids=evidence_ids,
                    confidence=Confidence.HIGH,
                    remediation="Review the cited local evidence and resolve or accept the condition.",
                    owning_plane="discover",
                )
            )
            recommendations.append(
                Recommendation(
                    id=_stable_id("recommendation", finding_id),
                    category="evidence_quality",
                    action="Review and resolve the corresponding Discover finding.",
                    rationale=diagnostic.message,
                    evidence_ids=evidence_ids,
                    expected_benefit="Improved repository understanding and verification confidence.",
                    cost_class="small",
                    risks=("The condition may be intentional.",),
                    owning_plane="work",
                )
            )

        unknowns: list[Unknown] = [
            Unknown(
                id="unknown-remote",
                code="REMOTE_EVIDENCE_UNAVAILABLE",
                reason="No approved remote repository provider is configured for this slice.",
            ),
            Unknown(
                id="unknown-semantic",
                code="SEMANTIC_PROVIDER_UNAVAILABLE",
                reason="No semantic provider is configured for this slice.",
            ),
        ]
        for index, reason in enumerate(detection.unknowns):
            unknowns.append(
                Unknown(
                    id=_stable_id("unknown-detection", f"{index}:{reason}"),
                    code="DETECTION_EVIDENCE_UNKNOWN",
                    reason=reason,
                )
            )
        if not git.available:
            unknowns.append(
                Unknown(
                    id="unknown-git",
                    code="GIT_EVIDENCE_UNAVAILABLE",
                    reason=git.diagnostics[0]["message"] if git.diagnostics else "Git evidence is unavailable.",
                )
            )
        unknowns.sort(key=lambda item: item.id)

        truncation_reasons = set(snapshot.truncation_reasons)
        truncation_reasons.update(python_index.truncation_reasons)
        if verification.truncated:
            truncation_reasons.add("verification_discovery")
        if git.truncated:
            truncation_reasons.add("git_output")
        truncated = bool(truncation_reasons)
        confidence = (
            Confidence.MEDIUM
            if truncated or diagnostics
            else Confidence.HIGH
        )

        topology = {
            "files": [item.label for item in snapshot.files],
            "directories": list(snapshot.directories),
            "excluded_paths": list(snapshot.excluded_paths),
            "file_count": len(snapshot.files),
            "directory_count": len(snapshot.directories),
            "total_bytes": snapshot.total_bytes,
            "visited_entries": snapshot.visited_entries,
        }
        repository_atlas: dict[str, Any] = {
            "project_name": detection.project_name,
            "topology": topology,
            "languages": [item.to_json_dict() for item in detection.languages],
            "manifests": [item.to_json_dict() for item in detection.manifests],
            "frameworks": list(detection.frameworks),
            "build_systems": list(detection.build_systems),
            "package_managers": list(detection.package_managers),
            "workspaces": [item.to_json_dict() for item in detection.workspaces],
            "entry_points": [item.to_json_dict() for item in detection.entry_points],
            "documentation": list(detection.documentation),
            "ci": list(detection.ci),
            "modules": list(detection.modules),
            "diagnostics": [item.to_json_dict() for item in detection.diagnostics],
            "unknowns": list(detection.unknowns),
        }
        verification_payload = verification.to_json_dict()
        verification_payload["declarations"] = [
            item.to_json_dict() for item in normalized_declarations
        ]
        instructions = tuple(
            {
                "path": path,
                "evidence_ids": (
                    [path_to_evidence[path]] if path in path_to_evidence else []
                ),
            }
            for path in detection.instructions
        )
        response = InspectProjectResponse(
            project=project,
            repository_atlas=repository_atlas,
            code_atlas=python_index.to_json_dict(),
            verification=verification_payload,
            contracts={
                "artifacts": [item.to_json_dict() for item in detection.contract_artifacts]
            },
            instructions=instructions,
            git=git,
            remote={"status": "not_configured", "local_only": True},
            providers={
                "filesystem": {
                    "available": True,
                    "provider": "local_filesystem",
                },
                "git": {"available": git.available, "provider": "local_git"},
                "remote": {"available": False, "reason": "not_configured"},
                "semantic": {"available": False, "reason": "not_configured"},
            },
            evidence=tuple(evidence),
            findings=tuple(findings),
            recommendations=tuple(recommendations),
            handoffs=tuple(handoffs),
            assumptions=(
                {
                    "code": "LOCAL_ONLY",
                    "statement": "The result uses only bounded local repository evidence.",
                },
            ),
            unknowns=tuple(unknowns),
            confidence=confidence,
            truncated=truncated,
            truncation_reasons=tuple(sorted(truncation_reasons)),
        )
        return ResultBudgeter(
            max_evidence=settings.limits.max_evidence,
            max_output_chars=settings.limits.max_output_chars,
        ).apply(response)


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


__all__ = ["InspectProjectService"]
