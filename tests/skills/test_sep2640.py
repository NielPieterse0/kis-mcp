from __future__ import annotations

import asyncio
import hashlib

from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from mcp.shared.exceptions import MCPError
from mcp_types import METHOD_NOT_FOUND

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.sep2640 import (
    SEP2640_EXTENSION_ID,
    ResourcesDirectoryReadParams,
    Sep2640SkillsExtension,
    SkillsGetParams,
    SkillsListParams,
    register_sep2640_extension,
    skill_requires_reapproval,
    skill_resource_set_fingerprint,
    verify_advertised_skill_resource,
)
from kis_mcp.skills.errors import SkillsError


def _server(catalogue: SkillCatalogue) -> FastMCP:
    server = FastMCP("sep2640-test")
    register_sep2640_extension(server, catalogue)
    return server


def _extension(server: FastMCP) -> Sep2640SkillsExtension:
    return server._extensions[SEP2640_EXTENSION_ID]


def _ctx(*, negotiated: bool = True):
    extensions = {SEP2640_EXTENSION_ID: {}} if negotiated else {}
    return SimpleNamespace(
        params={
            "_meta": {
                "io.modelcontextprotocol/clientCapabilities": {"extensions": extensions}
            }
        }
    )


def test_registers_draft_extension_capability(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    extension = _extension(server)
    assert extension.settings()["directoryRead"] is True
    capabilities = server._mcp_server.get_capabilities(protocol_version="2026-07-28")
    assert capabilities.extensions[SEP2640_EXTENSION_ID]["directoryRead"] is True


def test_skills_list_returns_complete_digest_bound_entries(skills_config, make_skill) -> None:
    root = make_skill(
        "alpha-skill",
        extra_files={"references/note.md": "bounded evidence\n"},
    )
    catalogue = SkillCatalogue(skills_config)
    server = _server(catalogue)

    result = asyncio.run(_extension(server)._skills_list(_ctx(), SkillsListParams()))
    [entry] = result.skills

    assert str(entry.uri) == "skill:///alpha-skill/SKILL.md"
    assert entry.frontmatter["name"] == "alpha-skill"
    assert entry.frontmatter["description"]
    assert {(str(item.uri), item.digest, item.size) for item in entry.resources} == {
        (
            "skill:///alpha-skill/SKILL.md",
            "sha256:" + hashlib.sha256((root / "SKILL.md").read_bytes()).hexdigest(),
            len((root / "SKILL.md").read_bytes()),
        ),
        (
            "skill:///alpha-skill/references/note.md",
            "sha256:" + hashlib.sha256((root / "references" / "note.md").read_bytes()).hexdigest(),
            len((root / "references" / "note.md").read_bytes()),
        ),
    }
    payload = result.model_dump(by_alias=True)
    assert payload["resultType"] == "complete"
    assert payload["ttlMs"] == 0
    assert payload["cacheScope"] == "private"


def test_skills_get_uses_uri_identity_independent_of_listing(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    result = asyncio.run(
        _extension(server)._skills_get(
            _ctx(), SkillsGetParams(uri="skill:///alpha-skill/SKILL.md")
        )
    )

    assert str(result.skill.uri) == "skill:///alpha-skill/SKILL.md"
    assert result.skill.frontmatter["name"] == "alpha-skill"


def test_direct_supporting_resource_uri_is_readable(skills_config, make_skill) -> None:
    root = make_skill("alpha-skill", extra_files={"references/note.md": "direct\n"})
    server = _server(SkillCatalogue(skills_config))

    content = asyncio.run(server.read_resource("skill:///alpha-skill/references/note.md"))

    assert content.contents[0].content == (root / "references" / "note.md").read_bytes()


def test_directory_read_returns_direct_children_only(skills_config, make_skill) -> None:
    make_skill(
        "alpha-skill",
        extra_files={
            "references/note.md": "note\n",
            "references/deep/other.md": "deep\n",
            "scripts/check.py": "print('x')\n",
        },
    )
    server = _server(SkillCatalogue(skills_config))

    root_result = asyncio.run(
        _extension(server)._directory_read(
            _ctx(), ResourcesDirectoryReadParams(uri="skill:///alpha-skill/")
        )
    )
    reference_result = asyncio.run(
        _extension(server)._directory_read(
            _ctx(), ResourcesDirectoryReadParams(uri="skill:///alpha-skill/references/")
        )
    )

    assert {(item.name, item.mime_type) for item in root_result.resources} == {
        ("SKILL.md", "text/markdown"),
        ("references", "inode/directory"),
        ("scripts", "inode/directory"),
    }
    assert {(item.name, item.mime_type) for item in reference_result.resources} == {
        ("deep", "inode/directory"),
        ("note.md", "text/markdown"),
    }


def test_extension_methods_require_request_negotiation(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    with pytest.raises(MCPError) as exc_info:
        asyncio.run(_extension(server)._skills_list(_ctx(negotiated=False), SkillsListParams()))

    assert exc_info.value.error.code == METHOD_NOT_FOUND


def test_direct_resource_read_fails_closed_after_snapshot_drift(skills_config, make_skill) -> None:
    root = make_skill("alpha-skill", extra_files={"references/note.md": "original\n"})
    server = _server(SkillCatalogue(skills_config))
    (root / "references" / "note.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(Exception, match="SKILLS_RESOURCE_STALE"):
        asyncio.run(server.read_resource("skill:///alpha-skill/references/note.md"))


def test_content_bound_approval_changes_with_resource_set(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    first_catalogue = SkillCatalogue(skills_config)
    first_entry = asyncio.run(
        _extension(_server(first_catalogue))._skills_get(
            _ctx(), SkillsGetParams(uri="skill:///alpha-skill/SKILL.md")
        )
    ).skill
    approved = skill_resource_set_fingerprint("server-a", first_entry)

    target = skills_config.root / "alpha-skill" / "references" / "new.md"
    target.parent.mkdir(parents=True)
    target.write_text("new\n", encoding="utf-8")
    second_entry = asyncio.run(
        _extension(_server(SkillCatalogue(skills_config)))._skills_get(
            _ctx(), SkillsGetParams(uri="skill:///alpha-skill/SKILL.md")
        )
    ).skill

    assert skill_requires_reapproval("server-a", first_entry, approved) is False
    assert skill_requires_reapproval("server-a", second_entry, approved) is True
    assert skill_requires_reapproval("server-b", first_entry, approved) is True


def test_host_verification_rejects_unlisted_or_mismatched_bytes(skills_config, make_skill) -> None:
    root = make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)
    entry = asyncio.run(
        _extension(_server(catalogue))._skills_get(
            _ctx(), SkillsGetParams(uri="skill:///alpha-skill/SKILL.md")
        )
    ).skill
    data = (root / "SKILL.md").read_bytes()

    verify_advertised_skill_resource(entry, str(entry.uri), data)
    with pytest.raises(SkillsError, match="SKILLS_EXTENSION_DIGEST_MISMATCH"):
        verify_advertised_skill_resource(entry, str(entry.uri), data + b"changed")
    with pytest.raises(SkillsError, match="SKILLS_EXTENSION_RESOURCE_UNLISTED"):
        verify_advertised_skill_resource(entry, "skill:///alpha-skill/extra.md", b"x")


def test_extension_rejects_skills_over_sep_resource_limit(skills_config, make_skill) -> None:
    extras = {f"references/{index:03d}.txt": "" for index in range(512)}
    make_skill("alpha-skill", extra_files=extras)
    server = _server(SkillCatalogue(skills_config))

    with pytest.raises(SkillsError, match="SKILLS_SEP2640_RESOURCE_LIMIT_EXCEEDED"):
        asyncio.run(
            _extension(server)._skills_get(
                _ctx(), SkillsGetParams(uri="skill:///alpha-skill/SKILL.md")
            )
        )


def test_list_omits_skills_over_sep_resource_limit(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    extras = {f"references/{index:03d}.txt": "" for index in range(512)}
    make_skill("oversized-skill", extra_files=extras)
    server = _server(SkillCatalogue(skills_config))

    result = asyncio.run(_extension(server)._skills_list(_ctx(), SkillsListParams()))

    assert [entry.frontmatter["name"] for entry in result.skills] == ["alpha-skill"]
