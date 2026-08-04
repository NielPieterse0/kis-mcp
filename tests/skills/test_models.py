from __future__ import annotations

from dataclasses import asdict

from pydantic import TypeAdapter

from kis_mcp.skills.models import (
    SkillCard,
    SkillEvaluationEvidence,
    SkillEvaluationResponse,
    SkillFileResponse,
    SkillListResponse,
    SkillLoadResponse,
    SkillMutationResponse,
    SkillRefreshResponse,
    SkillSearchResponse,
)


def test_skill_public_records_are_explicit_and_versioned() -> None:
    card = SkillCard(
        id="modularity-assessment",
        summary="Assess module boundaries.",
        category="architecture",
        capabilities=("read",),
        status="active",
    )
    response = SkillListResponse(
        skills=(card,),
        skill_count=1,
        next_cursor=None,
        snapshot_id="0123456789abcdef",
    )

    assert asdict(response) == {
        "skills": (
            {
                "id": "modularity-assessment",
                "summary": "Assess module boundaries.",
                "category": "architecture",
                "capabilities": ("read",),
                "status": "active",
                "schema_version": 1,
            },
        ),
        "skill_count": 1,
        "next_cursor": None,
        "snapshot_id": "0123456789abcdef",
        "schema_version": 1,
    }


def test_skill_response_schemas_are_bounded() -> None:
    expected = {
        SkillCard: {"id", "summary", "category", "capabilities", "status", "schema_version"},
        SkillListResponse: {
            "skills",
            "skill_count",
            "next_cursor",
            "snapshot_id",
            "schema_version",
        },
        SkillSearchResponse: {"skills", "snapshot_id", "schema_version"},
        SkillLoadResponse: {
            "skill",
            "content",
            "sha256",
            "file_count",
            "reference_group_counts",
            "snapshot_id",
            "schema_version",
        },
        SkillFileResponse: {
            "skill_id",
            "path",
            "size",
            "sha256",
            "content",
            "snapshot_id",
            "schema_version",
        },
        SkillRefreshResponse: {
            "snapshot_id",
            "skill_count",
            "schema_version",
        },
        SkillEvaluationEvidence: {
            "file_count",
            "total_bytes",
            "reference_group_counts",
            "entrypoint_sha256",
            "supported_file_count",
            "schema_version",
        },
        SkillEvaluationResponse: {
            "skill_id",
            "snapshot_id",
            "evidence",
            "schema_version",
        },
        SkillMutationResponse: {
            "skill_id",
            "relative_path",
            "before_sha256",
            "after_sha256",
            "snapshot_id",
            "changed_state",
            "schema_version",
        },
    }

    for record, fields in expected.items():
        schema = TypeAdapter(record).json_schema()
        assert set(schema["properties"]) == fields
        assert schema.get("additionalProperties") is not True
