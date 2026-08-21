from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.commissioning.evidence import MergedChangeResolver, MergeEvidenceError
from kis_mcp.commissioning.settings import load_post_merge_commissioning_settings

MERGE_SHA = "b" * 40
HEAD_SHA = "a" * 40


class FakeInvoker:
    def __init__(self, responses: dict[str, list[Any]]) -> None:
        self.responses = {key: list(value) for key, value in responses.items()}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def external(self, operation: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((operation, dict(arguments)))
        queue = self.responses.get(operation)
        if not queue:
            raise AssertionError(f"unexpected operation: {operation}")
        return queue.pop(0)


def _settings(tmp_path: Path):
    source = Path(__file__).resolve().parents[2] / "settings" / "post-merge-commissioning.settings.json"
    target = tmp_path / source.name
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return load_post_merge_commissioning_settings(target)


def _pr(*, merged: bool = True, body: str | None = None) -> dict[str, Any]:
    return {
        "number": 452,
        "state": "closed",
        "merged": merged,
        "merged_at": "2026-08-21T14:28:15Z",
        "body": body
        or "## Summary\n\nIssue: #419\nChange: 227-post-merge-project-field-commissioning",
        "head": {"sha": HEAD_SHA},
        "base": {"ref": "main"},
    }


def _commits(message: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "sha": MERGE_SHA,
            "commit": {
                "message": message
                or "Merge pull request #452 from NielPieterse0/change/227-post-merge-project-field-commissioning\n\nAdd bounded Project field commissioning"
            },
        }
    ]


def _commit() -> dict[str, Any]:
    return {
        "sha": MERGE_SHA,
        "files": [
            {"filename": ".work/changes/227-post-merge-project-field-commissioning/scope.json"},
            {"filename": "src/kis_mcp/providers/github/projects/schema_commissioning.py"},
            {"filename": "src/kis_mcp/projects/github_exact.py"},
        ],
    }


def _scope(**overrides: Any) -> str:
    document: dict[str, Any] = {
        "schema_version": 4,
        "change_id": "227-post-merge-project-field-commissioning",
        "risk_triggers": ["architecture_boundary", "external_action", "public_contract"],
        "work_management": {
            "project_id": "kis-mcp",
            "record_id": "WORK-419",
            "source_repository": "NielPieterse0/kis-mcp",
            "source_number": 419,
            "source_kind": "issue",
            "documentation_impact": "planned",
            "execution_owner": "codex",
        },
    }
    document.update(overrides)
    return json.dumps(document)


def _responses(
    *, pr: dict[str, Any] | None = None, commits: list[dict[str, Any]] | None = None,
    commit: dict[str, Any] | None = None, scope: str | None = None,
) -> dict[str, list[Any]]:
    return {
        "github_pull_request_read": [pr or _pr()],
        "github_list_commits": [commits or _commits()],
        "github_get_commit": [commit or _commit()],
        "github_get_file_contents": [scope or _scope()],
    }


def test_resolves_exact_landed_change_identity(tmp_path: Path) -> None:
    invoker = FakeInvoker(_responses())
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.repository == "NielPieterse0/kis-mcp"
    assert evidence.source_issue == 419
    assert evidence.source_pr == 452
    assert evidence.merge_sha == MERGE_SHA
    assert evidence.change_id == "227-post-merge-project-field-commissioning"
    assert evidence.risk_triggers == (
        "architecture_boundary",
        "external_action",
        "public_contract",
    )
    assert "src/kis_mcp/projects/github_exact.py" in evidence.changed_paths
    scope_calls = [call for call in invoker.calls if call[0] == "github_get_file_contents"]
    assert scope_calls[0][1]["sha"] == MERGE_SHA


def test_closed_only_pull_request_is_not_eligible(tmp_path: Path) -> None:
    invoker = FakeInvoker({"github_pull_request_read": [_pr(merged=False)]})
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="pr_not_merged"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))
    assert [call[0] for call in invoker.calls] == ["github_pull_request_read"]


