from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_secret_settings_define_only_metadata_and_approved_modes() -> None:
    settings = json.loads(
        (ROOT / "settings" / "secrets.settings.json").read_text(encoding="utf-8")
    )

    assert settings["root"] == r"C:\Projects\.kis-mcp\secrets"
    assert settings["bootstrap_environment"] == "KIS_MCP_VAULT_KEY"
    assert settings["interactive_unlock"] is True
    assert settings["self_unlocking_key_file"] is False
    assert settings["cipher"] == "AES-256-GCM"
    assert settings["kdf"] == "argon2id"
    serialized = json.dumps(settings).casefold()
    assert "passphrase" not in serialized
    assert "secret://" not in serialized
    assert "master.key" not in serialized


def test_common_script_transfers_sensitive_payload_only_over_standard_input() -> None:
    content = _script("secret-vault.ps1")

    assert "Read-Host" in content
    assert "-AsSecureString" in content
    assert "RedirectStandardInput" in content
    assert "AnonymousPipeServerStream" in content
    assert "ConvertTo-Json" in content
    assert "ZeroFreeBSTR" in content
    assert "KIS_MCP_VAULT_KEY" in content
    assert "KIS_MCP_SECRET_INPUT_PIPE_HANDLE" in content
    assert "ArgumentList" in content
    assert "$Process.Kill()" in content
    assert "--passphrase" not in content
    assert "--secret" not in content
    assert "master.key" not in content


def test_operator_scripts_use_common_secure_boundary() -> None:
    for name in (
        "initialize-secret-vault.ps1",
        "set-secret.ps1",
        "rotate-secret.ps1",
        "unlock-secrets.ps1",
    ):
        content = _script(name)
        assert "secret-vault.ps1" in content
        assert "Invoke-KisMcpSecretCommand" in content
        assert "windows-credential.ps1" not in content
        assert "Set-KisMcpWindowsCredential" not in content
        assert "Get-KisMcpWindowsCredential" not in content

    assert "-AsSecureString" in _script("set-secret.ps1")
    assert "-AsSecureString" in _script("rotate-secret.ps1")
    assert "resolve-internal" not in _script("unlock-secrets.ps1")


def test_local_launcher_does_not_unlock_or_launch_through_secret_vault() -> None:
    content = _script("start.ps1")

    assert "kis_mcp.server" in content
    assert "kis_mcp.secrets.launcher" not in content
    assert "KIS_MCP_SECRET_INPUT_PIPE_HANDLE" not in content
    assert "Start-KisMcpSecretAwareProcess" not in content
    assert "Read-Host 'Unlock kis-mcp secrets'" not in content
    assert "KIS_MCP_VAULT_PASSPHRASE" not in content
    assert "--passphrase" not in content


def test_local_launcher_validates_before_direct_runtime_start() -> None:
    content = _script("start.ps1")

    validation = content.index("load_runtime_config(Path.cwd())")
    process_start = content.index("$Process = [System.Diagnostics.Process]::new()")

    assert validation < process_start
