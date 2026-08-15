from __future__ import annotations

from types import SimpleNamespace

import pytest

from kis_mcp.workflows.verification.selection import (
    VerificationSelectionError,
    VerificationSelectionService,
)


def _handoff(
    verification_id: str,
    *,
    category: str = "test",
    profile: str = "python",
    arguments: tuple[str, ...] = ("-m", "pytest", "-q"),
    source_path: str = "pyproject.toml",
):
    return SimpleNamespace(
        verification_id=verification_id,
        category=category,
        reason=f"Run {verification_id}",
        profile=profile,
        arguments=arguments,
        source_path=source_path,
        target_plane="work",
        workflow="run_verification",
        execution_available=False,
    )


def _service(handoffs, declarations, *, source_fingerprint: str | None = None):
    impact = SimpleNamespace(
        verification_handoffs=tuple(handoffs),
        fingerprint="f" * 64,
        truncated=False,
        truncation_reasons=(),
    )
    change = (
        None
        if source_fingerprint is None
        else SimpleNamespace(change=SimpleNamespace(fingerprint=source_fingerprint))
    )
    analysis = SimpleNamespace(impact=impact, change=change)
    analyzer = SimpleNamespace(analyze=lambda request: analysis)
    inspection = SimpleNamespace(verification={"declarations": declarations})
    inspector = SimpleNamespace(inspect=lambda request: inspection)
    return VerificationSelectionService(analyzer=analyzer, inspector=inspector)


def _declaration(
    verification_id: str,
    *,
    category: str = "test",
    profile: str = "python",
    arguments: tuple[str, ...] = ("-m", "pytest", "-q"),
    source_path: str = "pyproject.toml",
):
    return {
        "id": verification_id,
        "category": category,
        "profile": profile,
        "arguments": list(arguments),
        "source_path": source_path,
        "execution_available": False,
    }


def test_selects_only_current_executable_handoffs_in_stable_priority_order() -> None:
    handoffs = (
        _handoff("python-ruff", category="lint", arguments=("-m", "ruff", "check", ".")),
        _handoff("python-pytest"),
        _handoff("repo-verify", category="repository_verification", profile="powershell_verify", arguments=()),
    )
    declarations = [
        _declaration("python-pytest"),
        _declaration("python-ruff", category="lint", arguments=("-m", "ruff", "check", ".")),
        _declaration("repo-verify", category="repository_verification", profile="powershell_verify", arguments=()),
    ]

    result = _service(handoffs, declarations).select(project=r"C:\Projects\fixture")

    assert [item.verification_id for item in result.selected] == [
        "repo-verify",
        "python-pytest",
        "python-ruff",
    ]
    assert result.skipped == ()
    assert result.source_fingerprint == "f" * 64
    assert result.truncated is False


def test_selection_prefers_canonical_inspected_change_fingerprint() -> None:
    handoffs = (_handoff("python-pytest"),)
    declarations = [_declaration("python-pytest")]

    result = _service(
        handoffs,
        declarations,
        source_fingerprint="c" * 64,
    ).select(project=r"C:\Projects\fixture")

    assert result.source_fingerprint == "c" * 64


def test_stale_and_unsupported_handoffs_are_reported_not_executed() -> None:
    handoffs = (
        _handoff("stale", arguments=("-m", "pytest")),
        _handoff("unsupported", profile="custom", arguments=("verify",)),
        _handoff("missing"),
    )
    declarations = [
        _declaration("stale", arguments=("-m", "pytest", "-q")),
        _declaration("unsupported", profile="custom", arguments=("verify",)),
    ]

    result = _service(handoffs, declarations).select(project=r"C:\Projects\fixture")

    assert result.selected == ()
    assert [(item.verification_id, item.code) for item in result.skipped] == [
        ("missing", "VERIFICATION_SELECTION_DECLARATION_MISSING"),
        ("stale", "VERIFICATION_SELECTION_HANDOFF_STALE"),
        ("unsupported", "VERIFICATION_SELECTION_PROFILE_UNSUPPORTED"),
    ]


def test_selection_is_bounded_without_converting_discover_to_execution_authority() -> None:
    handoffs = tuple(_handoff(f"test-{index}") for index in range(4))
    declarations = [_declaration(f"test-{index}") for index in range(4)]

    result = _service(handoffs, declarations).select(
        project=r"C:\Projects\fixture",
        max_verifications=2,
    )

    assert [item.verification_id for item in result.selected] == ["test-0", "test-1"]
    assert result.truncated is True
    assert result.omitted_count == 2
    assert all(item.execution_available is False for item in result.selected)


def test_selection_rejects_invalid_limits_before_analysis() -> None:
    service = _service((), ())

    with pytest.raises(VerificationSelectionError) as raised:
        service.select(project=r"C:\Projects\fixture", max_verifications=0)

    assert raised.value.code == "VERIFICATION_SELECTION_LIMIT_INVALID"
