from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from kis_mcp.commissioning.classifier import classify_change, commissioning_key
from kis_mcp.commissioning.models import ClassificationState, LandedChangeEvidence
from kis_mcp.commissioning.settings import (
    PostMergeCommissioningSettingsError,
    load_post_merge_commissioning_settings,
)


def _document() -> dict[str, object]:
    return {
        "schema_version": 2,
        "enabled": True,
        "host_instance": "kis-op",
        "state_namespace": "post-merge-commissioning",
        "receipt_retention": 120,
        "freshness_stale_after_seconds": 5400,
        "poll_interval_seconds": 300,
        "initial_delay_seconds": 30,
        "overlap_seconds": 900,
        "max_candidates": 50,
        "max_external_reads": 200,
        "max_mutations": 20,
        "ambiguous_risk_triggers": ["security", "deployment", "external_action"],
        "targets": [
            {
                "project_id": "kis-mcp",
                "repository": "NielPieterse0/kis-mcp",
                "default_branch": "main",
            }
        ],
        "surfaces": [
            {
                "id": "work-management",
                "path_patterns": ["src/kis_mcp/work_management/**", "settings/work-management/**"],
                "risk_triggers": [],
                "runtime_instance": "kis-op",
                "refresh_rule": "restart",
                "probe_id": "work-management-contract",
                "verification_procedure": "Restart kis-op and exercise the affected Work Management capability.",
                "expected_invariant": "The exposed Work Management capability uses the landed contract without runtime errors.",
                "evidence_target": "linked commissioning issue evidence",
                "terminal_success_criterion": "The real exposed capability passes against the landed merge SHA.",
            },
            {
                "id": "provider-runtime",
                "path_patterns": ["src/kis_mcp/providers/**", "settings/providers/**"],
                "risk_triggers": ["security"],
                "runtime_instance": "kis-op",
                "refresh_rule": "restart",
                "probe_id": "provider-status",
                "verification_procedure": "Restart kis-op and exercise the affected provider capability.",
                "expected_invariant": "Provider startup and the affected exposed capability succeed on the landed code.",
                "evidence_target": "linked commissioning issue evidence",
                "terminal_success_criterion": "The affected provider path passes live verification for the exact merge SHA.",
            },
        ],
    }


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "post-merge-commissioning.settings.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _evidence(paths: tuple[str, ...], risks: tuple[str, ...] = ()) -> LandedChangeEvidence:
    return LandedChangeEvidence(
        repository="NielPieterse0/kis-mcp",
        source_issue=419,
        source_pr=452,
        merge_sha="a" * 40,
        change_id="227-post-merge-project-field-commissioning",
        changed_paths=paths,
        risk_triggers=risks,
    )


def test_checked_in_settings_are_strict_and_normalized() -> None:
    settings = load_post_merge_commissioning_settings()

    assert settings.enabled is True
    assert settings.host_instance == "kis-op"
    assert settings.state_namespace == "post-merge-commissioning"
    assert settings.targets[0].repository == "NielPieterse0/kis-mcp"
    assert tuple(surface.id for surface in settings.surfaces) == tuple(
        sorted(surface.id for surface in settings.surfaces)
    )


def test_unknown_keys_duplicate_surfaces_and_invalid_globs_are_rejected(tmp_path: Path) -> None:
    document = _document()
    document["unexpected"] = True
    with pytest.raises(PostMergeCommissioningSettingsError, match="unknown keys"):
        load_post_merge_commissioning_settings(_write(tmp_path, document))

    document = _document()
    surfaces = document["surfaces"]
    assert isinstance(surfaces, list)
    surfaces.append(deepcopy(surfaces[0]))
    with pytest.raises(PostMergeCommissioningSettingsError, match="duplicate surface"):
        load_post_merge_commissioning_settings(_write(tmp_path, document))

    document = _document()
    surfaces = document["surfaces"]
    assert isinstance(surfaces, list) and isinstance(surfaces[0], dict)
    surfaces[0]["path_patterns"] = ["../outside/**"]
    with pytest.raises(PostMergeCommissioningSettingsError, match="path_patterns"):
        load_post_merge_commissioning_settings(_write(tmp_path, document))


