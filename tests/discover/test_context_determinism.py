from __future__ import annotations

from kis_mcp.discover.context_ranking import (
    relevance_sort_key,
    score_named_candidate,
    score_path_candidate,
    score_relationship_candidate,
    stable_fingerprint,
    task_terms,
)


def test_task_terms_split_case_separators_and_remove_generic_words() -> None:
    assert task_terms(
        "Add GitLab merge-request evidence to inspect_change and HTTPProvider"
    ) == (
        "git",
        "lab",
        "merge",
        "request",
        "evidence",
        "inspect",
        "change",
        "http",
        "provider",
    )


def test_path_scoring_prefers_direct_terms_and_category_intent() -> None:
    terms = task_terms("repair verification tests for context broker")

    direct = score_path_candidate(
        "tests/discover/test_context_broker.py",
        category="test",
        terms=terms,
        git_changed=True,
    )
    source = score_path_candidate(
        "src/kis_mcp/discover/context_broker.py",
        category="source",
        terms=terms,
    )
    unrelated = score_path_candidate(
        "docs/deployment.md",
        category="documentation",
        terms=terms,
    )

    assert direct.score > source.score > unrelated.score
    assert direct.matched_terms == ("test", "context", "broker")
    assert direct.git_changed is True


def test_named_scoring_prefers_exact_symbol_over_path_only_match() -> None:
    terms = task_terms("fix ContextBroker assemble_context")
    exact = score_named_candidate(
        identifier="kis_mcp.discover.context_broker.ContextBroker.assemble_context",
        name="assemble_context",
        path="src/kis_mcp/discover/context_broker.py",
        kind="method",
        terms=terms,
        parent_score=80,
    )
    path_only = score_named_candidate(
        identifier="kis_mcp.discover.context_broker.BudgetCompactor.apply",
        name="apply",
        path="src/kis_mcp/discover/context_broker.py",
        kind="method",
        terms=terms,
        parent_score=80,
    )

    assert exact.score > path_only.score
    assert exact.matched_terms == ("context", "broker", "assemble")


def test_relationship_scoring_rewards_selected_connections() -> None:
    terms = task_terms("context broker")
    connected = score_relationship_candidate(
        kind="call",
        source="ContextBroker.assemble",
        target="rank_context",
        path="src/context_broker.py",
        terms=terms,
        selected={"ContextBroker.assemble"},
    )
    unrelated = score_relationship_candidate(
        kind="import",
        source="settings",
        target="json",
        path="src/settings.py",
        terms=terms,
        selected={"ContextBroker.assemble"},
    )

    assert connected.score > unrelated.score
    assert connected.connected is True
    assert unrelated.connected is False


def test_sort_key_and_fingerprint_are_deterministic() -> None:
    candidates = [
        (20, "src/Z.py"),
        (20, "src/a.py"),
        (30, "src/m.py"),
        (20, "src/A.py"),
    ]

    ordered = sorted(candidates, key=lambda item: relevance_sort_key(item[0], item[1]))

    assert ordered == [
        (30, "src/m.py"),
        (20, "src/A.py"),
        (20, "src/a.py"),
        (20, "src/Z.py"),
    ]
    assert stable_fingerprint({"b": [2, 1], "a": {"y": 2, "x": 1}}) == stable_fingerprint(
        {"a": {"x": 1, "y": 2}, "b": [2, 1]}
    )
    assert len(stable_fingerprint({"value": 1})) == 64
