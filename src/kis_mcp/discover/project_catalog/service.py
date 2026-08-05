from __future__ import annotations

import hashlib
import json
import os
import tomllib
import xml.etree.ElementTree as ElementTree
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..contracts import Confidence, ProjectIdentity
from ..errors import DiscoverError
from ..read_authority import ReadAuthority, is_within_boundary
from ..scanner import RepositoryScanner
from ..settings import DiscoverSettings
from .contracts import (
    CatalogManifest,
    CatalogProject,
    ProjectCatalogOmissions,
    ProjectCatalogRequest,
    ProjectCatalogResponse,
    ProjectCatalogUnknown,
    ProjectRelationship,
)

_PACKAGE_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)


class ProjectCatalogService:
    def __init__(self, *, boundary: Path, settings: DiscoverSettings) -> None:
        self._boundary = boundary
        self._settings = settings

    def inspect(self, request: ProjectCatalogRequest) -> ProjectCatalogResponse:
        self._validate_budget(request)
        authority = ReadAuthority(self._boundary, self._settings)
        resolved = tuple(authority.resolve_project(value) for value in request.projects)
        canonical_keys = tuple(_path_key(item.canonical_path) for item in resolved)
        if len(set(canonical_keys)) != len(canonical_keys):
            raise _error(
                "DISCOVER_PROJECT_CATALOG_DUPLICATE",
                "The project catalog selection contains the same canonical project more than once.",
                "Duplicate canonical project identities are not accepted.",
                field="projects",
            )

        ordered_all = tuple(
            sorted(
                zip(resolved, request.projects, strict=True),
                key=lambda item: (
                    item[0].canonical_path.casefold(),
                    item[0].canonical_path,
                ),
            )
        )
        retained_pairs = ordered_all[: request.budget.max_projects]
        retained_identities = tuple(item[0] for item in retained_pairs)
        retained_keys = {_path_key(item.canonical_path): item for item in retained_identities}
        all_selected_keys = {_path_key(item.canonical_path) for item in resolved}
        projects = tuple(
            CatalogProject(project=identity, selected_path=selected_path)
            for identity, selected_path in retained_pairs
        )

        manifest_candidates: list[tuple[ProjectIdentity, str, str]] = []
        for identity in retained_identities:
            snapshot = RepositoryScanner(authority, self._settings).snapshot(
                identity.canonical_path
            )
            for record in snapshot.files:
                kind = _manifest_kind(record.label)
                if kind is not None:
                    manifest_candidates.append((identity, record.label, kind))
        manifest_candidates.sort(
            key=lambda item: (
                item[0].canonical_path.casefold(),
                item[1].casefold(),
                item[1],
            )
        )
        selected_manifest_candidates = manifest_candidates[: request.budget.max_manifests]

        manifests: list[CatalogManifest] = []
        relationships: list[ProjectRelationship] = []
        unknowns: list[ProjectCatalogUnknown] = []
        for identity, label, kind in selected_manifest_candidates:
            try:
                read = authority.read_relative_text(
                    identity.canonical_path,
                    label,
                    max_bytes=self._settings.limits.max_file_bytes,
                )
            except DiscoverError as exc:
                unknowns.append(
                    ProjectCatalogUnknown(
                        code="MANIFEST_READ_FAILED",
                        reason=f"The selected manifest could not be read safely: {exc.code}.",
                        source_project=identity,
                        source_manifest=label,
                        candidate_path=str(Path(identity.canonical_path) / label),
                    )
                )
                continue
            manifests.append(
                CatalogManifest(
                    project=identity,
                    path=read.label,
                    kind=kind,
                    content_digest=hashlib.sha256(
                        read.content.encode("utf-8")
                    ).hexdigest(),
                )
            )
            try:
                references = _parse_references(kind, read.content)
            except (json.JSONDecodeError, tomllib.TOMLDecodeError, ElementTree.ParseError, ValueError) as exc:
                unknowns.append(
                    ProjectCatalogUnknown(
                        code="MANIFEST_PARSE_FAILED",
                        reason=f"The selected {kind} manifest could not be parsed: {type(exc).__name__}.",
                        source_project=identity,
                        source_manifest=label,
                        candidate_path=str(Path(identity.canonical_path) / label),
                    )
                )
                continue
            for relationship_type, subject, raw_path in references:
                normalized = _normalize_reference_path(
                    boundary=self._boundary,
                    source_root=Path(identity.canonical_path),
                    raw_path=raw_path,
                )
                if normalized is None:
                    unknowns.append(
                        ProjectCatalogUnknown(
                            code="REFERENCE_OUTSIDE_BOUNDARY",
                            reason="A local project reference escaped or could not be normalized beneath the configured boundary.",
                            source_project=identity,
                            source_manifest=label,
                            candidate_path=raw_path,
                        )
                    )
                    continue
                target = _match_selected_project(normalized, retained_keys)
                if target is None:
                    code = (
                        "TARGET_PROJECT_OMITTED"
                        if _matches_any_selected(normalized, all_selected_keys)
                        else "UNSELECTED_PROJECT_REFERENCE"
                    )
                    unknowns.append(
                        ProjectCatalogUnknown(
                            code=code,
                            reason=(
                                "The referenced project was explicitly selected but omitted by the project budget."
                                if code == "TARGET_PROJECT_OMITTED"
                                else "The local reference does not resolve to a retained explicitly selected project and was not scanned."
                            ),
                            source_project=identity,
                            source_manifest=label,
                            candidate_path=str(normalized),
                        )
                    )
                    continue
                if target.project_id == identity.project_id:
                    continue
                relationships.append(
                    ProjectRelationship(
                        source_project=identity,
                        target_project=target,
                        relationship_type=relationship_type,
                        source_manifest=label,
                        subject=subject,
                        provenance="static_manifest_reference",
                        confidence=Confidence.HIGH,
                    )
                )

        relationships.extend(_nested_relationships(retained_identities))
        relationships = list(_dedupe_relationships(relationships))
        unknowns = list(_dedupe_unknowns(unknowns))

        selected_relationships = tuple(
            relationships[: request.budget.max_relationships]
        )
        selected_unknowns = tuple(unknowns[: request.budget.max_unknowns])
        omissions = ProjectCatalogOmissions(
            projects=max(0, len(ordered_all) - len(projects)),
            manifests=max(0, len(manifest_candidates) - len(selected_manifest_candidates)),
            relationships=max(0, len(relationships) - len(selected_relationships)),
            unknowns=max(0, len(unknowns) - len(selected_unknowns)),
        )
        truncation_reasons = tuple(
            name
            for name in (
                "max_projects",
                "max_manifests",
                "max_relationships",
                "max_unknowns",
            )
            if getattr(omissions, name.removeprefix("max_")) > 0
        )
        confidence = (
            Confidence.MEDIUM
            if selected_unknowns or truncation_reasons
            else Confidence.HIGH
        )
        response = ProjectCatalogResponse(
            projects=projects,
            manifests=tuple(manifests),
            relationships=selected_relationships,
            unknowns=selected_unknowns,
            omissions=omissions,
            confidence=confidence,
            truncated=bool(truncation_reasons),
            truncation_reasons=truncation_reasons,
            fingerprint="0" * 64,
        )
        payload = response.to_json_dict()
        payload.pop("fingerprint")
        return replace(response, fingerprint=_fingerprint(payload))

    def _validate_budget(self, request: ProjectCatalogRequest) -> None:
        maxima = {
            "max_projects": self._settings.limits.max_directories,
            "max_manifests": self._settings.limits.max_files,
            "max_relationships": self._settings.limits.max_evidence,
            "max_unknowns": self._settings.limits.max_evidence,
        }
        for name, maximum in maxima.items():
            if getattr(request.budget, name) > maximum:
                raise _error(
                    "DISCOVER_PROJECT_CATALOG_BUDGET_INVALID",
                    "The project catalog budget exceeds configured Discover limits.",
                    f"{name} must not exceed {maximum}.",
                    field=f"budget.{name}",
                )


