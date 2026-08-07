from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ...work_management import (
    ProjectBinding,
    ProjectInventory,
    ReconciliationAction,
    ReconciliationDecision,
    ReconciliationOutcome,
)
from .projects import GitHubProjectInventoryAdapter
from .projects.adapter import ToolCaller

_PROJECT_GET = "projects_get"
_PROJECT_LIST = "projects_list"
_PROJECT_WRITE = "projects_write"


@dataclass(frozen=True, slots=True)
class GitHubProjectCapabilities:
    read_inventory: bool
    add_item: bool
    update_item: bool
    built_in_workflows: bool
    available_tools: tuple[str, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "read_inventory": self.read_inventory,
            "add_item": self.add_item,
            "update_item": self.update_item,
            "built_in_workflows": self.built_in_workflows,
            "available_tools": list(self.available_tools),
        }


def detect_github_project_capabilities(
    tool_names: Sequence[str],
) -> GitHubProjectCapabilities:
    normalized = tuple(
        sorted(
            {
                str(name).strip().casefold()
                for name in tool_names
                if str(name).strip().casefold()
                in {_PROJECT_GET, _PROJECT_LIST, _PROJECT_WRITE}
            }
        )
    )
    available = set(normalized)
    return GitHubProjectCapabilities(
        read_inventory={_PROJECT_GET, _PROJECT_LIST}.issubset(available),
        add_item=_PROJECT_WRITE in available,
        update_item=_PROJECT_WRITE in available,
        built_in_workflows=False,
        available_tools=normalized,
    )


class GitHubProjectManagementError(RuntimeError):
    pass


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GitHubProjectManagementError(
            f"GITHUB_PROJECT_MANAGEMENT_INVALID_RESPONSE: {label} was missing"
        )
    return value.strip()


def _mapping(result: Any, operation: str) -> dict[str, Any]:
    if isinstance(result, Mapping):
        document = dict(result)
    else:
        data = getattr(result, "data", None)
        structured = getattr(result, "structured_content", None)
        if isinstance(data, Mapping):
            document = dict(data)
        elif isinstance(structured, Mapping):
            document = dict(structured)
        else:
            texts = [
                text
                for block in getattr(result, "content", ())
                if isinstance((text := getattr(block, "text", None)), str)
            ]
            if not texts:
                raise GitHubProjectManagementError(
                    f"GITHUB_PROJECT_MANAGEMENT_INVALID_RESPONSE: {operation}: result was not an object"
                )
            try:
                parsed = json.loads("\n".join(texts))
            except json.JSONDecodeError as exc:
                raise GitHubProjectManagementError(
                    f"GITHUB_PROJECT_MANAGEMENT_INVALID_RESPONSE: {operation}: result text was not JSON"
                ) from exc
            if not isinstance(parsed, Mapping):
                raise GitHubProjectManagementError(
                    f"GITHUB_PROJECT_MANAGEMENT_INVALID_RESPONSE: {operation}: result JSON was not an object"
                )
            document = dict(parsed)
    for key in ("result", "data"):
        nested = document.get(key)
        if isinstance(nested, Mapping):
            document = dict(nested)
    candidate = document.get("item", document.get("projectItem", document))
    if not isinstance(candidate, Mapping):
        raise GitHubProjectManagementError(
            f"GITHUB_PROJECT_MANAGEMENT_INVALID_RESPONSE: {operation}: item was not an object"
        )
    return dict(candidate)


def _fingerprint(decision: ReconciliationDecision) -> str:
    document = decision.to_json_dict()
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _revision(item: Mapping[str, Any], operation: str) -> str | None:
    value = item.get("updatedAt", item.get("updated_at", item.get("revision")))
    if value is None:
        return None
    return _required_text(value, f"{operation} revision")


def _item_id(item: Mapping[str, Any], operation: str) -> str:
    return _required_text(item.get("id", item.get("item_id")), f"{operation} item id")


