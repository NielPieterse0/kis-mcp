import asyncio
from dataclasses import replace
import shutil

from fastmcp import FastMCP
import pytest

from kis_mcp.capabilities.catalogue import CapabilityCatalogue
from kis_mcp.capabilities.runtime import CapabilityRuntimeState
from kis_mcp.capabilities.settings import load_capability_settings
from kis_mcp.capabilities.tools import register_capability_tools
from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.config import load_skills_config
from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.models import SkillCard
from kis_mcp.skills.platform import (
    active_skill_capability_contributions,
    register_platform_skills,
    skill_capability_contributions,
)
from kis_mcp.skills.service import SkillsService
from kis_mcp.skills.telemetry import SkillTelemetryStore


def test_production_settings_require_canonical_kis_mcp() -> None:
    assert load_skills_config().required_skills == ("kis-mcp",)


def test_unclassified_valid_skill_has_no_private_contribution() -> None:
    card = SkillCard(
        id="bayesian-modeler",
        summary="Valid shared skill without KIS capability metadata",
        category="uncategorized",
        capabilities=(),
        status="active",
    )
    assert skill_capability_contributions((card,), load_capability_settings()) == ()


def test_catalogue_requires_configured_kis_mcp(skills_config, make_skill) -> None:
    make_skill("bayesian-modeler")
    configured = replace(skills_config, required_skills=("kis-mcp",))
    with pytest.raises(SkillsError, match="SKILLS_REQUIRED_MISSING"):
        SkillCatalogue(configured)


def test_catalogue_accepts_required_and_unclassified_skills(skills_config, make_skill) -> None:
    make_skill("kis-mcp")
    make_skill("bayesian-modeler")
    catalogue = SkillCatalogue(replace(skills_config, required_skills=("kis-mcp",)))
    assert [item.id for item in catalogue.list_skills(limit=10).skills] == [
        "bayesian-modeler",
        "kis-mcp",
    ]


def test_active_skill_contributions_follow_refreshed_catalogue(skills_config, make_skill) -> None:
    make_skill("develop-code")
    make_skill("bayesian-modeler")
    catalogue = SkillCatalogue(skills_config)
    service = SkillsService(catalogue, backend=None)
    settings = load_capability_settings()

    initial = {
        item.contribution_id
        for item in active_skill_capability_contributions(service, settings)
    }
    assert "skill.develop-code" in initial
    assert "skill.bayesian-modeler" not in initial

    shutil.rmtree(skills_config.root / "develop-code")
    make_skill("github")
    catalogue.refresh_skills()

    refreshed = {
        item.contribution_id
        for item in active_skill_capability_contributions(service, settings)
    }
    assert "skill.develop-code" not in refreshed
    assert "skill.github" in refreshed
    assert catalogue.load_skill("github").skill.id == "github"


def test_internal_capability_enumeration_does_not_emit_discovery_telemetry(
    skills_config, make_skill, tmp_path, monkeypatch
) -> None:
    make_skill("develop-code")
    store = SkillTelemetryStore(tmp_path / "skills.sqlite3")
    service = SkillsService(SkillCatalogue(skills_config), backend=None, telemetry=store)
    monkeypatch.setattr(
        "kis_mcp.skills.platform.register_skills_tools",
        lambda server, telemetry=None: service,
    )

    registered_service, startup_cards = register_platform_skills(
        FastMCP("skill-startup-registration-test")
    )
    contributions = active_skill_capability_contributions(
        service, load_capability_settings()
    )

    assert registered_service is service
    assert any(card.id == "develop-code" for card in startup_cards)
    assert any(item.contribution_id == "skill.develop-code" for item in contributions)
    assert store.report().event_count == 0

    service.list_skills(limit=service.catalogue.config.limits.list_max_limit)
    report = store.report(skill_id="develop-code")
    assert report.event_count == 1
    assert report.groups[0].discovered_count == 1


def test_capability_search_reconciles_after_skill_refresh(skills_config, make_skill) -> None:
    make_skill("develop-code")
    catalogue = SkillCatalogue(skills_config)
    service = SkillsService(catalogue, backend=None)
    settings = load_capability_settings()

    def current():
        return active_skill_capability_contributions(service, settings)

    runtime = CapabilityRuntimeState.build(
        CapabilityCatalogue(current(), ()),
        settings,
        contributions_source=current,
    )
    server = FastMCP("skill-refresh-test")
    register_capability_tools(server, runtime)

    before = asyncio.run(
        server.call_tool("search_capabilities", {"query": "develop-code", "limit": 20})
    ).structured_content
    assert before is not None
    assert any(
        item["contribution_id"] == "skill.develop-code"
        for item in before["contributions"]
    )

    shutil.rmtree(skills_config.root / "develop-code")
    make_skill("github")
    catalogue.refresh_skills()

    removed = asyncio.run(
        server.call_tool("search_capabilities", {"query": "develop-code", "limit": 20})
    ).structured_content
    added = asyncio.run(
        server.call_tool("search_capabilities", {"query": "github", "limit": 20})
    ).structured_content
    assert removed is not None and added is not None
    assert all(
        item["contribution_id"] != "skill.develop-code"
        for item in removed["contributions"]
    )
    assert any(
        item["contribution_id"] == "skill.github"
        for item in added["contributions"]
    )
