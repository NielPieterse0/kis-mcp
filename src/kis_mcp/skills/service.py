from __future__ import annotations

import uuid
from time import perf_counter_ns

from .backend import SkillsWorkBackend
from .catalogue import SkillCatalogue
from .errors import SkillsError
from .models import (
    SkillCard,
    SkillEvaluationResponse,
    SkillFileResponse,
    SkillFileSearchResponse,
    SkillListResponse,
    SkillLoadResponse,
    SkillMutationResponse,
    SkillRefreshResponse,
    SkillSearchResponse,
)
from .telemetry import SkillTelemetryEvent, SkillTelemetryReport, SkillTelemetryStore


def _duration_ms(start_ns: int) -> int:
    return max(0, (perf_counter_ns() - start_ns) // 1_000_000)


class SkillsService:
    """Application service combining immutable reads with Work-backed mutation."""

    def __init__(
        self,
        catalogue: SkillCatalogue,
        backend: SkillsWorkBackend,
        *,
        telemetry: SkillTelemetryStore | None = None,
    ) -> None:
        self.catalogue = catalogue
        self.backend = backend
        self.telemetry = telemetry

    def _record(self, event: SkillTelemetryEvent) -> None:
        if self.telemetry is not None:
            self.telemetry.record(event)

    def _record_error(
        self,
        *,
        event_name: str,
        started_ns: int,
        error: Exception,
        skill_id: str | None = None,
        project_id: str | None = None,
        activation_id: str | None = None,
    ) -> None:
        error_class = error.code if isinstance(error, SkillsError) else type(error).__name__
        self._record(
            SkillTelemetryEvent(
                event_name=event_name,
                source="observed",
                skill_id=skill_id,
                project_id=project_id,
                activation_id=activation_id,
                outcome="error",
                duration_ms=_duration_ms(started_ns),
                error_class=error_class,
            )
        )

    def _discover(self, cards: tuple[SkillCard, ...], snapshot_id: str) -> None:
        if self.telemetry is None:
            return
        for card in cards:
            loaded = self.catalogue.load_skill(card.id)
            self._record(
                SkillTelemetryEvent(
                    event_name="skill_discovered",
                    source="observed",
                    skill_id=card.id,
                    snapshot_id=snapshot_id,
                    content_sha256=loaded.sha256,
                )
            )

    def _list_catalogue_skills(
        self, limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        """List cards for internal platform composition without usage telemetry."""
        return self.catalogue.list_skills(limit=limit, cursor=cursor)

    def list_skills(
        self, limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        result = self._list_catalogue_skills(limit=limit, cursor=cursor)
        self._discover(result.skills, result.snapshot_id)
        return result

    def search_skills(
        self, query: str, limit: int | None = None
    ) -> SkillSearchResponse:
        result = self.catalogue.search_skills(query=query, limit=limit)
        self._discover(result.skills, result.snapshot_id)
        return result

    def load_skill(
        self,
        skill_id: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillLoadResponse:
        started = perf_counter_ns()
        try:
            result = self.catalogue.load_skill(skill_id)
        except Exception as exc:
            self._record_error(
                event_name="skill_loaded",
                started_ns=started,
                error=exc,
                skill_id=skill_id,
                project_id=project_id,
                activation_id=activation_id,
            )
            raise
        self._record(
            SkillTelemetryEvent(
                event_name="skill_loaded",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=result.sha256,
                project_id=project_id,
                activation_id=activation_id,
                duration_ms=_duration_ms(started),
            )
        )
        return result

    def search_skill_files(
        self, skill_id: str, query: str, limit: int | None = None
    ) -> SkillFileSearchResponse:
        result = self.catalogue.search_skill_files(
            skill_id=skill_id, query=query, limit=limit
        )
        loaded = self.catalogue.load_skill(skill_id)
        self._record(
            SkillTelemetryEvent(
                event_name="skill_resource_discovered",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=loaded.sha256,
            )
        )
        return result

    def read_skill_file(
        self,
        skill_id: str,
        relative_path: str,
        activation_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillFileResponse:
        started = perf_counter_ns()
        result = self.catalogue.read_skill_file(skill_id, relative_path)
        version = self.catalogue.load_skill(skill_id)
        self._record(
            SkillTelemetryEvent(
                event_name="skill_resource_read",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=version.sha256,
                project_id=project_id,
                activation_id=activation_id,
                duration_ms=_duration_ms(started),
            )
        )
        return result

    def refresh_skills(self) -> SkillRefreshResponse:
        started = perf_counter_ns()
        result = self.catalogue.refresh_skills()
        self._record(
            SkillTelemetryEvent(
                event_name="skill_catalogue_refreshed",
                source="observed",
                snapshot_id=result.snapshot_id,
                duration_ms=_duration_ms(started),
            )
        )
        return result

    def evaluate_skill(self, skill_id: str) -> SkillEvaluationResponse:
        started = perf_counter_ns()
        result = self.catalogue.evaluate_skill(skill_id)
        self._record(
            SkillTelemetryEvent(
                event_name="skill_evaluated",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=result.evidence.entrypoint_sha256,
                duration_ms=_duration_ms(started),
            )
        )
        return result

    def record_skill_outcome(
        self,
        *,
        skill_id: str,
        activation_id: str,
        snapshot_id: str,
        content_sha256: str,
        project_id: str | None = None,
        phase: str,
        duration_ms: int | None = None,
        total_tokens: int | None = None,
        tool_calls: int | None = None,
        retries: int | None = None,
        verification_passed: bool | None = None,
    ) -> SkillTelemetryEvent:
        if self.telemetry is None:
            raise SkillsError(
                "SKILLS_TELEMETRY_UNAVAILABLE",
                "Skill telemetry is not configured",
                subject=skill_id,
            )
        if not self.telemetry.has_observed_load(
            skill_id=skill_id,
            activation_id=activation_id,
            snapshot_id=snapshot_id,
            content_sha256=content_sha256,
            project_id=project_id,
        ):
            raise SkillsError(
                "SKILLS_TELEMETRY_ATTRIBUTION_REQUIRED",
                "Reported skill outcome requires a matching observed load",
                subject=skill_id,
            )
        event_names = {
            "applied": "skill_applied",
            "completed": "skill_completed",
            "failed": "skill_failed",
        }
        if phase not in event_names:
            raise SkillsError(
                "SKILLS_TELEMETRY_PHASE_INVALID",
                "Skill outcome phase must be applied, completed, or failed",
                subject=skill_id,
            )
        event = SkillTelemetryEvent(
            event_name=event_names[phase],
            source="reported",
            skill_id=skill_id,
            snapshot_id=snapshot_id,
            content_sha256=content_sha256,
            project_id=project_id,
            activation_id=activation_id,
            outcome="failure" if phase == "failed" else "success",
            duration_ms=duration_ms,
            total_tokens=total_tokens,
            tool_calls=tool_calls,
            retries=retries,
            verification_passed=verification_passed,
        )
        self.telemetry.record(event)
        return event

    def skill_telemetry_report(
        self,
        *,
        skill_id: str | None = None,
        project_id: str | None = None,
        content_sha256: str | None = None,
    ) -> SkillTelemetryReport:
        if self.telemetry is None:
            raise SkillsError(
                "SKILLS_TELEMETRY_UNAVAILABLE", "Skill telemetry is not configured"
            )
        return self.telemetry.report(
            skill_id=skill_id,
            project_id=project_id,
            content_sha256=content_sha256,
        )

    async def create_skill(
        self, skill_id: str, skill_md: str
    ) -> SkillMutationResponse:
        started = perf_counter_ns()
        self.catalogue.refresh_skills()
        proposed = self.catalogue.validate_create(skill_id, skill_md)
        stage = self.catalogue.config.staging_root / f"create-{uuid.uuid4().hex}"
        destination = self.catalogue.root / skill_id
        try:
            await self.backend.create_directory(str(stage))
            await self.backend.write_text(str(stage / "SKILL.md"), proposed.content)
            await self.backend.move(str(stage), str(destination))
        except SkillsError:
            raise
        except Exception as exc:
            raise SkillsError(
                "SKILLS_BACKEND_FAILED",
                f"Skill creation failed; staged residue may remain at {stage}: {exc}",
                subject=skill_id,
            ) from exc
        refreshed = self.catalogue.refresh_skills()
        version = self.catalogue.load_skill(skill_id)
        result = SkillMutationResponse(
            skill_id=skill_id,
            relative_path=None,
            before_sha256=None,
            after_sha256=proposed.after_sha256,
            snapshot_id=refreshed.snapshot_id,
        )
        self._record(
            SkillTelemetryEvent(
                event_name="skill_created",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=version.sha256,
                duration_ms=_duration_ms(started),
            )
        )
        return result

    async def improve_skill(
        self,
        skill_id: str,
        relative_path: str,
        expected_sha256: str,
        content: str,
    ) -> SkillMutationResponse:
        started = perf_counter_ns()
        self.catalogue.refresh_skills()
        proposed = self.catalogue.validate_replacement(
            skill_id, relative_path, content
        )
        if expected_sha256 != proposed.before_sha256:
            raise SkillsError(
                "SKILLS_HASH_MISMATCH",
                "Expected SHA-256 does not match the active skill file",
                subject=proposed.relative_path,
            )
        try:
            await self.backend.replace_text(
                str(proposed.target_path),
                proposed.current_content,
                proposed.content,
            )
        except SkillsError:
            raise
        except Exception as exc:
            raise SkillsError(
                "SKILLS_BACKEND_FAILED",
                f"Skill improvement failed: {exc}",
                subject=proposed.relative_path,
            ) from exc
        refreshed = self.catalogue.refresh_skills()
        active = self.catalogue.read_skill_file(skill_id, proposed.relative_path)
        version = self.catalogue.load_skill(skill_id)
        if active.sha256 != proposed.after_sha256:
            raise SkillsError(
                "SKILLS_HASH_MISMATCH",
                "Skill file changed concurrently or the backend did not apply the exact replacement",
                subject=proposed.relative_path,
            )
        result = SkillMutationResponse(
            skill_id=skill_id,
            relative_path=proposed.relative_path,
            before_sha256=proposed.before_sha256,
            after_sha256=active.sha256,
            snapshot_id=refreshed.snapshot_id,
        )
        self._record(
            SkillTelemetryEvent(
                event_name="skill_improved",
                source="observed",
                skill_id=skill_id,
                snapshot_id=result.snapshot_id,
                content_sha256=version.sha256,
                duration_ms=_duration_ms(started),
            )
        )
        return result
