from kis_mcp.skills.status import (
    degraded_skills_runtime_status,
    ready_skills_runtime_status,
)


def test_skills_runtime_status_formats_ready_and_degraded_states() -> None:
    ready = ready_skills_runtime_status()
    assert ready.state == "ready"
    assert ready.code is None
    assert ready.implementation_value() == "ready"

    degraded = degraded_skills_runtime_status("SKILLS_REFRESH_REJECTED")
    assert degraded.state == "degraded"
    assert degraded.code == "SKILLS_REFRESH_REJECTED"
    assert degraded.implementation_value() == "degraded:SKILLS_REFRESH_REJECTED"
