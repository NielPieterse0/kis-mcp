from __future__ import annotations

import uuid
from pathlib import Path

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


class SkillsService:
    """Application service combining immutable reads with Work-backed mutation."""

    def __init__(
        self,
        catalogue: SkillCatalogue,
        backend: SkillsWorkBackend,
    ) -> None:
        self.catalogue = catalogue
        self.backend = backend

    def list_skills(
        self, limit: int | None = None, cursor: str | None = None
    ) -> SkillListResponse:
        return self.catalogue.list_skills(limit=limit, cursor=cursor)

    def search_skills(
        self, query: str, limit: int | None = None
    ) -> SkillSearchResponse:
        return self.catalogue.search_skills(query=query, limit=limit)

    def load_skill(self, skill_id: str) -> SkillLoadResponse:
        return self.catalogue.load_skill(skill_id)

    def search_skill_files(
        self, skill_id: str, query: str, limit: int | None = None
    ) -> SkillFileSearchResponse:
        return self.catalogue.search_skill_files(
            skill_id=skill_id, query=query, limit=limit
        )

    def read_skill_file(self, skill_id: str, relative_path: str) -> SkillFileResponse:
        return self.catalogue.read_skill_file(skill_id, relative_path)

    def refresh_skills(self) -> SkillRefreshResponse:
        return self.catalogue.refresh_skills()

    def evaluate_skill(self, skill_id: str) -> SkillEvaluationResponse:
        return self.catalogue.evaluate_skill(skill_id)

    async def create_skill(
        self, skill_id: str, skill_md: str
    ) -> SkillMutationResponse:
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
        return SkillMutationResponse(
            skill_id=skill_id,
            relative_path=None,
            before_sha256=None,
            after_sha256=proposed.after_sha256,
            snapshot_id=refreshed.snapshot_id,
        )

    async def improve_skill(
        self,
        skill_id: str,
        relative_path: str,
        expected_sha256: str,
        content: str,
    ) -> SkillMutationResponse:
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
        return SkillMutationResponse(
            skill_id=skill_id,
            relative_path=proposed.relative_path,
            before_sha256=proposed.before_sha256,
            after_sha256=proposed.after_sha256,
            snapshot_id=refreshed.snapshot_id,
        )
