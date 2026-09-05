from __future__ import annotations

import importlib.util
import json
import os
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


def work_management_evidence(**overrides):
    data = {
        "project_id": "kis-mcp",
        "record_id": "SPEC-001",
        "source_repository": "NielPieterse0/kis-mcp",
        "source_number": 101,
        "source_kind": "issue",
        "documentation_impact": "planned",
    }
    data.update(overrides)
    return data


def base_evidence():
    return {
        "local_sha": "a" * 40,
        "local_tree": "b" * 40,
        "upstream_sha": None,
        "upstream_tree": None,
        "upstream_ref": None,
        "evidence_source": "unavailable",
        "relation": "unavailable",
    }


def historical_schema_v4_scope(module, change_id: str = "083-historical") -> dict:
    data = claim(
        module,
        change_id,
        schema_version=4,
        complexity="medium",
        risk_triggers=[],
        base_evidence=base_evidence(),
    ).to_mapping()
    data["work_management"] = {
        "project_id": "commodity",
        "source_repository": "NielPieterse0/commodity",
        "source_number": 83,
        "source_kind": "issue",
        "documentation_impact": "planned",
        "execution_owner": "codex",
    }
    return data


def create_registered_change(module, repository: Path, **kwargs):
    change_number = kwargs["change_id"].split("-", 1)[0]
    kwargs.setdefault(
        "work_management",
        work_management_evidence(
            record_id=f"SPEC-{change_number}",
            source_number=100 + int(change_number),
        ),
    )
    return module.create_change_worktree(repository, **kwargs)


def test_schema_v1_claim_remains_valid_without_work_management() -> None:
    module = load_module()

    current = claim(module, "001-alpha")

    assert current.schema_version == 1
    assert current.work_management is None


def test_schema_v2_claim_requires_work_management_evidence() -> None:
    module = load_module()

    with pytest.raises(
        module.ClaimError, match="CHANGE_FIELDS_MISSING: work_management"
    ):
        claim(module, "001-alpha", schema_version=2)


def test_schema_v2_claim_validates_work_management_evidence() -> None:
    module = load_module()
    data = claim(module, "001-alpha").to_mapping()
    data["schema_version"] = 2
    data["work_management"] = work_management_evidence(record_id="bad")

    with pytest.raises(module.ClaimError, match="WORK_MANAGEMENT_RECORD_ID_INVALID"):
        module.ChangeClaim.from_mapping(data, source=Path("001-alpha/scope.json"))


def test_schema_v4_work_management_can_bind_execution_owner() -> None:
    module = load_module()
    current = claim(
        module,
        "001-alpha",
        schema_version=4,
        complexity="medium",
        risk_triggers=[],
        base_evidence=base_evidence(),
        work_management=work_management_evidence(execution_owner="codex"),
    )

    assert current.work_management is not None
    assert current.work_management.execution_owner == "codex"
    assert current.to_mapping()["work_management"]["execution_owner"] == "codex"


def test_schema_v4_direct_parser_remains_strict_for_missing_work_record_id() -> None:
    module = load_module()
    data = historical_schema_v4_scope(module)

    with pytest.raises(module.ClaimError, match="WORK_MANAGEMENT_FIELDS_MISSING: record_id"):
        module.ChangeClaim.from_mapping(data, source=Path("083-historical/scope.json"))


