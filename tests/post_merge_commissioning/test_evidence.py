from __future__ import annotations

import asyncio
import base64
import hashlib
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

    async def read(self, operation: str, arguments: dict[str, Any]) -> Any:
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


def _pr(
    *, merged: bool = True, body: str | None = None, changed_files: int = 3
) -> dict[str, Any]:
    return {
        "number": 452,
        "state": "closed",
        "merged": merged,
        "merged_at": "2026-08-21T14:28:15Z",
        "changed_files": changed_files,
        "body": body
        or "## Summary\n\nIssue: #419\nChange: 227-post-merge-project-field-commissioning",
        "head": {
            "sha": HEAD_SHA,
            "ref": "change/227-post-merge-project-field-commissioning",
            "repo": {"full_name": "NielPieterse0/kis-mcp"},
        },
        "base": {"ref": "main"},
    }


def _commits(message: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "sha": MERGE_SHA,
            "commit": {
                "message": message
                or "Merge pull request #452 from NielPieterse0/change/227-post-merge-project-field-commissioning\n\nAdd bounded Project field commissioning",
                "committer": {"date": "2026-08-21T14:28:15Z"},
            },
            "committer": {"login": "web-flow"},
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
        "branch": "change/227-post-merge-project-field-commissioning",
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


def _blob_sha(text: str) -> str:
    content = text.encode("utf-8")
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _tree(scope_text: str) -> dict[str, Any]:
    return {
        "sha": MERGE_SHA,
        "tree_sha": MERGE_SHA,
        "truncated": False,
        "tree": [
            {
                "path": ".work/changes/227-post-merge-project-field-commissioning/scope.json",
                "type": "blob",
                "sha": _blob_sha(scope_text),
            }
        ],
    }


def _board(
    *,
    source_issue: int = 419,
    change_id: str = "227-post-merge-project-field-commissioning",
    repository: str = "NielPieterse0/kis-mcp",
) -> dict[str, Any]:
    return {
        "provenance": {"complete": True},
        "result": {
            "complete": True,
            "truncated": False,
            "cards": [
                {
                    "number": source_issue,
                    "repository": repository,
                    "change_id": change_id,
                }
            ],
        },
    }


def _responses(
    *, pr: dict[str, Any] | None = None, commits: list[dict[str, Any]] | None = None,
    commit: dict[str, Any] | None = None, scope: str | None = None,
    source_commits: list[dict[str, Any]] | None = None,
) -> dict[str, list[Any]]:
    scope_text = scope if scope is not None else _scope()
    return {
        "github_pull_request_read": [
            pr or _pr(),
            source_commits if source_commits is not None else [{"sha": HEAD_SHA}],
        ],
        "github_list_commits": [commits or _commits()],
        "github_get_commit": [commit or _commit()],
        "github_get_repository_tree": [_tree(scope_text)],
        "github_get_file_contents": [scope_text],
        "project_management_board_data": [_board()],
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


def test_markerless_pull_request_resolves_from_unique_landed_scope(tmp_path: Path) -> None:
    invoker = FakeInvoker(_responses(pr=_pr(body="Tracks #419.")))
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.source_issue == 419
    assert evidence.change_id == "227-post-merge-project-field-commissioning"
    assert evidence.merge_sha == MERGE_SHA


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
    duplicate = json.loads(json.dumps(_commits()[0]))
    duplicate["sha"] = "c" * 40
    commits = _commits() + [duplicate]
    responses = _responses(commits=commits)
    responses.pop("github_get_commit")
    responses.pop("github_get_file_contents")
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="merge_commit_ambiguous"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_merge_commit_message_must_match_provider_head_ref(tmp_path: Path) -> None:
    commits = _commits(
        "Merge pull request #452 from NielPieterse0/change/999-other-governed-change"
    )
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(commits=commits)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="merge_commit_missing"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_merge_commit_requires_provider_native_web_flow_identity(tmp_path: Path) -> None:
    commits = _commits()
    commits[0]["committer"] = {"login": "NielPieterse0"}
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(commits=commits)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="merge_commit_missing"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize(
    "committed_at",
    ["2026-08-21T14:28:14Z", "2026-08-21T14:28:16Z", "2026-08-21T14:27:16Z"],
)
def test_merge_commit_time_allows_subminute_provider_drift(
    tmp_path: Path, committed_at: str
) -> None:
    commits = _commits()
    commits[0]["commit"]["committer"]["date"] = committed_at
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(commits=commits)), _settings(tmp_path)
    )

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.merge_sha == MERGE_SHA


