from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .backend import FastMcpWorkBackend
from .catalogue import SkillCatalogue
from .config import SkillsConfig, load_skills_config
from .errors import SkillsError
from .models import (
    SkillEvaluationResponse,
    SkillFileResponse,
    SkillFileSearchResponse,
    SkillListResponse,
    SkillLoadResponse,
    SkillMutationResponse,
    SkillRefreshResponse,
    SkillSearchResponse,
)
from .service import SkillsService


SKILLS_TOOL_NAMES = (
    "list_skills",
    "search_skills",
    "load_skill",
    "search_skill_files",
    "read_skill_file",
    "refresh_skills",
    "evaluate_skill",
    "create_skill",
    "improve_skill",
)


def register_skills_tools(
    server: FastMCP,
    *,
    config: SkillsConfig | None = None,
    service: SkillsService | None = None,
) -> SkillsService:
    """Register the versioned Skills interface on one existing kis-mcp server."""

    active = service
    if active is None:
        selected = config or load_skills_config()
        active = SkillsService(
            SkillCatalogue(selected),
            FastMcpWorkBackend(server),
        )

    @server.tool(
        name="list_skills",
        description="List bounded skill cards from the immutable active snapshot.",
    )
    def list_skills(
        limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        try:
            return active.list_skills(limit=limit, cursor=cursor)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="search_skills",
        description="Search skill identity and metadata in the active snapshot.",
    )
    def search_skills(query: str, limit: int | None = None) -> SkillSearchResponse:
        try:
            return active.search_skills(query=query, limit=limit)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="load_skill",
        description="Load one skill entrypoint and bounded catalogue evidence.",
    )
    def load_skill(skill_id: str) -> SkillLoadResponse:
        try:
            return active.load_skill(skill_id)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="search_skill_files",
        description="Search bounded relative file paths inside one active skill.",
    )
    def search_skill_files(
        skill_id: str, query: str, limit: int | None = None
    ) -> SkillFileSearchResponse:
        try:
            return active.search_skill_files(
                skill_id=skill_id, query=query, limit=limit
            )
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="read_skill_file",
        description="Read one bounded file from an active skill snapshot.",
    )
    def read_skill_file(skill_id: str, relative_path: str) -> SkillFileResponse:
        try:
            return active.read_skill_file(skill_id, relative_path)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="refresh_skills",
        description="Rebuild the immutable Skills snapshot from the configured root.",
    )
    def refresh_skills() -> SkillRefreshResponse:
        try:
            return active.refresh_skills()
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="evaluate_skill",
        description="Return bounded structural evidence for one active skill.",
    )
    def evaluate_skill(skill_id: str) -> SkillEvaluationResponse:
        try:
            return active.evaluate_skill(skill_id)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="create_skill",
        description=(
            "Validate and publish a new skill through the existing Work and "
            "Desktop Commander mutation path."
        ),
    )
    async def create_skill(skill_id: str, skill_md: str) -> SkillMutationResponse:
        try:
            return await active.create_skill(skill_id, skill_md)
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="improve_skill",
        description=(
            "Replace one text skill file using an expected SHA-256 and the existing "
            "Work and Desktop Commander mutation path."
        ),
    )
    async def improve_skill(
        skill_id: str,
        relative_path: str,
        expected_sha256: str,
        content: str,
    ) -> SkillMutationResponse:
        try:
            return await active.improve_skill(
                skill_id=skill_id,
                relative_path=relative_path,
                expected_sha256=expected_sha256,
                content=content,
            )
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    return active