def test_probe_id_is_required_and_uses_closed_vocabulary(tmp_path: Path) -> None:
    document = _document()
    surfaces = document["surfaces"]
    assert isinstance(surfaces, list) and isinstance(surfaces[0], dict)
    del surfaces[0]["probe_id"]
    with pytest.raises(PostMergeCommissioningSettingsError, match="missing required keys"):
        load_post_merge_commissioning_settings(_write(tmp_path, document))

    document = _document()
    surfaces = document["surfaces"]
    assert isinstance(surfaces, list) and isinstance(surfaces[0], dict)
    surfaces[0]["probe_id"] = "arbitrary-tool"
    with pytest.raises(PostMergeCommissioningSettingsError, match="probe_id"):
        load_post_merge_commissioning_settings(_write(tmp_path, document))


def test_live_surface_classification_is_deterministic_and_deduplicated(tmp_path: Path) -> None:
    settings = load_post_merge_commissioning_settings(_write(tmp_path, _document()))
    result = classify_change(
        _evidence(
            (
                "src/kis_mcp/providers/github/service.py",
                "src/kis_mcp/work_management/service.py",
                "src/kis_mcp/providers/github/projects/adapter.py",
            )
        ),
        settings,
    )

    assert result.state is ClassificationState.REQUIRED
    assert tuple(item.surface_id for item in result.obligations) == (
        "provider-runtime",
        "work-management",
    )
    assert all(item.commissioning_key.startswith("commission:nielpieterse0/kis-mcp:") for item in result.obligations)


def test_docs_tests_and_governance_only_are_not_required(tmp_path: Path) -> None:
    settings = load_post_merge_commissioning_settings(_write(tmp_path, _document()))
    result = classify_change(
        _evidence(("docs/OPERATIONS.md", "tests/foo/test_bar.py", ".work/changes/999-example/scope.json")),
        settings,
    )

    assert result.state is ClassificationState.NOT_REQUIRED
    assert result.obligations == ()


def test_unmapped_high_risk_change_fails_closed(tmp_path: Path) -> None:
    settings = load_post_merge_commissioning_settings(_write(tmp_path, _document()))
    result = classify_change(_evidence(("src/kis_mcp/other.py",), ("deployment",)), settings)

    assert result.state is ClassificationState.BLOCKED_AMBIGUOUS
    assert result.obligations == ()
    assert result.ambiguous_risk_triggers == ("deployment",)


def test_surface_risk_trigger_can_supply_obligation_without_path_match(tmp_path: Path) -> None:
    settings = load_post_merge_commissioning_settings(_write(tmp_path, _document()))
    result = classify_change(_evidence(("src/kis_mcp/other.py",), ("security",)), settings)

    assert result.state is ClassificationState.REQUIRED
    assert tuple(item.surface_id for item in result.obligations) == ("provider-runtime",)


def test_commissioning_key_normalizes_repository_and_rejects_bad_identity() -> None:
    assert commissioning_key("NielPieterse0/KIS-MCP", "A" * 40, "work-management") == (
        "commission:nielpieterse0/kis-mcp:" + "a" * 40 + ":work-management"
    )

    with pytest.raises(ValueError, match="repository"):
        commissioning_key("not-a-repository", "a" * 40, "work-management")
    with pytest.raises(ValueError, match="merge_sha"):
        commissioning_key("owner/repo", "abc", "work-management")
    with pytest.raises(ValueError, match="surface_id"):
        commissioning_key("owner/repo", "a" * 40, "Bad Surface")


def test_checked_in_classifier_covers_change_227_work_management_surface() -> None:
    settings = load_post_merge_commissioning_settings()
    result = classify_change(
        _evidence(
            (
                "src/kis_mcp/providers/github/projects/schema_commissioning.py",
                "src/kis_mcp/projects/github_exact.py",
            ),
            ("architecture_boundary", "external_action", "public_contract"),
        ),
        settings,
    )

    assert result.state is ClassificationState.REQUIRED
    assert "work-management" in {item.surface_id for item in result.obligations}


def test_checked_in_classifier_covers_post_merge_observer_surface() -> None:
    settings = load_post_merge_commissioning_settings()
    result = classify_change(
        _evidence(
            (
                "src/kis_mcp/commissioning_runtime/service.py",
                "settings/post-merge-commissioning.settings.json",
            ),
            ("architecture_boundary", "persistent_state"),
        ),
        settings,
    )

    assert result.state is ClassificationState.REQUIRED
    assert "post-merge-observer" in {item.surface_id for item in result.obligations}
