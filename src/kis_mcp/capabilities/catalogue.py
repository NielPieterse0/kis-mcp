from __future__ import annotations

from collections.abc import Iterable

from .contracts import CapabilityContribution, OperationDescriptor, WorkflowDescriptor


class CapabilityCatalogue:
    """Deterministic immutable index of normalized platform contributions."""

    def __init__(
        self,
        contributions: Iterable[CapabilityContribution],
        workflows: Iterable[WorkflowDescriptor],
    ) -> None:
        ordered = tuple(sorted(contributions, key=lambda item: item.contribution_id))
        workflow_items = tuple(sorted(workflows, key=lambda item: item.workflow_id))
        contribution_ids = [item.contribution_id for item in ordered]
        if len(set(contribution_ids)) != len(contribution_ids):
            raise ValueError("duplicate contribution ID")
        workflow_ids = [item.workflow_id for item in workflow_items]
        if len(set(workflow_ids)) != len(workflow_ids):
            raise ValueError("duplicate workflow ID")

        by_operation_id: dict[str, OperationDescriptor] = {}
        by_operation_name: dict[str, OperationDescriptor] = {}
        owner_by_operation: dict[str, CapabilityContribution] = {}
        for contribution in ordered:
            for operation in contribution.operations:
                if operation.operation_id in by_operation_id:
                    raise ValueError(f"duplicate operation ID: {operation.operation_id}")
                if operation.name in by_operation_name:
                    raise ValueError(f"duplicate operation name: {operation.name}")
                by_operation_id[operation.operation_id] = operation
                by_operation_name[operation.name] = operation
                owner_by_operation[operation.operation_id] = contribution

        self._contributions = ordered
        self._workflows = workflow_items
        self._by_operation_id = by_operation_id
        self._by_operation_name = by_operation_name
        self._owner_by_operation = owner_by_operation

    @property
    def contributions(self) -> tuple[CapabilityContribution, ...]:
        return self._contributions

    @property
    def workflows(self) -> tuple[WorkflowDescriptor, ...]:
        return self._workflows

    @property
    def operations(self) -> tuple[OperationDescriptor, ...]:
        return tuple(self._by_operation_id[key] for key in sorted(self._by_operation_id))

    def operation(self, operation_id_or_name: str) -> OperationDescriptor:
        operation = self._by_operation_id.get(operation_id_or_name)
        if operation is None:
            operation = self._by_operation_name.get(operation_id_or_name)
        if operation is None:
            raise KeyError(f"unknown operation: {operation_id_or_name}")
        return operation

    def contribution_for(self, operation: OperationDescriptor) -> CapabilityContribution:
        return self._owner_by_operation[operation.operation_id]

    def contribution(self, contribution_id: str) -> CapabilityContribution:
        for item in self._contributions:
            if item.contribution_id == contribution_id:
                return item
        raise KeyError(f"unknown contribution: {contribution_id}")

    def workflow(self, workflow_id: str) -> WorkflowDescriptor:
        for item in self._workflows:
            if item.workflow_id == workflow_id:
                return item
        raise KeyError(f"unknown workflow: {workflow_id}")

    def capabilities(self) -> frozenset[str]:
        return frozenset(
            capability
            for contribution in self._contributions
            for capability in contribution.capabilities
        )


__all__ = ["CapabilityCatalogue"]
