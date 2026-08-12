from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_codex_bootstrap_is_exact_stable_and_project_contained() -> None:
    settings = json.loads(
        (ROOT / "settings" / "bootstrap" / "codex.install.json").read_text("utf-8")
    )

    assert settings["tool_id"] == "codex-cli"
    assert settings["package"] == "@openai/codex"
    assert settings["version"] == "0.147.0"
    assert settings["install_root"] == r"C:\Projects\.kis-mcp\tools\codex\0.147.0"
    assert settings["managed_home"] == r"C:\Projects\.kis-mcp\agent-hosts\codex-reviewer"
    for key in ("install_root", "managed_home", "npm_cache_root", "temp_root", "quarantine_root"):
        assert settings[key].casefold().startswith("c:\\projects\\")


def test_codex_install_script_uses_exact_local_prefix_without_global_install() -> None:
    content = (ROOT / "scripts" / "install-codex.ps1").read_text("utf-8")

    assert "@openai/codex" in content
    assert "0.147.0" in content
    assert "npm.cmd" in content
    assert "install --prefix" in content
    assert "--save-exact" in content
    assert " -g " not in content
    assert "@latest" not in content
    assert "Assert-InProjects" in content
    assert "CODEX_PATH_REPARSE_POINT" in content
    assert "CODEX_ACTIVATION_ROLLBACK_FAILED" in content


def test_codex_auth_script_uses_managed_home_and_chatgpt_login() -> None:
    content = (ROOT / "scripts" / "auth-codex.ps1").read_text("utf-8")

    assert "CODEX_HOME" in content
    assert "managed_home" in content
    assert "& $Executable login --device-auth" in content
    assert "login status 2>&1" in content
    assert "login status 2>$null" not in content
    assert "--login" not in content
    assert "login_mode" in content
    assert "Remove-Item Env:OPENAI_API_KEY" in content
    assert "CODEX_PATH_REPARSE_POINT" in content
    assert "api_key" not in json.loads(
        (ROOT / "settings" / "bootstrap" / "codex.install.json").read_text("utf-8")
    )


def test_agent_and_bootstrap_codex_paths_remain_aligned() -> None:
    bootstrap = json.loads(
        (ROOT / "settings" / "bootstrap" / "codex.install.json").read_text("utf-8")
    )
    agent = json.loads(
        (ROOT / "settings" / "agents" / "code-review-agent.settings.json").read_text("utf-8")
    )["codex"]

    assert agent["executable"] == bootstrap["executable"]
    assert agent["home_path"] == bootstrap["managed_home"]
    assert agent["expected_version"] == bootstrap["version"]
