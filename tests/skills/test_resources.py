from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from fastmcp import FastMCP

from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.resources import register_skill_resources


def _read(server: FastMCP, uri: str):
    return asyncio.run(server.read_resource(uri)).contents[0].content


def _server(catalogue: SkillCatalogue) -> FastMCP:
    server = FastMCP("skills-resources-test")
    register_skill_resources(server, catalogue)
    return server


def test_catalogue_index_is_deterministic_and_progressive(skills_config, make_skill) -> None:
    make_skill("beta-skill")
    make_skill("alpha-skill", extra_files={"references/note.md": "hidden until read"})
    catalogue = SkillCatalogue(skills_config)
    server = _server(catalogue)

    payload = json.loads(_read(server, "skill:///"))

    assert payload["snapshot_id"] == catalogue.snapshot_id
    assert [item["skill_id"] for item in payload["skills"]] == ["alpha-skill", "beta-skill"]
    assert payload["skills"][0]["uri"] == "skill:///alpha-skill/SKILL.md"
    assert "references/note.md" not in json.dumps(payload)


def test_entrypoint_and_nested_resources_are_byte_identical(skills_config, make_skill) -> None:
    root = make_skill(
        "alpha-skill",
        extra_files={
            "references/note.md": "bounded evidence\n",
            "scripts/check.py": "print('data only')\n",
        },
    )
    catalogue = SkillCatalogue(skills_config)
    server = _server(catalogue)

    entrypoint = _read(server, "skill:///alpha-skill/SKILL.md")
    note = _read(server, "skill:///alpha-skill/resource?path=references%2Fnote.md")
    script = _read(server, "skill:///alpha-skill/resource?path=scripts%2Fcheck.py")

    assert entrypoint == (root / "SKILL.md").read_bytes()
    assert note == (root / "references" / "note.md").read_bytes()
    assert script == (root / "scripts" / "check.py").read_bytes()
    assert hashlib.sha256(entrypoint).hexdigest() == catalogue.load_skill("alpha-skill").sha256


def test_binary_asset_is_returned_as_exact_bytes(skills_config, make_skill) -> None:
    root = make_skill("alpha-skill")
    asset = root / "assets" / "pixel.png"
    asset.parent.mkdir()
    expected = b"\x89PNG\r\n\x1a\n\x00\xffbinary"
    asset.write_bytes(expected)
    server = _server(SkillCatalogue(skills_config))

    actual = _read(server, "skill:///alpha-skill/resource?path=assets%2Fpixel.png")

    assert actual == expected
    assert hashlib.sha256(actual).hexdigest() == hashlib.sha256(expected).hexdigest()


def test_resource_read_rejects_stale_snapshot_bytes(skills_config, make_skill) -> None:
    root = make_skill(
        "alpha-skill",
        extra_files={"references/note.md": "original\n"},
    )
    catalogue = SkillCatalogue(skills_config)
    target = root / "references" / "note.md"
    target.write_text("changed after snapshot\n", encoding="utf-8")

    with pytest.raises(SkillsError, match="SKILLS_RESOURCE_STALE"):
        catalogue.read_skill_resource_bytes("alpha-skill", "references/note.md")


def test_resource_read_rejects_traversal(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    catalogue = SkillCatalogue(skills_config)

    with pytest.raises(SkillsError, match="SKILLS_PATH_UNSAFE"):
        catalogue.read_skill_resource_bytes("alpha-skill", "../outside.md")


def test_fastmcp_exposes_index_and_resource_templates(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    resources = asyncio.run(server.list_resources())
    templates = asyncio.run(server.list_resource_templates())

    assert [str(item.uri) for item in resources] == ["skill:///"]
    assert {item.uri_template for item in templates} == {
        "skill:///{skill_id}/SKILL.md",
        "skill:///{skill_id}/resource{?path}",
    }


def test_supporting_template_does_not_alias_entrypoint(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    with pytest.raises(Exception, match="SKILLS_RESOURCE_URI_INVALID"):
        _read(server, "skill:///alpha-skill/resource?path=SKILL.md")


def test_fastmcp_preserves_unsafe_path_error(skills_config, make_skill) -> None:
    make_skill("alpha-skill")
    server = _server(SkillCatalogue(skills_config))

    with pytest.raises(Exception, match="SKILLS_PATH_UNSAFE"):
        _read(server, "skill:///alpha-skill/resource?path=..%2Foutside.md")


def test_fastmcp_reports_missing_post_snapshot_resource_as_stale(
    skills_config, make_skill
) -> None:
    root = make_skill("alpha-skill", extra_files={"references/note.md": "present\n"})
    server = _server(SkillCatalogue(skills_config))
    (root / "references" / "note.md").unlink()

    with pytest.raises(Exception, match="SKILLS_RESOURCE_STALE"):
        _read(server, "skill:///alpha-skill/resource?path=references%2Fnote.md")


def test_fastmcp_preserves_link_rejection(
    skills_config, make_skill, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_skill("alpha-skill", extra_files={"references/note.md": "present\n"})
    catalogue = SkillCatalogue(skills_config)

    def reject_link(*_args) -> None:
        raise SkillsError("SKILLS_LINK_REJECTED", "linked resource rejected")

    monkeypatch.setattr(catalogue.source_reader, "assert_safe_chain", reject_link)
    server = _server(catalogue)

    with pytest.raises(Exception, match="SKILLS_LINK_REJECTED"):
        _read(server, "skill:///alpha-skill/resource?path=references%2Fnote.md")
