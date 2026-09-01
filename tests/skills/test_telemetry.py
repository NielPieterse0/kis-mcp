from __future__ import annotations

import sqlite3
from pathlib import Path

from kis_mcp.skills.telemetry import SkillTelemetryEvent, SkillTelemetryStore


def _event(
    event_name: str,
    *,
    source: str = "observed",
    activation_id: str | None = "activation-1",
    project_id: str | None = "project-alpha",
    duration_ms: int | None = 10,
    total_tokens: int | None = None,
) -> SkillTelemetryEvent:
    return SkillTelemetryEvent(
        event_name=event_name,
        source=source,
        skill_id="alpha-skill",
        snapshot_id="snapshot-a",
        content_sha256="a" * 64,
        project_id=project_id,
        activation_id=activation_id,
        request_id="request-1",
        outcome="success",
        duration_ms=duration_ms,
        total_tokens=total_tokens,
    )


def test_store_survives_recreation_and_prunes_oldest_rows(tmp_path: Path) -> None:
    path = tmp_path / "skills.sqlite3"
    store = SkillTelemetryStore(path, max_events=2)
    store.record(_event("skill_discovered"))
    store.record(_event("skill_loaded"))
    store.record(_event("skill_resource_read"))

    reopened = SkillTelemetryStore(path, max_events=2)
    report = reopened.report(skill_id="alpha-skill")

    assert report.event_count == 2
    assert len(report.groups) == 1
    group = report.groups[0]
    assert group.discovered_count == 0
    assert group.loaded_count == 1
    assert group.resource_read_count == 1


def test_report_preserves_missing_metrics_as_not_observable(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    store.record(_event("skill_loaded", duration_ms=None))
    store.record(_event("skill_completed", source="reported", total_tokens=321))

    group = store.report(skill_id="alpha-skill").groups[0]

    assert group.completed_count == 1
    assert group.duration_samples == 1
    assert group.token_samples == 1
    assert group.total_tokens == 321
    assert group.tool_call_samples == 0
    assert group.total_tool_calls is None
    assert group.retry_samples == 0
    assert group.total_retries is None


def test_observed_load_lookup_requires_exact_identity(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    store.record(_event("skill_loaded"))

    assert store.has_observed_load(
        skill_id="alpha-skill",
        activation_id="activation-1",
        snapshot_id="snapshot-a",
        content_sha256="a" * 64,
        project_id="project-alpha",
    )
    assert not store.has_observed_load(
        skill_id="alpha-skill",
        activation_id="activation-2",
        snapshot_id="snapshot-a",
        content_sha256="a" * 64,
        project_id="project-alpha",
    )


def test_sqlite_schema_has_no_payload_columns(tmp_path: Path) -> None:
    path = tmp_path / "skills.sqlite3"
    SkillTelemetryStore(path).record(_event("skill_loaded"))

    with sqlite3.connect(path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(skill_events)")
        }

    forbidden = {"prompt", "content", "file_content", "query", "arguments", "path"}
    assert columns.isdisjoint(forbidden)


def test_existing_database_migrates_delivery_columns_without_rewriting_native_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "skills.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE skill_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL,
                event_name TEXT NOT NULL, source TEXT NOT NULL, skill_id TEXT,
                snapshot_id TEXT, content_sha256 TEXT, project_id TEXT,
                activation_id TEXT, request_id TEXT, outcome TEXT NOT NULL,
                duration_ms INTEGER, error_class TEXT, total_tokens INTEGER,
                tool_calls INTEGER, retries INTEGER, verification_passed INTEGER
            )"""
        )
        connection.execute(
            """INSERT INTO skill_events (
                occurred_at, event_name, source, skill_id, snapshot_id,
                content_sha256, project_id, activation_id, request_id, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "2026-08-16T00:00:00+00:00", "skill_loaded", "observed",
                "alpha-skill", "snapshot-a", "a" * 64, "project-alpha",
                "activation-1", "request-1", "success",
            ),
        )

    store = SkillTelemetryStore(path)
    report = store.delivery_report(skill_id="alpha-skill")

    assert report.groups[0].delivery_path == "kis_native"
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(skill_events)")}
    assert {
        "delivery_path",
        "resource_uri",
        "resource_class",
        "server_origin",
        "server_identity_fingerprint",
        "protocol_version",
        "extension_id",
        "extension_settings_fingerprint",
        "commissioning_receipt_id",
        "canonical_skill_uri",
        "resource_set_fingerprint",
        "integrity_proof",
        "digest_verified",
    } <= columns
    with sqlite3.connect(path) as connection:
        migrated = connection.execute(
            "SELECT delivery_path, server_identity_fingerprint, commissioning_receipt_id "
            "FROM skill_events WHERE skill_id = 'alpha-skill'"
        ).fetchone()
    assert migrated == ("kis_native", None, None)
