from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.discover.change_service import InspectChangeService
from kis_mcp.discover.git_change_reader import GitChangeReader
from kis_mcp.discover.read_authority import ReadAuthority
from kis_mcp.discover.settings import DiscoverLimits, DiscoverSettings
from kis_mcp.workflows.code_review.evidence import EvidenceError, GitReviewEvidenceCollector


class FakeInspector:
    def __init__(
        self,
        *,
        source: str = "working_tree",
        path: str = "src/example.py",
        untracked: bool = False,
        fingerprints: tuple[str, ...] = ("a" * 64,),
        fingerprint_basis: str = "legacy",
    ) -> None:
        self.source = source
        self.path = path
        self.untracked = untracked
        self.fingerprints = list(fingerprints)
        self.fingerprint_basis = fingerprint_basis
        self.requests = []

    def inspect(self, request):
        self.requests.append(request)
        fingerprint = self.fingerprints.pop(0) if len(self.fingerprints) > 1 else self.fingerprints[0]
        return SimpleNamespace(
            available=True,
            change=SimpleNamespace(
                source=self.source,
                fingerprint=fingerprint,
                fingerprint_basis=self.fingerprint_basis,
                resolved_commit_ref="c" * 40 if self.source == "commit" else None,
                resolved_base_ref="d" * 40 if self.source in {"range", "branch"} else None,
                resolved_head_ref="e" * 40 if self.source in {"range", "branch"} else None,
            ),
            changed_files=(
                SimpleNamespace(
                    path=self.path,
                    previous_path=None,
                    staged_status=None,
                    worktree_status="modified" if self.source == "working_tree" else None,
                    untracked=self.untracked,
                ),
            ),
            truncated=False,
        )


def test_evidence_collector_packages_complete_source_bound_file_sections(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "AGENTS.md").write_text("repository instructions", encoding="utf-8")
    calls: list[list[str]] = []

    def run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=("diff --git a/src/example.py b/src/example.py\n" if "--cached" not in args else ""),
            stderr="",
        )

    inspector = FakeInspector()
    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        inspector=inspector,
        runner=run,
    )

    evidence = collector.collect(project)

    assert evidence.source == "working_tree"
    assert evidence.source_fingerprint == "a" * 64
    assert evidence.changed_files == ("src/example.py",)
    assert evidence.included_files == ("src/example.py",)
    assert evidence.omitted_files == ()
    assert evidence.complete is True
    assert "repository instructions" in evidence.content
    assert "diff --git" in evidence.content
    assert calls == [
        ["git", "diff", "--no-ext-diff", "--no-textconv", "--unified=3", "--", "src/example.py"],
        ["git", "diff", "--cached", "--no-ext-diff", "--no-textconv", "--unified=3", "--", "src/example.py"],
    ]


def test_evidence_collector_commit_source_ignores_unrelated_worktree_state(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    calls: list[list[str]] = []

    def run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="commit patch\n", stderr="")

    inspector = FakeInspector(source="commit", path="src/committed.py")
    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        inspector=inspector,
        runner=run,
    )

    evidence = collector.collect(project, source="commit", commit_ref="abc123")

    assert evidence.source == "commit"
    assert evidence.commit_ref == "c" * 40
    assert evidence.changed_files == ("src/committed.py",)
    assert evidence.complete is True
    assert "commit patch" in evidence.content
    assert calls == [[
        "git", "show", "--format=", "--no-ext-diff", "--no-textconv", "--unified=3",
        "--end-of-options", "c" * 40, "--", "src/committed.py",
    ]]


def test_evidence_collector_range_source_uses_only_selected_refs(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    calls: list[list[str]] = []

    def run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="range patch\n", stderr="")

    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        inspector=FakeInspector(source="range", path="src/range.py"),
        runner=run,
    )

    evidence = collector.collect(
        project,
        source="range",
        base_ref="main",
        head_ref="feature",
    )

    assert evidence.source == "range"
    assert evidence.base_ref == "d" * 40
    assert evidence.head_ref == "e" * 40
    assert evidence.complete is True
    assert "range patch" in evidence.content
    assert calls == [[
        "git", "diff", "--no-ext-diff", "--no-textconv", "--unified=3",
        "--end-of-options", f"{'d' * 40}...{'e' * 40}", "--", "src/range.py",
    ]]


def test_evidence_collector_binds_mutable_fingerprint_to_packaged_bytes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    def run(args, **kwargs):
        command = tuple(args[1:])
        if command == ("rev-parse", "HEAD"):
            output = "f" * 40 + "\n"
        elif "--cached" in command:
            output = ""
        else:
            output = "diff --git a/src/example.py b/src/example.py\n+changed payload\n"
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        inspector=FakeInspector(fingerprint_basis="evidence_snapshot"),
        runner=run,
    )

    evidence = collector.collect(project)

    assert evidence.complete is False
    assert evidence.source_fingerprint != "a" * 64
    assert "AGENT_EVIDENCE_SOURCE_CHANGED" in evidence.diagnostics
    assert "changed payload" in evidence.content


