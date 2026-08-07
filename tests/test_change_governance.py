from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "change-governance.py"


def load_module():
    spec = importlib.util.spec_from_file_location("change_governance", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def claim(module, change_id: str, **overrides):
    data = {
        "schema_version": 1,
        "change_id": change_id,
        "status": "active",
        "branch": f"change/{change_id}",
        "worktree": f".work/worktrees/{change_id}",
        "base": "main",
        "outcome": f"Implement {change_id}",
        "owned_paths": [f"components/{change_id}/**"],
        "shared_paths": [],
        "excluded_paths": [],
        "dependencies": [],
        "integration_owner": None,
    }
    data.update(overrides)
    return module.ChangeClaim.from_mapping(data, source=Path(f"{change_id}/scope.json"))


def test_claim_requires_standard_branch_and_worktree() -> None:
    module = load_module()

    with pytest.raises(module.ClaimError, match="CHANGE_BRANCH_NONSTANDARD"):
        claim(module, "001-alpha", branch="feat/alpha")

    with pytest.raises(module.ClaimError, match="CHANGE_WORKTREE_NONSTANDARD"):
        claim(module, "001-alpha", worktree=".temp/worktrees/alpha")


def test_duplicate_active_outcome_is_rejected() -> None:
    module = load_module()
    first = claim(module, "001-alpha", outcome="Add contract governance")
    second = claim(module, "002-beta", outcome="  add   CONTRACT governance ")

    conflicts = module.find_claim_conflicts([first, second])

    assert any("DUPLICATE_ACTIVE_OUTCOME" in conflict for conflict in conflicts)


def test_exclusive_path_overlap_is_rejected() -> None:
    module = load_module()
    first = claim(module, "001-alpha", owned_paths=["src/**"])
    second = claim(module, "002-beta", owned_paths=["src/kis_mcp/server.py"])

    conflicts = module.find_claim_conflicts([first, second])

    assert any("EXCLUSIVE_PATH_OVERLAP" in conflict for conflict in conflicts)


def test_coordinated_shared_path_overlap_is_allowed() -> None:
    module = load_module()
    first = claim(
        module,
        "001-alpha",
        owned_paths=["components/alpha/**"],
        shared_paths=["docs/OPERATIONS.md"],
    )
    second = claim(
        module,
        "002-beta",
        owned_paths=["components/beta/**"],
        shared_paths=["docs/OPERATIONS.md"],
        dependencies=["001-alpha"],
    )

    conflicts = module.find_claim_conflicts([first, second])

    assert not conflicts


def test_uncoordinated_shared_path_overlap_is_rejected() -> None:
    module = load_module()
    first = claim(
        module,
        "001-alpha",
        owned_paths=["components/alpha/**"],
        shared_paths=["docs/OPERATIONS.md"],
    )
    second = claim(
        module,
        "002-beta",
        owned_paths=["components/beta/**"],
        shared_paths=["docs/OPERATIONS.md"],
    )

    conflicts = module.find_claim_conflicts([first, second])

    assert any("UNCOORDINATED_SHARED_PATH" in conflict for conflict in conflicts)


def test_changed_paths_must_be_declared_and_not_excluded() -> None:
    module = load_module()
    current = claim(
        module,
        "001-alpha",
        owned_paths=["scripts/**", ".work/changes/001-alpha/**"],
        excluded_paths=["policy/**"],
    )

    violations = module.paths_outside_claim(
        current,
        [
            "scripts/change-governance.py",
            ".work/changes/001-alpha/spec.md",
            "README.md",
            "policy/kis-mcp.policy.json",
        ],
    )

    assert violations == [
        "PATH_OUTSIDE_CLAIM: README.md",
        "PATH_EXCLUDED_BY_CLAIM: policy/kis-mcp.policy.json",
    ]


def test_claim_paths_reject_ambiguous_globs_and_absolute_paths() -> None:
    module = load_module()

    with pytest.raises(module.ClaimError, match="CHANGE_PATH_PATTERN_INVALID"):
        claim(module, "001-alpha", owned_paths=["src/*.py"])

    with pytest.raises(module.ClaimError, match="CHANGE_PATH_PATTERN_INVALID"):
        claim(module, "001-alpha", owned_paths=["C:/Projects/kis-mcp/src/**"])


def run_git(repository: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=check,
        capture_output=True,
        text=True,
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
    (repository / "README.md").write_text("# Test repository\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "test: initialize repository")
    return repository


def set_change_status(target: Path, change_id: str, status: str) -> None:
    scope_path = target / ".work" / "changes" / change_id / "scope.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope["status"] = status
    scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")


def test_claim_discovery_ignores_underscore_template_directories(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_root = repository / ".work" / "changes" / "001-alpha"
    change_root.mkdir(parents=True)
    change_root.joinpath("scope.json").write_text(
        json.dumps(claim(module, "001-alpha", status="closed").to_mapping()),
        encoding="utf-8",
    )

    worktree_claims = module.load_worktree_claims(repository)
    checkout_claims = module._claims_in_checkout(repository)

    assert [item.change_id for item in worktree_claims] == ["001-alpha"]
    assert [item.change_id for item in checkout_claims] == ["001-alpha"]


def test_primary_claim_overrides_stale_copies_in_other_worktrees(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_id = "004-live-proxy-commissioning"
    change_root = repository / ".work" / "changes" / change_id
    change_root.mkdir(parents=True)
    active_claim = claim(module, change_id)
    change_root.joinpath("scope.json").write_text(
        json.dumps(active_claim.to_mapping()),
        encoding="utf-8",
    )
    run_git(repository, "add", ".work/changes/004-live-proxy-commissioning")
    run_git(repository, "commit", "-m", "test: register active historical claim")

    unrelated = repository / ".work" / "worktrees" / "001-alpha"
    run_git(repository, "worktree", "add", str(unrelated), "-b", "change/001-alpha", "main")

    closed_mapping = active_claim.to_mapping()
    closed_mapping["status"] = "closed"
    change_root.joinpath("scope.json").write_text(
        json.dumps(closed_mapping),
        encoding="utf-8",
    )

    claims = module.load_worktree_claims(repository)
    matches = [item for item in claims if item.change_id == change_id]

    assert len(matches) == 1
    assert matches[0].status == "closed"


def test_create_change_worktree_uses_standard_location_and_artifacts(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )

    assert target == repository / ".work" / "worktrees" / "001-alpha"
    assert target.is_dir()
    scope = json.loads(
        (target / ".work" / "changes" / "001-alpha" / "scope.json").read_text(
            encoding="utf-8"
        )
    )
    assert scope["branch"] == "change/001-alpha"
    assert scope["worktree"] == ".work/worktrees/001-alpha"
    assert scope["owned_paths"] == ["src/**", ".work/changes/001-alpha/**"]
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md"):
        assert (target / ".work" / "changes" / "001-alpha" / name).is_file()


def test_create_change_worktree_rejects_duplicate_active_outcome(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/alpha/**"],
    )

    with pytest.raises(module.ClaimError, match="DUPLICATE_ACTIVE_OUTCOME"):
        module.create_change_worktree(
            repository,
            change_id="002-beta",
            outcome="  implement   ALPHA ",
            owned_paths=["src/beta/**"],
        )


def test_create_change_worktree_rejects_existing_unregistered_worktree(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    existing = repository / ".work" / "worktrees" / "001-alpha"
    run_git(repository, "worktree", "add", str(existing), "-b", "change/001-alpha", "main")

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_CLAIM_MISSING"):
        module.create_change_worktree(
            repository,
            change_id="002-beta",
            outcome="Implement beta",
            owned_paths=["src/beta/**"],
        )


def test_validate_repository_resolves_primary_root_from_linked_worktree(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    shutil.rmtree(repository / ".work" / "changes" / "_template")

    claims = module.validate_repository(target)

    assert [item.change_id for item in claims if item.status == "active"] == ["001-alpha"]


def test_validate_repository_rejects_unregistered_change_worktree(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "001-alpha"
    run_git(repository, "worktree", "add", str(target), "-b", "change/001-alpha", "main")

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_CLAIM_MISSING"):
        module.validate_repository(repository)


def test_validate_repository_can_skip_worktree_topology_for_isolated_ci(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_root = repository / ".work" / "changes" / "001-alpha"
    change_root.mkdir(parents=True)
    change_root.joinpath("scope.json").write_text(
        json.dumps(claim(module, "001-alpha").to_mapping()) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_WORKTREE_MISSING"):
        module.validate_repository(repository)

    claims = module.validate_repository(repository, require_active_worktrees=False)

    assert [item.change_id for item in claims if item.status == "active"] == ["001-alpha"]


def test_cleanup_refuses_dirty_worktree(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(module.ClaimError, match="CHANGE_WORKTREE_DIRTY"):
        module.cleanup_change_worktree(repository, "001-alpha")

    assert target.exists()


@pytest.mark.parametrize("status", ["active", "ready"])
def test_cleanup_refuses_merged_claim_until_status_is_closed(
    tmp_path: Path,
    status: str,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    set_change_status(target, "001-alpha", status)
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", f"docs: register {status} alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")

    with pytest.raises(module.ClaimError, match="CHANGE_STATUS_NOT_CLOSED"):
        module.cleanup_change_worktree(repository, "001-alpha")

    assert target.exists()
    assert run_git(repository, "branch", "--list", "change/001-alpha").stdout.strip()


def test_cleanup_removes_clean_merged_worktree_and_branch(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    set_change_status(target, "001-alpha", "closed")
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", "docs: register alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")

    module.cleanup_change_worktree(repository, "001-alpha")

    assert not target.exists()
    branches = run_git(repository, "branch", "--list", "change/001-alpha").stdout
    assert not branches.strip()


def test_cleanup_recovers_unregistered_long_path_remnant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    set_change_status(target, "001-alpha", "closed")
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", "docs: register alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")
    original_run_git = module._run_git

    def failing_remove(repo: Path, *args: str, check: bool = True):
        if args[:4] == ("-c", "core.longpaths=true", "worktree", "remove"):
            original_run_git(repository, "worktree", "remove", str(target))
            target.mkdir(parents=True)
            (target / "remnant.txt").write_text("recoverable\n", encoding="utf-8")
            return subprocess.CompletedProcess(
                ["git", *args],
                1,
                "",
                "Filename too long",
            )
        return original_run_git(repo, *args, check=check)

    monkeypatch.setattr(module, "_run_git", failing_remove)

    result = module.cleanup_change_worktree(repository, "001-alpha")

    assert result.recovered is True
    assert result.backup_path is not None
    assert result.backup_path.parent == tmp_path / ".backup"
    assert (result.backup_path / "remnant.txt").read_text(encoding="utf-8") == "recoverable\n"
    assert not target.exists()
    assert not run_git(repository, "branch", "--list", "change/001-alpha").stdout.strip()


def test_cleanup_does_not_move_or_delete_when_registration_remains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    set_change_status(target, "001-alpha", "closed")
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", "docs: register alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")
    original_run_git = module._run_git

    def failing_remove(repo: Path, *args: str, check: bool = True):
        if args[:4] == ("-c", "core.longpaths=true", "worktree", "remove"):
            return subprocess.CompletedProcess(
                ["git", *args],
                1,
                "",
                "Filename too long",
            )
        return original_run_git(repo, *args, check=check)

    monkeypatch.setattr(module, "_run_git", failing_remove)

    with pytest.raises(module.ClaimError, match="CHANGE_WORKTREE_REMOVE_FAILED"):
        module.cleanup_change_worktree(repository, "001-alpha")

    assert target.exists()
    assert run_git(repository, "branch", "--list", "change/001-alpha").stdout.strip()
    assert not (tmp_path / ".backup").exists()