@pytest.mark.parametrize(
    "committed_at",
    ["2026-08-21T14:27:15Z", "2026-08-21T14:29:15Z"],
)
def test_merge_commit_time_rejects_minute_level_mismatch(
    tmp_path: Path, committed_at: str
) -> None:
    commits = _commits()
    commits[0]["commit"]["committer"]["date"] = committed_at
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(commits=commits)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="merge_commit_missing"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_invalid_lookalike_merge_does_not_mask_valid_provider_merge(tmp_path: Path) -> None:
    forged = json.loads(json.dumps(_commits()[0]))
    forged["sha"] = "c" * 40
    forged["committer"] = {"login": "NielPieterse0"}
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(commits=[forged, *_commits()])), _settings(tmp_path)
    )

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.merge_sha == MERGE_SHA


def test_source_commit_cannot_impersonate_provider_merge(tmp_path: Path) -> None:
    forged = json.loads(json.dumps(_commits()[0]))
    forged["sha"] = HEAD_SHA
    resolver = MergedChangeResolver(
        FakeInvoker(
            _responses(
                commits=[forged, *_commits()],
                source_commits=[{"sha": HEAD_SHA}],
            )
        ),
        _settings(tmp_path),
    )

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.merge_sha == MERGE_SHA


@pytest.mark.parametrize(
    "body",
    [
        "Issue: #419",
        "Change: 227-post-merge-project-field-commissioning",
        "Issue: #419\nIssue: #420\nChange: 227-post-merge-project-field-commissioning",
        "Issue: 419\nChange: 227-post-merge-project-field-commissioning",
        "Issue: #419\nChange: bad change id",
        "Issue: #999\nChange: 999-other-governed-change",
    ],
)
def test_pr_body_text_does_not_gate_exact_landed_scope_identity(
    tmp_path: Path, body: str
) -> None:
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(pr=_pr(body=body))), _settings(tmp_path)
    )

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.source_issue == 419
    assert evidence.change_id == "227-post-merge-project-field-commissioning"
    assert evidence.merge_sha == MERGE_SHA


@pytest.mark.parametrize(
    ("scope_text", "code"),
    [
        ("not-json", "scope_invalid"),
        (_scope(schema_version=3), "scope_invalid"),
        (_scope(change_id="999-other"), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "other/repo", "source_number": 419, "source_kind": "issue"}), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "NielPieterse0/kis-mcp", "source_number": 0, "source_kind": "issue"}), "scope_identity_mismatch"),
        (_scope(work_management={"source_repository": "NielPieterse0/kis-mcp", "source_number": 419, "source_kind": "pull_request"}), "scope_identity_mismatch"),
        (_scope(risk_triggers=["architecture_boundary", ""]), "scope_invalid"),
        (_scope(risk_triggers=["architecture_boundary", 7]), "scope_invalid"),
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


def test_merge_commit_pagination_rejects_repeated_full_page(tmp_path: Path) -> None:
    page = [
        {"sha": f"{index + 1:040x}", "commit": {"message": f"ordinary commit {index}"}}
        for index in range(100)
    ]
    responses = _responses()
    responses["github_list_commits"] = [page, page]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    pages = [args["page"] for op, args in invoker.calls if op == "github_list_commits"]
    assert pages == [1, 2]


