from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .backend import (
    ProjectBinding,
    ProjectField,
    ProjectFieldKind,
    ProjectInventory,
    ProjectItem,
)
from .command_settings import CommandPlaneSettings, load_command_plane_settings
from .contracts import LifecycleState, ManagedProject, WorkRecord
from .evidence import EvidenceWriteResult, ReviewEvidenceStore
from .lifecycle import evaluate_transition
from .project_commands import (
    ProjectWorkSelection,
    build_item_projections,
    find_issue_item,
    select_next_project_item,
)
from .reconciliation import (
    DesiredProjection,
    ObservedProjection,
    ReconciliationBackend,
    ReconciliationOutcome,
    plan_reconciliation,
    run_reconciliation,
)
from .reviews import ReviewArtifactKind, ReviewEvidenceManifest
from .schema import (
    ProjectSchemaPlan,
    ProjectSchemaStatus,
    compare_project_schema,
    load_project_schema_manifest,
    plan_project_schema_repair,
)
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

_EXACT_TARGET_ITEM_LIMIT = 1000


def _active_worktree_scope_path(project_root: Path, change_id: str) -> Path:
    worktrees_root = project_root / ".work" / "worktrees"
    if not worktrees_root.is_dir():
        raise ValueError(f"authoritative change scope does not exist: {change_id}")

    candidates: list[Path] = []
    rejected: list[str] = []
    for worktree in sorted(worktrees_root.iterdir(), key=lambda path: path.name.casefold()):
        scope_path = worktree / ".work" / "changes" / change_id / "scope.json"
        if not scope_path.is_file():
            continue
        try:
            document = json.loads(scope_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            rejected.append(f"{worktree.name}: unreadable scope ({type(exc).__name__})")
            continue
        expected_worktree = f".work/worktrees/{worktree.name}"
        if not isinstance(document, dict) or document.get("change_id") != change_id:
            rejected.append(f"{worktree.name}: change identity mismatch")
            continue
        if document.get("status") != "active":
            rejected.append(f"{worktree.name}: scope is not active")
            continue
        if str(document.get("worktree", "")).replace("\\", "/") != expected_worktree:
            rejected.append(f"{worktree.name}: worktree identity mismatch")
            continue
        if not (worktree / ".git").exists():
            rejected.append(f"{worktree.name}: governed worktree marker is missing")
            continue
        candidates.append(scope_path)

    if len(candidates) > 1:
        names = ", ".join(path.parents[3].name for path in candidates)
        raise ValueError(f"authoritative active change scope is ambiguous: {change_id} ({names})")
    if len(candidates) == 1:
        return candidates[0]
    if rejected:
        raise ValueError(
            f"authoritative active change scope is invalid: {change_id} ({'; '.join(rejected)})"
        )
    raise ValueError(f"authoritative change scope does not exist: {change_id}")


def _change_scope_path(project_root: Path, change_id: str) -> Path:
    primary = project_root / ".work" / "changes" / change_id / "scope.json"
    return primary if primary.is_file() else _active_worktree_scope_path(project_root, change_id)


def _normalized_project_choice(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().casefold().replace(" ", "_").replace("-", "_")


def _field_value(item: ProjectItem, field_name: str) -> object | None:
    target = field_name.casefold()
    for field_value in item.field_values:
        if field_value.field_name.casefold() == target:
            return field_value.value
    return None


def _field_spec(inventory: ProjectInventory, field_name: str) -> ProjectField:
    target = field_name.casefold()
    matches = tuple(
        field for field in inventory.fields if field.name.casefold() == target
    )
    if len(matches) != 1:
        raise ValueError(f"Project field is not uniquely available: {field_name}")
    return matches[0]


def _live_single_select_option(
    inventory: ProjectInventory,
    field_name: str,
    canonical_value: str,
) -> str:
    field = _field_spec(inventory, field_name)
    if field.kind is not ProjectFieldKind.SINGLE_SELECT:
        raise ValueError(f"Project field must be single_select: {field_name}")
    expected = _normalized_project_choice(canonical_value)
    matches = tuple(
        option.name
        for option in field.options
        if _normalized_project_choice(option.name) == expected
    )
    if len(matches) != 1:
        raise ValueError(
            f"Project option is not uniquely available: {field_name}:{canonical_value}"
        )
    return matches[0]


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

    def _require_feature(
        self, feature: str, *, project_id: str, mutation: bool
    ) -> None:
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
        item_limit: int = 1000,
    ) -> ProjectInventory:
        project, binding = self._project_and_binding(project_id)
        backend = self._backend(project, binding)
        return await backend.read_inventory(
            self._project_binding(project, binding),
            field_names=field_names,
            item_limit=item_limit,
        )

    @staticmethod
    def _command_settings() -> CommandPlaneSettings:
        return load_command_plane_settings()

    @staticmethod
    def _command_field_names(settings: CommandPlaneSettings) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    settings.queue.state_field,
                    settings.queue.priority_field,
                    settings.queue.effort_field,
                    settings.queue.created_field,
                    settings.queue.blocked_by_field,
                    settings.claim.execution_owner_field,
                    *settings.readiness.required_project_fields,
                    *(
                        field
                        for _state, fields in settings.transition_requirements
                        for field in fields
                    ),
                )
            )
        )

    async def next_work(
        self,
        project_id: str,
        *,
        item_limit: int = 1000,
    ) -> ProjectWorkSelection:
        settings = self._command_settings()
        inventory = await self.read_inventory(
            project_id,
            field_names=self._command_field_names(settings),
            item_limit=item_limit,
        )
        return select_next_project_item(inventory, settings=settings)

    async def take_next_work(
        self,
        project_id: str,
        execution_owner: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
        item_limit: int = 1000,
    ) -> dict[str, Any]:
        selection = await self.next_work(project_id, item_limit=item_limit)
        if selection.selected is None:
            return {
                "mode": "apply" if apply else "preview",
                "selection": selection.to_json_dict(),
                "claim": None,
            }
        selected = selection.selected
        if selected.repository is None or selected.number is None:
            raise ValueError("selected Project issue is missing source identity")
        claim = await self.claim_work(
            project_id,
            selected.repository,
            selected.number,
            execution_owner,
            apply=apply,
            idempotency_key=idempotency_key,
        )
        return {
            "mode": "apply" if apply else "preview",
            "selection": selection.to_json_dict(),
            "claim": claim,
        }

    async def _issue_command_inventory(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        *,
        extra_fields: tuple[str, ...] = (),
        item_limit: int = _EXACT_TARGET_ITEM_LIMIT,
    ) -> tuple[ProjectInventory, ProjectItem, CommandPlaneSettings]:
        settings = self._command_settings()
        fields = tuple(
            dict.fromkeys((*self._command_field_names(settings), *extra_fields))
        )
        inventory = await self.read_inventory(
            project_id,
            field_names=fields,
            item_limit=item_limit,
        )
        item = find_issue_item(inventory, repository, issue_number)
        if inventory.truncated:
            raise ValueError(
                "exact-target truncated Project inventory remains incomplete after bounded resolution scan"
            )
        return inventory, item, settings

    async def _reconcile_issue_fields(
        self,
        project_id: str,
        inventory: ProjectInventory,
        item: ProjectItem,
        fields: Mapping[str, Any],
        *,
        apply: bool,
        idempotency_key: str | None,
    ) -> tuple[ReconciliationOutcome, ...]:
        desired, observed = build_item_projections(project_id, item, dict(fields))
        supported_fields = tuple(field.name for field in inventory.fields)
        return await self.reconcile(
            project_id,
            (desired,),
            (observed,),
            supported_fields=supported_fields,
            apply=apply,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def _issue_transition_state(
        item: ProjectItem,
        settings: CommandPlaneSettings,
    ) -> LifecycleState:
        value = _normalized_project_choice(
            _field_value(item, settings.queue.state_field)
        )
        if value is None:
            raise ValueError("Project item has no Work State")
        intake_state = settings.intake_state(value)
        if intake_state is not None:
            return intake_state
        try:
            state = LifecycleState(value)
        except ValueError as exc:
            raise ValueError(
                f"Project item has unsupported Work State: {value}"
            ) from exc
        if state not in settings.work_states:
            raise ValueError(
                f"Project item state is not a command-plane Work State: {value}"
            )
        return state

    @staticmethod
    def _require_ready_metadata(
        item: ProjectItem,
        settings: CommandPlaneSettings,
        overrides: Mapping[str, Any] | None = None,
    ) -> None:
        proposed = {key.casefold(): value for key, value in (overrides or {}).items()}
        missing: list[str] = []
        for field_name in settings.readiness.required_project_fields:
            value = proposed.get(field_name.casefold(), _field_value(item, field_name))
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field_name)
        if missing:
            raise ValueError(f"Ready requires Project fields: {', '.join(missing)}")
        blocker = _field_value(item, settings.queue.blocked_by_field)
        if blocker not in (None, "", False, 0):
            raise ValueError("Ready is blocked by an observed native dependency")

    async def claim_work(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        execution_owner: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        owner = execution_owner.strip() if isinstance(execution_owner, str) else ""
        if not owner:
            raise ValueError("execution_owner must be a non-empty string")
        inventory, item, settings = await self._issue_command_inventory(
            project_id, repository, issue_number
        )
        self._require_ready_metadata(item, settings)
        if self._issue_transition_state(item, settings) is not LifecycleState.READY:
            raise ValueError("only Ready work can be claimed")
        existing = _field_value(item, settings.claim.execution_owner_field)
        if isinstance(existing, str) and existing.strip():
            raise ValueError(f"work is already claimed by {existing.strip()}")
        active_option = _live_single_select_option(
            inventory, settings.queue.state_field, LifecycleState.ACTIVE.value
        )
        desired_fields = {
            settings.claim.execution_owner_field: owner,
            settings.queue.state_field: active_option,
        }
        if not apply:
            preview = await self._reconcile_issue_fields(
                project_id,
                inventory,
                item,
                desired_fields,
                apply=False,
                idempotency_key=None,
            )
            return {
                "mode": "preview",
                "outcomes": [value.to_json_dict() for value in preview],
            }
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key is required when apply is true")

        lock = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            {settings.claim.execution_owner_field: owner},
            apply=True,
            idempotency_key=f"{idempotency_key}:claim",
        )
        if not all(value.success for value in lock):
            return {
                "mode": "apply",
                "phase": "claim",
                "outcomes": [value.to_json_dict() for value in lock],
            }
        inventory, item, settings = await self._issue_command_inventory(
            project_id, repository, issue_number
        )
        if _field_value(item, settings.claim.execution_owner_field) != owner:
            raise ValueError("claim could not be verified after apply")
        activation = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            {
                settings.queue.state_field: _live_single_select_option(
                    inventory, settings.queue.state_field, LifecycleState.ACTIVE.value
                ),
            },
            apply=True,
            idempotency_key=f"{idempotency_key}:activate",
        )
        return {
            "mode": "apply",
            "phase": "active",
            "outcomes": [value.to_json_dict() for value in (*lock, *activation)],
        }

    async def release_work(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        expected_owner: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        owner = expected_owner.strip() if isinstance(expected_owner, str) else ""
        if not owner:
            raise ValueError("expected_owner must be a non-empty string")
        inventory, item, settings = await self._issue_command_inventory(
            project_id, repository, issue_number
        )
        if _field_value(item, settings.claim.execution_owner_field) != owner:
            raise ValueError("expected_owner does not own the current claim")
        current = self._issue_transition_state(item, settings)
        if LifecycleState.READY not in settings.transition_targets(current):
            raise ValueError(f"Work State {current.value} cannot be released to Ready")
        fields = {
            settings.claim.execution_owner_field: None,
            settings.queue.state_field: _live_single_select_option(
                inventory, settings.queue.state_field, LifecycleState.READY.value
            ),
        }
        outcomes = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            fields,
            apply=apply,
            idempotency_key=idempotency_key,
        )
        return {
            "mode": "apply" if apply else "preview",
            "outcomes": [value.to_json_dict() for value in outcomes],
        }

    async def transition_work(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        target: LifecycleState,
        *,
        metadata: Mapping[str, Any] | None = None,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(target, LifecycleState):
            raise ValueError("target must be a LifecycleState")
        inventory, item, settings = await self._issue_command_inventory(
            project_id,
            repository,
            issue_number,
            extra_fields=tuple((metadata or {}).keys()),
        )
        if target not in settings.work_states:
            raise ValueError("target must be a command-plane Work State")
        if target is settings.completion.terminal_state:
            raise ValueError("use complete_work for the terminal Work State")
        current = self._issue_transition_state(item, settings)
        if target not in settings.transition_targets(current):
            raise ValueError(
                f"transition is not declared: {current.value}->{target.value}"
            )
        values = dict(metadata or {})
        claim_field = settings.claim.execution_owner_field.casefold()
        for field_name in values:
            if field_name.casefold() == claim_field:
                raise ValueError(
                    "transition metadata cannot modify execution claims; use claim_work or release_work"
                )
            try:
                authority = settings.authority(field_name)
            except KeyError as exc:
                raise ValueError(
                    f"transition metadata field is not declared: {field_name}"
                ) from exc
            if authority.direction == "evidence":
                raise ValueError(
                    f"transition metadata cannot overwrite evidence-owned field: {field_name}"
                )
        for field_name in settings.required_fields_for_transition(target):
            candidate = values.get(field_name, _field_value(item, field_name))
            if candidate is None or (
                isinstance(candidate, str) and not candidate.strip()
            ):
                raise ValueError(f"transition to {target.value} requires {field_name}")
        if target is LifecycleState.READY:
            existing_owner = _field_value(item, settings.claim.execution_owner_field)
            if isinstance(existing_owner, str) and existing_owner.strip():
                raise ValueError(
                    "claimed work must use release_work before returning to Ready"
                )
            self._require_ready_metadata(item, settings, values)
        values[settings.queue.state_field] = _live_single_select_option(
            inventory, settings.queue.state_field, target.value
        )
        outcomes = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            values,
            apply=apply,
            idempotency_key=idempotency_key,
        )
        return {
            "mode": "apply" if apply else "preview",
            "outcomes": [value.to_json_dict() for value in outcomes],
        }

    async def sync_change_classification(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        change_id: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(change_id, str) or not change_id.strip():
            raise ValueError("change_id must be a non-empty string")
        normalized_change_id = change_id.strip()
        if Path(normalized_change_id).name != normalized_change_id or any(
            separator in normalized_change_id for separator in ("/", "\\")
        ):
            raise ValueError("change_id must be one local change identifier")
        project, _binding = self._project_and_binding(project_id)
        project_root = Path(project.local_root)
        scope_path = _change_scope_path(project_root, normalized_change_id)
        document = json.loads(scope_path.read_text(encoding="utf-8-sig"))
        if (
            not isinstance(document, dict)
            or document.get("change_id") != normalized_change_id
        ):
            raise ValueError(
                "authoritative change scope identity does not match change_id"
            )
        schema_version = document.get("schema_version")
        if (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version < 4
        ):
            raise ValueError(
                "change classification projection requires scope schema version 4+"
            )
        complexity = document.get("complexity")
        if not isinstance(complexity, str) or not complexity.strip():
            raise ValueError("authoritative change scope has no complexity")
        raw_triggers = document.get("risk_triggers", [])
        if not isinstance(raw_triggers, list) or any(
            not isinstance(value, str) or not value.strip() for value in raw_triggers
        ):
            raise ValueError("authoritative change scope risk_triggers are invalid")
        triggers = tuple(sorted(value.strip() for value in raw_triggers))
        if len(set(triggers)) != len(triggers):
            raise ValueError(
                "authoritative change scope risk_triggers contain duplicates"
            )

        settings = self._command_settings()
        evidence_fields = (
            settings.delivery.change_id_field,
            settings.delivery.complexity_field,
            settings.delivery.risk_triggers_field,
            settings.delivery.stage_field,
        )
        inventory, item, settings = await self._issue_command_inventory(
            project_id,
            repository,
            issue_number,
            extra_fields=evidence_fields,
        )
        for field_name in evidence_fields:
            if settings.authority(field_name).direction != "evidence":
                raise ValueError(
                    f"classification projection field is not evidence-owned: {field_name}"
                )
        desired = {
            settings.delivery.change_id_field: normalized_change_id,
            settings.delivery.complexity_field: _live_single_select_option(
                inventory, settings.delivery.complexity_field, complexity.strip()
            ),
            settings.delivery.risk_triggers_field: ", ".join(triggers),
            settings.delivery.stage_field: _live_single_select_option(
                inventory,
                settings.delivery.stage_field,
                settings.delivery.change_created_stage.value,
            ),
        }
        outcomes = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            desired,
            apply=apply,
            idempotency_key=idempotency_key,
        )
        return {
            "mode": "apply" if apply else "preview",
            "source_scope": str(
                scope_path.relative_to(Path(project.local_root))
            ).replace("\\", "/"),
            "classification": {
                "change_id": normalized_change_id,
                "complexity": complexity.strip(),
                "risk_triggers": list(triggers),
            },
            "outcomes": [value.to_json_dict() for value in outcomes],
        }

    async def complete_work(
        self,
        project_id: str,
        repository: str,
        issue_number: int,
        record: WorkRecord,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if record.project_id != project_id:
            raise ValueError("record project_id does not match command project_id")
        settings = self._command_settings()
        decision = evaluate_transition(
            record,
            settings.completion.terminal_state,
            settings=settings,
        )
        if not decision.allowed:
            return {
                "mode": "blocked",
                "reasons": list(decision.reasons),
                "source_close_required": False,
            }
        inventory, item, settings = await self._issue_command_inventory(
            project_id,
            repository,
            issue_number,
            extra_fields=(settings.delivery.stage_field,),
        )
        desired = {
            settings.queue.state_field: _live_single_select_option(
                inventory,
                settings.queue.state_field,
                settings.completion.terminal_state.value,
            ),
            settings.delivery.stage_field: _live_single_select_option(
                inventory,
                settings.delivery.stage_field,
                settings.delivery.complete_stage.value,
            ),
        }
        outcomes = await self._reconcile_issue_fields(
            project_id,
            inventory,
            item,
            desired,
            apply=apply,
            idempotency_key=idempotency_key,
        )
        successful = all(value.success for value in outcomes)
        return {
            "mode": "apply" if apply else "preview",
            "outcomes": [value.to_json_dict() for value in outcomes],
            "source_close_required": successful,
        }

    async def schema_status(
        self,
        project_id: str,
        *,
        manifest_path: Path | None = None,
    ) -> ProjectSchemaStatus:
        project, binding = self._project_and_binding(project_id)
        backend = self._backend(project, binding)
        reader = getattr(backend, "read_schema_fields", None)
        if reader is None:
            raise WorkManagementUnavailable(
                project.project_id,
                binding.provider,
                "configured provider does not expose bounded Project field inventory",
                error_code="project_schema_unavailable",
            )
        manifest = load_project_schema_manifest(manifest_path)
        if manifest.portfolio_id != self.settings.portfolio_id:
            raise ValueError(
                "project schema manifest does not match configured portfolio"
            )
        project_binding = self._project_binding(project, binding)
        observed_fields = await reader(project_binding)
        views_reader = getattr(backend, "read_schema_views", None)
        observed_views = (
            None
            if views_reader is None
            else tuple(await views_reader(project_binding))
        )
        return compare_project_schema(
            manifest,
            tuple(observed_fields),
            project_id=project.project_id,
            views_observed=observed_views,
        )

    async def schema_plan(
        self,
        project_id: str,
        *,
        manifest_path: Path | None = None,
    ) -> ProjectSchemaPlan:
        status = await self.schema_status(project_id, manifest_path=manifest_path)
        manifest = load_project_schema_manifest(manifest_path)
        return plan_project_schema_repair(status, manifest)

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
                raise ValueError(
                    "reconciliation projections must match selected project"
                )
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
