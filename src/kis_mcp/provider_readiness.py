from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .config import RuntimeConfig


class ProviderReadinessError(RuntimeError):
    pass


def _is_loopback_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").strip("[]").casefold()
    return parsed.scheme in {"http", "https"} and host in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def local_chrome_candidates(
    *,
    config_root: str,
    local_appdata: str | None = None,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    cache_root = Path(config_root) / "puppeteer-cache" / "chrome"
    if cache_root.exists():
        candidates.extend(cache_root.glob("*/chrome-win64/chrome.exe"))
        candidates.extend(cache_root.glob("*/chrome-linux64/chrome"))
        candidates.extend(
            cache_root.glob(
                "*/chrome-mac-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            )
        )

    candidates.extend(
        [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Chromium\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Chromium\Application\chrome.exe"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    )
    appdata = local_appdata or os.environ.get("LOCALAPPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Google" / "Chrome" / "Application" / "chrome.exe")

    return tuple(dict.fromkeys(candidates))


def find_local_chrome(config: RuntimeConfig) -> Path | None:
    for candidate in local_chrome_candidates(
        config_root=config.desktop_commander_config_root
    ):
        if candidate.is_file():
            return candidate
    return None


def validate_provider_installation(config: RuntimeConfig) -> None:
    entry = Path(config.desktop_commander_entry)
    metadata_path = Path(config.desktop_commander_package_metadata)
    if not entry.is_file():
        raise ProviderReadinessError(
            f"PROVIDER_NOT_READY: Desktop Commander entry point is missing: {entry}"
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ProviderReadinessError(
            f"PROVIDER_NOT_READY: Desktop Commander package metadata is missing: {metadata_path}"
        ) from exc
    except (json.JSONDecodeError, OSError, UnicodeError) as exc:
        raise ProviderReadinessError(
            f"PROVIDER_NOT_READY: Desktop Commander package metadata is invalid: {metadata_path}"
        ) from exc
    if not isinstance(metadata, dict):
        raise ProviderReadinessError(
            "PROVIDER_NOT_READY: Desktop Commander package metadata must be an object."
        )
    if str(metadata.get("name", "")) != config.desktop_commander_package:
        raise ProviderReadinessError(
            "PROVIDER_NOT_READY: Installed Desktop Commander package identity differs from settings."
        )
    if str(metadata.get("version", "")) != config.desktop_commander_version:
        raise ProviderReadinessError(
            "PROVIDER_NOT_READY: Installed Desktop Commander version differs from the pinned version."
        )


def validate_provider_policy_state(config: RuntimeConfig) -> None:
    state_path = Path(config.provider_state_file)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ProviderReadinessError(
            f"PROVIDER_NOT_READY: Desktop Commander policy state is missing: {state_path}"
        ) from exc
    except (json.JSONDecodeError, OSError, UnicodeError) as exc:
        raise ProviderReadinessError(
            f"PROVIDER_NOT_READY: Desktop Commander policy state is invalid: {state_path}"
        ) from exc
    if not isinstance(state, dict):
        raise ProviderReadinessError(
            "PROVIDER_NOT_READY: Desktop Commander policy state must be an object."
        )
    if state.get("blockedCommands") != []:
        raise ProviderReadinessError(
            "PROVIDER_POLICY_CONFLICT: Desktop Commander's built-in command denylist "
            "must remain empty; FastMCP enforces only HR-001, HR-002, and HR-003."
        )
    if state.get("allowedDirectories") != []:
        raise ProviderReadinessError(
            "PROVIDER_POLICY_CONFLICT: Desktop Commander's directory allowlist must "
            "remain empty; FastMCP applies the approved write boundary."
        )
    telemetry = state.get("telemetryEnabled")
    if telemetry is not False and str(telemetry).strip().casefold() != "false":
        raise ProviderReadinessError(
            "HR-002_EXTERNAL_NETWORK: Desktop Commander persisted telemetry must be disabled."
        )


def validate_provider_offline_readiness(config: RuntimeConfig) -> Path | None:
    validate_provider_installation(config)
    validate_provider_policy_state(config)
    launch_env = {
        str(key): str(value)
        for key, value in config.desktop_commander_launch.get("env", {}).items()
    }

    if launch_env.get("DESKTOP_COMMANDER_DISABLE_TELEMETRY", "").casefold() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise ProviderReadinessError(
            "HR-002_EXTERNAL_NETWORK: Desktop Commander telemetry must be disabled."
        )

    flag_url = launch_env.get("DC_FLAG_URL", "")
    if not _is_loopback_url(flag_url):
        raise ProviderReadinessError(
            "HR-002_EXTERNAL_NETWORK: Desktop Commander feature flags must resolve to loopback."
        )

    chrome = find_local_chrome(config)
    if config.require_local_chrome and chrome is None:
        raise ProviderReadinessError(
            "HR-002_EXTERNAL_NETWORK: Desktop Commander would download Chrome at startup. "
            "Install Chrome/Chromium through an operator-supervised bootstrap action or "
            f"pre-populate {config.puppeteer_cache_root}."
        )
    return chrome