def test_merge_commit_pagination_has_local_page_bound(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import kis_mcp.commissioning.evidence as evidence_module

    page = [
        {"sha": f"{index + 1:040x}", "commit": {"message": f"ordinary commit {index}"}}
        for index in range(100)
    ]
    monkeypatch.setattr(evidence_module, "_MAX_MERGE_COMMIT_PAGES", 1)
    responses = _responses()
    responses["github_list_commits"] = [page]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    pages = [args["page"] for op, args in invoker.calls if op == "github_list_commits"]
    assert pages == [1]


def test_merge_and_file_evidence_paginate_to_completion(tmp_path: Path) -> None:
    ordinary_commits = [
        {"sha": f"{index + 1:040x}", "commit": {"message": f"ordinary commit {index}"}}
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
            "github_pull_request_read": [
                _pr(changed_files=102),
                [{"sha": HEAD_SHA}],
            ],
            "github_list_commits": [ordinary_commits, _commits()],
            "github_get_commit": [first_files, second_files],
            "github_get_repository_tree": [_tree(_scope())],
            "github_get_file_contents": [_scope()],
            "project_management_board_data": [_board()],
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
    invoker = FakeInvoker(_responses(pr=_pr(changed_files=1), commit=commit))
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="scope_path_missing"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert all(operation != "github_get_file_contents" for operation, _ in invoker.calls)


def test_multiple_changed_scope_paths_fail_closed(tmp_path: Path) -> None:
    commit = _commit()
    commit["files"].append(
        {"filename": ".work/changes/999-other-governed-change/scope.json"}
    )
    invoker = FakeInvoker(
        _responses(pr=_pr(body="Tracks #419.", changed_files=4), commit=commit)
    )
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="scope_path_ambiguous"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert all(operation != "github_get_file_contents" for operation, _ in invoker.calls)


def test_changed_file_count_mismatch_is_retryable_provider_evidence(
    tmp_path: Path,
) -> None:
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(pr=_pr(changed_files=4))), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_invalid_pull_request_changed_file_count_is_retryable_provider_evidence(
    tmp_path: Path,
) -> None:
    pr = _pr()
    pr["changed_files"] = None
    resolver = MergedChangeResolver(
        FakeInvoker({"github_pull_request_read": [pr]}), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_unreadable_scope_provider_content_is_retryable_provider_evidence(
    tmp_path: Path,
) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = [
        {"content": "%%%not-base64%%%", "encoding": "base64"}
    ]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_missing_scope_provider_content_is_retryable_provider_evidence(
    tmp_path: Path,
) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = [{"unexpected": "shape"}]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_truncated_scope_tree_is_retryable_provider_evidence(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["truncated"] = True
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_tree_blob_mismatch_is_retryable_provider_evidence(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"][0]["sha"] = "c" * 40
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_readable_wrong_scope_payload_is_retryable_provider_evidence(tmp_path: Path) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = ["{}"]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_pull_request_head_ref_must_match_landed_change_id(tmp_path: Path) -> None:
    pr = _pr()
    pr["head"] = {
        "sha": HEAD_SHA,
        "ref": "change/999-other-governed-change",
        "repo": {"full_name": "NielPieterse0/kis-mcp"},
    }
    commits = _commits(
        "Merge pull request #452 from NielPieterse0/change/999-other-governed-change"
    )
    invoker = FakeInvoker(_responses(pr=pr, commits=commits))
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="scope_identity_mismatch"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert all(operation != "project_management_board_data" for operation, _ in invoker.calls)


def test_source_work_change_id_corroborates_landed_scope(tmp_path: Path) -> None:
    responses = _responses()
    responses["project_management_board_data"] = [_board()]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.source_issue == 419
    work_calls = [args for op, args in invoker.calls if op == "project_management_board_data"]
    assert work_calls == [{
        "project_id": "kis-mcp", "include_history": True, "query": "419",
        "group_by": "state", "item_limit": 1000,
    }]

def test_incomplete_source_work_binding_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    responses["project_management_board_data"] = [{
        "provenance": {"complete": False},
        "result": {"complete": False, "truncated": False, "cards": []},
    }]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_source_work_change_id_mismatch_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    responses["project_management_board_data"] = [
        _board(change_id="999-other-governed-change")
    ]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_source_work_card_must_be_unique_for_exact_issue(tmp_path: Path) -> None:
    responses = _responses()
    board = _board()
    board["result"]["cards"].append(dict(board["result"]["cards"][0]))
    responses["project_management_board_data"] = [board]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

def test_scope_provider_wrapper_depth_is_bounded(tmp_path: Path) -> None:
    responses = _responses()
    value: Any = _scope()
    for _ in range(8):
        value = {"data": value}
    responses["github_get_file_contents"] = [value]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_provider_content_size_is_bounded(tmp_path: Path) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = ["x" * 1_100_000]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(
        MergeEvidenceError, match="scope provider content exceeds size limit"
    ):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_tree_entry_count_is_bounded(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"].extend(
        {
            "path": f"docs/unrelated-{index}.md",
            "type": "blob",
            "sha": "c" * 40,
        }
        for index in range(20)
    )
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

def test_pull_request_head_repository_must_be_governed_repository(
    tmp_path: Path,
) -> None:
    pr = _pr()
    pr["head"] = {
        "sha": HEAD_SHA,
        "ref": "change/227-post-merge-project-field-commissioning",
        "repo": {"full_name": "OtherOwner/kis-mcp"},
    }
    invoker = FakeInvoker(_responses(pr=pr))
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert [operation for operation, _ in invoker.calls] == ["github_pull_request_read"]


def test_non_governed_pull_request_head_ref_is_retryable(tmp_path: Path) -> None:
    pr = _pr()
    pr["head"] = {
        "sha": HEAD_SHA,
        "ref": "feature/not-a-governed-change",
        "repo": {"full_name": "NielPieterse0/kis-mcp"},
    }
    invoker = FakeInvoker({"github_pull_request_read": [pr]})
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert [operation for operation, _ in invoker.calls] == ["github_pull_request_read"]


def test_landed_scope_branch_must_match_governed_change_branch(tmp_path: Path) -> None:
    scope_text = _scope(branch="change/999-other-governed-change")
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(scope=scope_text)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="scope_identity_mismatch"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

def test_source_work_card_missing_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    responses["project_management_board_data"] = [{
        "provenance": {"complete": True},
        "result": {"complete": True, "truncated": False, "cards": []},
    }]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_source_work_repository_mismatch_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    responses["project_management_board_data"] = [
        _board(repository="OtherOwner/kis-mcp")
    ]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_provider_content_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    scope_text = _scope()
    scope_text += " " * (1_048_576 - len(scope_text.encode("utf-8")))
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(scope=scope_text)), _settings(tmp_path)
    )

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.change_id == "227-post-merge-project-field-commissioning"


def test_scope_provider_content_one_byte_over_limit_is_retryable(tmp_path: Path) -> None:
    scope_text = _scope()
    scope_text += " " * (1_048_577 - len(scope_text.encode("utf-8")))
    resolver = MergedChangeResolver(
        FakeInvoker(_responses(scope=scope_text)), _settings(tmp_path)
    )

    with pytest.raises(MergeEvidenceError, match="scope provider content exceeds size limit"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_provider_wrapper_exact_depth_limit_is_accepted(tmp_path: Path) -> None:
    value: Any = _scope()
    for _ in range(4):
        value = {"data": value}
    responses = _responses()
    responses["github_get_file_contents"] = [value]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.source_issue == 419


def test_scope_provider_wrapper_one_over_limit_is_retryable(tmp_path: Path) -> None:
    value: Any = _scope()
    for _ in range(5):
        value = {"data": value}
    responses = _responses()
    responses["github_get_file_contents"] = [value]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_tree_exact_entry_limit_is_accepted(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"].extend(
        {"path": f"docs/unrelated-{index}.md", "type": "blob", "sha": "c" * 40}
        for index in range(15)
    )
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.change_id == "227-post-merge-project-field-commissioning"


def test_scope_tree_one_entry_over_limit_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"].extend(
        {"path": f"docs/unrelated-{index}.md", "type": "blob", "sha": "c" * 40}
        for index in range(16)
    )
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize("tree_sha", [None, "c" * 40])
def test_scope_tree_commitish_echo_must_match_merge_sha(
    tmp_path: Path, tree_sha: str | None
) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree_sha"] = tree_sha
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def _scope_at_size(size: int) -> str:
    text = _scope()
    encoded = text.encode("utf-8")
    assert len(encoded) <= size
    return text + (" " * (size - len(encoded)))


def test_scope_provider_bytes_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    scope_text = _scope_at_size(1_048_576)
    responses = _responses(scope=scope_text)
    responses["github_get_file_contents"] = [scope_text.encode("utf-8")]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.source_issue == 419


def test_scope_provider_bytes_one_over_limit_is_retryable(tmp_path: Path) -> None:
    scope_text = _scope_at_size(1_048_577)
    responses = _responses(scope=scope_text)
    responses["github_get_file_contents"] = [scope_text.encode("utf-8")]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(
        MergeEvidenceError, match="scope provider content exceeds size limit"
    ):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_provider_base64_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    scope_text = _scope_at_size(1_048_576)
    encoded = base64.b64encode(scope_text.encode("utf-8")).decode("ascii")
    responses = _responses(scope=scope_text)
    responses["github_get_file_contents"] = [
        {"content": encoded, "encoding": "base64"}
    ]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    evidence = asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert evidence.change_id == "227-post-merge-project-field-commissioning"


def test_scope_provider_base64_one_over_limit_is_retryable(tmp_path: Path) -> None:
    scope_text = _scope_at_size(1_048_577)
    encoded = base64.b64encode(scope_text.encode("utf-8")).decode("ascii")
    responses = _responses(scope=scope_text)
    responses["github_get_file_contents"] = [
        {"content": encoded, "encoding": "base64"}
    ]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(
        MergeEvidenceError, match="scope provider content exceeds size limit"
    ):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_provider_multibyte_encoded_size_is_bounded(tmp_path: Path) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = ["é" * 600_000]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(
        MergeEvidenceError, match="scope provider content exceeds size limit"
    ):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize("tree_sha", [None, "c" * 40])
def test_scope_tree_primary_sha_must_match_merge_sha(
    tmp_path: Path, tree_sha: str | None
) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["sha"] = tree_sha
    responses["github_get_repository_tree"] = [tree]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert all(op != "github_get_file_contents" for op, _ in invoker.calls)


def test_scope_tree_requires_exactly_one_matching_blob(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    duplicate = dict(tree["tree"][0])
    tree["tree"].append(duplicate)
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))
    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


def test_scope_tree_requires_matching_scope_path(tmp_path: Path) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"][0]["path"] = "docs/not-the-scope.md"
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize(
    ("entry_type", "blob_sha"),
    [("tree", "c" * 40), ("blob", "not-a-sha")],
)
def test_scope_tree_entry_must_be_valid_blob(
    tmp_path: Path, entry_type: str, blob_sha: str
) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"][0]["type"] = entry_type
    tree["tree"][0]["sha"] = blob_sha
    responses["github_get_repository_tree"] = [tree]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError, match="provider_evidence_invalid"):
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))