def test_evidence_collector_rejects_source_that_changes_during_collection(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="patch\n", stderr="")

    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=5000,
        inspector=FakeInspector(fingerprints=("a" * 64, "b" * 64)),
        runner=run,
    )

    evidence = collector.collect(project)

    assert evidence.complete is False
    assert "AGENT_EVIDENCE_SOURCE_CHANGED" in evidence.diagnostics
    assert evidence.source_fingerprint == "a" * 64


def test_evidence_collector_omits_whole_file_section_when_budget_is_exceeded(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "huge.txt").write_text("x" * 5000, encoding="utf-8")
    inspector = FakeInspector(path="huge.txt", untracked=True)
    collector = GitReviewEvidenceCollector(
        project_boundary=tmp_path,
        max_chars=1000,
        inspector=inspector,
    )

    evidence = collector.collect(project)

    assert len(evidence.content) <= 1000
    assert evidence.complete is False
    assert evidence.included_files == ()
    assert evidence.omitted_files == ("huge.txt",)
    assert "AGENT_EVIDENCE_FILES_OMITTED" in evidence.diagnostics
    assert "x" * 100 not in evidence.content


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _discover_settings() -> DiscoverSettings:
    return DiscoverSettings(
        enabled=True,
        limits=DiscoverLimits(
            max_files=100,
            max_directories=100,
            max_total_bytes=1_000_000,
            max_file_bytes=1_000,
            max_evidence=100,
            max_output_chars=100_000,
            max_depth=8,
            max_visited_entries=1_000,
            traversal_timeout_seconds=30,
            git_timeout_seconds=5,
            git_max_output_bytes=20_000,
            git_history_limit=20,
            git_metadata_max_bytes=4096,
            python_max_nodes=10_000,
            python_max_records=1_000,
        ),
        excluded_segments=(".git", ".work"),
        allowed_extensions=(".py", ".txt", ".md", ".json"),
        allowed_filenames=("Makefile",),
        text_encodings=("utf-8", "utf-8-sig", "utf-16"),
        reject_hard_links=True,
    )


def _real_collector(project: Path, boundary: Path) -> GitReviewEvidenceCollector:
    discover_settings = _discover_settings()
    reader = GitChangeReader(
        authority=ReadAuthority(boundary, discover_settings),
        settings=discover_settings,
    )
    return GitReviewEvidenceCollector(
        project_boundary=boundary,
        max_chars=20_000,
        inspector=InspectChangeService(reader),
    )


def test_committed_change_is_reviewed_when_worktree_is_clean(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Review Tests")
    _git(project, "config", "user.email", "review@example.invalid")
    source = project / "value.py"
    source.write_text("value = 1\n", encoding="utf-8")
    _commit(project, "initial")
    source.write_text("value = 2\n", encoding="utf-8")
    implementation = _commit(project, "implementation")
    assert _git(project, "status", "--porcelain").stdout == ""

    evidence = _real_collector(project, tmp_path).collect(
        project,
        source="commit",
        commit_ref=implementation,
    )

    assert evidence.complete is True
    assert evidence.commit_ref == implementation
    assert evidence.changed_files == ("value.py",)
    assert "+value = 2" in evidence.content


def test_exact_range_ignores_unrelated_dirty_worktree_state(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.name", "Review Tests")
    _git(project, "config", "user.email", "review@example.invalid")
    source = project / "value.py"
    source.write_text("value = 1\n", encoding="utf-8")
    base = _commit(project, "initial")
    source.write_text("value = 2\n", encoding="utf-8")
    head = _commit(project, "implementation")
    (project / "unrelated.txt").write_text("dirty state\n", encoding="utf-8")

    evidence = _real_collector(project, tmp_path).collect(
        project,
        source="range",
        base_ref=base,
        head_ref=head,
    )

    assert evidence.complete is True
    assert evidence.base_ref == base
    assert evidence.head_ref == head
    assert evidence.changed_files == ("value.py",)
    assert "+value = 2" in evidence.content
    assert "dirty state" not in evidence.content
    assert "unrelated.txt" not in evidence.content


def test_evidence_collector_rejects_path_outside_boundary(tmp_path: Path) -> None:
    boundary = tmp_path / "boundary"
    boundary.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    collector = GitReviewEvidenceCollector(
        project_boundary=boundary,
        max_chars=1000,
        inspector=FakeInspector(),
    )

    with pytest.raises(EvidenceError, match="project boundary"):
        collector.collect(outside)
