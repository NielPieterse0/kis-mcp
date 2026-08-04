from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from .config import SkillsConfig
from .errors import SkillsError
from .frontmatter import parse_skill_frontmatter


@dataclass(frozen=True, slots=True)
class SkillFile:
    path: str
    group: str
    size: int
    sha256: str
    content: str | None


@dataclass(frozen=True, slots=True)
class SkillSource:
    id: str
    source_directory: str
    summary: str
    category: str
    capabilities: tuple[str, ...]
    status: str
    content: str
    content_hash: str
    files: tuple[SkillFile, ...]
    reference_group_counts: MappingProxyType[str, int]


class SkillSourceReader:
    """Validate and normalize one configured on-disk or proposed skill source."""

    def __init__(self, config: SkillsConfig) -> None:
        self.config = config
        configured_root = config.root.absolute()
        for candidate in (*reversed(configured_root.parents), configured_root):
            self.assert_no_link(candidate)
        self.root = configured_root.resolve(strict=True)
        if not self.root.is_dir():
            raise SkillsError("SKILLS_ROOT_INVALID", "Skills root must be a directory")

    def read_directory(self, skill_root: Path) -> SkillSource:
        files: list[SkillFile] = []
        total = 0
        for current_root, directory_names, file_names in os.walk(
            skill_root, topdown=True, followlinks=False
        ):
            current = Path(current_root)
            self.assert_safe_chain(skill_root, current)
            directory_names.sort(key=str.casefold)
            file_names.sort(key=str.casefold)
            for directory_name in directory_names:
                self.assert_safe_chain(skill_root, current / directory_name)
            for file_name in file_names:
                path = current / file_name
                self.assert_safe_chain(skill_root, path)
                relative = path.relative_to(skill_root).as_posix()
                item = self.read_file(skill_root, relative)
                total += item.size
                if total > self.config.limits.max_skill_bytes:
                    raise SkillsError(
                        "SKILLS_SIZE_EXCEEDED", "Skill exceeds maximum total size"
                    )
                files.append(item)
        return self.build_source(
            source_directory=skill_root.name,
            files=tuple(files),
        )

    def build_source(
        self, *, source_directory: str, files: tuple[SkillFile, ...]
    ) -> SkillSource:
        if not files:
            raise SkillsError("SKILLS_ENTRYPOINT_MISSING", "SKILL.md is required")
        total = sum(item.size for item in files)
        if total > self.config.limits.max_skill_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill exceeds maximum total size"
            )
        entrypoint = next((item for item in files if item.path == "SKILL.md"), None)
        if entrypoint is None or entrypoint.content is None:
            raise SkillsError("SKILLS_ENTRYPOINT_MISSING", "SKILL.md is required")

        frontmatter = parse_skill_frontmatter(entrypoint.content)
        name = frontmatter.get("name")
        description = frontmatter.get("description")
        if not isinstance(name, str) or not name.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "SKILL.md name is required"
            )
        if not isinstance(description, str) or not description.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "SKILL.md description is required"
            )
        canonical_id = name.strip()
        self.validate_skill_id(canonical_id)

        category = frontmatter.get("category", "uncategorized")
        status = frontmatter.get("status", "active")
        capabilities = frontmatter.get("capabilities", ())
        if not isinstance(category, str) or not category.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Skill category must be text"
            )
        if not isinstance(status, str) or not status.strip():
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID", "Skill status must be text"
            )
        if isinstance(capabilities, list):
            capabilities = tuple(capabilities)
        if not isinstance(capabilities, tuple) or not all(
            isinstance(item, str) and item.strip() for item in capabilities
        ):
            raise SkillsError(
                "SKILLS_FRONTMATTER_INVALID",
                "Skill capabilities must be a string list",
            )

        groups: dict[str, int] = {}
        for item in files:
            groups[item.group] = groups.get(item.group, 0) + 1
        return SkillSource(
            id=canonical_id,
            source_directory=source_directory,
            summary=description.strip(),
            category=category.strip(),
            capabilities=tuple(item.strip() for item in capabilities),
            status=status.strip(),
            content=entrypoint.content,
            content_hash=entrypoint.sha256,
            files=tuple(sorted(files, key=lambda item: item.path)),
            reference_group_counts=MappingProxyType(dict(sorted(groups.items()))),
        )

    def read_file(self, root: Path, relative_path: str) -> SkillFile:
        relative = self.safe_relative_path(relative_path)
        candidate = root.joinpath(*relative.parts)
        self.assert_safe_chain(root, candidate)
        if not candidate.is_file():
            raise SkillsError("SKILLS_FILE_INVALID", "Skill entry must be a file")
        suffix = candidate.suffix.casefold()
        if suffix not in self.config.validation.allowed_suffixes:
            raise SkillsError(
                "SKILLS_SUFFIX_FORBIDDEN",
                f"Skill file suffix is not configured: {suffix or '<none>'}",
            )
        data = candidate.read_bytes()
        if len(data) > self.config.limits.max_file_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill file exceeds maximum size"
            )
        content: str | None
        if suffix == ".png":
            content = None
        else:
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SkillsError(
                    "SKILLS_ENCODING_INVALID", "Skill file must be UTF-8 text"
                ) from exc
        path = relative.as_posix()
        return SkillFile(
            path=path,
            group=path.split("/", 1)[0] if "/" in path else "root",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            content=content,
        )

    def virtual_file(self, relative_path: str, content: str) -> SkillFile:
        relative = self.safe_relative_path(relative_path)
        suffix = relative.suffix.casefold()
        if suffix not in self.config.validation.allowed_suffixes or suffix == ".png":
            raise SkillsError(
                "SKILLS_SUFFIX_FORBIDDEN", "Replacement target must be configured text"
            )
        encoded = content.encode("utf-8")
        if len(encoded) > self.config.limits.max_file_bytes:
            raise SkillsError(
                "SKILLS_SIZE_EXCEEDED", "Skill file exceeds maximum size"
            )
        path = relative.as_posix()
        return SkillFile(
            path=path,
            group=path.split("/", 1)[0] if "/" in path else "root",
            size=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            content=content,
        )

    def target_path(self, source_directory: str, relative_path: str) -> Path:
        relative = self.safe_relative_path(relative_path)
        return self.root / source_directory / Path(*relative.parts)

    def safe_relative_path(self, value: str) -> PurePosixPath:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or (self.config.validation.reject_backslashes and "\\" in value)
        ):
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Skill file path is empty or unsafe"
            )
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Skill file path must remain relative"
            )
        return path

    def assert_safe_chain(self, root: Path, candidate: Path) -> None:
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise SkillsError(
                "SKILLS_PATH_UNSAFE", "Path is outside the selected skill"
            ) from exc
        current = root
        self.assert_no_link(current)
        for part in relative.parts:
            current = current / part
            self.assert_no_link(current)

    def assert_no_link(self, path: Path) -> None:
        try:
            info = os.lstat(path)
        except FileNotFoundError as exc:
            raise SkillsError("SKILLS_PATH_MISSING", "Skill path does not exist") from exc
        if self.config.validation.reject_links and stat.S_ISLNK(info.st_mode):
            raise SkillsError("SKILLS_LINK_REJECTED", "Symbolic links are not allowed")
        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if self.config.validation.reject_reparse_points and attributes & reparse_flag:
            raise SkillsError("SKILLS_LINK_REJECTED", "Reparse points are not allowed")
        if (
            self.config.validation.reject_hard_links
            and stat.S_ISREG(info.st_mode)
            and info.st_nlink > 1
        ):
            raise SkillsError("SKILLS_LINK_REJECTED", "Hard-linked files are not allowed")

    def validate_skill_id(self, skill_id: str) -> None:
        if (
            not isinstance(skill_id, str)
            or self.config.validation.skill_id_pattern.fullmatch(skill_id) is None
        ):
            raise SkillsError(
                "SKILLS_ID_INVALID", "Skill ID must be lowercase and hyphenated"
            )
