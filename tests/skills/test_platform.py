from types import SimpleNamespace

from fastmcp import FastMCP

from kis_mcp.capabilities.contracts import ReadinessState
from kis_mcp.skills.platform import (
    current_skill_capability_contributions,
    register_platform_skills,
    skills_runtime_status,
)


def test_degraded_skills_service_exposes_catalogue_contribution() -> None:
    service = SimpleNamespace(failure_code="SKILLS_REFRESH_REJECTED")
    status = skills_runtime_status(service)
    contributions = current_skill_capability_contributions(
        service,
        (),
        None,  # type: ignore[arg-type]
    )

    assert status.implementation_value() == "degraded:SKILLS_REFRESH_REJECTED"
    assert len(contributions) == 1
    contribution = contributions[0]
    assert contribution.contribution_id == "skills.catalogue"
    assert contribution.capabilities == ("skills.catalogue",)
    readiness = contribution.readiness_probe()
    assert readiness.contribution_id == "skills.catalogue"
    assert readiness.state is ReadinessState.DEGRADED
    assert "SKILLS_REFRESH_REJECTED" in readiness.summary


def test_platform_registration_preserves_two_value_contract_when_degraded(monkeypatch) -> None:
    service = SimpleNamespace(failure_code="SKILLS_FRONTMATTER_INVALID")
    monkeypatch.setattr(
        "kis_mcp.skills.platform.register_skills_tools",
        lambda server, telemetry=None: service,
    )

    registered_service, startup_cards = register_platform_skills(
        FastMCP("skills-degraded-platform-test")
    )

    assert registered_service is service
    assert startup_cards == ()
    assert skills_runtime_status(registered_service).implementation_value() == (
        "degraded:SKILLS_FRONTMATTER_INVALID"
    )
