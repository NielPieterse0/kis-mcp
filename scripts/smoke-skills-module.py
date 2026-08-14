from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from kis_mcp.server import build_server
from kis_mcp.skills import SKILLS_TOOL_NAMES
from kis_mcp.skills.config import APPROVED_SKILLS_ROOT


async def _call(server: Any, name: str, arguments: dict[str, object]) -> dict[str, Any]:
    result = await server.call_tool(name, arguments)
    if getattr(result, "is_error", False):
        detail = "; ".join(
            str(getattr(item, "text", "")) for item in getattr(result, "content", ())
        )
        raise RuntimeError(f"SKILLS_SMOKE_TOOL_FAILED: {name}: {detail}")
    structured = getattr(result, "structured_content", None)
    if not isinstance(structured, dict):
        raise RuntimeError(f"SKILLS_SMOKE_RESULT_INVALID: {name} returned no structured record")
    return structured


async def _dispatch(
    server: Any, name: str, arguments: dict[str, object]
) -> dict[str, Any]:
    described = await _call(server, "describe_capability", {"capability_id": name})
    operations = described.get("operations")
    if not isinstance(operations, list) or len(operations) != 1:
        raise RuntimeError(f"SKILLS_SMOKE_CAPABILITY_MISSING: {name}")
    surface = operations[0].get("execution_surface")
    if surface not in {"execute_read_action", "execute_change_action"}:
        raise RuntimeError(f"SKILLS_SMOKE_CAPABILITY_EFFECT_INVALID: {name}: {surface}")
    return await _call(
        server,
        surface,
        {"operation": name, "arguments": arguments},
    )


async def main(server: Any) -> None:
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    if set(SKILLS_TOOL_NAMES).intersection(names):
        raise RuntimeError("SKILLS_SMOKE_DIRECT_SURFACE: Skills tools must remain discoverable long-tail")
    if "give_feedback_to_desktop_commander" in names:
        raise RuntimeError("SKILLS_SMOKE_NETWORK_SURFACE: feedback tool must remain hidden")

    listed = await _dispatch(server, "list_skills", {"limit": 100})
    cards = listed.get("skills")
    if not isinstance(cards, list) or not any(
        isinstance(item, dict) and item.get("id") == "modularity-assessment"
        for item in cards
    ):
        raise RuntimeError("SKILLS_SMOKE_CATALOGUE_INVALID: modularity-assessment missing")
    activation_id = f"skills-smoke-{uuid.uuid4().hex[:12]}"
    loaded = await _dispatch(
        server,
        "load_skill",
        {
            "skill_id": "modularity-assessment",
            "activation_id": activation_id,
            "project_id": "kis-mcp",
        },
    )
    evaluated = await _dispatch(
        server, "evaluate_skill", {"skill_id": "modularity-assessment"}
    )
    if loaded.get("sha256") != evaluated.get("evidence", {}).get(
        "entrypoint_sha256"
    ):
        raise RuntimeError("SKILLS_SMOKE_EVIDENCE_MISMATCH: entrypoint hash differs")
    await _dispatch(
        server,
        "record_skill_outcome",
        {
            "skill_id": "modularity-assessment",
            "activation_id": activation_id,
            "snapshot_id": loaded["snapshot_id"],
            "content_sha256": loaded["sha256"],
            "project_id": "kis-mcp",
            "phase": "completed",
            "verification_passed": True,
        },
    )
    telemetry = await _dispatch(
        server,
        "skill_telemetry_report",
        {
            "skill_id": "modularity-assessment",
            "project_id": "kis-mcp",
            "content_sha256": loaded["sha256"],
        },
    )
    groups = telemetry.get("groups")
    if not isinstance(groups, list) or not any(
        isinstance(item, dict)
        and item.get("loaded_count", 0) >= 1
        and item.get("completed_count", 0) >= 1
        for item in groups
    ):
        raise RuntimeError("SKILLS_SMOKE_TELEMETRY_MISSING: correlated evidence absent")

    skill_id = f"kis-mcp-smoke-{uuid.uuid4().hex[:12]}"
    target = Path(APPROVED_SKILLS_ROOT) / skill_id
    created = False
    quarantined: dict[str, Any] | None = None
    original_content = (
        "---\n"
        f"name: {skill_id}\n"
        "description: Temporary kis-mcp Skills write smoke.\n"
        "category: verification\n"
        "capabilities: [read, write]\n"
        "status: active\n"
        "---\n\n"
        "# Skills smoke\n"
    )
    improved_content = original_content.replace(
        "Temporary kis-mcp Skills write smoke.",
        "Improved temporary kis-mcp Skills write smoke.",
    )
    try:
        created_record = await _dispatch(
            server,
            "create_skill",
            {"skill_id": skill_id, "skill_md": original_content},
        )
        created = True
        loaded_created = await _dispatch(server, "load_skill", {"skill_id": skill_id})
        if loaded_created.get("sha256") != created_record.get("after_sha256"):
            raise RuntimeError("SKILLS_SMOKE_CREATE_MISMATCH: created hash differs")

        improved_record = await _dispatch(
            server,
            "improve_skill",
            {
                "skill_id": skill_id,
                "relative_path": "SKILL.md",
                "expected_sha256": loaded_created["sha256"],
                "content": improved_content,
            },
        )
        loaded_improved = await _dispatch(server, "load_skill", {"skill_id": skill_id})
        if (
            loaded_improved.get("sha256") != improved_record.get("after_sha256")
            or loaded_improved.get("skill", {}).get("summary")
            != "Improved temporary kis-mcp Skills write smoke."
        ):
            raise RuntimeError("SKILLS_SMOKE_IMPROVE_MISMATCH: improved skill differs")
    finally:
        if target.exists():
            quarantined = await _call(
                server, "kis_quarantine_path", {"path": str(target)}
            )
            await _dispatch(server, "refresh_skills", {})

    if not created or quarantined is None:
        raise RuntimeError("SKILLS_SMOKE_RECOVERY_FAILED: smoke skill was not quarantined")

    print(
        json.dumps(
            {
                "ok": True,
                "tool_count": len(names),
                "skills_tool_count": len(SKILLS_TOOL_NAMES),
                "catalogue_skill_count": listed.get("skill_count"),
                "catalogue_snapshot_id": listed.get("snapshot_id"),
                "loaded_skill": "modularity-assessment",
                "write_smoke_skill": skill_id,
                "quarantine_operation_id": quarantined.get("operation_id"),
                "policy_rules": ["HR-001", "HR-002", "HR-003"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main(build_server()))