def test_merge_commit_must_uniquely_identify_the_pull_request(tmp_path: Path) -> None:
    responses = _responses(commits=_commits("ordinary commit"))
    responses.pop("github_get_commit")
    responses.pop("github_get_file_contents")
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="merge_commit_missing"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_multiple_matching_merge_commits_fail_closed(tmp_path: Path) -> None:
    commits = _commits() + [{"sha": "c" * 40, "commit": {"message": _commits()[0]["commit"]["message"]}}]
    responses = _responses(commits=commits)
    responses.pop("github_get_commit")
    responses.pop("github_get_file_contents")
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="merge_commit_ambiguous"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize(
    "body",
    [
        "Issue: #419",
        "Change: 227-post-merge-project-field-commissioning",
        "Issue: #419\nIssue: #420\nChange: 227-post-merge-project-field-commissioning",
        "Issue: 419\nChange: 227-post-merge-project-field-commissioning",
        "Issue: #419\nChange: bad change id",
    ],
)
def test_pr_markers_are_strict_and_unique(tmp_path: Path, body: str) -> None:
    responses = _responses(pr=_pr(body=body))
    responses.pop("github_list_commits")
    responses.pop("github_get_commit")
    responses.pop("github_get_file_contents")
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="pr_markers_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize(
    ("scope_text", "code"),
    [
        ("not-json", "scope_invalid"),
        (_scope(schema_version=3), "scope_invalid"),
        (_scope(change_id="999-other"), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "other/repo", "source_number": 419, "source_kind": "issue"}), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "NielPieterse0/kis-mcp", "source_number": 420, "source_kind": "issue"}), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "NielPieterse0/kis-mcp", "source_number": 419, "source_kind": "pull_request"}), "scope_identity_mismatch"),
    ],
)
def test_landed_scope_identity_is_required(
    tmp_path: Path, scope_text: str, code: str
) -> None:
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(scope=scope_text)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match=code):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_unknown_repository_target_is_rejected_before_provider_reads(tmp_path: Path) -> None:
    invoker = FakeInvoker({})
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="repository_not_configured"):
        asyncio.run(resolver.resolve("other/repo", 1))
    assert invoker.calls == []


def test_merge_and_file_evidence_paginate_to_completion(tmp_path: Path) -> None:
    ordinary_commits = [
        {"sha": "c" * 40, "commit": {"message": f"ordinary commit {index}"}}
        for index in range(100)
    ]
    first_files = {
        "sha": MERGE_SHA,
        "files": [{"filename": f"docs/page-one-{index}.md"} for index in range(100)],
    }
    second_files = {
        "sha": MERGE_SHA,
        "files": [
            {"filename": ".work/changes/227-post-merge-project-field-commissioning/scope.json"},
            {"filename": "src/kis_mcp/work_management/service.py"},
        ],
    }
    invoker = FakeInvoker(
        {
            "github_pull_request_read": [_pr()],
            "github_list_commits": [ordinary_commits, _commits()],
            "github_get_commit": [first_files, second_files],
            "github_get_file_contents": [_scope()],
        }
    )

    evidence = asyncio.run(
        MergedChangeResolver(invoker, _settings(tmp_path)).resolve(
            "NielPieterse0/kis-mcp", 452
        )
    )

    assert "src/kis_mcp/work_management/service.py" in evidence.changed_paths
    commit_pages = [args["page"] for op, args in invoker.calls if op == "github_list_commits"]
    file_pages = [args["page"] for op, args in invoker.calls if op == "github_get_commit"]
    assert commit_pages == [1, 2]
    assert file_pages == [1, 2]


def test_scope_must_be_part_of_the_observed_merge_file_set(tmp_path: Path) -> None:
    commit = {
        "sha": MERGE_SHA,
        "files": [{"filename": "src/kis_mcp/work_management/service.py"}],
    }
    invoker = FakeInvoker(_responses(commit=commit))
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="scope_identity_mismatch"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert all(operation != "github_get_file_contents" for operation, _ in invoker.calls)
