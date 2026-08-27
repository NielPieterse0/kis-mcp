from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from hashlib import sha1
from pathlib import Path
from threading import Barrier, Thread
from types import SimpleNamespace

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import GitHubProjectBinding, ProjectDefinition, ProjectRegistry
from kis_mcp.projects.github_merge_queue import (
    CandidateCheck,
    MergeQueueCoordinator,
    MergeQueueSettings,
    PullRequestSnapshot,
    QueueStateStore,
    QueueTarget,
    RegisteredGitHubMergeQueueBackend,
    RegisteredGitHubMergeQueueOperations,
    _queue_state_key,
    load_merge_queue_settings,
)
from kis_mcp.projects.post_land import PostLandHooks

BASE = "1" * 40
H1 = "2" * 40
H2 = "3" * 40
H3 = "4" * 40
H4 = "5" * 40


def _post_land_hooks(
    dispatcher: Callable[..., None],
    failure_recorder: Callable[..., None] | None = None,
) -> PostLandHooks:
    return PostLandHooks(
        dispatcher=dispatcher,
        failure_recorder=failure_recorder or (lambda *args: None),
    )


class FakeBackend:
    def __init__(self, root: Path) -> None:
        self.target_value = QueueTarget("kis-mcp", "NielPieterse0/kis-mcp", root, "https://github.com/NielPieterse0/kis-mcp.git")
        self.live_base = BASE
        self.prs = {
            1: PullRequestSnapshot(1, H1, "one", "main", "OPEN", False, "https://example/1"),
            2: PullRequestSnapshot(2, H2, "two", "main", "OPEN", False, "https://example/2"),
            3: PullRequestSnapshot(3, H3, "three", "main", "OPEN", False, "https://example/3"),
            4: PullRequestSnapshot(4, H4, "four", "main", "OPEN", False, "https://example/4"),
        }
        self.checks: dict[str, CandidateCheck] = {}
        self.ancestry: dict[str, set[str]] = {}
        self.published: list[tuple[str, str]] = []
        self.land_calls: list[tuple[str, str, str]] = []
        self.conflicts: set[str] = set()

    def target(self, project_id: str) -> QueueTarget:
        assert project_id == "kis-mcp"
        return self.target_value

    def prepare(self, target: QueueTarget, target_branch: str) -> str:
        assert target == self.target_value
        assert target_branch == "main"
        return self.live_base

    def pull_request(self, target: QueueTarget, pull_number: int) -> PullRequestSnapshot:
        return self.prs[pull_number]

    def build_candidate(
        self, target: QueueTarget, pull_number: int, parent: str, head: str, message: str
    ) -> str | None:
        assert pull_number in self.prs
        if head in self.conflicts:
            return None
        digest = sha1(f"{parent}|{head}|{message}".encode()).hexdigest()
        inherited = set(self.ancestry.get(parent, {parent}))
        self.ancestry[digest] = inherited | {parent, head}
        return digest

    def publish_candidate(self, target: QueueTarget, branch: str, candidate_sha: str) -> None:
        self.published.append((branch, candidate_sha))

    def candidate_check(self, target: QueueTarget, branch: str, candidate_sha: str) -> CandidateCheck:
        return self.checks.get(candidate_sha, CandidateCheck("pending", None, None, None))

    def is_ancestor(self, target: QueueTarget, ancestor: str, descendant: str) -> bool:
        return ancestor == descendant or ancestor in self.ancestry.get(descendant, set())

    def advance_base(self, target: QueueTarget, target_branch: str, expected_base: str, candidate_sha: str) -> None:
        assert self.live_base == expected_base
        self.land_calls.append((target_branch, expected_base, candidate_sha))
        self.live_base = candidate_sha


def coordinator(tmp_path: Path, *, build_concurrency: int = 3) -> tuple[MergeQueueCoordinator, FakeBackend]:
    settings = MergeQueueSettings(
        enabled=True,
        state_root=tmp_path / "state",
        target_branch="main",
        merge_method="merge",
        grouping_strategy="allgreen",
        build_concurrency=build_concurrency,
        status_check_timeout_minutes=30,
        min_entries_to_merge=1,
        max_entries_to_merge=3,
        min_entries_to_merge_wait_minutes=0,
        allow_jump=False,
        candidate_ref_prefix="kis-readonly-queue",
        verification_workflow="work-management.yml",
    )
    backend = FakeBackend(tmp_path)
    return MergeQueueCoordinator(settings, QueueStateStore(settings.state_root), backend), backend


