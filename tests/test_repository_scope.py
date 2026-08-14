from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_repository_skills_use_only_approved_runtime_catalogue() -> None:
    runtime_root = REPOSITORY_ROOT / "src"
    assert (runtime_root / "kis_mcp" / "skills").is_dir()
    assert not (runtime_root / "skills").exists()

    skills_settings = json.loads(
        (REPOSITORY_ROOT / "settings" / "skills.settings.json").read_text(
            encoding="utf-8"
        )
    )
    assert skills_settings["schema_version"] == 1
    assert skills_settings["root"] == r"C:\Projects\.agents\skills"
    assert skills_settings["staging_root"] == r"C:\Projects\.kis-mcp\temp\skills"

    runtime_and_config_files = [
        *runtime_root.rglob("*.py"),
        *(REPOSITORY_ROOT / "settings").rglob("*.json"),
        *(REPOSITORY_ROOT / "policy").rglob("*.json"),
    ]
    for path in runtime_and_config_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if ".agents\\skills" in line or ".agents\\\\skills" in line:
                assert "C:\\Projects\\.agents\\skills" in line or (
                    "C:\\\\Projects\\\\.agents\\\\skills" in line
                )


def test_repository_contains_no_tracked_local_skill_catalogue() -> None:
    pathspec = "/".join((".agents", "skills"))
    tracked = (
        __import__("subprocess")
        .run(
            ["git", "ls-files", pathspec],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.splitlines()
    )
    assert tracked == []

    agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "load_skill" in agents
    assert "read_skill_file" in agents
    assert ("/".join((".agents", "skills")) + "/") not in agents


def test_verification_uses_locked_external_interpreter() -> None:
    powershell = (REPOSITORY_ROOT / "scripts" / "verify.ps1").read_text(
        encoding="utf-8"
    )
    python = (REPOSITORY_ROOT / "scripts" / "verify.py").read_text(encoding="utf-8")
    start = (REPOSITORY_ROOT / "scripts" / "start.ps1").read_text(encoding="utf-8")

    assert "uv sync --offline --dev --frozen" in powershell
    assert "sys.executable" in python
    assert '"-m",\n            "pytest"' in python
    assert "uv run --no-sync pytest" not in powershell
    assert "uv run --no-sync kis-mcp" not in start


def test_desktop_commander_bootstrap_resolves_windows_node_and_npm_launchers() -> None:
    installer = (
        REPOSITORY_ROOT / "scripts" / "install-desktop-commander.ps1"
    ).read_text(encoding="utf-8")

    assert "& npm.exe" not in installer
    assert "Get-Command 'node.exe'" in installer
    assert "Get-Command 'npm.cmd'" in installer
    assert "NODE_NOT_INSTALLED" in installer
    assert "NPM_NOT_INSTALLED" in installer


def test_desktop_commander_bootstrap_uses_verified_scanned_archive_offline() -> None:
    installer = (
        REPOSITORY_ROOT / "scripts" / "install-desktop-commander.ps1"
    ).read_text(encoding="utf-8")
    settings = (REPOSITORY_ROOT / "settings" / "kis-mcp.settings.json").read_text(
        encoding="utf-8"
    )

    assert "wonderwhy-er-desktop-commander-0.2.46.tgz" in settings
    assert "DA392A6CC44CA1E3B390FCD8D95F79584F8CD40147A793EA94504843C05C4CED" in settings
    assert "Get-FileHash" in installer
    assert "HASH_MISMATCH" in installer
    assert "--offline" in installer
    assert "--ignore-scripts" in installer
    assert "$ArchivePath" in installer
    assert '"$Package@$Version"' not in installer
    assert "authoritative npm registry" not in installer


def test_dependency_cache_preparation_is_supervised_scanned_and_separate() -> None:
    preparation = (
        REPOSITORY_ROOT / "scripts" / "prepare-desktop-commander-cache.ps1"
    ).read_text(encoding="utf-8")
    installer = (
        REPOSITORY_ROOT / "scripts" / "install-desktop-commander.ps1"
    ).read_text(encoding="utf-8")

    assert "Get-FileHash" in preparation
    assert "MpCmdRun.exe" in preparation
    assert "--ignore-scripts" in preparation
    assert "$ArchivePath" in preparation
    assert '"$Package@$Version"' not in preparation
    assert "Move-Item -LiteralPath $AcquisitionCache -Destination $CacheRoot" in preparation
    assert "Previous cache retained" in preparation
    assert "--offline" in installer
    assert "NPM_CONFIG_OFFLINE = 'true'" in installer


def test_desktop_commander_is_not_vendored() -> None:
    assert not (REPOSITORY_ROOT / "node_modules").exists()
    assert not (REPOSITORY_ROOT / "DesktopCommanderMCP").exists()


def test_provider_contract_capture_and_artifacts_are_repository_managed() -> None:
    contract_root = REPOSITORY_ROOT / "contracts" / "desktop-commander"
    assert (contract_root / "0.2.46.tools.json").is_file()
    assert (contract_root / "0.2.46.schema.sha256").is_file()
    assert (REPOSITORY_ROOT / "scripts" / "capture-provider-contract.py").is_file()
    assert (REPOSITORY_ROOT / "scripts" / "capture-provider-contract.ps1").is_file()


def test_no_predecessor_runtime_package_is_present() -> None:
    assert not (REPOSITORY_ROOT / "src" / "sdk_tool").exists()
    assert not (REPOSITORY_ROOT / "src" / "mcp_tool").exists()


def test_policy_declares_only_three_rules() -> None:
    policy_text = (REPOSITORY_ROOT / "policy" / "kis-mcp.policy.json").read_text(
        encoding="utf-8"
    )
    assert policy_text.count('"id": "HR-') == 3


def test_parallel_change_workflow_is_standardized_and_tracked() -> None:
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    operations = (REPOSITORY_ROOT / "docs" / "OPERATIONS.md").read_text(
        encoding="utf-8"
    )
    wrapper = (REPOSITORY_ROOT / "scripts" / "change-workflow.ps1").read_text(
        encoding="utf-8"
    )

    assert ".work/worktrees/" in gitignore.splitlines()
    assert ".work/worktrees/<change-id>" in agents
    assert "Parallel agent count is not limited" in agents
    assert "scope.json" in agents
    assert "change-governance.py" in wrapper
    assert "change-workflow.ps1 new" in operations
    assert "change-workflow.ps1 check" in operations
    assert "change-workflow.ps1 cleanup" in operations

    template = REPOSITORY_ROOT / ".work" / "changes" / "_template"
    for name in ("scope.json", "spec.md", "plan.md", "tasks.md", "closeout.md"):
        assert (template / name).is_file()


def test_repository_verification_checks_change_governance_layout() -> None:
    verifier = (REPOSITORY_ROOT / "scripts" / "verify.py").read_text(encoding="utf-8")

    assert "verify_change_governance" in verifier
    assert "change-governance.py" in verifier
    assert ".work/changes/_template" in verifier


def _load_repository_verifier():
    path = REPOSITORY_ROOT / "scripts" / "verify.py"
    spec = importlib.util.spec_from_file_location("kis_repository_verify", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_declares_canonical_line_ending_policy() -> None:
    attributes = (REPOSITORY_ROOT / ".gitattributes").read_text(encoding="utf-8")
    editor = (REPOSITORY_ROOT / ".editorconfig").read_text(encoding="utf-8")
    configure = (
        REPOSITORY_ROOT / "scripts" / "configure-repository.ps1"
    ).read_text(encoding="utf-8")
    workflow = (REPOSITORY_ROOT / "scripts" / "change-workflow.ps1").read_text(
        encoding="utf-8"
    )
    verification = (REPOSITORY_ROOT / "scripts" / "verify.ps1").read_text(
        encoding="utf-8"
    )

    assert "* text=auto eol=lf" in attributes
    assert "*.cmd text eol=crlf" in attributes
    assert "end_of_line = lf" in editor
    assert "core.autocrlf false" in configure
    assert "core.eol lf" in configure
    assert "core.safecrlf true" in configure
    assert "configure-repository.ps1" in workflow
    assert "configure-repository.ps1" in verification


def test_line_ending_verifier_flags_only_lf_policy_violations() -> None:
    verifier = _load_repository_verifier()
    output = "\n".join(
        (
            "i/lf    w/lf    attr/text=auto eol=lf\tgood.py",
            "i/crlf  w/crlf  attr/text=auto eol=lf\tbad.json",
            "i/lf    w/mixed attr/text=auto eol=lf\tmixed.md",
            "i/lf    w/crlf  attr/text eol=crlf\tlegacy.cmd",
            "i/-text w/-text attr/-text\timage.png",
        )
    )

    assert verifier._line_ending_violations(output) == [
        {
            "path": "bad.json",
            "index": "crlf",
            "worktree": "crlf",
        },
        {
            "path": "mixed.md",
            "index": "lf",
            "worktree": "mixed",
        },
    ]


def test_repository_verification_runs_line_ending_check() -> None:
    verifier = (REPOSITORY_ROOT / "scripts" / "verify.py").read_text(encoding="utf-8")

    assert "def verify_repository_line_endings()" in verifier
    assert "verify_repository_line_endings," in verifier
    assert '"repository-line-endings"' in verifier