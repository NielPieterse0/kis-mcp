from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "git-workflow.py"


def load_module():
    spec = importlib.util.spec_from_file_location("git_workflow", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_git(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )


def initialize_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    run_git(repository, "init", "-b", "main")
    run_git(repository, "config", "user.name", "Test Operator")
    run_git(repository, "config", "user.email", "operator@example.invalid")
    (repository / ".gitignore").write_text(".work/worktrees/\n", encoding="utf-8")
    template = repository / ".work" / "changes" / "_template"
    template.mkdir(parents=True)
    (template / "scope.json").write_text("{}\n", encoding="utf-8")
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md"):
        (template / name).write_text(f"# {name}\n", encoding="utf-8")
    (repository / "alpha.txt").write_text("one\n", encoding="utf-8")
    (repository / "old.txt").write_text("rename me\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "test: initialize")
    return repository


def write_claim(repository: Path, change_id: str, *, status: str = "active") -> None:
    root = repository / ".work" / "changes" / change_id
    root.mkdir(parents=True, exist_ok=True)
    scope = {
        "schema_version": 1,
        "change_id": change_id,
        "status": status,
        "branch": f"change/{change_id}",
        "worktree": f".work/worktrees/{change_id}",
        "base": "main",
        "outcome": f"Implement {change_id}",
        "owned_paths": ["alpha.txt", "new.txt", f".work/changes/{change_id}/**"],
        "shared_paths": [],
        "excluded_paths": [],
        "dependencies": [],
        "integration_owner": None,
    }
    (root / "scope.json").write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md"):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")


def test_diff_summary_reports_status_numstat_commits_and_rename(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "switch", "-c", "feature")
    (repository / "alpha.txt").write_text("one\ntwo\n", encoding="utf-8")
    run_git(repository, "mv", "old.txt", "new.txt")
    (repository / "added.bin").write_bytes(b"\x00\x01\x02")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: update fixture")

    result = module.diff_summary(repository, base="main", head="HEAD")

    assert result["operation"] == "diff-summary"
    assert result["base"] == "main"
    assert result["head"] == "HEAD"
    assert result["summary"]["files"] == 3
    assert result["summary"]["added_lines"] == 1
    assert result["summary"]["binary_files"] == 1
    assert [item["subject"] for item in result["commits"]] == ["feat: update fixture"]
    by_path = {item["path"]: item for item in result["files"]}
    assert by_path["alpha.txt"]["status"] == "modified"
    assert by_path["new.txt"]["status"] == "renamed"
    assert by_path["new.txt"]["previous_path"] == "old.txt"
    assert by_path["added.bin"]["binary"] is True


def test_diff_summary_rejects_option_shaped_refs(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    with pytest.raises(module.GitWorkflowError, match="GIT_REF_INVALID"):
        module.diff_summary(repository, base="--output=/tmp/pwn", head="HEAD")


def test_diff_summary_bounds_records_but_preserves_total_counts(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "switch", "-c", "feature")
    (repository / "first.txt").write_text("first\n", encoding="utf-8")
    (repository / "second.txt").write_text("second\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: add two files")

    result = module.diff_summary(repository, base="main", head="HEAD", max_files=1)

    assert result["truncated"] is True
    assert result["summary"]["files"] == 2
    assert result["summary"]["returned_files"] == 1
    assert result["summary"]["omitted_files"] == 1
    assert result["summary"]["added_lines"] == 2
    assert result["summary"]["statuses"] == {"added": 2}


def test_diff_summary_rejects_nonpositive_output_limit(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    with pytest.raises(module.GitWorkflowError, match="GIT_LIMIT_INVALID"):
        module.diff_summary(
            repository,
            base="main",
            head="HEAD",
            max_output_bytes=0,
        )


def test_diff_summary_enforces_streaming_output_limit(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "switch", "-c", "feature")
    (repository / "large-name-and-content.txt").write_text("x" * 500 + "\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: add bounded output fixture")

    with pytest.raises(module.GitWorkflowError, match="GIT_OUTPUT_LIMIT_EXCEEDED"):
        module.diff_summary(
            repository,
            base="main",
            head="HEAD",
            max_output_bytes=16,
        )


def test_invalid_repository_path_uses_structural_error(tmp_path: Path) -> None:
    module = load_module()

    with pytest.raises(module.GitWorkflowError, match="GIT_REPOSITORY_INVALID"):
        module.pr_readiness(tmp_path / "missing", base="main")


def test_pr_readiness_reports_ready_governed_change(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_id = "001-alpha"
    run_git(repository, "switch", "-c", f"change/{change_id}")
    write_claim(repository, change_id)
    (repository / "alpha.txt").write_text("changed\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: alpha")

    result = module.pr_readiness(repository, base="main")

    assert result["operation"] == "pr-readiness"
    assert result["ready"] is True
    assert result["change_id"] == change_id
    assert result["ahead"] == 1
    assert result["behind"] == 0
    assert result["scope_check"]["passed"] is True
    assert result["blockers"] == []


def test_pr_readiness_blocks_dirty_and_unscoped_branch(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "switch", "-c", "feature/unscoped")
    (repository / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = module.pr_readiness(repository, base="main")

    assert result["ready"] is False
    assert "WORKTREE_DIRTY" in result["blockers"]
    assert "CHANGE_CLAIM_MISSING" in result["blockers"]


def test_cleanup_preview_classifies_dirty_and_merged_worktrees(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_id = "001-alpha"
    target = repository / ".work" / "worktrees" / change_id
    run_git(repository, "worktree", "add", str(target), "-b", f"change/{change_id}", "main")
    write_claim(target, change_id)
    run_git(target, "add", f".work/changes/{change_id}")
    run_git(target, "commit", "-m", "docs: register change")
    run_git(repository, "merge", "--no-ff", f"change/{change_id}", "-m", "merge alpha")

    clean = module.cleanup_preview(repository, change_id=change_id)
    assert clean["worktrees"][0]["eligible"] is True

    (target / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    dirty = module.cleanup_preview(repository, change_id=change_id)
    assert dirty["worktrees"][0]["eligible"] is False
    assert "WORKTREE_DIRTY" in dirty["worktrees"][0]["blockers"]


def test_name_status_parser_preserves_copy_provenance() -> None:
    module = load_module()

    records = module._parse_name_status(b"C100\x00old.txt\x00new.txt\x00")

    assert records == [
        {
            "path": "new.txt",
            "previous_path": "old.txt",
            "status": "copied",
            "similarity": 100,
            "added": 0,
            "deleted": 0,
            "binary": False,
        }
    ]


def test_diff_summary_supports_repository_relative_path_filter(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "switch", "-c", "feature")
    (repository / "alpha.txt").write_text("one\ntwo\n", encoding="utf-8")
    (repository / "other.txt").write_text("other\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: update filtered fixture")

    result = module.diff_summary(
        repository,
        base="main",
        head="HEAD",
        path="alpha.txt",
    )

    assert result["path"] == "alpha.txt"
    assert result["summary"]["files"] == 1
    assert [item["path"] for item in result["files"]] == ["alpha.txt"]


def test_pr_readiness_blocks_detached_head(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "checkout", "--detach")

    result = module.pr_readiness(repository, base="main")

    assert result["ready"] is False
    assert result["detached"] is True
    assert "DETACHED_HEAD" in result["blockers"]
    assert "CHANGE_CLAIM_MISSING" in result["blockers"]


def test_pr_readiness_blocks_scope_violation(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_id = "001-alpha"
    run_git(repository, "switch", "-c", f"change/{change_id}")
    write_claim(repository, change_id)
    (repository / "outside.txt").write_text("outside scope\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "feat: violate registered scope")

    result = module.pr_readiness(repository, base="main")

    assert result["ready"] is False
    assert result["scope_check"]["passed"] is False
    assert "SCOPE_CHECK_FAILED" in result["blockers"]


def test_cleanup_preview_rejects_invalid_change_id(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    with pytest.raises(module.GitWorkflowError, match="CHANGE_ID_INVALID"):
        module.cleanup_preview(repository, change_id="../../bad")


def test_cleanup_preview_does_not_depend_on_primary_worktree_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_id = "001-alpha"
    target = repository / ".work" / "worktrees" / change_id
    run_git(repository, "worktree", "add", str(target), "-b", f"change/{change_id}", "main")
    write_claim(target, change_id)
    run_git(target, "add", f".work/changes/{change_id}")
    run_git(target, "commit", "-m", "docs: register change")
    run_git(repository, "merge", "--no-ff", f"change/{change_id}", "-m", "merge alpha")

    class ClaimError(ValueError):
        pass

    fake_governance = SimpleNamespace(
        ClaimError=ClaimError,
        load_worktree_claims=lambda root: [
            SimpleNamespace(branch=f"change/{change_id}", base="main")
        ],
        discover_worktrees=lambda root: [
            SimpleNamespace(
                path=target.resolve(),
                branch=f"change/{change_id}",
                head=run_git(target, "rev-parse", "HEAD").stdout.strip(),
            ),
            SimpleNamespace(
                path=repository.resolve(),
                branch="main",
                head=run_git(repository, "rev-parse", "HEAD").stdout.strip(),
            ),
        ],
        primary_worktree=lambda root: repository.resolve(),
    )
    monkeypatch.setattr(module, "_load_change_governance", lambda: fake_governance)

    result = module.cleanup_preview(repository, change_id=change_id)

    assert [item["change_id"] for item in result["worktrees"]] == [change_id]
    assert result["worktrees"][0]["eligible"] is True
