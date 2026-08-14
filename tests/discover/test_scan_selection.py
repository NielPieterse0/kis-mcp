from __future__ import annotations

from kis_mcp.discover.scan_selection import evidence_path_priority


def test_evidence_priority_orders_project_source_support_docs_and_auxiliary() -> None:
    labels = [
        ".agents/helper.py",
        "misc/tool.py",
        "docs/guide.md",
        "tests/test_app.py",
        "src/app.py",
        "pyproject.toml",
    ]

    assert sorted(labels, key=evidence_path_priority) == [
        "pyproject.toml",
        "src/app.py",
        "tests/test_app.py",
        "docs/guide.md",
        "misc/tool.py",
        ".agents/helper.py",
    ]


def test_same_priority_paths_use_casefolded_lexical_order() -> None:
    labels = ["zeta.py", "Beta.py", "alpha.py"]

    assert sorted(labels, key=evidence_path_priority) == [
        "alpha.py",
        "Beta.py",
        "zeta.py",
    ]


def test_hidden_github_configuration_is_not_treated_as_auxiliary() -> None:
    assert evidence_path_priority(".github/workflows/ci.yml") < evidence_path_priority(
        ".archive/legacy.py"
    )


def test_auxiliary_markdown_remains_lower_priority_than_project_documentation() -> None:
    assert evidence_path_priority(".agents/example.md") > evidence_path_priority(
        "docs/guide.md"
    )
