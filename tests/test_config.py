from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from kis_mcp.config import EXPECTED_RULE_IDS, load_runtime_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _configuration_copy(tmp_path: Path) -> Path:
    root = tmp_path / "configuration-copy"
    (root / "settings").mkdir(parents=True)
    (root / "policy").mkdir()
    (root / "settings" / "kis-mcp.settings.json").write_text(
        (REPOSITORY_ROOT / "settings" / "kis-mcp.settings.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (root / "policy" / "kis-mcp.policy.json").write_text(
        (REPOSITORY_ROOT / "policy" / "kis-mcp.policy.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    return root


def _read_settings(root: Path) -> dict[str, object]:
    return json.loads(
        (root / "settings" / "kis-mcp.settings.json").read_text(encoding="utf-8")
    )


def _write_settings(root: Path, settings: dict[str, object]) -> None:
    (root / "settings" / "kis-mcp.settings.json").write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )


def test_configuration_loads_with_exact_three_rules() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    rule_ids = tuple(rule["id"] for rule in config.raw_policy["rules"])
    assert rule_ids == EXPECTED_RULE_IDS


def test_settings_and_policy_share_boundaries() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    assert config.project_boundary == config.raw_policy["project_boundary"]
    assert config.quarantine_root == config.raw_policy["quarantine_root"]


def test_status_fields_do_not_control_tool_availability() -> None:
    config = load_runtime_config(REPOSITORY_ROOT)
    assert "commissioning" not in config.raw_settings
    assert "implementation_status" in config.raw_settings


def test_generated_paths_must_remain_beneath_canonical_state_root(
    tmp_path: Path,
) -> None:
    root = _configuration_copy(tmp_path)
    settings = _read_settings(root)
    settings["paths"]["temp_root"] = r"C:\Windows\Temp\kis-mcp"  # type: ignore[index]
    _write_settings(root, settings)

    with pytest.raises(RuntimeError, match="temp_root.*state_root"):
        load_runtime_config(root)


def test_state_root_is_fixed_by_repository_authority(tmp_path: Path) -> None:
    root = _configuration_copy(tmp_path)
    settings = _read_settings(root)
    settings["paths"]["state_root"] = r"C:\Projects\.other-state"  # type: ignore[index]
    _write_settings(root, settings)

    with pytest.raises(RuntimeError, match="state_root must be"):
        load_runtime_config(root)


def test_provider_entry_must_remain_beneath_install_root(tmp_path: Path) -> None:
    root = _configuration_copy(tmp_path)
    settings = _read_settings(root)
    settings["desktop_commander"]["launch"]["args"][0] = (  # type: ignore[index]
        r"C:\Projects\other\index.js"
    )
    _write_settings(root, settings)

    with pytest.raises(RuntimeError, match="entry point"):
        load_runtime_config(root)


def test_configuration_validation_does_not_create_generated_directories(
    tmp_path: Path,
) -> None:
    root = _configuration_copy(tmp_path)
    settings = _read_settings(root)
    candidate = Path(r"C:\Projects\.kis-mcp") / f"not-created-{uuid.uuid4().hex}"
    settings["paths"]["log_root"] = str(candidate)  # type: ignore[index]
    _write_settings(root, settings)

    load_runtime_config(root)
    assert not candidate.exists()


def test_invalid_discover_settings_are_rejected(tmp_path: Path) -> None:
    root = _configuration_copy(tmp_path)
    settings = _read_settings(root)
    settings["discover"]["limits"]["max_files"] = 0  # type: ignore[index]
    _write_settings(root, settings)

    with pytest.raises(RuntimeError, match="settings.discover.limits.max_files"):
        load_runtime_config(root)


def test_default_configuration_requires_a_source_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kis_mcp.config as config_module

    installed_module = tmp_path / "site-packages" / "kis_mcp" / "config.py"
    installed_module.parent.mkdir(parents=True)
    installed_module.write_text("# installed copy\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "__file__", str(installed_module))

    with pytest.raises(RuntimeError, match="KIS_MCP_SOURCE_CHECKOUT_REQUIRED"):
        config_module.load_runtime_config()