@pytest.mark.parametrize(
    "scope_value",
    [
        b"\xff",
        {"content": base64.b64encode(b"\xff").decode("ascii"), "encoding": "base64"},
    ],
)
def test_scope_provider_invalid_utf8_is_retryable(
    tmp_path: Path, scope_value: Any
) -> None:
    responses = _responses()
    responses["github_get_file_contents"] = [scope_value]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "provider_evidence_invalid"
    assert all(op != "project_management_board_data" for op, _ in invoker.calls)


def test_truncated_source_work_binding_is_retryable(tmp_path: Path) -> None:
    responses = _responses()
    board = _board()
    board["result"]["truncated"] = True
    responses["project_management_board_data"] = [board]
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "provider_evidence_invalid"


@pytest.mark.parametrize("malformed_entry", [None, "invalid-entry", []])
def test_malformed_scope_tree_entry_is_retryable(
    tmp_path: Path, malformed_entry: Any
) -> None:
    responses = _responses()
    tree = _tree(_scope())
    tree["tree"].append(malformed_entry)
    responses["github_get_repository_tree"] = [tree]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "provider_evidence_invalid"
    assert all(op != "github_get_file_contents" for op, _ in invoker.calls)


def test_changed_file_pagination_rejects_nonprogressing_full_page(tmp_path: Path) -> None:
    files = [{"filename": f"src/file-{index:03d}.py"} for index in range(100)]
    page = {"sha": MERGE_SHA, "files": files}
    responses = _responses(pr=_pr(changed_files=101))
    responses["github_get_commit"] = [page, page]
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "provider_evidence_invalid"
    commit_calls = [args for op, args in invoker.calls if op == "github_get_commit"]
    assert [args["page"] for args in commit_calls] == [1, 2]


def test_pull_request_changed_files_accepts_provider_maximum(tmp_path: Path) -> None:
    responses = {
        "github_pull_request_read": [
            _pr(changed_files=3000),
            [{"sha": HEAD_SHA}],
        ],
        "github_list_commits": [_commits("ordinary commit")],
    }
    invoker = FakeInvoker(responses)
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "merge_commit_missing"


def test_pull_request_changed_files_rejects_above_provider_maximum(tmp_path: Path) -> None:
    invoker = FakeInvoker({"github_pull_request_read": [_pr(changed_files=3001)]})
    resolver = MergedChangeResolver(invoker, _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "provider_evidence_invalid"
    assert [op for op, _ in invoker.calls] == ["github_pull_request_read"]


def test_deeply_nested_landed_scope_is_bounded_scope_invalid(tmp_path: Path) -> None:
    scope_text = "[" * 2_000 + "0" + "]" * 2_000
    responses = _responses(scope=scope_text)
    resolver = MergedChangeResolver(FakeInvoker(responses), _settings(tmp_path))

    with pytest.raises(MergeEvidenceError) as caught:
        asyncio.run(resolver.resolve("NielPieterse0/kis-mcp", 452))

    assert caught.value.code == "scope_invalid"
