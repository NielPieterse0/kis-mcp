from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from fastmcp import FastMCP
from fastmcp.resources import ResourceSecurity

from .catalogue import SkillCatalogue
from .errors import SkillsError

SKILLS_RESOURCE_INDEX_URI = "skill:///"
SKILLS_RESOURCE_INDEX_TEMPLATE = "skill:///catalogue{?cursor}"
SKILL_ENTRYPOINT_TEMPLATE = "skill:///{skill_id}/SKILL.md"
SKILL_RESOURCE_TEMPLATE = "skill:///{skill_id}/resource{?path}"


def _catalogue_index(
    catalogue: SkillCatalogue,
    *,
    cursor: str | None = None,
) -> dict[str, Any]:
    page = catalogue.list_skills(
        limit=catalogue.config.limits.list_max_limit,
        cursor=cursor,
    )
    skills: list[dict[str, object]] = []
    for card in page.skills:
        loaded = catalogue.load_skill(card.id)
        skills.append(
            {
                "skill_id": card.id,
                "uri": f"skill:///{card.id}/SKILL.md",
                "sha256": loaded.sha256,
                "file_count": loaded.file_count,
            }
        )
    next_uri = (
        f"skill:///catalogue?cursor={quote(page.next_cursor, safe='')}"
        if page.next_cursor is not None
        else None
    )
    return {
        "schema_version": 1,
        "snapshot_id": catalogue.snapshot_id,
        "skill_count": page.skill_count,
        "skills": skills,
        "truncated": page.next_cursor is not None,
        "next_uri": next_uri,
    }


def register_skill_resources(server: FastMCP, catalogue: SkillCatalogue) -> None:
    """Register the canonical Skills snapshot as read-only MCP resources."""

    @server.resource(
        SKILLS_RESOURCE_INDEX_URI,
        name="KIS Skills Catalogue",
        description="Deterministic index of canonical KIS Skills entrypoint resources.",
        mime_type="application/json",
    )
    def skills_resource_index() -> str:
        return json.dumps(
            _catalogue_index(catalogue),
            sort_keys=True,
            separators=(",", ":"),
        )

    @server.resource(
        SKILLS_RESOURCE_INDEX_TEMPLATE,
        name="KIS Skills Catalogue Page",
        description="Bounded continuation page for the canonical Skills resource index.",
        mime_type="application/json",
    )
    def skills_resource_index_page(cursor: str = "") -> str:
        return json.dumps(
            _catalogue_index(catalogue, cursor=cursor or None),
            sort_keys=True,
            separators=(",", ":"),
        )

    @server.resource(
        SKILL_ENTRYPOINT_TEMPLATE,
        name="KIS Skill Entrypoint",
        description="Exact canonical SKILL.md bytes from the active validated snapshot.",
        mime_type="text/markdown",
    )
    def skill_entrypoint_resource(skill_id: str) -> bytes:
        return catalogue.read_skill_resource_bytes(skill_id, "SKILL.md")

    @server.resource(
        SKILL_RESOURCE_TEMPLATE,
        name="KIS Skill Resource",
        description=(
            "Exact supporting resource bytes from the active validated snapshot; "
            "scripts and assets are data only and are never executed."
        ),
        mime_type="application/octet-stream",
        security=ResourceSecurity(exempt_params={"path"}),
    )
    def skill_supporting_resource(skill_id: str, path: str = "") -> bytes:
        if path == "SKILL.md":
            raise SkillsError(
                "SKILLS_RESOURCE_URI_INVALID",
                "SKILL.md has the canonical entrypoint resource URI",
                subject=path,
            )
        return catalogue.read_skill_resource_bytes(skill_id, path)


__all__ = [
    "SKILLS_RESOURCE_INDEX_TEMPLATE",
    "SKILLS_RESOURCE_INDEX_URI",
    "SKILL_ENTRYPOINT_TEMPLATE",
    "SKILL_RESOURCE_TEMPLATE",
    "register_skill_resources",
]
