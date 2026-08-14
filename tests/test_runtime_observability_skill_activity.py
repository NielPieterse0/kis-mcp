from __future__ import annotations

from kis_mcp.runtime_observability import RuntimeObservability


def test_skill_activity_is_bounded_newest_first_and_payload_free() -> None:
    registry = RuntimeObservability(max_recent_calls=2)

    registry.record_skill_activity(
        event_name="skill_loaded",
        source="observed",
        skill_id="alpha-skill",
        snapshot_id="snapshot-a",
        content_sha256="a" * 64,
        project_id="alpha-project",
        activation_id="activation-1",
        request_id="request-1",
        outcome="success",
        duration_ms=12,
    )
    registry.record_skill_activity(
        event_name="skill_resource_read",
        source="observed",
        skill_id="alpha-skill",
        snapshot_id="snapshot-a",
        content_sha256="b" * 64,
        outcome="success",
        duration_ms=4,
    )
    registry.record_skill_activity(
        event_name="skill_completed",
        source="reported",
        skill_id="alpha-skill",
        snapshot_id="snapshot-a",
        content_sha256="a" * 64,
        outcome="success",
        duration_ms=100,
        total_tokens=321,
        tool_calls=5,
        retries=1,
        verification_passed=True,
    )

    snapshot = registry.snapshot()
    assert [item.event_name for item in snapshot.recent_skill_activity] == [
        "skill_completed",
        "skill_resource_read",
    ]
    assert snapshot.recent_skill_activity[0].source == "reported"
    assert snapshot.recent_skill_activity[0].total_tokens == 321
    rendered = str(snapshot.to_dict())
    assert "prompt-secret" not in rendered
    assert "file-content-secret" not in rendered
    assert "tool-argument-secret" not in rendered
