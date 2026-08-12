from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from ..discover.errors import DiscoverError
from ..discover.read_authority import ReadAuthority
from .contracts import GovernanceEvidence
from .settings import GovernanceSettings

_PATH = re.compile(r"`([^`]+)`")
IdentifiersProvider = Callable[[str], Iterable[str] | None]


class GovernanceEvidenceCollector:
    def __init__(
        self,
        *,
        read_authority: ReadAuthority,
        settings: GovernanceSettings,
        identifiers_provider: IdentifiersProvider | None = None,
    ) -> None:
        self._read_authority = read_authority
        self._settings = settings
        self._identifiers_provider = identifiers_provider

    def collect(self, project: str) -> GovernanceEvidence:
        identity = self._read_authority.resolve_project(project)
        canonical = identity.canonical_path
        agents_text: str | None = None
        missing: list[str] = []
        documents: list[tuple[str, str]] = []
        try:
            agents = self._read_authority.read_relative_text(
                canonical, "AGENTS.md", max_bytes=self._settings.max_file_bytes
            )
            agents_text = agents.content
            documents.append(("AGENTS.md", agents.content))
        except DiscoverError as exc:
            if exc.code == "DISCOVER_FILE_NOT_FOUND":
                missing.append("AGENTS.md")
            else:
                raise

        for path in self._document_paths(agents_text or ""):
            if path == "AGENTS.md":
                continue
            try:
                read = self._read_authority.read_relative_text(
                    canonical, path, max_bytes=self._settings.max_file_bytes
                )
            except DiscoverError as exc:
                if exc.code == "DISCOVER_FILE_NOT_FOUND":
                    missing.append(path)
                    continue
                raise
            documents.append((path, read.content))

        identifiers = None
        if self._identifiers_provider is not None:
            supplied = self._identifiers_provider(canonical)
            if supplied is not None:
                identifiers = frozenset(
                    item for item in supplied if isinstance(item, str) and item.strip()
                )
        return GovernanceEvidence(
            project=canonical,
            agents_text=agents_text,
            documents=tuple(documents),
            missing_paths=tuple(sorted(set(missing))),
            implementation_identifiers=identifiers,
        )

    def _document_paths(self, text: str) -> tuple[str, ...]:
        paths: list[str] = []
        for value in _PATH.findall(text):
            if not _is_concrete_relative_document(value):
                continue
            if value not in paths:
                paths.append(value)
            if len(paths) >= self._settings.max_authority_documents:
                break
        return tuple(paths)


def _is_concrete_relative_document(value: str) -> bool:
    if not value or any(token in value for token in ("*", "<", ">", "$", "\\", "://")):
        return False
    if value.startswith("/") or value.startswith(".") or ".." in value.split("/"):
        return False
    return value.casefold().endswith((".md", ".json"))


__all__ = ["GovernanceEvidenceCollector", "IdentifiersProvider"]
