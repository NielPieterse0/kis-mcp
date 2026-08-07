from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .backend import ProjectBinding, ProjectInventory
from .contracts import ManagedProject, WorkRecord
from .evidence import EvidenceWriteResult, ReviewEvidenceStore
from .reconciliation import (
    DesiredProjection,
    ObservedProjection,
    ReconciliationBackend,
    ReconciliationOutcome,
    plan_reconciliation,
    run_reconciliation,
)
from .reviews import ReviewArtifactKind, ReviewEvidenceManifest
from .settings import (
    BackendBindingSettings,
    EvidenceSettings,
    FeatureMode,
    WorkManagementSettings,
)
from .status import PortfolioStatus, build_portfolio_status


@runtime_checkable
class WorkManagementBackend(ReconciliationBackend, Protocol):
    async def read_inventory(
        self,
        project_binding: ProjectBinding,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
    ) -> ProjectInventory: ...


class WorkManagementUnavailable(RuntimeError):
    def __init__(
        self,
        project_id: str,
        provider: str,
        reason: str,
        *,
        error_code: str = "provider_unavailable",
    ) -> None:
        self.project_id = project_id
        self.provider = provider
        self.reason = reason
        self.error_code = error_code
        super().__init__(f"{provider} is unavailable for {project_id}: {reason}")

    def to_json_dict(self) -> dict[str, str]:
        return {
            "error_code": self.error_code,
            "project_id": self.project_id,
            "provider": self.provider,
            "reason": self.reason,
        }


EvidenceStoreFactory = Callable[[ManagedProject, EvidenceSettings], ReviewEvidenceStore]


def _default_evidence_store(
    project: ManagedProject,
    limits: EvidenceSettings,
) -> ReviewEvidenceStore:
    return ReviewEvidenceStore(
        Path(project.local_root),
        max_file_bytes=limits.max_file_bytes,
        max_total_bytes=limits.max_total_bytes,
    )


class WorkManagementService:
    def __init__(
        self,
        settings: WorkManagementSettings,
        backends: Mapping[str, WorkManagementBackend],
        *,
        evidence_store_factory: EvidenceStoreFactory = _default_evidence_store,
    ) -> None:
        if not isinstance(settings, WorkManagementSettings):
            raise ValueError("settings must be WorkManagementSettings")
        self.settings = settings
        self.backends = dict(backends)
        self.evidence_store_factory = evidence_store_factory
        self._evidence_stores: dict[str, ReviewEvidenceStore] = {}

    def _project_and_binding(
        self,
        project_id: str,
    ) -> tuple[ManagedProject, BackendBindingSettings]:
        try:
            project = self.settings.project(project_id)
        except KeyError as exc:
            raise ValueError(f"project is not configured: {project_id}") from exc
        binding = self.settings.binding(project.backend_binding)
        return project, binding

    def _backend(
        self,
        project: ManagedProject,
        binding: BackendBindingSettings,
    ) -> WorkManagementBackend:
        backend = self.backends.get(binding.provider)
        if backend is None:
            raise WorkManagementUnavailable(
                project.project_id,
                binding.provider,
                "configured provider backend is not registered",
            )
        return backend

    def _project_binding(
        self,
        project: ManagedProject,
        binding: BackendBindingSettings,
    ) -> ProjectBinding:
        if binding.project_number is None:
            raise WorkManagementUnavailable(
                project.project_id,
                binding.provider,
                "backend Project has not been commissioned",
                error_code="project_not_commissioned",
            )
        return ProjectBinding(
            binding_id=binding.binding_id,
            managed_project_id=project.project_id,
            provider_id=binding.provider,
            owner=binding.owner,
            owner_type=binding.owner_type,
            project_number=binding.project_number,
            repository=project.repository,
        )

    def _require_feature(self, feature: str, *, project_id: str, mutation: bool) -> None:
        mode = self.settings.feature_mode(feature)
        if mode is FeatureMode.DISABLED:
            raise ValueError(f"{feature} feature is disabled for {project_id}")
        if mutation and mode is FeatureMode.READ_ONLY:
            raise ValueError(f"{feature} feature is read-only for {project_id}")

    async def read_inventory(
        self,
        project_id: str,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
    ) -> ProjectInventory:
        project, binding = self._project_and_binding(project_id)
        backend = self._backend(project, binding)
        return await backend.read_inventory(
            self._project_binding(project, binding),
            field_names=field_names,
            item_limit=item_limit,
        )

    async def reconcile(
        self,
        project_id: str,
        desired: tuple[DesiredProjection, ...],
        observed: tuple[ObservedProjection, ...],
        *,
        supported_fields: tuple[str, ...],
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> tuple[ReconciliationOutcome, ...]:
        project, binding = self._project_and_binding(project_id)
        self._require_feature(
            "reconciliation",
            project_id=project.project_id,
            mutation=apply,
        )
        backend = self._backend(project, binding)
        for item in (*desired, *observed):
            if item.project_id != project.project_id:
                raise ValueError("reconciliation projections must match selected project")
        decisions = plan_reconciliation(
            desired,
            observed,
            supported_fields=supported_fields,
        )
        return await run_reconciliation(
            decisions,
            backend,
            apply=apply,
            idempotency_key=idempotency_key,
        )

    def _evidence_store(self, project_id: str) -> ReviewEvidenceStore:
        project, _binding = self._project_and_binding(project_id)
        if project.project_id not in self._evidence_stores:
            self._evidence_stores[project.project_id] = self.evidence_store_factory(
                project,
                self.settings.evidence,
            )
        return self._evidence_stores[project.project_id]

    def persist_review_artifact(
        self,
        project_id: str,
        manifest: ReviewEvidenceManifest,
        kind: ReviewArtifactKind,
        content: str | bytes,
        *,
        expected_sha256: str | None = None,
    ) -> EvidenceWriteResult:
        project, _binding = self._project_and_binding(project_id)
        self._require_feature(
            "review_import",
            project_id=project.project_id,
            mutation=True,
        )
        return self._evidence_store(project_id).write_artifact(
            manifest,
            kind,
            content,
            expected_sha256=expected_sha256,
        )

    def portfolio_status(
        self,
        records: tuple[WorkRecord, ...],
        *,
        traceability_gaps: Mapping[str, tuple[str, ...]] | None = None,
        provider_failures: Mapping[str, str] | None = None,
        truncated_projects: tuple[str, ...] = (),
    ) -> PortfolioStatus:
        return build_portfolio_status(
            self.settings,
            records,
            traceability_gaps=traceability_gaps,
            provider_failures=provider_failures,
            truncated_projects=truncated_projects,
        )


__all__ = [
    "EvidenceStoreFactory",
    "WorkManagementBackend",
    "WorkManagementService",
    "WorkManagementUnavailable",
]
