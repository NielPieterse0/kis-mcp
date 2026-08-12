from __future__ import annotations

from kis_mcp.govern.contracts import GovernanceEvidence
from kis_mcp.govern.service import GovernanceService
from kis_mcp.govern.settings import GovernanceSettings


def _settings(**overrides):
    values = {
        "enabled": True,
        "max_authority_documents": 20,
        "max_file_bytes": 200000,
        "max_findings": 50,
        "min_duplicate_paragraph_chars": 80,
        "enabled_rules": (
            "authority-order", "documentation-ownership", "owner-reference-integrity",
            "duplicate-owner", "duplicate-current-fact", "current-implementation-drift",
        ),
    }
    values.update(overrides)
    return GovernanceSettings(**values)


def _agents(owner_rows: str) -> str:
    return f"""# repo

## Authority order

1. `AGENTS.md` — rules.
2. `SPEC.md` — current truth.
3. `docs/OPERATIONS.md` — operations.

## Documentation ownership and routing

| Information | Canonical owner |
|---|---|
{owner_rows}
"""


def test_parses_authority_and_ownership_without_findings() -> None:
    agents = _agents(
        "| Current implemented product architecture | `SPEC.md` |\n"
        "| Installation and operations | `docs/OPERATIONS.md` |"
    )
    evidence = GovernanceEvidence(
        project=r"C:\Projects\demo",
        agents_text=agents,
        documents=(("AGENTS.md", agents), ("SPEC.md", "# Spec\n"), ("docs/OPERATIONS.md", "# Ops\n")),
        implementation_identifiers=frozenset(),
    )
    report = GovernanceService(_settings()).inspect(evidence)

    assert [item.path for item in report.authority_order] == ["AGENTS.md", "SPEC.md", "docs/OPERATIONS.md"]
    assert report.ownership[0].owner == "SPEC.md"
    assert report.findings == ()
    assert report.unknowns == ()
    assert report.to_json_dict()["policy_effect"] == "advisory_only"


def test_reports_missing_owner_and_conflicting_owner_declarations() -> None:
    agents = _agents(
        "| Current product truth | `SPEC.md` |\n"
        "| Current product truth | `docs/OTHER.md` |"
    )
    evidence = GovernanceEvidence(
        project="demo",
        agents_text=agents,
        documents=(("AGENTS.md", agents), ("SPEC.md", "# Spec")),
        missing_paths=("docs/OPERATIONS.md", "docs/OTHER.md"),
        implementation_identifiers=frozenset(),
    )
    report = GovernanceService(_settings()).inspect(evidence)
    codes = {item.rule_id for item in report.findings}

    assert "owner-reference-integrity" in codes
    assert "duplicate-owner" in codes
    assert all(item.to_json_dict()["owning_plane"] == "govern" for item in report.findings)


def test_exact_long_paragraph_duplicate_is_advisory_evidence() -> None:
    agents = _agents("| Current product truth | `SPEC.md` |\n| Operations | `docs/OPERATIONS.md` |")
    repeated = (
        "This implementation fact is deliberately long enough to be treated as a governed current fact "
        "and it contains the same exact normalized wording in two canonical owner documents for testing."
    )
    evidence = GovernanceEvidence(
        project="demo",
        agents_text=agents,
        documents=(("AGENTS.md", agents), ("SPEC.md", repeated), ("docs/OPERATIONS.md", repeated)),
        implementation_identifiers=frozenset(),
    )
    report = GovernanceService(_settings()).inspect(evidence)
    finding = next(item for item in report.findings if item.rule_id == "duplicate-current-fact")

    assert finding.severity == "warning"
    assert finding.confidence == "medium"
    assert "one canonical owner" in finding.remediation


def test_current_implementation_drift_requires_supplied_implementation_evidence() -> None:
    agents = _agents("| Current implemented product architecture | `SPEC.md` |")
    spec = """# Spec

## Current implementation boundary

- `implemented_tool` is current.
- `stale_tool` is current.
"""
    evidence = GovernanceEvidence(
        project="demo",
        agents_text=agents,
        documents=(("AGENTS.md", agents), ("SPEC.md", spec)),
        implementation_identifiers=frozenset({"implemented_tool"}),
    )
    report = GovernanceService(_settings()).inspect(evidence)

    drift = [item for item in report.findings if item.rule_id == "current-implementation-drift"]
    assert [item.observation.split("`")[1] for item in drift] == ["stale_tool"]

    unknown = GovernanceService(_settings()).inspect(
        GovernanceEvidence(project="demo", agents_text=agents, documents=(("SPEC.md", spec),))
    )
    assert "CURRENT_IMPLEMENTATION_IDENTIFIERS_UNAVAILABLE" in unknown.unknowns


def test_explicit_rule_subset_cannot_enable_undeclared_rules() -> None:
    service = GovernanceService(_settings(enabled_rules=("authority-order",)))
    evidence = GovernanceEvidence(project="demo", agents_text="", documents=())
    report = service.inspect(evidence, rule_ids=("authority-order",))
    assert [item.rule_id for item in report.findings] == ["authority-order"]

    try:
        service.inspect(evidence, rule_ids=("duplicate-owner",))
    except ValueError as exc:
        assert "not enabled" in str(exc)
    else:
        raise AssertionError("disabled governance rule must not be evaluated")