def _manifest_kind(label: str) -> str | None:
    if label == "package.json":
        return "npm"
    if label == "pyproject.toml":
        return "python"
    if "/" not in label and label.casefold().endswith(".csproj"):
        return "dotnet"
    return None


def _parse_references(kind: str, content: str) -> tuple[tuple[str, str, str], ...]:
    if kind == "npm":
        return _parse_package_json(content)
    if kind == "python":
        return _parse_pyproject(content)
    if kind == "dotnet":
        return _parse_csproj(content)
    raise ValueError(f"unsupported manifest kind: {kind}")


def _parse_package_json(content: str) -> tuple[tuple[str, str, str], ...]:
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("package.json root must be an object")
    records: list[tuple[str, str, str]] = []
    for section in _PACKAGE_SECTIONS:
        values = payload.get(section, {})
        if values is None:
            continue
        if not isinstance(values, dict):
            raise ValueError(f"package.json {section} must be an object")
        for name, value in values.items():
            if not isinstance(name, str) or not isinstance(value, str):
                continue
            prefix = next(
                (candidate for candidate in ("file:", "link:") if value.startswith(candidate)),
                None,
            )
            if prefix is not None and value[len(prefix) :].strip():
                records.append(
                    ("npm_local_dependency", name, value[len(prefix) :].strip())
                )
    return tuple(_sorted_reference_records(records))


def _parse_pyproject(content: str) -> tuple[tuple[str, str, str], ...]:
    payload = tomllib.loads(content)
    records: list[tuple[str, str, str]] = []
    tool = payload.get("tool", {})
    if not isinstance(tool, dict):
        return ()
    poetry = tool.get("poetry", {})
    if isinstance(poetry, dict):
        _collect_path_mapping(
            poetry.get("dependencies", {}),
            records,
            "python_path_dependency",
        )
        groups = poetry.get("group", {})
        if isinstance(groups, dict):
            for group in groups.values():
                if isinstance(group, dict):
                    _collect_path_mapping(
                        group.get("dependencies", {}),
                        records,
                        "python_path_dependency",
                    )
    uv = tool.get("uv", {})
    if isinstance(uv, dict):
        _collect_path_mapping(
            uv.get("sources", {}),
            records,
            "python_path_dependency",
        )
    return tuple(_sorted_reference_records(records))