def test_load_claim_projects_historical_schema_v4_work_record_id(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "083-historical" / "scope.json"
    path.parent.mkdir()
    path.write_text(json.dumps(historical_schema_v4_scope(module)), encoding="utf-8")

    current = module.load_claim(path, historical_compatibility=True)

    assert current.work_management is not None
    assert current.work_management.record_id == "WORK-83"
    assert current.work_management.source_number == 83


def test_load_claim_projects_historical_schema_v4_metadata_only(tmp_path: Path) -> None:
    module = load_module()
    data = historical_schema_v4_scope(module, "273-historical")
    data["risk_triggers"] = ["research-methodology", "protected-outcome-boundary"]
    data["integration_owner"] = "codex"
    data["base_evidence"] = {}
    path = tmp_path / "273-historical" / "scope.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data), encoding="utf-8")

    current = module.load_claim(path, historical_compatibility=True)

    assert current.risk_triggers == (
        "research-methodology",
        "protected-outcome-boundary",
    )
    assert current.integration_owner is None
    assert current.base_evidence is None


def test_load_claim_projects_early_schema_v4_omitted_fields(tmp_path: Path) -> None:
    module = load_module()
    data = historical_schema_v4_scope(module, "273-historical")
    for field in (
        "owned_paths",
        "shared_paths",
        "excluded_paths",
        "dependencies",
        "base_evidence",
    ):
        data.pop(field)
    data["work_management"].pop("documentation_impact")
    path = tmp_path / "273-historical" / "scope.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data), encoding="utf-8")

    current = module.load_claim(path, historical_compatibility=True)

    assert [item.raw for item in current.owned_paths] == [
        ".work/changes/273-historical/**"
    ]
    assert current.shared_paths == ()
    assert current.excluded_paths == ()
    assert current.dependencies == ()
    assert current.base_evidence is None
    assert current.work_management is not None
    assert current.work_management.documentation_impact == "not_assessed"


def test_load_claim_reports_noncanonical_historical_dependency_tokens(tmp_path: Path) -> None:
    module = load_module()
    data = historical_schema_v4_scope(module, "115-historical")
    data["dependencies"] = ["86", "114-valid-dependency"]
    path = tmp_path / "115-historical" / "scope.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data), encoding="utf-8")

    current = module.load_claim(path, historical_compatibility=True)

    assert current.dependencies == ("114-valid-dependency",)
    assert current.compatibility_warnings == (
        "HISTORICAL_DEPENDENCY_UNRESOLVED:86",
        "HISTORICAL_WORK_RECORD_ID_SYNTHESIZED",
    )


def test_schema_v3_claim_remains_valid_with_legacy_risk_profile() -> None:
    module = load_module()

    current = claim(
        module,
        "001-alpha",
        schema_version=3,
        risk_profile="lean",
        base_evidence=base_evidence(),
    )

    assert current.risk_profile == "lean"
    assert current.complexity is None
    assert current.risk_triggers == ()


def test_schema_v4_claim_validates_two_axis_classification() -> None:
    module = load_module()

    current = claim(
        module,
        "001-alpha",
        schema_version=4,
        complexity="small",
        risk_triggers=["public_contract", "secrets"],
        base_evidence=base_evidence(),
    )
    assert current.complexity == "small"
    assert current.risk_triggers == ("public_contract", "secrets")

    with pytest.raises(module.ClaimError, match="CHANGE_RISK_TRIGGER_DUPLICATE"):
        claim(
            module,
            "001-alpha",
            schema_version=4,
            complexity="small",
            risk_triggers=["secrets", "secrets"],
            base_evidence=base_evidence(),
        )

    with pytest.raises(module.ClaimError, match="CHANGE_RISK_TRIGGER_ORDER_INVALID"):
        claim(
            module,
            "001-alpha",
            schema_version=4,
            complexity="small",
            risk_triggers=["secrets", "public_contract"],
            base_evidence=base_evidence(),
        )


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
    assert any("intersection=src/kis_mcp/server.py" in conflict for conflict in conflicts)


def test_recursive_path_overlap_reports_exact_intersection() -> None:
    module = load_module()
    first = claim(module, "001-alpha", owned_paths=["src/**"])
    second = claim(module, "002-beta", owned_paths=["src/kis_mcp/**"])

    conflicts = module.find_claim_conflicts([first, second])

    assert conflicts == [
        (
            "EXCLUSIVE_PATH_OVERLAP: 001-alpha:src/** overlaps "
            "002-beta:src/kis_mcp/**; intersection=src/kis_mcp/**"
        )
    ]


def test_pull_request_claim_projection_releases_landed_schema_v3_claims() -> None:
    module = load_module()
    historical = claim(
        module,
        "115-historical",
        schema_version=3,
        risk_profile="standard",
        base_evidence=base_evidence(),
        owned_paths=["docs/OPERATIONS.md"],
    )
    current = claim(
        module,
        "117-current",
        schema_version=4,
        complexity="medium",
        risk_triggers=["public_contract"],
        base_evidence=base_evidence(),
        owned_paths=["docs/OPERATIONS.md"],
    )
    legacy = claim(
        module,
        "099-legacy",
        schema_version=2,
        work_management=work_management_evidence(
            record_id="SPEC-099", source_number=99
        ),
        owned_paths=["legacy/**"],
    )

    assert module.find_claim_conflicts([historical, current])

    projected = module.project_pull_request_claims(
        [historical, current, legacy],
        current_branch=current.branch,
    )

    projected_by_id = {item.change_id: item for item in projected}
    assert projected_by_id[historical.change_id].status == "closed"
    assert projected_by_id[current.change_id].status == "active"
    assert projected_by_id[legacy.change_id].status == "active"
    assert not module.find_claim_conflicts(projected)


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


def run_git(
    repository: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
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
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md", "change.md"):
        (template / name).write_text(f"# {name}\n", encoding="utf-8")
    (repository / "README.md").write_text("# Test repository\n", encoding="utf-8")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "test: initialize repository")
    return repository


def run_concurrent_new(
    repository: Path,
    state_root: Path,
    changes: list[tuple[str, str, str]],
    *,
    allocate_next: bool = False,
) -> list[subprocess.CompletedProcess[str]]:
    environment = {**os.environ, "KIS_STATE_ROOT": str(state_root)}
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--repository",
                str(repository),
                "new",
                change_id,
                *(["--allocate-next"] if allocate_next else []),
                "--outcome",
                outcome,
                "--owned",
                owned_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        for change_id, outcome, owned_path in changes
    ]
    results = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        results.append(
            subprocess.CompletedProcess(
                process.args,
                process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        )
    return results


def set_change_status(target: Path, change_id: str, status: str) -> None:
    scope_path = target / ".work" / "changes" / change_id / "scope.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope["status"] = status
    scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")


def test_claim_discovery_ignores_underscore_template_directories(
    tmp_path: Path,
) -> None:
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


def test_inventory_accepts_only_landed_malformed_schema_v4(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "083-historical"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/083-historical",
        "main",
    )
    change_root = target / ".work" / "changes" / "083-historical"
    change_root.mkdir(parents=True)
    change_root.joinpath("scope.json").write_text(
        json.dumps(historical_schema_v4_scope(module), indent=2) + "\n",
        encoding="utf-8",
    )
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md"):
        change_root.joinpath(name).write_text(f"# {name}\n", encoding="utf-8")
    run_git(target, "add", ".work/changes/083-historical")
    run_git(target, "commit", "-m", "test: add historical malformed scope")
    run_git(repository, "merge", "--no-ff", "change/083-historical", "-m", "merge historical")

    claims = module.load_worktree_claims(repository)
    current = next(item for item in claims if item.change_id == "083-historical")

    assert current.status == "closed"
    assert "HISTORICAL_WORK_RECORD_ID_SYNTHESIZED" in current.compatibility_warnings


def test_inventory_rejects_unmerged_malformed_schema_v4(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "083-historical"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/083-historical",
        "main",
    )
    change_root = target / ".work" / "changes" / "083-historical"
    change_root.mkdir(parents=True)
    change_root.joinpath("scope.json").write_text(
        json.dumps(historical_schema_v4_scope(module), indent=2) + "\n",
        encoding="utf-8",
    )
    run_git(target, "add", ".work/changes/083-historical/scope.json")
    run_git(target, "commit", "-m", "test: add active malformed scope")

    with pytest.raises(module.ClaimError, match="WORK_MANAGEMENT_FIELDS_MISSING: record_id"):
        module.load_worktree_claims(repository)


def test_validate_cli_exposes_additive_historical_compatibility_warnings(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "083-historical"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/083-historical",
        "main",
    )
    change_root = target / ".work" / "changes" / "083-historical"
    change_root.mkdir(parents=True)
    scope = historical_schema_v4_scope(module)
    scope["dependencies"] = ["86"]
    change_root.joinpath("scope.json").write_text(
        json.dumps(scope, indent=2) + "\n",
        encoding="utf-8",
    )
    for name in ("spec.md", "plan.md", "tasks.md", "closeout.md"):
        change_root.joinpath(name).write_text(f"# {name}\n", encoding="utf-8")
    run_git(target, "add", ".work/changes/083-historical")
    run_git(target, "commit", "-m", "test: add historical malformed scope")
    run_git(repository, "merge", "--no-ff", "change/083-historical", "-m", "merge historical")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repository",
            str(repository),
            "validate",
            "--claims-only",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert set(payload) == {
        "active_changes",
        "historical_compatibility_warnings",
        "orphaned_change_worktrees",
    }
    assert payload == {
        "active_changes": 0,
        "historical_compatibility_warnings": [
            {
                "change_id": "083-historical",
                "warnings": [
                    "HISTORICAL_DEPENDENCY_UNRESOLVED:86",
                    "HISTORICAL_WORK_RECORD_ID_SYNTHESIZED",
                ],
            }
        ],
        "orphaned_change_worktrees": [],
    }


def test_validate_cli_keeps_unmerged_malformed_claim_error_contract(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "083-historical"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/083-historical",
        "main",
    )
    change_root = target / ".work" / "changes" / "083-historical"
    change_root.mkdir(parents=True)
    change_root.joinpath("scope.json").write_text(
        json.dumps(historical_schema_v4_scope(module), indent=2) + "\n",
        encoding="utf-8",
    )
    run_git(target, "add", ".work/changes/083-historical/scope.json")
    run_git(target, "commit", "-m", "test: add active malformed scope")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repository",
            str(repository),
            "validate",
            "--claims-only",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "WORK_MANAGEMENT_FIELDS_MISSING: record_id\n"


def test_primary_claim_overrides_stale_copies_in_other_worktrees(
    tmp_path: Path,
) -> None:
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
    run_git(
        repository, "worktree", "add", str(unrelated), "-b", "change/001-alpha", "main"
    )

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


def test_create_change_worktree_allows_local_first_initialization(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    scope = json.loads(
        (target / ".work" / "changes" / "001-alpha" / "scope.json").read_text(
            encoding="utf-8"
        )
    )
    assert scope["schema_version"] == 4
    assert scope["complexity"] == "medium"
    assert scope["risk_triggers"] == []
    assert scope["base_evidence"]["relation"] == "unavailable"
    assert scope["base_evidence"]["evidence_source"] == "unavailable"
    assert "work_management" not in scope


def test_create_change_worktree_classifies_tree_equivalent_upstream_base(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    tree = run_git(repository, "rev-parse", "main^{tree}").stdout.strip()
    upstream = run_git(
        repository, "commit-tree", tree, "-m", "equivalent upstream"
    ).stdout.strip()

    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
        upstream_sha=upstream,
        upstream_tree=tree,
        upstream_ref="refs/remotes/origin/main",
    )
    scope = json.loads(
        (target / ".work" / "changes" / "001-alpha" / "scope.json").read_text(
            encoding="utf-8"
        )
    )

    assert scope["base_evidence"]["relation"] == "tree_equivalent"
    assert scope["base_evidence"]["upstream_sha"] == upstream
    assert scope["base_evidence"]["upstream_tree"] == tree
    assert scope["base_evidence"]["evidence_source"] == "provided"


def test_create_change_worktree_emits_schema_v4_work_management_evidence(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
        work_management=work_management_evidence(),
    )

    scope = json.loads(
        (target / ".work" / "changes" / "001-alpha" / "scope.json").read_text(
            encoding="utf-8"
        )
    )
    assert scope["schema_version"] == 4
    assert scope["complexity"] == "medium"
    assert scope["work_management"] == work_management_evidence()


def test_create_change_worktree_uses_standard_location_and_artifacts(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = create_registered_change(
        module,
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


def test_check_current_change_keeps_current_schema_v4_strict(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    scope_path = target / ".work" / "changes" / "001-alpha" / "scope.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope["risk_triggers"] = ["historical-only-trigger"]
    scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(module.ClaimError, match="CHANGE_RISK_TRIGGER_INVALID"):
        module.check_current_change(target)


def test_create_small_change_with_risk_trigger_uses_compact_record(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = module.create_change_worktree(
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
        complexity="small",
        risk_triggers=["secrets"],
    )
    change_root = target / ".work" / "changes" / "001-alpha"
    scope = json.loads((change_root / "scope.json").read_text(encoding="utf-8"))
    assert scope["complexity"] == "small"
    assert scope["risk_triggers"] == ["secrets"]
    assert (change_root / "scope.json").is_file()
    assert (change_root / "change.md").is_file()
    assert not (change_root / "spec.md").exists()
    assert not (change_root / "plan.md").exists()
    assert not (change_root / "tasks.md").exists()
    assert not (change_root / "closeout.md").exists()


def test_create_change_worktree_writes_all_change_artifacts_with_lf_bytes(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)

    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )

    change_root = target / ".work" / "changes" / "001-alpha"
    for name in ("scope.json", "spec.md", "plan.md", "tasks.md", "closeout.md"):
        content = (change_root / name).read_bytes()
        assert content.endswith(b"\n")
        assert b"\r\n" not in content


def test_create_change_worktree_rejects_duplicate_active_outcome(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/alpha/**"],
    )

    with pytest.raises(module.ClaimError, match="DUPLICATE_ACTIVE_OUTCOME"):
        create_registered_change(
            module,
            repository,
            change_id="002-beta",
            outcome="  implement   ALPHA ",
            owned_paths=["src/beta/**"],
        )


def test_create_change_worktree_rejects_historical_numeric_prefix_reuse(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    change_root = repository / ".work" / "changes" / "001-historical"
    change_root.mkdir(parents=True)
    historical = claim(module, "001-historical", status="closed")
    change_root.joinpath("scope.json").write_text(
        json.dumps(historical.to_mapping()) + "\n",
        encoding="utf-8",
    )
    run_git(repository, "add", ".work/changes/001-historical/scope.json")
    run_git(repository, "commit", "-m", "test: preserve historical change identity")

    with pytest.raises(module.ClaimError, match="DUPLICATE_CHANGE_NUMBER: 001"):
        create_registered_change(
            module,
            repository,
            change_id="001-new",
            outcome="Implement new work",
            owned_paths=["src/new/**"],
        )


def test_create_change_worktree_rejects_numeric_prefix_from_branch_ref(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "branch", "change/002-legacy", "main")

    with pytest.raises(module.ClaimError, match="DUPLICATE_CHANGE_NUMBER: 002"):
        create_registered_change(
            module,
            repository,
            change_id="002-new",
            outcome="Implement new work",
            owned_paths=["src/new/**"],
        )


def test_create_change_worktree_rejects_numeric_prefix_from_detached_worktree(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    legacy = repository / ".work" / "worktrees" / "003-legacy"
    run_git(repository, "worktree", "add", "--detach", str(legacy), "main")

    with pytest.raises(module.ClaimError, match="DUPLICATE_CHANGE_NUMBER: 003"):
        create_registered_change(
            module,
            repository,
            change_id="003-new",
            outcome="Implement new work",
            owned_paths=["src/new/**"],
        )


def test_allocate_next_uses_highest_governed_numeric_identity(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    run_git(repository, "branch", "change/003-legacy", "main")

    target = module.create_change_worktree(
        repository,
        change_id="allocated-work",
        outcome="Implement allocated work",
        owned_paths=["src/allocated/**"],
        allocate_next=True,
    )

    assert target.name == "004-allocated-work"
    assert run_git(repository, "branch", "--show-current").stdout.strip() == "main"


def test_concurrent_allocate_next_creators_receive_distinct_prefixes(
    tmp_path: Path,
) -> None:
    repository = initialize_repository(tmp_path)
    results = run_concurrent_new(
        repository,
        tmp_path / "state",
        [
            ("alpha", "Implement alpha", "src/alpha/**"),
            ("beta", "Implement beta", "src/beta/**"),
        ],
        allocate_next=True,
    )

    assert [result.returncode for result in results] == [0, 0]
    allocated = sorted(json.loads(result.stdout)["change_id"] for result in results)
    assert allocated == ["001-alpha", "002-beta"] or allocated == ["001-beta", "002-alpha"]


def test_concurrent_explicit_duplicate_prefix_allows_only_one_creator(
    tmp_path: Path,
) -> None:
    repository = initialize_repository(tmp_path)
    results = run_concurrent_new(
        repository,
        tmp_path / "state",
        [
            ("010-alpha", "Implement alpha", "src/alpha/**"),
            ("010-beta", "Implement beta", "src/beta/**"),
        ],
    )

    assert sorted(result.returncode for result in results) == [0, 1]
    failure = next(result for result in results if result.returncode != 0)
    assert "DUPLICATE_CHANGE_NUMBER: 010" in failure.stderr


def test_three_concurrent_scopes_never_admit_intersecting_ownership(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    results = run_concurrent_new(
        repository,
        tmp_path / "state",
        [
            ("011-alpha", "Implement alpha", "src/alpha/**"),
            ("012-beta", "Implement beta", "src/beta/**"),
            ("013-gamma", "Implement gamma", "src/**"),
        ],
    )

    failures = [result for result in results if result.returncode != 0]
    assert failures
    assert all("EXCLUSIVE_PATH_OVERLAP" in result.stderr for result in failures)
    claims = module.load_worktree_claims(repository)
    assert not module.find_claim_conflicts(claims)


def test_create_change_worktree_rejects_existing_unregistered_worktree(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    existing = repository / ".work" / "worktrees" / "001-alpha"
    run_git(
        repository, "worktree", "add", str(existing), "-b", "change/001-alpha", "main"
    )

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_CLAIM_MISSING"):
        create_registered_change(
            module,
            repository,
            change_id="002-beta",
            outcome="Implement beta",
            owned_paths=["src/beta/**"],
        )


def test_validate_repository_resolves_primary_root_from_linked_worktree(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    shutil.rmtree(repository / ".work" / "changes" / "_template")

    claims = module.validate_repository(target)

    assert [item.change_id for item in claims if item.status == "active"] == [
        "001-alpha"
    ]


def test_validate_repository_rejects_unregistered_change_worktree(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "001-alpha"
    run_git(
        repository, "worktree", "add", str(target), "-b", "change/001-alpha", "main"
    )

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_CLAIM_MISSING"):
        module.validate_repository(repository)


def test_validate_repository_can_skip_worktree_topology_for_isolated_ci(
    tmp_path: Path,
) -> None:
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

    assert [item.change_id for item in claims if item.status == "active"] == [
        "001-alpha"
    ]


def test_cleanup_refuses_dirty_worktree(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
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
def test_schema_v3_cleanup_derives_closed_state_after_verified_merge(
    tmp_path: Path,
    status: str,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    set_change_status(target, "001-alpha", status)
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", f"docs: register {status} alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")

    module.cleanup_change_worktree(repository, "001-alpha")

    assert not target.exists()
    assert not run_git(
        repository, "branch", "--list", "change/001-alpha"
    ).stdout.strip()
    claims = module.load_worktree_claims(repository)
    current = next(item for item in claims if item.change_id == "001-alpha")
    assert current.status == "closed"


def test_legacy_schema_v2_cleanup_still_requires_explicit_closed_status(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )
    scope_path = target / ".work" / "changes" / "001-alpha" / "scope.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope["schema_version"] = 2
    scope.pop("complexity")
    scope.pop("risk_triggers")
    scope.pop("base_evidence")
    scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
    run_git(target, "add", ".work/changes/001-alpha")
    run_git(target, "commit", "-m", "docs: register legacy alpha change")
    run_git(repository, "merge", "--no-ff", "change/001-alpha", "-m", "merge alpha")

    with pytest.raises(module.ClaimError, match="CHANGE_STATUS_NOT_CLOSED"):
        module.cleanup_change_worktree(repository, "001-alpha")

    assert target.exists()


def test_cleanup_removes_clean_merged_worktree_and_branch(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
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
    target = create_registered_change(
        module,
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
    assert (result.backup_path / "remnant.txt").read_text(
        encoding="utf-8"
    ) == "recoverable\n"
    assert not target.exists()
    assert not run_git(
        repository, "branch", "--list", "change/001-alpha"
    ).stdout.strip()


def test_cleanup_does_not_move_or_delete_when_registration_remains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = create_registered_change(
        module,
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


def test_schema_v4_classification_uses_repository_settings() -> None:
    module = load_module()
    settings_path = REPOSITORY_ROOT / "settings" / "change-governance.settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))

    assert module.COMPLEXITIES == frozenset(settings["complexities"])
    assert module.RISK_TRIGGERS == frozenset(settings["risk_triggers"])
    assert module.CHANGE_FILES_BY_COMPLEXITY["small"] == tuple(
        settings["complexities"]["small"]["artifacts"]
    )


def test_retire_closed_orphan_preserves_unmerged_branch_and_unblocks_validation(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "078-diagnostics-agent3"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/078-diagnostics-agent3",
        "main",
    )
    (target / "evidence.txt").write_text("preserved\n", encoding="utf-8")
    run_git(target, "add", "evidence.txt")
    run_git(target, "commit", "-m", "retain orphan evidence")
    head = run_git(target, "rev-parse", "HEAD").stdout.strip()

    with pytest.raises(module.ClaimError, match="ACTIVE_CHANGE_CLAIM_MISSING"):
        module.validate_repository(repository)
    assert module.orphaned_change_worktrees(repository) == [
        {"branch": "change/078-diagnostics-agent3", "path": str(target.resolve())}
    ]

    result = module.retire_closed_orphan_worktree(
        repository,
        "078-diagnostics-agent3",
        terminal_work_confirmed=True,
    )

    assert result.branch == "change/078-diagnostics-agent3"
    assert not target.exists()
    assert run_git(repository, "rev-parse", result.branch).stdout.strip() == head
    assert module.validate_repository(repository) == []


def test_retire_closed_orphan_requires_terminal_confirmation_and_recovers_dirty_state(
    tmp_path: Path,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "078-diagnostics-agent3"
    run_git(repository, "worktree", "add", str(target), "-b", "change/078-diagnostics-agent3", "main")

    with pytest.raises(module.ClaimError, match="TERMINAL_WORK_EVIDENCE_REQUIRED"):
        module.retire_closed_orphan_worktree(
            repository,
            "078-diagnostics-agent3",
            terminal_work_confirmed=False,
        )

    (target / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    head = run_git(target, "rev-parse", "HEAD").stdout.strip()
    result = module.retire_closed_orphan_worktree(
        repository,
        "078-diagnostics-agent3",
        terminal_work_confirmed=True,
    )

    assert result.recovered is True
    assert result.backup_path is not None
    assert result.backup_path.joinpath("dirty.txt").read_text(encoding="utf-8") == "dirty\n"
    assert not target.exists()
    assert run_git(repository, "rev-parse", result.branch).stdout.strip() == head
    assert result.branch not in {
        entry.branch for entry in module.discover_worktrees(repository) if entry.branch
    }


def test_retire_closed_orphan_refuses_registered_claim(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    create_registered_change(
        module,
        repository,
        change_id="001-alpha",
        outcome="Implement alpha",
        owned_paths=["src/**"],
    )

    with pytest.raises(module.ClaimError, match="ORPHAN_CHANGE_CLAIM_PRESENT"):
        module.retire_closed_orphan_worktree(
            repository,
            "001-alpha",
            terminal_work_confirmed=True,
        )


def test_retire_closed_orphan_accepts_legacy_mismatched_worktree_directory(tmp_path: Path) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "082-kronos-empirical"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/081-kronos-target-interface-contract-repair",
        "main",
    )
    head = run_git(target, "rev-parse", "HEAD").stdout.strip()

    result = module.retire_closed_orphan_worktree(
        repository,
        "081-kronos-target-interface-contract-repair",
        terminal_work_confirmed=True,
    )

    assert not target.exists()
    assert run_git(repository, "rev-parse", result.branch).stdout.strip() == head


def test_retire_closed_orphan_recovers_when_git_status_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    repository = initialize_repository(tmp_path)
    target = repository / ".work" / "worktrees" / "081-broken-submodule"
    run_git(
        repository,
        "worktree",
        "add",
        str(target),
        "-b",
        "change/081-broken-submodule",
        "main",
    )
    marker = target / "preserve-me.txt"
    marker.write_text("recoverable\n", encoding="utf-8")
    head = run_git(target, "rev-parse", "HEAD").stdout.strip()
    original_run_git = module._run_git

    def flaky_run_git(repo: Path, *args: str, check: bool = True):
        if args[:1] == ("status",):
            return subprocess.CompletedProcess(["git", *args], 128, "", "broken submodule metadata")
        return original_run_git(repo, *args, check=check)

    monkeypatch.setattr(module, "_run_git", flaky_run_git)
    result = module.retire_closed_orphan_worktree(
        repository,
        "081-broken-submodule",
        terminal_work_confirmed=True,
    )

    assert result.recovered is True
    assert result.backup_path is not None
    assert result.backup_path.joinpath("preserve-me.txt").read_text(encoding="utf-8") == "recoverable\n"
    assert run_git(repository, "rev-parse", result.branch).stdout.strip() == head