class GitHubProjectManagementAdapter:
    def __init__(
        self,
        caller: ToolCaller,
        bindings: Mapping[str, ProjectBinding],
        *,
        available_tools: Sequence[str],
        page_size: int = 50,
        max_pages: int = 20,
    ) -> None:
        if not hasattr(caller, "call_tool"):
            raise ValueError("caller must provide call_tool")
        normalized_bindings: dict[str, ProjectBinding] = {}
        for project_id, binding in bindings.items():
            if not isinstance(binding, ProjectBinding):
                raise ValueError("bindings must contain ProjectBinding values")
            if project_id != binding.managed_project_id:
                raise ValueError("binding key must match managed_project_id")
            if binding.provider_id != "github-mcp":
                raise ValueError("GitHub project management requires github-mcp bindings")
            normalized_bindings[project_id] = binding
        if not normalized_bindings:
            raise ValueError("at least one project binding is required")
        self._caller = caller
        self._bindings = normalized_bindings
        self.capabilities = detect_github_project_capabilities(available_tools)
        self._inventory = GitHubProjectInventoryAdapter(
            caller,
            page_size=page_size,
            max_pages=max_pages,
        )
        self._idempotency: dict[
            str,
            tuple[str, ReconciliationOutcome],
        ] = {}

    def _binding(self, project_id: str) -> ProjectBinding:
        try:
            return self._bindings[project_id]
        except KeyError as exc:
            raise ValueError(f"project binding is not configured: {project_id}") from exc

    @staticmethod
    def _base(binding: ProjectBinding) -> dict[str, Any]:
        return {
            "owner": binding.owner,
            "owner_type": binding.owner_type.value,
            "project_number": binding.project_number,
        }

    async def _call(
        self,
        operation: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = await self._caller.call_tool(tool_name, arguments)
        except Exception as exc:
            raise GitHubProjectManagementError(
                f"GITHUB_PROJECT_MANAGEMENT_FAILED: {operation}: {type(exc).__name__}"
            ) from exc
        return _mapping(result, operation)

    async def read_inventory(
        self,
        project_binding: ProjectBinding,
        *,
        field_names: tuple[str, ...] = (),
        item_limit: int = 100,
    ) -> ProjectInventory:
        if not self.capabilities.read_inventory:
            raise GitHubProjectManagementError(
                "GITHUB_PROJECT_MANAGEMENT_UNSUPPORTED: inventory tools are unavailable"
            )
        configured = self._binding(project_binding.managed_project_id)
        if configured != project_binding:
            raise ValueError("project_binding does not match configured GitHub binding")
        return await self._inventory.read_inventory(
            project_binding,
            field_names=field_names,
            item_limit=item_limit,
        )

    def _unsupported(
        self,
        decision: ReconciliationDecision,
        message: str,
    ) -> ReconciliationOutcome:
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=ReconciliationAction.UNSUPPORTED,
            applied=False,
            success=False,
            provider_revision=decision.observed_revision,
            message=message,
        )

    def _idempotency_result(
        self,
        decision: ReconciliationDecision,
        idempotency_key: str,
    ) -> ReconciliationOutcome | None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key must be a non-empty string")
        fingerprint = _fingerprint(decision)
        previous = self._idempotency.get(idempotency_key)
        if previous is None:
            return None
        previous_fingerprint, outcome = previous
        if previous_fingerprint == fingerprint:
            return outcome
        return ReconciliationOutcome(
            project_id=decision.project_id,
            record_id=decision.record_id,
            action=ReconciliationAction.CONFLICT,
            applied=False,
            success=False,
            provider_revision=outcome.provider_revision,
            message="idempotency key was already used for a different command",
        )

    def _remember(
        self,
        idempotency_key: str,
        decision: ReconciliationDecision,
        outcome: ReconciliationOutcome,
    ) -> ReconciliationOutcome:
        self._idempotency[idempotency_key] = (_fingerprint(decision), outcome)
        return outcome

    async def _preflight_update(
        self,
        binding: ProjectBinding,
        decision: ReconciliationDecision,
    ) -> tuple[str, str | None]:
        if decision.external_id is None:
            raise GitHubProjectManagementError(
                "GITHUB_PROJECT_MANAGEMENT_INVALID_COMMAND: update requires external_id"
            )
        item = await self._call(
            "get_project_item",
            _PROJECT_GET,
            {
                "method": "get_project_item",
                **self._base(binding),
                "item_id": decision.external_id,
                "field_names": list(decision.changed_fields),
            },
        )
        return _item_id(item, "get_project_item"), _revision(item, "get_project_item")

    async def _update_fields(
        self,
        binding: ProjectBinding,
        decision: ReconciliationDecision,
        item_id: str,
    ) -> str | None:
        desired = dict(decision.desired_fields)
        latest_revision = decision.observed_revision
        for field_name in decision.changed_fields:
            item = await self._call(
                "update_project_item",
                _PROJECT_WRITE,
                {
                    "method": "update_project_item",
                    **self._base(binding),
                    "item_id": item_id,
                    "updated_field": {
                        "name": field_name,
                        "value": desired[field_name],
                    },
                },
            )
            latest_revision = _revision(item, "update_project_item") or latest_revision
        return latest_revision

    async def _create_item(
        self,
        binding: ProjectBinding,
        decision: ReconciliationDecision,
    ) -> tuple[str, str | None]:
        if (
            decision.source_repository is None
            or decision.source_number is None
            or decision.source_kind is None
        ):
            raise GitHubProjectManagementError(
                "GITHUB_PROJECT_MANAGEMENT_INVALID_COMMAND: create requires source identity"
            )
        owner, repository = decision.source_repository.split("/", 1)
        arguments: dict[str, Any] = {
            "method": "add_project_item",
            **self._base(binding),
            "item_owner": owner,
            "item_repo": repository,
            "item_type": decision.source_kind,
        }
        if decision.source_kind == "issue":
            arguments["issue_number"] = decision.source_number
        else:
            arguments["pull_request_number"] = decision.source_number
        item = await self._call("add_project_item", _PROJECT_WRITE, arguments)
        return _item_id(item, "add_project_item"), _revision(item, "add_project_item")

    async def apply_reconciliation(
        self,
        decision: ReconciliationDecision,
        *,
        idempotency_key: str,
    ) -> ReconciliationOutcome:
        if not isinstance(decision, ReconciliationDecision):
            raise ValueError("decision must be ReconciliationDecision")
        replay = self._idempotency_result(decision, idempotency_key)
        if replay is not None:
            return replay
        binding = self._binding(decision.project_id)
        if decision.action is ReconciliationAction.CREATE:
            if not self.capabilities.add_item:
                return self._unsupported(decision, "projects_write add capability is unavailable")
            item_id, revision = await self._create_item(binding, decision)
            if decision.changed_fields:
                revision = await self._update_fields(binding, decision, item_id)
        elif decision.action is ReconciliationAction.UPDATE:
            if not self.capabilities.update_item:
                return self._unsupported(decision, "projects_write update capability is unavailable")
            item_id, current_revision = await self._preflight_update(binding, decision)
            if (
                decision.observed_revision is not None
                and current_revision != decision.observed_revision
            ):
                return self._remember(
                    idempotency_key,
                    decision,
                    ReconciliationOutcome(
                        project_id=decision.project_id,
                        record_id=decision.record_id,
                        action=ReconciliationAction.CONFLICT,
                        applied=False,
                        success=False,
                        provider_revision=current_revision,
                        message="observed GitHub Project item revision changed",
                    ),
                )
            revision = await self._update_fields(binding, decision, item_id)
        else:
            return self._unsupported(
                decision,
                f"reconciliation action {decision.action.value} is not mutable",
            )
        return self._remember(
            idempotency_key,
            decision,
            ReconciliationOutcome(
                project_id=decision.project_id,
                record_id=decision.record_id,
                action=decision.action,
                applied=True,
                success=True,
                provider_revision=revision,
                message="GitHub Project reconciliation applied",
            ),
        )


__all__ = [
    "GitHubProjectCapabilities",
    "GitHubProjectManagementAdapter",
    "GitHubProjectManagementError",
    "detect_github_project_capabilities",
]