def _collect_path_mapping(
    value: Any,
    records: list[tuple[str, str, str]],
    relationship_type: str,
) -> None:
    if not isinstance(value, dict):
        return
    for name, declaration in value.items():
        if not isinstance(name, str) or not isinstance(declaration, dict):
            continue
        path = declaration.get("path")
        if isinstance(path, str) and path.strip():
            records.append((relationship_type, name, path.strip()))


def _parse_csproj(content: str) -> tuple[tuple[str, str, str], ...]:
    root = ElementTree.fromstring(content)
    records: list[tuple[str, str, str]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "ProjectReference":
            continue
        include = element.attrib.get("Include")
        if isinstance(include, str) and include.strip():
            records.append(
                (
                    "dotnet_project_reference",
                    Path(include.replace("\\", "/")).stem,
                    include.strip(),
                )
            )
    return tuple(_sorted_reference_records(records))


def _sorted_reference_records(
    records: Iterable[tuple[str, str, str]],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            set(records),
            key=lambda item: (
                item[0],
                item[1].casefold(),
                item[1],
                item[2].casefold(),
                item[2],
            ),
        )
    )


def _normalize_reference_path(
    *, boundary: Path, source_root: Path, raw_path: str
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
        return None
    normalized_text = raw_path.strip().replace("\\", os.sep).replace("/", os.sep)
    candidate = Path(normalized_text)
    if candidate.is_absolute():
        return None
    try:
        normalized = (source_root / candidate).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    if not is_within_boundary(boundary, normalized):
        return None
    return normalized


def _match_selected_project(
    candidate: Path,
    retained: Mapping[str, ProjectIdentity],
) -> ProjectIdentity | None:
    matches = [
        identity
        for identity in retained.values()
        if is_within_boundary(Path(identity.canonical_path), candidate)
        or _path_key(identity.canonical_path) == _path_key(str(candidate))
    ]
    if not matches:
        return None
    return max(matches, key=lambda item: len(Path(item.canonical_path).parts))


def _matches_any_selected(candidate: Path, selected_keys: set[str]) -> bool:
    candidate_key = _path_key(str(candidate))
    return any(
        candidate_key == selected
        or candidate_key.startswith(selected.rstrip("\\/") + os.sep.casefold())
        for selected in selected_keys
    )


def _nested_relationships(
    projects: tuple[ProjectIdentity, ...],
) -> tuple[ProjectRelationship, ...]:
    records: list[ProjectRelationship] = []
    for parent in projects:
        parent_path = Path(parent.canonical_path)
        for child in projects:
            if parent.project_id == child.project_id:
                continue
            child_path = Path(child.canonical_path)
            if is_within_boundary(parent_path, child_path):
                records.append(
                    ProjectRelationship(
                        source_project=parent,
                        target_project=child,
                        relationship_type="contains_selected_project",
                        source_manifest=None,
                        subject=None,
                        provenance="explicit_selection",
                        confidence=Confidence.HIGH,
                    )
                )
    return tuple(records)


def _dedupe_relationships(
    records: Iterable[ProjectRelationship],
) -> tuple[ProjectRelationship, ...]:
    values: dict[tuple[str, str, str, str | None, str | None], ProjectRelationship] = {}
    for item in records:
        key = (
            item.source_project.project_id,
            item.target_project.project_id,
            item.relationship_type,
            item.source_manifest,
            item.subject,
        )
        values.setdefault(key, item)
    return tuple(
        sorted(
            values.values(),
            key=lambda item: (
                item.source_project.canonical_path.casefold(),
                item.target_project.canonical_path.casefold(),
                item.relationship_type,
                (item.source_manifest or "").casefold(),
                (item.subject or "").casefold(),
            ),
        )
    )


def _dedupe_unknowns(
    records: Iterable[ProjectCatalogUnknown],
) -> tuple[ProjectCatalogUnknown, ...]:
    values: dict[tuple[str, str, str, str], ProjectCatalogUnknown] = {}
    for item in records:
        key = (
            item.code,
            item.source_project.project_id if item.source_project else "",
            item.source_manifest or "",
            item.candidate_path,
        )
        values.setdefault(key, item)
    return tuple(
        sorted(
            values.values(),
            key=lambda item: (
                item.code,
                item.source_project.canonical_path.casefold()
                if item.source_project
                else "",
                (item.source_manifest or "").casefold(),
                item.candidate_path.casefold(),
            ),
        )
    )


def _path_key(value: str) -> str:
    return os.path.normcase(os.path.abspath(value)).casefold()


def _error(
    code: str,
    message: str,
    reason: str,
    *,
    field: str | None = None,
) -> DiscoverError:
    return DiscoverError(
        code=code,
        message=message,
        reason=reason,
        field=field,
        accepted="A bounded explicit selection of local projects beneath the configured Discover boundary.",
        corrective_actions=("Correct the explicit project selection or budget and retry.",),
    )


def _fingerprint(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


__all__ = ["ProjectCatalogService"]
