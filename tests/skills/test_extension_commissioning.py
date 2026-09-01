from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from fastmcp import Client, FastMCP

from kis_mcp.mcp_extensions import McpExtensionCommissioningService, negotiated_extension_settings
from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.commissioning import (
    SEP2640_COMMISSIONING_PROFILE,
    Sep2640SkillsCommissioningProfile,
)
from kis_mcp.skills.delivery_telemetry import register_skill_delivery_telemetry
from kis_mcp.skills.sep2640 import (
    SEP2640_EXTENSION_ID,
    catalogue_skill_resource_set_fingerprint,
    register_sep2640_extension,
)
from kis_mcp.skills.telemetry import SkillTelemetryStore


def _commissioning_server(catalogue: SkillCatalogue, store: SkillTelemetryStore):
    server = FastMCP("skills-commissioning-test")
    service = McpExtensionCommissioningService(server)
    profile = Sep2640SkillsCommissioningProfile(catalogue, store)
    service.register_profile(profile)
    register_sep2640_extension(
        server,
        catalogue,
        store,
        server_identity_fingerprint=service.server_identity_fingerprint,
    )
    register_skill_delivery_telemetry(
        server,
        catalogue,
        store,
        server_identity_fingerprint=service.server_identity_fingerprint,
        extension_id=SEP2640_EXTENSION_ID,
        resource_set_fingerprint_resolver=lambda skill_id: catalogue_skill_resource_set_fingerprint(
            catalogue,
            skill_id,
            service.server_identity_fingerprint,
        ),
        negotiated_settings_resolver=negotiated_extension_settings,
        commissioning_receipt_validator=lambda receipt_id: service.is_active_receipt(
            receipt_id, SEP2640_COMMISSIONING_PROFILE
        ),
    )
    return service
def test_sep2640_live_commissioning_traverses_dispatch_and_records_correlated_evidence(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill(
        "alpha-skill",
        extra_files={"references/note.md": "bounded\n"},
    )
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    service = _commissioning_server(catalogue, store)

    receipt = asyncio.run(service.commission(SEP2640_COMMISSIONING_PROFILE))

    assert receipt.overall == "PASS", (receipt.steps, receipt.evidence)
    assert receipt.evidence["skill_id"] == "alpha-skill"
    assert receipt.evidence["canonical_skill_uri"] == "skill:///alpha-skill/SKILL.md"
    assert receipt.evidence["negative_negotiation"] == "METHOD_NOT_FOUND"
    assert {step.step for step in receipt.steps} == {
        "server/discover",
        "skills/list",
        "skills/get",
        "resources/read",
        "resources/directory/read",
        "skills/list:unnegotiated",
        "skills/get:unnegotiated",
        "resources/directory/read:unnegotiated",
    }

    with sqlite3.connect(store.path) as connection:
        rows = connection.execute(
            "SELECT event_name, commissioning_receipt_id, protocol_version, extension_id, "
            "server_identity_fingerprint, canonical_skill_uri, integrity_proof "
            "FROM skill_events ORDER BY id"
        ).fetchall()
    names = [row[0] for row in rows]
    assert "skills_list_observed" in names
    assert "skills_get_observed" in names
    assert "skill_directory_read" in names
    assert "skill_loaded" in names
    assert "skills_negative_negotiation_observed" in names
    assert "skill_commissioned" in names
    correlated = [row for row in rows if row[1] == receipt.receipt_id]
    assert correlated
    assert all(row[2] == receipt.protocol_version for row in correlated if row[2])
    assert all(row[3] == SEP2640_EXTENSION_ID for row in correlated if row[3])
    assert all(row[4] == receipt.server_identity_fingerprint for row in correlated if row[4])

    report = store.delivery_report(skill_id="alpha-skill")
    assert report.protocol_observation_count >= 2
    assert report.negative_negotiation_count == 1
    [mcp_group] = [group for group in report.groups if group.delivery_path == "mcp_resource"]
    assert mcp_group.commissioning_correlated_load_count == 1
    assert mcp_group.live_commissioned_count == 1
    [comparison] = report.comparisons
    assert comparison.mcp_commissioned is True
    assert comparison.commissioning_reason == "live_commissioning_correlated"


def test_ordinary_resource_read_is_not_misattributed_to_sep2640(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    service = _commissioning_server(catalogue, store)

    async def read_unnegotiated() -> None:
        async with Client(service.server, mode="2026-07-28") as client:
            await client.read_resource("skill:///alpha-skill/SKILL.md")

    asyncio.run(read_unnegotiated())

    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT extension_id, extension_settings_fingerprint, commissioning_receipt_id "
            "FROM skill_events WHERE event_name = 'skill_loaded'"
        ).fetchone()
    assert row == (None, None, None)


def test_completed_receipt_cannot_be_reused_as_commissioning_correlation(
    skills_config, make_skill, tmp_path: Path
) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    service = _commissioning_server(catalogue, store)
    receipt = asyncio.run(service.commission(SEP2640_COMMISSIONING_PROFILE))
    assert service.is_active_receipt(receipt.receipt_id, SEP2640_COMMISSIONING_PROFILE) is False

    async def replay_receipt() -> None:
        async with Client(service.server, mode="2026-07-28") as client:
            await client.read_resource(
                "skill:///alpha-skill/SKILL.md",
                meta={"kis_commissioning_receipt_id": receipt.receipt_id},
            )

    asyncio.run(replay_receipt())
    with sqlite3.connect(store.path) as connection:
        replay = connection.execute(
            "SELECT commissioning_receipt_id FROM skill_events "
            "WHERE event_name = 'skill_loaded' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert replay == (None,)


def test_sep2640_receipt_fails_closed_after_canonical_resource_set_drift(
    skills_config, make_skill, tmp_path: Path
) -> None:
    root = make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    service = _commissioning_server(catalogue, store)
    receipt = asyncio.run(service.commission(SEP2640_COMMISSIONING_PROFILE))

    assert service.receipt_matches_current(receipt) is True
    reference = root / "references" / "new.md"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text("new evidence\n", encoding="utf-8")
    catalogue.refresh_skills()

    assert service.receipt_matches_current(receipt) is False
