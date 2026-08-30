from __future__ import annotations

import logging

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
from .telemetry import (
    SkillDeliveryTelemetryReport,
    SkillTelemetryEvent,
    SkillTelemetryReport,
    SkillTelemetryStore,
)

LOGGER = logging.getLogger(__name__)

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
    "record_skill_outcome",
    "skill_telemetry_report",
    "skill_delivery_telemetry_report",
)


class _UnavailableSkillsService:
    """Keep the server available while returning one corrective Skills failure."""

    def __init__(self, failure: SkillsError) -> None:
        self._code = failure.code
        self._message = failure.message
        self._subject = failure.subject

    @property
    def failure_code(self) -> str:
        return self._code

    @property
    def failure_message(self) -> str:
        return self._message

    def _raise(self) -> None:
        raise SkillsError(self._code, self._message, subject=self._subject)

    def list_skills(
        self, limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        del limit, cursor
        self._raise()

    def search_skills(
        self, query: str, limit: int | None = None
    ) -> SkillSearchResponse:
        del query, limit
        self._raise()

    def load_skill(
        self,
        skill_id: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillLoadResponse:
        del skill_id, activation_id, project_id
        self._raise()

    def search_skill_files(
        self, skill_id: str, query: str, limit: int | None = None
    ) -> SkillFileSearchResponse:
        del skill_id, query, limit
        self._raise()

    def read_skill_file(
        self,
        skill_id: str,
        relative_path: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillFileResponse:
        del skill_id, relative_path, activation_id, project_id
        self._raise()

    def refresh_skills(self) -> SkillRefreshResponse:
        self._raise()

    def evaluate_skill(self, skill_id: str) -> SkillEvaluationResponse:
        del skill_id
        self._raise()

    async def create_skill(
        self, skill_id: str, skill_md: str
    ) -> SkillMutationResponse:
        del skill_id, skill_md
        self._raise()

    async def improve_skill(
        self,
        skill_id: str,
        relative_path: str,
        expected_sha256: str,
        content: str,
    ) -> SkillMutationResponse:
        del skill_id, relative_path, expected_sha256, content
        self._raise()

    def record_skill_outcome(self, **kwargs) -> SkillTelemetryEvent:
        del kwargs
        self._raise()

    def skill_telemetry_report(self, **kwargs) -> SkillTelemetryReport:
        del kwargs
        self._raise()

    def skill_delivery_telemetry_report(self, **kwargs) -> SkillDeliveryTelemetryReport:
        del kwargs
        self._raise()


def _build_service(
    server: FastMCP,
    config: SkillsConfig | None,
    telemetry: SkillTelemetryStore | None,
) -> SkillsService | _UnavailableSkillsService:
    try:
        selected = config or load_skills_config()
        return SkillsService(
            SkillCatalogue(selected),
            FastMcpWorkBackend(server),
            telemetry=telemetry,
        )
    except SkillsError as exc:
        if exc.code == "SKILLS_REQUIRED_MISSING":
            raise
        failure = exc
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        failure = SkillsError(
            "SKILLS_UNAVAILABLE",
            f"Skills initialization failed: {exc}",
        )
    LOGGER.warning("Skills catalogue unavailable: %s", failure)
    return _UnavailableSkillsService(failure)


def register_skills_tools(
    server: FastMCP,
    *,
    config: SkillsConfig | None = None,
    service: SkillsService | None = None,
    telemetry: SkillTelemetryStore | None = None,
) -> SkillsService | _UnavailableSkillsService:
    """Register the versioned Skills interface without blocking server startup."""

    active: SkillsService | _UnavailableSkillsService = service or _build_service(
        server, config, telemetry
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
        description="Load one skill entrypoint by skill_id and return bounded catalogue evidence; use skill_id, not a display name argument.",
    )
    def load_skill(
        skill_id: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillLoadResponse:
        try:
            return active.load_skill(
                skill_id,
                activation_id=activation_id,
                project_id=project_id,
            )
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
        description="Read one bounded relative_path from an active skill identified by skill_id; use skill_id, not a display name argument.",
    )
    def read_skill_file(
        skill_id: str,
        relative_path: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillFileResponse:
        try:
            return active.read_skill_file(
                skill_id,
                relative_path,
                activation_id=activation_id,
                project_id=project_id,
            )
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

    @server.tool(
        name="record_skill_outcome",
        description=(
            "Record a caller-attributed skill application/completion outcome only "
            "when it matches a prior observed load."
        ),
    )
    def record_skill_outcome(
        skill_id: str,
        activation_id: str,
        snapshot_id: str,
        content_sha256: str,
        project_id: str | None = None,
        phase: str = "completed",
        duration_ms: int | None = None,
        total_tokens: int | None = None,
        tool_calls: int | None = None,
        retries: int | None = None,
        verification_passed: bool | None = None,
        delivery_path: str = "kis_native",
    ) -> SkillTelemetryEvent:
        try:
            return active.record_skill_outcome(
                skill_id=skill_id,
                activation_id=activation_id,
                snapshot_id=snapshot_id,
                content_sha256=content_sha256,
                project_id=project_id,
                phase=phase,
                duration_ms=duration_ms,
                total_tokens=total_tokens,
                tool_calls=tool_calls,
                retries=retries,
                verification_passed=verification_passed,
                delivery_path=delivery_path,
            )
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="skill_telemetry_report",
        description="Return bounded redacted usage/outcome evidence grouped by skill version and project.",
    )
    def skill_telemetry_report(
        skill_id: str | None = None,
        project_id: str | None = None,
        content_sha256: str | None = None,
    ) -> SkillTelemetryReport:
        try:
            return active.skill_telemetry_report(
                skill_id=skill_id,
                project_id=project_id,
                content_sha256=content_sha256,
            )
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="skill_delivery_telemetry_report",
        description=(
            "Compare bounded skill usage/outcome evidence by kis_native versus "
            "mcp_resource delivery for the same canonical content hash."
        ),
    )
    def skill_delivery_telemetry_report(
        skill_id: str | None = None,
        project_id: str | None = None,
        content_sha256: str | None = None,
    ) -> SkillDeliveryTelemetryReport:
        try:
            return active.skill_delivery_telemetry_report(
                skill_id=skill_id,
                project_id=project_id,
                content_sha256=content_sha256,
            )
        except SkillsError as exc:
            raise ToolError(str(exc)) from exc

    return active
