from __future__ import annotations

import asyncio

import pytest

from kis_mcp.work_management import DocumentationImpact, LifecycleState, Priority, RecordType
from kis_mcp.work_management.intake import (
    CaptureWorkItem,
    IntakeBackend,
    MutationDisposition,
    MutationResult,
    capture_work_item,
)


class Backend:
    def __init__(self, result: MutationResult) -> None:
        self.result = result
        self.commands: list[CaptureWorkItem] = []

    async def capture(self, command: CaptureWorkItem) -> MutationResult:
        self.commands.append(command)
        return self.result


def result(
    disposition: MutationDisposition,
    idempotency_key: str = "capture-001",
) -> MutationResult:
    return MutationResult(
        project_id="kis-mcp",
        idempotency_key=idempotency_key,
        disposition=disposition,
        record_id="IDEA-1",
        message="captured",
    )


def test_capture_defaults_to_low_friction_inbox_idea() -> None:
    backend = Backend(result(MutationDisposition.CREATED))

    outcome = asyncio.run(
        capture_work_item(
            backend,
            project_id="kis-mcp",
            title="Explore Project automation",
            idempotency_key="capture-001",
        )
    )

    command = backend.commands[0]
    assert command.record_type is RecordType.IDEA
    assert command.state is LifecycleState.INBOX
    assert command.priority is Priority.MEDIUM
    assert command.documentation_impact is DocumentationImpact.NOT_ASSESSED
    assert command.note is None
    assert outcome.disposition is MutationDisposition.CREATED


def test_capture_accepts_explicit_type_state_and_metadata() -> None:
    backend = Backend(result(MutationDisposition.UPDATED, "capture-002"))

    asyncio.run(
        capture_work_item(
            backend,
            project_id="kis-mcp",
            title="Implement typed records",
            idempotency_key="capture-002",
            note="P2 internal contract slice",
            record_type=RecordType.TASK,
            priority=Priority.HIGH,
            module="work-management",
            state=LifecycleState.TRIAGE,
            documentation_impact=DocumentationImpact.PLANNED,
        )
    )

    command = backend.commands[0]
    assert command.record_type is RecordType.TASK
    assert command.state is LifecycleState.TRIAGE
    assert command.module == "work-management"
    assert command.documentation_impact is DocumentationImpact.PLANNED


def test_actionable_intake_requires_documentation_classification() -> None:
    with pytest.raises(ValueError, match="documentation_impact"):
        CaptureWorkItem(
            project_id="kis-mcp",
            title="Implement without docs classification",
            idempotency_key="capture-docs-001",
            record_type=RecordType.TASK,
        )


def test_capture_requires_stable_project_and_idempotency_identity() -> None:
    backend = Backend(result(MutationDisposition.REJECTED))

    with pytest.raises(ValueError, match="idempotency_key"):
        asyncio.run(
            capture_work_item(
                backend,
                project_id="kis-mcp",
                title="Invalid",
                idempotency_key=" ",
            )
        )

    with pytest.raises(ValueError, match="project_id"):
        CaptureWorkItem(
            project_id="KIS MCP",
            title="Invalid",
            idempotency_key="capture-003",
        )


def test_mutation_result_is_bounded_and_explicit() -> None:
    value = MutationResult(
        project_id="kis-mcp",
        idempotency_key="capture-004",
        disposition=MutationDisposition.CONFLICT,
        record_id=None,
        message="Observed state changed",
        conflict_revision="rev-2",
    )

    assert value.to_json_dict() == {
        "schema_version": 1,
        "project_id": "kis-mcp",
        "idempotency_key": "capture-004",
        "disposition": "conflict",
        "record_id": None,
        "message": "Observed state changed",
        "conflict_revision": "rev-2",
    }


def test_backend_protocol_is_provider_neutral() -> None:
    assert isinstance(Backend(result(MutationDisposition.CREATED)), IntakeBackend)
