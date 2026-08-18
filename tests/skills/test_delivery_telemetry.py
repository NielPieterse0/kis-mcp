from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from fastmcp import Client, FastMCP

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.delivery_telemetry import register_skill_delivery_telemetry
from kis_mcp.skills.resources import register_skill_resources
from kis_mcp.skills.telemetry import SkillTelemetryEvent, SkillTelemetryStore


def _server(catalogue: SkillCatalogue, store: SkillTelemetryStore) -> FastMCP:
    server = FastMCP("kis-skills-origin")
    register_skill_resources(server, catalogue)
    register_skill_delivery_telemetry(server, catalogue, store)
    return server


async def _list_only(server: FastMCP) -> None:
    async with Client(server) as client:
        await client.list_resources()
        await client.list_resource_templates()


async def _read(server: FastMCP, uri: str, *, meta: dict | None = None):
    async with Client(server) as client:
        return await client.read_resource(uri, meta=meta)


def test_passive_resource_enumeration_records_no_skill_use(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    server = _server(SkillCatalogue(skills_config), store)

    asyncio.run(_list_only(server))

    report = store.delivery_report(skill_id="alpha-skill")
    assert report.event_count == 0
    assert report.catalogue_exposure_count == 0
    assert report.groups == ()


def test_catalogue_read_is_exposure_not_skill_use(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    server = _server(SkillCatalogue(skills_config), store)

    asyncio.run(_read(server, "skill:///"))

    report = store.delivery_report(skill_id="alpha-skill")
    assert report.event_count == 0
    assert store.delivery_report().catalogue_exposure_count == 1
    assert report.groups == ()


def test_mcp_entrypoint_records_delivery_identity_and_correlation(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    server = _server(catalogue, store)

    asyncio.run(
        _read(
            server,
            "skill:///alpha-skill/SKILL.md",
            meta={"kis_activation_id": "activation-1", "kis_project_id": "project-alpha"},
        )
    )

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT event_name, skill_id, content_sha256, project_id, activation_id, "
            "delivery_path, resource_uri, resource_class, server_origin, digest_verified "
            "FROM skill_events WHERE event_name = 'skill_loaded'"
        ).fetchone()
    assert row == (
        "skill_loaded",
        "alpha-skill",
        catalogue.load_skill("alpha-skill").sha256,
        "project-alpha",
        "activation-1",
        "mcp_resource",
        "skill:///alpha-skill/SKILL.md",
        "SKILL.md",
        "kis-skills-origin",
        1,
    )


def test_same_hash_compares_native_and_mcp_delivery(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    version = catalogue.load_skill("alpha-skill")
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    store.record(
        SkillTelemetryEvent(
            event_name="skill_loaded",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id=version.snapshot_id,
            content_sha256=version.sha256,
            project_id="project-alpha",
            activation_id="native-1",
        )
    )
    server = _server(catalogue, store)
    asyncio.run(
        _read(
            server,
            "skill:///alpha-skill/SKILL.md",
            meta={"kis_activation_id": "mcp-1", "kis_project_id": "project-alpha"},
        )
    )

    report = store.delivery_report(skill_id="alpha-skill", project_id="project-alpha")
    comparison = report.comparisons[0]
    assert comparison.content_sha256 == version.sha256
    assert comparison.comparable is True
    assert comparison.reason == "matched_content_sha256"
    assert {group.delivery_path for group in report.groups} == {"kis_native", "mcp_resource"}


def test_different_hashes_are_not_valid_cross_path_comparisons(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    for delivery_path, digest, verified in (
        ("kis_native", "a" * 64, None),
        ("mcp_resource", "b" * 64, True),
    ):
        store.record(
            SkillTelemetryEvent(
                event_name="skill_loaded",
                source="observed",
                skill_id="alpha-skill",
                snapshot_id="snapshot-1",
                content_sha256=digest,
                delivery_path=delivery_path,
                digest_verified=verified,
            )
        )

    report = store.delivery_report(skill_id="alpha-skill")

    assert len(report.comparisons) == 2
    assert all(item.comparable is False for item in report.comparisons)
    assert {item.reason for item in report.comparisons} == {
        "missing_kis_native",
        "missing_mcp_resource",
    }


def test_failed_digest_is_explicitly_non_comparable(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    for delivery_path, verified in (("kis_native", None), ("mcp_resource", False)):
        store.record(
            SkillTelemetryEvent(
                event_name="skill_loaded",
                source="observed",
                skill_id="alpha-skill",
                snapshot_id="snapshot-1",
                content_sha256="a" * 64,
                delivery_path=delivery_path,
                digest_verified=verified,
            )
        )

    comparison = store.delivery_report(skill_id="alpha-skill").comparisons[0]
    assert comparison.comparable is False
    assert comparison.reason == "digest_verification_failed"


def test_comparison_requires_successful_load_on_both_delivery_paths(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    digest = "a" * 64
    store.record(
        SkillTelemetryEvent(
            event_name="skill_evaluated",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
        )
    )
    store.record(
        SkillTelemetryEvent(
            event_name="skill_resource_read",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
            delivery_path="mcp_resource",
            resource_uri="skill:///alpha-skill/resource?path=references%2Fnote.md",
            resource_class="reference",
            server_origin="kis-test",
            digest_verified=True,
        )
    )

    comparison = store.delivery_report(skill_id="alpha-skill").comparisons[0]
    assert comparison.comparable is False
    assert comparison.reason == "missing_kis_native_load"


def test_mcp_supporting_read_does_not_substitute_for_mcp_entrypoint_load(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    digest = "a" * 64
    store.record(
        SkillTelemetryEvent(
            event_name="skill_loaded",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
        )
    )
    store.record(
        SkillTelemetryEvent(
            event_name="skill_resource_read",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
            delivery_path="mcp_resource",
            resource_uri="skill:///alpha-skill/resource?path=references%2Fnote.md",
            resource_class="reference",
            server_origin="kis-test",
            digest_verified=True,
        )
    )

    comparison = store.delivery_report(skill_id="alpha-skill").comparisons[0]
    assert comparison.comparable is False
    assert comparison.reason == "missing_mcp_resource_load"


def test_delivery_telemetry_does_not_reread_canonical_resource(
    skills_config, make_skill, tmp_path: Path, monkeypatch
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    calls = 0
    original = catalogue.read_skill_resource_bytes

    def counted(skill_id: str, relative_path: str) -> bytes:
        nonlocal calls
        calls += 1
        return original(skill_id, relative_path)

    monkeypatch.setattr(catalogue, "read_skill_resource_bytes", counted)
    server = _server(catalogue, store)

    asyncio.run(_read(server, "skill:///alpha-skill/SKILL.md"))

    assert calls == 1
    assert store.delivery_report(skill_id="alpha-skill").groups[0].digest_verified_count == 1


def test_telemetry_persistence_failure_does_not_fail_resource_delivery(
    skills_config, make_skill, tmp_path: Path, monkeypatch
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")

    def fail_record(_event) -> None:
        raise RuntimeError("telemetry unavailable")

    monkeypatch.setattr(store, "record", fail_record)
    server = _server(catalogue, store)

    result = asyncio.run(_read(server, "skill:///alpha-skill/SKILL.md"))

    assert len(result) == 1


def test_delivery_report_drops_identity_split_by_row_bound(tmp_path: Path) -> None:
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3", max_report_rows=1)
    digest = "a" * 64
    store.record(
        SkillTelemetryEvent(
            event_name="skill_loaded",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
        )
    )
    store.record(
        SkillTelemetryEvent(
            event_name="skill_loaded",
            source="observed",
            skill_id="alpha-skill",
            snapshot_id="snapshot-1",
            content_sha256=digest,
            delivery_path="mcp_resource",
            resource_uri="skill:///alpha-skill/SKILL.md",
            resource_class="SKILL.md",
            server_origin="kis-test",
            digest_verified=True,
        )
    )

    report = store.delivery_report(skill_id="alpha-skill")

    assert report.truncated is True
    assert report.groups == ()
    assert report.comparisons == ()
