from __future__ import annotations

from kis_mcp import runtime_observability
from kis_mcp.runtime_observability import RuntimeObservability


def test_public_exports_are_unique() -> None:
    assert len(runtime_observability.__all__) == len(set(runtime_observability.__all__))


def test_recent_calls_are_bounded_newest_first_and_store_only_argument_keys() -> None:
    registry = RuntimeObservability(max_recent_calls=2, max_policy_decisions=2)

    registry.record_tool_call(
        tool_name="write_file",
        argument_keys=("path", "content"),
        decision="allow",
        outcome="success",
    )
    registry.record_tool_call(
        tool_name="execute_command",
        argument_keys=("command",),
        decision="block",
        outcome="rejected",
        code="HR-002_EXTERNAL_NETWORK",
    )
    registry.record_tool_call(
        tool_name="read_file",
        argument_keys=("path",),
        decision="allow",
        outcome="success",
    )

    snapshot = registry.snapshot()

    assert [record.tool_name for record in snapshot.recent_calls] == [
        "read_file",
        "execute_command",
    ]
    assert snapshot.recent_calls[1].argument_keys == ("command",)
    assert [record.call_id for record in snapshot.recent_calls] == [
        "call-000003",
        "call-000002",
    ]
    rendered = str(snapshot.to_dict())
    assert "secret-value" not in rendered
    assert "result body" not in rendered


def test_policy_decisions_are_bounded_and_exclude_allowed_calls() -> None:
    registry = RuntimeObservability(max_recent_calls=5, max_policy_decisions=2)

    registry.record_tool_call(
        tool_name="read_file",
        argument_keys=("path",),
        decision="allow",
        outcome="success",
    )
    registry.record_tool_call(
        tool_name="execute_command",
        argument_keys=("command",),
        decision="block",
        outcome="rejected",
        code="HR-002_EXTERNAL_NETWORK",
    )
    registry.record_tool_call(
        tool_name="delete_file",
        argument_keys=("path",),
        decision="quarantine",
        outcome="success",
        code="HR-003_QUARANTINE_REQUIRED",
    )
    registry.record_tool_call(
        tool_name="write_file",
        argument_keys=("path", "content"),
        decision="block",
        outcome="rejected",
        code="HR-001_WRITE_OUTSIDE_PROJECTS",
    )

    snapshot = registry.snapshot()

    assert [record.code for record in snapshot.recent_policy_decisions] == [
        "HR-001_WRITE_OUTSIDE_PROJECTS",
        "HR-003_QUARANTINE_REQUIRED",
    ]


def test_process_and_search_lifecycle_tracks_only_active_records() -> None:
    registry = RuntimeObservability(max_recent_calls=5, max_policy_decisions=5)

    registry.process_started(pid=101, cwd=r"C:\Projects\alpha", shell="powershell")
    registry.process_started(pid=202, cwd=r"C:\Projects\beta", shell="cmd")
    registry.process_interacted(pid=101)
    registry.search_started(search_id="search-1", tool_name="start_search")
    registry.search_started(search_id="search-2", tool_name="start_search")
    registry.process_stopped(pid=202)
    registry.search_stopped(search_id="search-1")

    snapshot = registry.snapshot()

    assert [(item.pid, item.cwd, item.shell) for item in snapshot.active_processes] == [
        (101, r"C:\Projects\alpha", "powershell")
    ]
    assert [item.search_id for item in snapshot.active_searches] == ["search-2"]
    assert snapshot.active_processes[0].interaction_count == 1


def test_boundary_requests_are_bounded_and_payload_free() -> None:
    registry = RuntimeObservability(
        max_recent_calls=2,
        max_policy_decisions=2,
        max_boundary_requests=2,
    )
    registry.record_boundary_request(method="initialize", outcome="success")
    registry.record_boundary_request(method="tools/list", outcome="success")
    registry.record_boundary_request(
        method="tools/call",
        tool_name="kis_health",
        outcome="error",
        error_type="ToolError",
    )

    snapshot = registry.snapshot()
    assert [item.request_id for item in snapshot.recent_boundary_requests] == [
        "request-000003",
        "request-000002",
    ]
    assert snapshot.recent_boundary_requests[0].tool_name == "kis_health"
    assert snapshot.recent_boundary_requests[0].error_type == "ToolError"
    rendered = str(snapshot.to_dict())
    assert "secret-value" not in rendered
    assert "result body" not in rendered
