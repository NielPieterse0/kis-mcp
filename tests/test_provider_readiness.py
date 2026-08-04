from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from kis_mcp.config import RuntimeConfig, load_runtime_config
from kis_mcp.provider_readiness import (
    ProviderReadinessError,
    validate_provider_offline_readiness,
)
from kis_mcp.server import _provider_environment, build_server


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_runtime_config(REPOSITORY_ROOT)


def _config_with_provider_changes(**changes: object) -> RuntimeConfig:
    settings = deepcopy(CONFIG.raw_settings)
    provider = settings["desktop_commander"]
    for key, value in changes.items():
        if key.startswith("env_"):
            provider["launch"]["env"][key.removeprefix("env_")] = value
        else:
            provider[key] = value
    return RuntimeConfig(raw_settings=settings, raw_policy=deepcopy(CONFIG.raw_policy))


def _ready_config(
    tmp_path: Path,
    *,
    installed_name: str | None = None,
    installed_version: str | None = None,
    **changes: object,
) -> RuntimeConfig:
    settings = deepcopy(CONFIG.raw_settings)
    provider = settings["desktop_commander"]
    install_root = tmp_path / "desktop-commander"
    package_root = (
        install_root
        / "node_modules"
        / "@wonderwhy-er"
        / "desktop-commander"
    )
    entry = package_root / "dist" / "index.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("// test provider entry\n", encoding="utf-8")
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": installed_name or provider["package"],
                "version": installed_version or provider["version"],
            }
        ),
        encoding="utf-8",
    )

    config_root = tmp_path / "desktop-commander-config"
    config_root.mkdir()
    (config_root / "config.json").write_text(
        json.dumps(
            {
                "blockedCommands": [],
                "allowedDirectories": [],
                "telemetryEnabled": False,
            }
        ),
        encoding="utf-8",
    )

    settings["paths"]["desktop_commander_root"] = str(install_root)
    settings["paths"]["desktop_commander_config_root"] = str(config_root)
    provider["launch"]["cwd"] = str(install_root)
    provider["launch"]["args"][0] = str(entry)
    for key, value in changes.items():
        if key.startswith("env_"):
            provider["launch"]["env"][key.removeprefix("env_")] = value
        else:
            provider[key] = value
    return RuntimeConfig(raw_settings=settings, raw_policy=deepcopy(CONFIG.raw_policy))


def test_offline_readiness_accepts_disabled_telemetry_and_loopback_flags(
    tmp_path: Path,
) -> None:
    config = _ready_config(tmp_path, require_local_chrome=False)
    validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_provider_command_denylist(tmp_path: Path) -> None:
    config = _ready_config(tmp_path, require_local_chrome=False)
    Path(config.provider_state_file).write_text(
        json.dumps(
            {
                "blockedCommands": ["sudo"],
                "allowedDirectories": [],
                "telemetryEnabled": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProviderReadinessError, match="command denylist"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_provider_directory_allowlist(tmp_path: Path) -> None:
    config = _ready_config(tmp_path, require_local_chrome=False)
    Path(config.provider_state_file).write_text(
        json.dumps(
            {
                "blockedCommands": [],
                "allowedDirectories": [r"C:\Projects\kis-mcp"],
                "telemetryEnabled": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProviderReadinessError, match="directory allowlist"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_persisted_telemetry(tmp_path: Path) -> None:
    config = _ready_config(tmp_path, require_local_chrome=False)
    Path(config.provider_state_file).write_text(
        json.dumps(
            {
                "blockedCommands": [],
                "allowedDirectories": [],
                "telemetryEnabled": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProviderReadinessError, match="persisted telemetry"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_enabled_telemetry(tmp_path: Path) -> None:
    config = _ready_config(
        tmp_path,
        require_local_chrome=False,
        env_DESKTOP_COMMANDER_DISABLE_TELEMETRY="false",
    )
    with pytest.raises(ProviderReadinessError, match="telemetry"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_external_feature_flags(tmp_path: Path) -> None:
    config = _ready_config(
        tmp_path,
        require_local_chrome=False,
        env_DC_FLAG_URL="https://example.com/flags",
    )
    with pytest.raises(ProviderReadinessError, match="feature flags"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_missing_feature_flag_override(tmp_path: Path) -> None:
    config = _ready_config(tmp_path, require_local_chrome=False)
    config.raw_settings["desktop_commander"]["launch"]["env"].pop("DC_FLAG_URL")
    with pytest.raises(ProviderReadinessError, match="feature flags"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_missing_chrome_before_provider_download(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _ready_config(tmp_path, require_local_chrome=True)
    monkeypatch.setattr("kis_mcp.provider_readiness.find_local_chrome", lambda _config: None)
    with pytest.raises(ProviderReadinessError, match="download Chrome"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_installed_version_mismatch(
    tmp_path: Path,
) -> None:
    config = _ready_config(
        tmp_path,
        installed_version="0.0.0",
        require_local_chrome=False,
    )
    with pytest.raises(ProviderReadinessError, match="version differs"):
        validate_provider_offline_readiness(config)


def test_offline_readiness_rejects_installed_identity_mismatch(
    tmp_path: Path,
) -> None:
    config = _ready_config(
        tmp_path,
        installed_name="different-package",
        require_local_chrome=False,
    )
    with pytest.raises(ProviderReadinessError, match="identity differs"):
        validate_provider_offline_readiness(config)


def test_provider_environment_cannot_override_gateway_owned_paths() -> None:
    config = _config_with_provider_changes(
        require_local_chrome=False,
        env_HOME=r"C:\Windows",
        env_TEMP=r"C:\Windows\Temp",
        env_NPM_CONFIG_CACHE=r"C:\Windows\npm-cache",
        env_PUPPETEER_CACHE_DIR=r"C:\Windows\browser-cache",
        env_NO_UPDATE_NOTIFIER="0",
    )
    environment = _provider_environment(config)

    assert environment["HOME"] == CONFIG.state_root
    assert environment["TEMP"] == CONFIG.temp_root
    assert environment["NPM_CONFIG_CACHE"] == CONFIG.npm_cache_root
    assert environment["PUPPETEER_CACHE_DIR"] == CONFIG.puppeteer_cache_root
    assert environment["NO_UPDATE_NOTIFIER"] == "1"


def test_server_construction_enforces_provider_readiness(monkeypatch) -> None:
    def fail(_config: RuntimeConfig) -> None:
        raise ProviderReadinessError("readiness sentinel")

    monkeypatch.setattr("kis_mcp.server.validate_provider_offline_readiness", fail)
    with pytest.raises(ProviderReadinessError, match="sentinel"):
        build_server(CONFIG)


def test_server_construction_can_skip_readiness_for_isolated_contract_tests() -> None:
    server = build_server(CONFIG, validate_provider=False)
    assert server.name == CONFIG.server_name
