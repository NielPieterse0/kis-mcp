from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastmcp import FastMCP

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.config import SkillsConfig
from kis_mcp.skills.service import SkillsService
from kis_mcp.skills.tools import SKILLS_TOOL_NAMES, register_skills_tools


class FilesystemBackend:
    async def create_directory(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=False)

    async def write_text(self, path: str, content: str) -> None:
        Path(path).write_bytes(content.encode("utf-8"))

    async def move(self, source: str, destination: str) -> None:
        Path(source).replace(destination)

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        target = Path(path)
        current = target.read_bytes().decode("utf-8")
        if current.count(old_string) != 1:
            raise RuntimeError("replacement count mismatch")
        target.write_bytes(current.replace(old_string, new_string).encode("utf-8"))


def _server(skills_config: SkillsConfig) -> FastMCP:
    server = FastMCP("skills-test")
    service = SkillsService(SkillCatalogue(skills_config), FilesystemBackend())
    returned = register_skills_tools(server, service=service)
    assert returned is service
    return server


def test_register_skills_tools_exposes_exact_eleven_operation_names(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill("alpha-skill")
    server = _server(skills_config)

    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert names == set(SKILLS_TOOL_NAMES)
    assert SKILLS_TOOL_NAMES == (
        "list_skills",
        "search_skills",
        "load_skill",
        "search_skill_files",
        "read_skill_file",
        "refresh_skills",
        "evaluate_skill",
        "create_skill",
        "improve_skill",
        "record_skill_outcome",
        "skill_telemetry_report",
    )
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name["list_skills"].parameters["properties"]) == {"limit", "cursor"}
    assert set(by_name["improve_skill"].parameters["properties"]) == {
        "skill_id",
        "relative_path",
        "expected_sha256",
        "content",
    }
    assert set(by_name["load_skill"].parameters["properties"]) == {
        "skill_id",
        "activation_id",
        "project_id",
    }
    assert set(by_name["read_skill_file"].parameters["properties"]) == {
        "skill_id",
        "relative_path",
        "activation_id",
        "project_id",
    }
    assert set(by_name["record_skill_outcome"].parameters["properties"]) == {
        "skill_id",
        "activation_id",
        "snapshot_id",
        "content_sha256",
        "project_id",
        "phase",
        "duration_ms",
        "total_tokens",
        "tool_calls",
        "retries",
        "verification_passed",
    }


def test_invalid_catalogue_does_not_block_server_construction(
    skills_config: SkillsConfig,
) -> None:
    broken = skills_config.root / "broken-skill"
    broken.mkdir()
    (broken / "SKILL.md").write_text("# missing frontmatter\n", encoding="utf-8")
    server = FastMCP("skills-unavailable-test")

    register_skills_tools(server, config=skills_config)
    tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in tools} == set(SKILLS_TOOL_NAMES)
    with pytest.raises(Exception, match="SKILLS_REFRESH_REJECTED"):
        asyncio.run(server.call_tool("list_skills", {}))


def test_registered_read_tools_return_structured_versioned_records(
    skills_config: SkillsConfig, make_skill
) -> None:
    make_skill(
        "alpha-skill",
        extra_files={"references/note.md": "bounded evidence"},
    )
    server = _server(skills_config)

    listed = asyncio.run(server.call_tool("list_skills", {}))
    loaded = asyncio.run(
        server.call_tool("load_skill", {"skill_id": "alpha-skill"})
    )
    searched = asyncio.run(
        server.call_tool("search_skills", {"query": "alpha"})
    )

    assert listed.structured_content["skills"][0]["id"] == "alpha-skill"
    assert listed.structured_content["schema_version"] == 1
    assert loaded.structured_content["skill"]["id"] == "alpha-skill"
    assert loaded.structured_content["file_count"] == 2
    assert searched.structured_content["skills"][0]["id"] == "alpha-skill"
    assert searched.structured_content["snapshot_id"] == listed.structured_content[
        "snapshot_id"
    ]


def test_registered_mutation_tools_create_and_improve_skill(
    skills_config: SkillsConfig,
) -> None:
    server = _server(skills_config)
    created_content = "---\nname: new-skill\ndescription: New skill\n---\n# New\n"

    created = asyncio.run(
        server.call_tool(
            "create_skill",
            {"skill_id": "new-skill", "skill_md": created_content},
        )
    )
    loaded = asyncio.run(
        server.call_tool("load_skill", {"skill_id": "new-skill"})
    )
    improved_content = created_content.replace("New skill", "Improved skill")
    improved = asyncio.run(
        server.call_tool(
            "improve_skill",
            {
                "skill_id": "new-skill",
                "relative_path": "SKILL.md",
                "expected_sha256": loaded.structured_content["sha256"],
                "content": improved_content,
            },
        )
    )

    assert created.structured_content["changed_state"] is True
    assert improved.structured_content["before_sha256"] == loaded.structured_content[
        "sha256"
    ]
    assert asyncio.run(
        server.call_tool("load_skill", {"skill_id": "new-skill"})
    ).structured_content["skill"]["summary"] == "Improved skill"


def test_registered_tools_surface_corrective_skills_error(
    skills_config: SkillsConfig,
) -> None:
    server = _server(skills_config)

    with pytest.raises(Exception, match="SKILLS_UNKNOWN"):
        asyncio.run(server.call_tool("load_skill", {"skill_id": "missing-skill"}))