def enqueue(queue: MergeQueueCoordinator, pull: int, head: str) -> dict[str, object]:
    return queue.enqueue(project_id="kis-mcp", pull_number=pull, expected_head=head)


def test_concurrent_enqueues_same_queue_preserve_both_accepted_entries(tmp_path: Path) -> None:
    queue_one, backend = coordinator(tmp_path)
    barrier = Barrier(2)
    original_pull_request = backend.pull_request

    def synchronized_pull_request(target: QueueTarget, pull_number: int) -> PullRequestSnapshot:
        barrier.wait(timeout=5)
        return original_pull_request(target, pull_number)

    backend.pull_request = synchronized_pull_request  # type: ignore[method-assign]
    queue_two = MergeQueueCoordinator(queue_one.settings, QueueStateStore(queue_one.settings.state_root), backend)
    failures: list[Exception] = []

    def run(queue: MergeQueueCoordinator, pull: int, head: str) -> None:
        try:
            enqueue(queue, pull, head)
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [
        Thread(target=run, args=(queue_one, 1, H1)),
        Thread(target=run, args=(queue_two, 2, H2)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not failures
    assert all(not thread.is_alive() for thread in threads)
    state = queue_one.status(project_id="kis-mcp")["queue"]
    assert sorted(entry["pull_number"] for entry in state["entries"]) == [1, 2]
    assert [entry["position"] for entry in state["entries"]] == [1, 2]


def test_mutation_locks_for_disjoint_queue_identities_do_not_block_each_other(tmp_path: Path) -> None:
    store = QueueStateStore(tmp_path / "state")
    barrier = Barrier(2)
    failures: list[Exception] = []

    def hold(project_id: str) -> None:
        try:
            with store.mutation_lock(project_id, "main"):
                barrier.wait(timeout=5)
        except Exception as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [Thread(target=hold, args=("project-one",)), Thread(target=hold, args=("project-two",))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not failures
    assert all(not thread.is_alive() for thread in threads)


def test_queue_state_key_preserves_case_sensitive_git_branch_identity() -> None:
    assert _queue_state_key("main") != _queue_state_key("Main")


def test_canonical_store_reads_legacy_once_then_prefers_canonical_state(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    canonical_root = tmp_path / "canonical"
    store = QueueStateStore(
        legacy_root,
        canonical=True,
        canonical_path_resolver=lambda project_id, target_branch: (
            canonical_root / project_id / f"{target_branch}.json"
        ),
    )
    legacy_path = legacy_root / "kis-mcp" / "main.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_state = {
        "schema_version": 1,
        "project_id": "kis-mcp",
        "target_branch": "main",
        "entries": [],
        "events": [{"kind": "legacy"}],
    }
    legacy_path.write_text(json.dumps(legacy_state), encoding="utf-8")

    assert store.load("kis-mcp", "main") == legacy_state
    canonical_state = {**legacy_state, "events": [{"kind": "canonical"}]}
    canonical_path = store.save(canonical_state)
    legacy_path.write_text(json.dumps({**legacy_state, "events": [{"kind": "stale"}]}), encoding="utf-8")

    assert canonical_path == canonical_root / "kis-mcp" / "main.json"
    assert legacy_path.is_file()
    assert store.load("kis-mcp", "main") == canonical_state


def test_enqueue_freezes_exact_head_and_rejects_stale_identity(tmp_path: Path) -> None:
    queue, _ = coordinator(tmp_path)

    result = enqueue(queue, 1, H1)
    entry = result["queue"]["entries"][0]
    assert entry["pull_number"] == 1
    assert entry["head_sha"] == H1
    assert entry["position"] == 1
    assert result["queue"]["base_sha"] == BASE

    with pytest.raises(ToolError, match="QUEUE_PULL_REQUEST_HEAD_MISMATCH"):
        enqueue(queue, 2, H1)

    duplicate = enqueue(queue, 1, H1)
    assert duplicate["state"] == "already_queued"
    assert len(duplicate["queue"]["entries"]) == 1


def test_appending_to_built_queue_advances_generation_and_invalidates_candidates(tmp_path: Path) -> None:
    queue, _ = coordinator(tmp_path)
    enqueue(queue, 1, H1)
    built = queue.reconcile(project_id="kis-mcp")["queue"]
    assert built["entries"][0]["candidate_sha"] is not None

    appended = enqueue(queue, 2, H2)["queue"]

    assert appended["generation"] == built["generation"] + 1
    assert [entry["candidate_sha"] for entry in appended["entries"]] == [None, None]
    assert all(entry["generation"] == appended["generation"] for entry in appended["entries"])
    assert any(event["reason"] == "enqueue_topology_changed" for event in appended["events"])


def test_enqueue_rejects_review_or_protection_blocked_pull_request(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    backend.prs[1] = PullRequestSnapshot(
        1,
        H1,
        "one",
        "main",
        "OPEN",
        False,
        "https://example/1",
        "REVIEW_REQUIRED",
        "BLOCKED",
    )

    with pytest.raises(ToolError, match="QUEUE_PULL_REQUEST_NOT_ELIGIBLE"):
        enqueue(queue, 1, H1)


def test_reconcile_builds_cumulative_candidates_with_bounded_concurrency(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path, build_concurrency=3)
    for pull, head in ((1, H1), (2, H2), (3, H3), (4, H4)):
        enqueue(queue, pull, head)

    first = queue.reconcile(project_id="kis-mcp")["queue"]
    entries = first["entries"]
    assert [item["state"] for item in entries] == ["AWAITING_CHECKS", "AWAITING_CHECKS", "AWAITING_CHECKS", "QUEUED"]
    assert entries[0]["member_heads"] == [H1]
    assert entries[1]["member_heads"] == [H1, H2]
    assert entries[2]["member_heads"] == [H1, H2, H3]
    assert entries[3]["candidate_sha"] is None

    backend.checks[entries[0]["candidate_sha"]] = CandidateCheck("success", "run-1", "https://example/run-1", "2026-08-13T20:00:00Z")
    second = queue.reconcile(project_id="kis-mcp")["queue"]
    entries = second["entries"]
    assert entries[0]["state"] == "MERGEABLE"
    assert entries[3]["state"] == "AWAITING_CHECKS"
    assert entries[3]["member_heads"] == [H1, H2, H3, H4]
    assert len(backend.published) == 4


def test_failed_predecessor_is_removed_and_invalidates_successors(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    for pull, head in ((1, H1), (2, H2), (3, H3)):
        enqueue(queue, pull, head)
    built = queue.reconcile(project_id="kis-mcp")["queue"]
    old_generation = built["generation"]
    old_candidates = [item["candidate_sha"] for item in built["entries"]]
    backend.checks[old_candidates[1]] = CandidateCheck("failure", "run-2", "https://example/run-2", "2026-08-13T20:00:00Z")

    rebuilt = queue.reconcile(project_id="kis-mcp")["queue"]
    assert rebuilt["generation"] == old_generation + 1
    assert [item["pull_number"] for item in rebuilt["entries"]] == [1, 3]
    assert all(item["generation"] == rebuilt["generation"] for item in rebuilt["entries"])
    assert [item["candidate_sha"] for item in rebuilt["entries"]] != [old_candidates[0], old_candidates[2]]
    assert any(event["reason"] == "candidate_check_failure" and event["pull_number"] == 2 for event in rebuilt["events"])


def test_conflict_removes_entry_and_rebuilds_remaining_generation(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    backend.conflicts.add(H2)
    for pull, head in ((1, H1), (2, H2), (3, H3)):
        enqueue(queue, pull, head)

    before = queue.status(project_id="kis-mcp")["queue"]["generation"]
    state = queue.reconcile(project_id="kis-mcp")["queue"]
    assert [item["pull_number"] for item in state["entries"]] == [1, 3]
    assert state["generation"] == before + 1
    assert any(event["reason"] == "candidate_conflict" and event["pull_number"] == 2 for event in state["events"])


def test_base_movement_invalidates_all_candidate_evidence(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    enqueue(queue, 1, H1)
    enqueue(queue, 2, H2)
    original = queue.reconcile(project_id="kis-mcp")["queue"]
    old_generation = original["generation"]
    old_candidates = [item["candidate_sha"] for item in original["entries"]]

    backend.live_base = "a" * 40
    refreshed = queue.reconcile(project_id="kis-mcp")["queue"]
    assert refreshed["base_sha"] == "a" * 40
    assert refreshed["generation"] == old_generation + 1
    assert all(item["generation"] == refreshed["generation"] for item in refreshed["entries"])
    assert [item["candidate_sha"] for item in refreshed["entries"]] != old_candidates
    assert any(event["reason"] == "base_moved" for event in refreshed["events"])


def test_dequeue_requires_frozen_head_and_invalidates_remaining_order(tmp_path: Path) -> None:
    queue, _ = coordinator(tmp_path)
    enqueue(queue, 1, H1)
    enqueue(queue, 2, H2)
    queue.reconcile(project_id="kis-mcp")

    with pytest.raises(ToolError, match="QUEUE_PULL_REQUEST_HEAD_MISMATCH"):
        queue.dequeue(project_id="kis-mcp", pull_number=1, expected_head=H2)

    generation = queue.status(project_id="kis-mcp")["queue"]["generation"]
    result = queue.dequeue(project_id="kis-mcp", pull_number=1, expected_head=H1)["queue"]
    assert [item["pull_number"] for item in result["entries"]] == [2]
    assert result["generation"] == generation + 1
    assert result["entries"][0]["state"] == "QUEUED"


def test_land_requires_allgreen_exact_generation_and_fast_forward_membership(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    enqueue(queue, 1, H1)
    enqueue(queue, 2, H2)
    state = queue.reconcile(project_id="kis-mcp")["queue"]
    first, second = state["entries"]
    backend.checks[first["candidate_sha"]] = CandidateCheck("success", "run-1", "https://example/1", "2026-08-13T20:00:00Z")
    backend.checks[second["candidate_sha"]] = CandidateCheck("success", "run-2", "https://example/2", "2026-08-13T20:00:00Z")
    ready = queue.reconcile(project_id="kis-mcp")["queue"]

    with pytest.raises(ToolError, match="QUEUE_GENERATION_MISMATCH"):
        queue.land(project_id="kis-mcp", expected_generation=ready["generation"] + 1, expected_base=BASE)

    landed, landed_sha = queue.land_with_identity(
        project_id="kis-mcp", expected_generation=ready["generation"], expected_base=BASE
    )
    assert set(landed) == {
        "schema_version", "state", "landed_pull_numbers", "candidate_sha", "queue"
    }
    assert landed["state"] == "landed"
    assert landed["landed_pull_numbers"] == [1, 2]
    assert backend.land_calls == [("main", BASE, second["candidate_sha"])]
    assert landed_sha == second["candidate_sha"]
    assert landed["queue"]["base_sha"] == second["candidate_sha"]
    assert landed["queue"]["entries"] == []
    assert landed["queue"]["generation"] == ready["generation"] + 1


def test_registered_queue_land_schedules_development_restart(
    tmp_path: Path,
) -> None:
    operations = object.__new__(RegisteredGitHubMergeQueueOperations)
    operations.settings = SimpleNamespace(target_branch="main")
    operations.backend = SimpleNamespace(
        _require_approval=lambda approved: None,
        target=lambda project_id: QueueTarget(
            project_id,
            "NielPieterse0/kis-mcp",
            tmp_path,
            "https://github.com/NielPieterse0/kis-mcp.git",
        ),
    )
    operations.coordinator = SimpleNamespace(
        preview_land=lambda **kwargs: {"entries": [{"pull_number": 1, "head_sha": H1}]},
        land_with_identity=lambda **kwargs: (
            {
                "schema_version": 1,
                "state": "landed",
                "landed_pull_numbers": [1],
                "candidate_sha": H2,
                "queue": {"base_sha": H2},
            },
            H2,
        ),
    )
    operations.governance_validator = lambda *args: {"ready": True}
    calls: list[tuple[object, ...]] = []
    operations.post_land_hooks = _post_land_hooks(
        lambda *args: calls.append(args) or {"state": "scheduled", "pid": 321}
    )
    result = operations.land(
        project_id="kis-mcp",
        expected_generation=1,
        expected_base=BASE,
        governance=[{"pull_number": 1, "record": {}, "trace": {}}],
        approved=True,
    )
    assert set(result) == {
        "schema_version", "state", "landed_pull_numbers", "candidate_sha", "queue", "governance"
    }
    assert calls == [("kis-mcp", tmp_path, "main", H2)]


def test_registered_queue_land_preserves_success_when_dispatcher_raises(
    tmp_path: Path,
) -> None:
    operations = object.__new__(RegisteredGitHubMergeQueueOperations)
    operations.settings = SimpleNamespace(target_branch="main")
    operations.backend = SimpleNamespace(
        _require_approval=lambda approved: None,
        target=lambda project_id: QueueTarget(
            project_id, "NielPieterse0/kis-mcp", tmp_path,
            "https://github.com/NielPieterse0/kis-mcp.git",
        ),
    )
    landed = {
        "schema_version": 1, "state": "landed", "landed_pull_numbers": [1],
        "candidate_sha": H2, "queue": {"base_sha": H2},
    }
    operations.coordinator = SimpleNamespace(
        preview_land=lambda **kwargs: {"entries": [{"pull_number": 1, "head_sha": H1}]},
        land_with_identity=lambda **kwargs: (landed, H2),
    )
    operations.governance_validator = lambda *args: {"ready": True}
    failures: list[tuple[object, ...]] = []
    operations.post_land_hooks = _post_land_hooks(
        lambda *args: (_ for _ in ()).throw(RuntimeError("boom")),
        lambda *args: failures.append(args),
    )
    result = operations.land(
        project_id="kis-mcp", expected_generation=1, expected_base=BASE,
        governance=[{"pull_number": 1, "record": {}, "trace": {}}], approved=True,
    )
    assert result["state"] == "landed"
    assert set(result) == {
        "schema_version", "state", "landed_pull_numbers", "candidate_sha", "queue", "governance"
    }
    assert len(failures) == 1
    assert isinstance(failures[0][-1], RuntimeError)


def test_land_stops_at_first_non_green_entry(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    for pull, head in ((1, H1), (2, H2), (3, H3)):
        enqueue(queue, pull, head)
    state = queue.reconcile(project_id="kis-mcp")["queue"]
    backend.checks[state["entries"][0]["candidate_sha"]] = CandidateCheck("success", "run-1", "https://example/1", "2026-08-13T20:00:00Z")
    state = queue.reconcile(project_id="kis-mcp")["queue"]

    landed = queue.land(project_id="kis-mcp", expected_generation=state["generation"], expected_base=BASE)
    assert landed["landed_pull_numbers"] == [1]
    assert [item["pull_number"] for item in landed["queue"]["entries"]] == [2, 3]
    assert landed["queue"]["generation"] == state["generation"] + 1
    assert all(item["state"] == "QUEUED" for item in landed["queue"]["entries"])


def test_status_reports_live_base_drift_without_mutating_generation(tmp_path: Path) -> None:
    queue, backend = coordinator(tmp_path)
    enqueue(queue, 1, H1)
    before = queue.status(project_id="kis-mcp")
    backend.live_base = "b" * 40

    status = queue.status(project_id="kis-mcp")
    assert status["base_current"] is False
    assert status["live_base_sha"] == "b" * 40
    assert status["queue"]["generation"] == before["queue"]["generation"]


def test_repository_merge_queue_settings_are_bounded_v1_defaults() -> None:
    settings = load_merge_queue_settings()
    assert settings.enabled is True
    assert settings.target_branch == "main"
    assert settings.merge_method == "merge"
    assert settings.grouping_strategy == "allgreen"
    assert settings.build_concurrency == 3
    assert settings.max_entries_to_merge == 3
    assert settings.allow_jump is False
    assert settings.verification_workflow == "work-management.yml"


def scripted_registered_backend(
    results: Sequence[SimpleNamespace],
) -> tuple[RegisteredGitHubMergeQueueBackend, QueueTarget, list[tuple[tuple[str, ...], Path, Mapping[str, str]]]]:
    pending = list(results)
    calls: list[tuple[tuple[str, ...], Path, Mapping[str, str]]] = []

    def runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> SimpleNamespace:
        calls.append((tuple(args), cwd, dict(env)))
        if not pending:
            raise AssertionError(f"unexpected command: {args}")
        return pending.pop(0)

    registry = ProjectRegistry(
        default_project_id="kis-mcp",
        projects=(
            ProjectDefinition(
                project_id="kis-mcp",
                display_name="KIS MCP",
                local_root=r"C:\Projects\kis-mcp",
                github=GitHubProjectBinding(repository="NielPieterse0/kis-mcp"),
            ),
        ),
    )
    backend = RegisteredGitHubMergeQueueBackend(
        registry,
        verification_workflow="work-management.yml",
        runner=runner,
    )
    target = QueueTarget(
        "kis-mcp",
        "NielPieterse0/kis-mcp",
        Path(r"C:\Projects\kis-mcp"),
        "https://github.com/NielPieterse0/kis-mcp.git",
    )
    return backend, target, calls


def test_registered_backend_builds_real_two_parent_merge_candidate() -> None:
    tree = "6" * 40
    candidate = "7" * 40
    backend, target, calls = scripted_registered_backend(
        (
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout=f"{tree}\n", stderr=""),
            SimpleNamespace(returncode=0, stdout=f"{candidate}\n", stderr=""),
        )
    )

    result = backend.build_candidate(target, 1, BASE, H1, "queue candidate")

    assert result == candidate
    assert calls[1][0] == ("git", "merge-tree", "--write-tree", BASE, H1)
    assert calls[2][0] == (
        "git",
        "commit-tree",
        tree,
        "-p",
        BASE,
        "-p",
        H1,
        "-m",
        "queue candidate",
    )


def test_registered_backend_accepts_actions_evidence_only_for_exact_candidate_sha() -> None:
    candidate = "7" * 40
    other = "8" * 40
    payload = [
        {
            "databaseId": 10,
            "status": "completed",
            "conclusion": "success",
            "headSha": other,
            "url": "https://example/other",
            "createdAt": "2026-08-13T20:00:00Z",
            "updatedAt": "2026-08-13T20:01:00Z",
        },
        {
            "databaseId": 11,
            "status": "completed",
            "conclusion": "success",
            "headSha": candidate,
            "url": "https://example/exact",
            "createdAt": "2026-08-13T20:02:00Z",
            "updatedAt": "2026-08-13T20:03:00Z",
        },
    ]
    backend, target, calls = scripted_registered_backend(
        (SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),)
    )

    check = backend.candidate_check(
        target,
        "kis-readonly-queue/main/g1/pr-1",
        candidate,
    )

    assert check.state == "success"
    assert check.run_id == "11"
    assert check.url == "https://example/exact"
    assert "--workflow" in calls[0][0]
    assert "work-management.yml" in calls[0][0]
    assert "--event" in calls[0][0]
    assert "push" in calls[0][0]


def test_registered_backend_reuses_exact_publication_for_base_advance(monkeypatch) -> None:
    candidate = "7" * 40
    backend, target, _ = scripted_registered_backend(())
    calls: list[dict[str, object]] = []

    def publish_commit(**kwargs):
        calls.append(kwargs)
        return {"state": "published"}

    monkeypatch.setattr(backend, "publish_commit", publish_commit)
    backend.advance_base(target, "main", BASE, candidate)

    assert calls == [
        {
            "project_id": "kis-mcp",
            "commit": candidate,
            "branch": "main",
            "expected_remote_base": BASE,
            "approved": True,
        }
    ]


def test_land_with_identity_uses_internal_landing_identity_not_public_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue, _ = coordinator(tmp_path)
    expected = {"candidate_sha": "bad", "queue": {"base_sha": H2}, "state": "landed"}
    monkeypatch.setattr(
        queue,
        "_land_outcome",
        lambda **kwargs: SimpleNamespace(result=expected, landed_sha=H1),
    )

    result, landed_sha = queue.land_with_identity(
        project_id="kis-mcp", expected_generation=1, expected_base=BASE
    )

    assert result is expected
    assert landed_sha == H1


@pytest.mark.parametrize(
    ("candidate_value", "include_candidate"),
    [
        (None, False),
        ("bad", True),
        (123, True),
        (True, True),
    ],
)
def test_land_with_identity_does_not_parse_public_candidate_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_value: object,
    include_candidate: bool,
) -> None:
    queue, _ = coordinator(tmp_path)
    expected: dict[str, object] = {"queue": {"base_sha": H1}, "state": "landed"}
    if include_candidate:
        expected["candidate_sha"] = candidate_value
    monkeypatch.setattr(
        queue,
        "_land_outcome",
        lambda **kwargs: SimpleNamespace(result=expected, landed_sha=H2),
    )

    result, landed_sha = queue.land_with_identity(
        project_id="kis-mcp", expected_generation=1, expected_base=BASE
    )

    assert result is expected
    assert landed_sha == H2


def test_registered_land_emits_missing_identity_to_shared_dispatcher(
    tmp_path: Path,
) -> None:
    operations = object.__new__(RegisteredGitHubMergeQueueOperations)
    operations.settings = SimpleNamespace(target_branch="main")
    operations.backend = SimpleNamespace(
        _require_approval=lambda approved: None,
        target=lambda project_id: QueueTarget(
            project_id, "NielPieterse0/kis-mcp", tmp_path,
            "https://github.com/NielPieterse0/kis-mcp.git",
        ),
    )
    landed = {
        "schema_version": 1,
        "state": "landed",
        "landed_pull_numbers": [1],
        "candidate_sha": H2,
        "queue": {"base_sha": H1},
    }
    operations.coordinator = SimpleNamespace(
        preview_land=lambda **kwargs: {"entries": [{"pull_number": 1, "head_sha": H1}]},
        land_with_identity=lambda **kwargs: (landed, None),
    )
    operations.governance_validator = lambda *args: {"ready": True}
    calls: list[tuple[object, ...]] = []
    operations.post_land_hooks = _post_land_hooks(lambda *args: calls.append(args))

    result = operations.land(
        project_id="kis-mcp",
        expected_generation=1,
        expected_base=BASE,
        governance=[{"pull_number": 1, "record": {}, "trace": {}}],
        approved=True,
    )
    assert result["state"] == "landed"
    assert calls == [("kis-mcp", tmp_path, "main", None)]


@pytest.mark.parametrize(
    "failure_stage",
    ["approval", "preview", "governance", "land"],
)
def test_registered_queue_land_never_dispatches_before_confirmed_landing(
    tmp_path: Path, failure_stage: str
) -> None:
    calls: list[tuple[object, ...]] = []

    def reject(message: str):
        raise ToolError(message)

    operations = object.__new__(RegisteredGitHubMergeQueueOperations)
    operations.settings = SimpleNamespace(target_branch="main")
    operations.backend = SimpleNamespace(
        _require_approval=(
            (lambda approved: reject("APPROVAL_REJECTED"))
            if failure_stage == "approval"
            else (lambda approved: None)
        ),
        target=lambda project_id: QueueTarget(
            project_id, "NielPieterse0/kis-mcp", tmp_path,
            "https://github.com/NielPieterse0/kis-mcp.git",
        ),
    )
    operations.coordinator = SimpleNamespace(
        preview_land=(
            (lambda **kwargs: reject("PREVIEW_REJECTED"))
            if failure_stage == "preview"
            else (lambda **kwargs: {"entries": [{"pull_number": 1, "head_sha": H1}]})
        ),
        land_with_identity=(
            (lambda **kwargs: reject("LAND_REJECTED"))
            if failure_stage == "land"
            else (lambda **kwargs: ({"state": "landed", "queue": {}}, H2))
        ),
    )
    operations.governance_validator = (
        (lambda *args: reject("GOVERNANCE_REJECTED"))
        if failure_stage == "governance"
        else (lambda *args: {"ready": True})
    )
    operations.post_land_hooks = _post_land_hooks(lambda *args: calls.append(args))

    with pytest.raises(ToolError, match="REJECTED"):
        operations.land(
            project_id="kis-mcp", expected_generation=1, expected_base=BASE,
            governance=[{"pull_number": 1, "record": {}, "trace": {}}],
            approved=True,
        )
    assert calls == []
