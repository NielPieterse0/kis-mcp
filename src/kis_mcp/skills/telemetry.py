from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..runtime_observability import RuntimeObservability, current_request_id

_EVENT_NAMES = frozenset(
    {
        "skill_discovered",
        "skill_loaded",
        "skill_resource_discovered",
        "skill_resource_read",
        "skill_catalogue_exposed",
        "skill_catalogue_refreshed",
        "skill_evaluated",
        "skill_created",
        "skill_improved",
        "skill_applied",
        "skill_completed",
        "skill_failed",
    }
)
_REPORTED_EVENTS = frozenset({"skill_applied", "skill_completed", "skill_failed"})
_DELIVERY_PATHS = frozenset({"kis_native", "mcp_resource"})
_RESOURCE_CLASSES = frozenset(
    {"catalogue", "SKILL.md", "reference", "script", "asset", "agent", "other"}
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_ERROR_CLASS = re.compile(r"^[A-Za-z0-9_.]{1,128}$")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class SkillTelemetryEvent:
    event_name: str
    source: str
    skill_id: str | None = None
    snapshot_id: str | None = None
    content_sha256: str | None = None
    project_id: str | None = None
    activation_id: str | None = None
    request_id: str | None = None
    outcome: str = "success"
    duration_ms: int | None = None
    error_class: str | None = None
    total_tokens: int | None = None
    tool_calls: int | None = None
    retries: int | None = None
    verification_passed: bool | None = None
    delivery_path: str = "kis_native"
    resource_uri: str | None = None
    resource_class: str | None = None
    server_origin: str | None = None
    digest_verified: bool | None = None
    occurred_at: str | None = None


@dataclass(frozen=True, slots=True)
class SkillTelemetryGroup:
    skill_id: str | None
    content_sha256: str | None
    project_id: str | None
    discovered_count: int
    loaded_count: int
    resource_read_count: int
    evaluated_count: int
    mutation_count: int
    applied_count: int
    completed_count: int
    failed_count: int
    error_count: int
    duration_samples: int
    total_duration_ms: int | None
    token_samples: int
    total_tokens: int | None
    tool_call_samples: int
    total_tool_calls: int | None
    retry_samples: int
    total_retries: int | None
    verification_samples: int
    verification_passes: int | None


@dataclass(frozen=True, slots=True)
class SkillTelemetryReport:
    groups: tuple[SkillTelemetryGroup, ...]
    event_count: int
    truncated: bool
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class SkillDeliveryTelemetryGroup:
    skill_id: str
    content_sha256: str
    project_id: str | None
    delivery_path: str
    loaded_count: int
    resource_read_count: int
    applied_count: int
    completed_count: int
    failed_count: int
    error_count: int
    digest_verified_count: int
    digest_failed_count: int


@dataclass(frozen=True, slots=True)
class SkillDeliveryComparison:
    skill_id: str
    content_sha256: str
    project_id: str | None
    comparable: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SkillDeliveryTelemetryReport:
    groups: tuple[SkillDeliveryTelemetryGroup, ...]
    comparisons: tuple[SkillDeliveryComparison, ...]
    event_count: int
    catalogue_exposure_count: int
    truncated: bool
    schema_version: int = 1


def _optional_id(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if _SAFE_ID.fullmatch(normalized) is None:
        raise ValueError(f"{label} is invalid")
    return normalized


def _optional_metric(value: int | None, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _optional_text(value: str | None, label: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or len(normalized) > max_length or any(ord(ch) < 32 for ch in normalized):
        raise ValueError(f"{label} is invalid")
    return normalized


def _normalize_event(event: SkillTelemetryEvent) -> SkillTelemetryEvent:
    if event.event_name not in _EVENT_NAMES:
        raise ValueError("skill telemetry event_name is invalid")
    if event.source not in {"observed", "reported"}:
        raise ValueError("skill telemetry source is invalid")
    if (event.event_name in _REPORTED_EVENTS) != (event.source == "reported"):
        raise ValueError("reported skill events must remain distinct from observed events")
    skill_id = _optional_id(event.skill_id, "skill_id")
    snapshot_id = _optional_id(event.snapshot_id, "snapshot_id")
    project_id = _optional_id(event.project_id, "project_id")
    activation_id = _optional_id(event.activation_id, "activation_id")
    request_id = _optional_id(event.request_id or current_request_id(), "request_id")
    content_sha256 = event.content_sha256
    if content_sha256 is not None and _SHA256.fullmatch(content_sha256) is None:
        raise ValueError("content_sha256 must be a lowercase SHA-256 value")
    error_class = event.error_class
    if error_class is not None and _ERROR_CLASS.fullmatch(error_class) is None:
        raise ValueError("error_class is invalid")
    if not event.outcome or len(event.outcome) > 32:
        raise ValueError("outcome is invalid")
    if event.delivery_path not in _DELIVERY_PATHS:
        raise ValueError("delivery_path is invalid")
    resource_uri = _optional_text(event.resource_uri, "resource_uri", max_length=2048)
    resource_class = event.resource_class
    if resource_class is not None and resource_class not in _RESOURCE_CLASSES:
        raise ValueError("resource_class is invalid")
    server_origin = _optional_text(event.server_origin, "server_origin", max_length=256)
    if event.delivery_path == "kis_native" and any(
        value is not None for value in (resource_uri, resource_class, server_origin, event.digest_verified)
    ):
        raise ValueError("MCP resource attribution requires mcp_resource delivery_path")
    return SkillTelemetryEvent(
        event_name=event.event_name,
        source=event.source,
        skill_id=skill_id,
        snapshot_id=snapshot_id,
        content_sha256=content_sha256,
        project_id=project_id,
        activation_id=activation_id,
        request_id=request_id,
        outcome=str(event.outcome),
        duration_ms=_optional_metric(event.duration_ms, "duration_ms"),
        error_class=error_class,
        total_tokens=_optional_metric(event.total_tokens, "total_tokens"),
        tool_calls=_optional_metric(event.tool_calls, "tool_calls"),
        retries=_optional_metric(event.retries, "retries"),
        verification_passed=event.verification_passed,
        delivery_path=event.delivery_path,
        resource_uri=resource_uri,
        resource_class=resource_class,
        server_origin=server_origin,
        digest_verified=event.digest_verified,
        occurred_at=event.occurred_at or _timestamp(),
    )


class SkillTelemetryStore:
    def __init__(
        self,
        path: Path,
        *,
        max_events: int = 20_000,
        max_report_rows: int = 100,
        observability: RuntimeObservability | None = None,
    ) -> None:
        if min(max_events, max_report_rows) < 1:
            raise ValueError("skill telemetry limits must be positive")
        self.path = path.resolve()
        self.max_events = int(max_events)
        self.max_report_rows = int(max_report_rows)
        self.observability = observability
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=2.0)
        connection.execute("PRAGMA busy_timeout = 2000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    skill_id TEXT,
                    snapshot_id TEXT,
                    content_sha256 TEXT,
                    project_id TEXT,
                    activation_id TEXT,
                    request_id TEXT,
                    outcome TEXT NOT NULL,
                    duration_ms INTEGER,
                    error_class TEXT,
                    total_tokens INTEGER,
                    tool_calls INTEGER,
                    retries INTEGER,
                    verification_passed INTEGER,
                    delivery_path TEXT NOT NULL DEFAULT 'kis_native',
                    resource_uri TEXT,
                    resource_class TEXT,
                    server_origin TEXT,
                    digest_verified INTEGER
                )
                """
            )
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(skill_events)")
            }
            for name, declaration in (
                ("delivery_path", "TEXT NOT NULL DEFAULT 'kis_native'"),
                ("resource_uri", "TEXT"),
                ("resource_class", "TEXT"),
                ("server_origin", "TEXT"),
                ("digest_verified", "INTEGER"),
            ):
                if name not in existing_columns:
                    connection.execute(f"ALTER TABLE skill_events ADD COLUMN {name} {declaration}")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill_events_identity "
                "ON skill_events(skill_id, content_sha256, project_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill_events_activation "
                "ON skill_events(skill_id, activation_id, snapshot_id, content_sha256)"
            )

    def record(self, event: SkillTelemetryEvent) -> None:
        selected = _normalize_event(event)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_events (
                    occurred_at, event_name, source, skill_id, snapshot_id,
                    content_sha256, project_id, activation_id, request_id,
                    outcome, duration_ms, error_class, total_tokens, tool_calls,
                    retries, verification_passed, delivery_path, resource_uri,
                    resource_class, server_origin, digest_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    selected.occurred_at,
                    selected.event_name,
                    selected.source,
                    selected.skill_id,
                    selected.snapshot_id,
                    selected.content_sha256,
                    selected.project_id,
                    selected.activation_id,
                    selected.request_id,
                    selected.outcome,
                    selected.duration_ms,
                    selected.error_class,
                    selected.total_tokens,
                    selected.tool_calls,
                    selected.retries,
                    None if selected.verification_passed is None else int(selected.verification_passed),
                    selected.delivery_path,
                    selected.resource_uri,
                    selected.resource_class,
                    selected.server_origin,
                    None if selected.digest_verified is None else int(selected.digest_verified),
                ),
            )
            connection.execute(
                "DELETE FROM skill_events WHERE id <= COALESCE(("
                "SELECT id FROM skill_events ORDER BY id DESC LIMIT 1 OFFSET ?"
                "), -1)",
                (self.max_events,),
            )
        if self.observability is not None:
            self.observability.record_skill_activity(
                event_name=selected.event_name,
                source=selected.source,
                skill_id=selected.skill_id,
                snapshot_id=selected.snapshot_id,
                content_sha256=selected.content_sha256,
                project_id=selected.project_id,
                activation_id=selected.activation_id,
                request_id=selected.request_id,
                outcome=selected.outcome,
                duration_ms=selected.duration_ms,
                error_class=selected.error_class,
                total_tokens=selected.total_tokens,
                tool_calls=selected.tool_calls,
                retries=selected.retries,
                verification_passed=selected.verification_passed,
            )

    def has_observed_load(
        self,
        *,
        skill_id: str,
        activation_id: str,
        snapshot_id: str,
        content_sha256: str,
        project_id: str | None,
        delivery_path: str = "kis_native",
    ) -> bool:
        values = (
            _optional_id(skill_id, "skill_id"),
            _optional_id(activation_id, "activation_id"),
            _optional_id(snapshot_id, "snapshot_id"),
            content_sha256,
            _optional_id(project_id, "project_id"),
            _optional_id(project_id, "project_id"),
            delivery_path,
        )
        if _SHA256.fullmatch(content_sha256) is None:
            raise ValueError("content_sha256 must be a lowercase SHA-256 value")
        if delivery_path not in _DELIVERY_PATHS:
            raise ValueError("delivery_path is invalid")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM skill_events
                WHERE event_name = 'skill_loaded' AND source = 'observed'
                  AND skill_id = ? AND activation_id = ? AND snapshot_id = ?
                  AND content_sha256 = ?
                  AND ((project_id = ?) OR (project_id IS NULL AND ? IS NULL))
                  AND delivery_path = ?
                LIMIT 1
                """,
                values,
            ).fetchone()
        return row is not None

    def _filters(
        self,
        *,
        skill_id: str | None,
        project_id: str | None,
        content_sha256: str | None,
    ) -> tuple[str, list[str]]:
        clauses: list[str] = []
        values: list[str] = []
        if skill_id is not None:
            clauses.append("skill_id = ?")
            values.append(_optional_id(skill_id, "skill_id") or "")
        if project_id is not None:
            clauses.append("project_id = ?")
            values.append(_optional_id(project_id, "project_id") or "")
        if content_sha256 is not None:
            if _SHA256.fullmatch(content_sha256) is None:
                raise ValueError("content_sha256 must be a lowercase SHA-256 value")
            clauses.append("content_sha256 = ?")
            values.append(content_sha256)
        return (" WHERE " + " AND ".join(clauses) if clauses else "", values)

    def report(
        self,
        *,
        skill_id: str | None = None,
        project_id: str | None = None,
        content_sha256: str | None = None,
    ) -> SkillTelemetryReport:
        where, values = self._filters(
            skill_id=skill_id,
            project_id=project_id,
            content_sha256=content_sha256,
        )
        with self._connect() as connection:
            event_count = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM skill_events{where}", values
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT skill_id, content_sha256, project_id,
                  SUM(event_name = 'skill_discovered' AND outcome = 'success'),
                  SUM(event_name = 'skill_loaded' AND outcome = 'success'),
                  SUM(event_name = 'skill_resource_read' AND outcome = 'success'),
                  SUM(event_name = 'skill_evaluated' AND outcome = 'success'),
                  SUM(event_name IN ('skill_created', 'skill_improved') AND outcome = 'success'),
                  SUM(event_name = 'skill_applied' AND outcome = 'success'),
                  SUM(event_name = 'skill_completed' AND outcome = 'success'),
                  SUM(event_name = 'skill_failed'),
                  SUM(outcome != 'success'),
                  COUNT(duration_ms), SUM(duration_ms),
                  COUNT(total_tokens), SUM(total_tokens),
                  COUNT(tool_calls), SUM(tool_calls),
                  COUNT(retries), SUM(retries),
                  COUNT(verification_passed), SUM(verification_passed)
                FROM skill_events{where}
                GROUP BY skill_id, content_sha256, project_id
                ORDER BY skill_id, content_sha256, project_id
                LIMIT ?
                """,
                (*values, self.max_report_rows + 1),
            ).fetchall()
        truncated = len(rows) > self.max_report_rows
        groups = tuple(self._group(row) for row in rows[: self.max_report_rows])
        return SkillTelemetryReport(
            groups=groups,
            event_count=event_count,
            truncated=truncated,
        )

    def delivery_report(
        self,
        *,
        skill_id: str | None = None,
        project_id: str | None = None,
        content_sha256: str | None = None,
    ) -> SkillDeliveryTelemetryReport:
        where, values = self._filters(
            skill_id=skill_id,
            project_id=project_id,
            content_sha256=content_sha256,
        )
        connector = " AND " if where else " WHERE "
        meaningful_where = f"{where}{connector}skill_id IS NOT NULL AND content_sha256 IS NOT NULL"
        with self._connect() as connection:
            event_count = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM skill_events{meaningful_where}", values
                ).fetchone()[0]
            )
            catalogue_exposure_count = 0
            if not values:
                catalogue_exposure_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM skill_events "
                        "WHERE event_name = 'skill_catalogue_exposed' "
                        "AND delivery_path = 'mcp_resource'"
                    ).fetchone()[0]
                )
            rows = connection.execute(
                f"""
                SELECT skill_id, content_sha256, project_id, delivery_path,
                  SUM(event_name = 'skill_loaded' AND outcome = 'success'),
                  SUM(event_name = 'skill_resource_read' AND outcome = 'success'),
                  SUM(event_name = 'skill_applied' AND outcome = 'success'),
                  SUM(event_name = 'skill_completed' AND outcome = 'success'),
                  SUM(event_name = 'skill_failed'),
                  SUM(outcome != 'success'),
                  SUM(digest_verified = 1), SUM(digest_verified = 0)
                FROM skill_events{meaningful_where}
                GROUP BY skill_id, content_sha256, project_id, delivery_path
                ORDER BY skill_id, content_sha256, project_id, delivery_path
                LIMIT ?
                """,
                (*values, self.max_report_rows + 1),
            ).fetchall()
        truncated = len(rows) > self.max_report_rows
        selected_rows = list(rows[: self.max_report_rows])
        if truncated and selected_rows:
            boundary_identity = tuple(selected_rows[-1][:3])
            next_identity = tuple(rows[self.max_report_rows][:3])
            if boundary_identity == next_identity:
                selected_rows = [
                    row for row in selected_rows if tuple(row[:3]) != boundary_identity
                ]
        groups = tuple(self._delivery_group(row) for row in selected_rows)
        return SkillDeliveryTelemetryReport(
            groups=groups,
            comparisons=self._comparisons(groups),
            event_count=event_count,
            catalogue_exposure_count=catalogue_exposure_count,
            truncated=truncated,
        )

    @staticmethod
    def _group(row: tuple[object, ...]) -> SkillTelemetryGroup:
        return SkillTelemetryGroup(
            skill_id=row[0] if isinstance(row[0], str) else None,
            content_sha256=row[1] if isinstance(row[1], str) else None,
            project_id=row[2] if isinstance(row[2], str) else None,
            discovered_count=int(row[3] or 0),
            loaded_count=int(row[4] or 0),
            resource_read_count=int(row[5] or 0),
            evaluated_count=int(row[6] or 0),
            mutation_count=int(row[7] or 0),
            applied_count=int(row[8] or 0),
            completed_count=int(row[9] or 0),
            failed_count=int(row[10] or 0),
            error_count=int(row[11] or 0),
            duration_samples=int(row[12] or 0),
            total_duration_ms=int(row[13]) if row[13] is not None else None,
            token_samples=int(row[14] or 0),
            total_tokens=int(row[15]) if row[15] is not None else None,
            tool_call_samples=int(row[16] or 0),
            total_tool_calls=int(row[17]) if row[17] is not None else None,
            retry_samples=int(row[18] or 0),
            total_retries=int(row[19]) if row[19] is not None else None,
            verification_samples=int(row[20] or 0),
            verification_passes=int(row[21]) if row[21] is not None else None,
        )

    @staticmethod
    def _delivery_group(row: tuple[object, ...]) -> SkillDeliveryTelemetryGroup:
        return SkillDeliveryTelemetryGroup(
            skill_id=str(row[0]),
            content_sha256=str(row[1]),
            project_id=row[2] if isinstance(row[2], str) else None,
            delivery_path=str(row[3]),
            loaded_count=int(row[4] or 0),
            resource_read_count=int(row[5] or 0),
            applied_count=int(row[6] or 0),
            completed_count=int(row[7] or 0),
            failed_count=int(row[8] or 0),
            error_count=int(row[9] or 0),
            digest_verified_count=int(row[10] or 0),
            digest_failed_count=int(row[11] or 0),
        )

    @staticmethod
    def _comparisons(
        groups: tuple[SkillDeliveryTelemetryGroup, ...],
    ) -> tuple[SkillDeliveryComparison, ...]:
        by_identity: dict[tuple[str, str, str | None], dict[str, SkillDeliveryTelemetryGroup]] = {}
        for group in groups:
            key = (group.skill_id, group.content_sha256, group.project_id)
            by_identity.setdefault(key, {})[group.delivery_path] = group
        comparisons: list[SkillDeliveryComparison] = []
        for (skill_id, content_sha256, project_id), paths in sorted(
            by_identity.items(), key=lambda item: tuple(value or "" for value in item[0])
        ):
            native = paths.get("kis_native")
            mcp = paths.get("mcp_resource")
            if native is None:
                comparable, reason = False, "missing_kis_native"
            elif mcp is None:
                comparable, reason = False, "missing_mcp_resource"
            elif native.loaded_count < 1:
                comparable, reason = False, "missing_kis_native_load"
            elif mcp.loaded_count < 1:
                comparable, reason = False, "missing_mcp_resource_load"
            elif mcp.digest_failed_count:
                comparable, reason = False, "digest_verification_failed"
            elif mcp.digest_verified_count < 1:
                comparable, reason = False, "digest_unverified"
            else:
                comparable, reason = True, "matched_content_sha256"
            comparisons.append(
                SkillDeliveryComparison(
                    skill_id=skill_id,
                    content_sha256=content_sha256,
                    project_id=project_id,
                    comparable=comparable,
                    reason=reason,
                )
            )
        return tuple(comparisons)


__all__ = [
    "SkillDeliveryComparison",
    "SkillDeliveryTelemetryGroup",
    "SkillDeliveryTelemetryReport",
    "SkillTelemetryEvent",
    "SkillTelemetryGroup",
    "SkillTelemetryReport",
    "SkillTelemetryStore",
]
