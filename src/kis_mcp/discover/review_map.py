from __future__ import annotations

from collections import defaultdict
from typing import Any

from .change_inspection_contracts import InspectChangeResponse
from .review_map_contracts import (
    REVIEW_MAP_SCHEMA_VERSION,
    REVIEW_MAP_TOOL,
    ReviewMapLimits,
)

_CATEGORY_ORDER = (
    "source",
    "test",
    "contract",
    "documentation",
    "configuration",
    "policy",
    "other",
)


def _section_key(path: str, categories: tuple[str, ...]) -> tuple[int, str, str]:
    category = next((item for item in _CATEGORY_ORDER if item in categories), "other")
    top = path.split("/", 1)[0] if "/" in path else "."
    return (_CATEGORY_ORDER.index(category), category, top)


def _relationship(kind: str, source: str, targets: list[str]) -> dict[str, Any]:
    return {"kind": kind, "source": source, "targets": targets}


def build_review_map(
    inspection: InspectChangeResponse,
    *,
    limits: ReviewMapLimits,
    expected_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    fingerprint = inspection.change.fingerprint
    if (
        expected_source_fingerprint is not None
        and expected_source_fingerprint != fingerprint
    ):
        raise ValueError("review map source fingerprint is stale")

    files = sorted(inspection.changed_files, key=lambda item: item.path.casefold())
    included = files[: limits.max_files]
    omitted = files[limits.max_files :]

    grouped: dict[tuple[int, str, str], list[Any]] = defaultdict(list)
    for item in included:
        grouped[_section_key(item.path, item.categories)].append(item)

    sections: list[dict[str, Any]] = []
    section_items = sorted(grouped.items(), key=lambda item: item[0])
    included_sections = section_items[: limits.max_sections]
    omitted_section_items = section_items[limits.max_sections :]
    section_omitted_files = [
        changed.path for _key, values in omitted_section_items for changed in values
    ]
    visible_paths: set[str] = set()
    for ordinal, ((_, category, top), values) in enumerate(included_sections, start=1):
        paths = sorted(item.path for item in values)
        visible_paths.update(paths)
        sections.append(
            {
                "section_id": f"section-{ordinal:03d}",
                "ordinal": ordinal,
                "category": category,
                "scope": top,
                "files": paths,
                "navigation_key": f"{category}:{top}",
                "review_status": "pending",
            }
        )

    omitted_paths = sorted(
        {item.path for item in omitted}.union(section_omitted_files),
        key=str.casefold,
    )

    relationships: list[dict[str, Any]] = []
    for scope in sorted(inspection.affected_scopes, key=str.casefold):
        targets = sorted(
            path
            for path in visible_paths
            if path == scope or path.startswith(f"{scope}/")
        )
        if targets:
            relationships.append(_relationship("affected_scope", scope, targets))
    for handoff in sorted(
        inspection.verification_handoffs, key=lambda item: item.handoff_id
    ):
        targets = sorted(path for path in handoff.paths if path in visible_paths)
        if targets:
            relationships.append(
                _relationship("verification_handoff", handoff.handoff_id, targets)
            )
    omitted_relationship_count = max(0, len(relationships) - limits.max_relationships)
    relationships = relationships[: limits.max_relationships]

    truncated = bool(
        inspection.truncated
        or omitted_paths
        or omitted_section_items
        or omitted_relationship_count
    )
    return {
        "schema_version": REVIEW_MAP_SCHEMA_VERSION,
        "tool": REVIEW_MAP_TOOL,
        "authority": "navigation_evidence_only",
        "source": inspection.source,
        "source_fingerprint": fingerprint,
        "source_identity": inspection.change.to_json_dict(),
        "sections": sections,
        "relationships": relationships,
        "omitted_relationship_count": omitted_relationship_count,
        "included_files": sorted(visible_paths, key=str.casefold),
        "omitted_files": omitted_paths,
        "progress": {
            "total_sections": len(sections),
            "reviewed_sections": 0,
            "pending_sections": len(sections),
        },
        "truncated": truncated,
        "incomplete": bool(
            truncated or not inspection.available or inspection.unknowns
        ),
        "unknowns": [item.to_json_dict() for item in inspection.unknowns],
        "diagnostics": [dict(item) for item in inspection.diagnostics],
        "gate_authority": {
            "review": False,
            "verification": False,
            "merge_readiness": False,
            "mutation": False,
        },
    }


__all__ = ["build_review_map"]
