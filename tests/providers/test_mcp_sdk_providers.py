from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.providers import (
    ProviderBoundary,
    ProviderKind,
    ProviderState,
)
from kis_mcp.providers.gitlab.provider import gitlab_provider_descriptor
from kis_mcp.providers.gitlab.settings import GitLabProviderSettings
from kis_mcp.providers.python_sdk.provider import python_sdk_provider_descriptor
from kis_mcp.providers.python_sdk.settings import PythonSdkSettings

ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_provider_settings_pin_exact_upstreams() -> None:
    python_sdk = PythonSdkSettings.load(
        ROOT / "settings" / "providers" / "python-sdk.provider.json"
    )
    gitlab = GitLabProviderSettings.load(
        ROOT / "settings" / "providers" / "gitlab.provider.json"
    )

    assert python_sdk.source_revision == "a4f4ccd091138771535e17191123f20b30fda68e"
    assert python_sdk.distribution_name == "mcp"
    assert python_sdk.module_name == "mcp"
    assert python_sdk.expected_version == "1.29.0"
    assert gitlab.source_revision == "9be4674d1ddf8c469e6461a27a337eeb65f76c2e"
    assert gitlab.package_name == "@modelcontextprotocol/server-gitlab"
    assert gitlab.package_version == "0.6.2"
    assert gitlab.archived is True
    assert gitlab.enabled is False


def test_python_sdk_provider_reports_exact_version_and_builds_only_explicitly() -> None:
    settings = PythonSdkSettings.load(
        ROOT / "settings" / "providers" / "python-sdk.provider.json"
    )
    imports: list[str] = []
    module = SimpleNamespace(name="mcp")

    def importer(module_name: str) -> object:
        imports.append(module_name)
        return module

    descriptor = python_sdk_provider_descriptor(
        settings,
        version_lookup=lambda distribution: "1.29.0",
        importer=importer,
    )

    assert descriptor.provider_kind is ProviderKind.PLATFORM
    assert descriptor.boundary is ProviderBoundary.PLATFORM_INTERNAL
    assert descriptor.readiness_probe().state is ProviderState.READY
    assert imports == []
    assert descriptor.builder() is module
    assert imports == ["mcp"]


@pytest.mark.parametrize(
    ("version", "expected_state"),
    [
        (None, ProviderState.UNAVAILABLE),
        ("1.28.0", ProviderState.DEGRADED),
        ("1.29.0", ProviderState.READY),
    ],
)
def test_python_sdk_readiness_distinguishes_missing_and_mismatched_versions(
    version: str | None,
    expected_state: ProviderState,
) -> None:
    settings = PythonSdkSettings.load(
        ROOT / "settings" / "providers" / "python-sdk.provider.json"
    )

    def lookup(_: str) -> str:
        if version is None:
            raise LookupError("not installed")
        return version

    descriptor = python_sdk_provider_descriptor(
        settings,
        version_lookup=lookup,
        importer=lambda _: object(),
    )

    readiness = descriptor.readiness_probe()
    assert readiness.state is expected_state
    assert "1.29.0" in readiness.details.get("expected_version", "1.29.0")


def test_gitlab_provider_is_archived_disabled_and_never_reads_secret_values() -> None:
    settings = GitLabProviderSettings.load(
        ROOT / "settings" / "providers" / "gitlab.provider.json"
    )

    def forbidden_which(_: str) -> str | None:
        raise AssertionError("disabled GitLab must not probe executable")

    def forbidden_environment(_: str) -> bool:
        raise AssertionError("disabled GitLab must not inspect environment")

    descriptor = gitlab_provider_descriptor(
        settings,
        which=forbidden_which,
        environment_present=forbidden_environment,
    )
    readiness = descriptor.readiness_probe()
    command = descriptor.builder()
    serialized = str(command.to_json_dict()) + str(descriptor.to_json_dict())

    assert descriptor.provider_kind is ProviderKind.CONNECTOR
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR
    assert descriptor.capabilities[0].tool_names == (
        "create_branch",
        "create_issue",
        "create_merge_request",
        "create_or_update_file",
        "create_repository",
        "fork_repository",
        "get_file_contents",
        "push_files",
        "search_repositories",
    )
    assert readiness.state is ProviderState.DISABLED
    assert readiness.details["archived_upstream"] is True
    assert command.environment_names == (
        "GITLAB_API_URL",
        "GITLAB_PERSONAL_ACCESS_TOKEN",
    )
    assert "secret-token-value" not in serialized


def test_gitlab_readiness_requires_local_entrypoint_and_pat_presence(
    tmp_path: Path,
) -> None:
    entry_point = tmp_path / "dist" / "index.js"
    entry_point.parent.mkdir()
    entry_point.write_text("// test", encoding="utf-8")
    settings = replace(
        GitLabProviderSettings.load(
            ROOT / "settings" / "providers" / "gitlab.provider.json"
        ),
        enabled=True,
        executable="node",
        entry_point=entry_point,
    )

    missing_token = gitlab_provider_descriptor(
        settings,
        which=lambda executable: f"C:/bin/{executable}.exe",
        environment_present=lambda name: name != "GITLAB_PERSONAL_ACCESS_TOKEN",
    ).readiness_probe()
    ready = gitlab_provider_descriptor(
        settings,
        which=lambda executable: f"C:/bin/{executable}.exe",
        environment_present=lambda name: name == "GITLAB_PERSONAL_ACCESS_TOKEN",
    ).readiness_probe()

    assert missing_token.state is ProviderState.DEGRADED
    assert missing_token.details["missing_environment_names"] == (
        "GITLAB_PERSONAL_ACCESS_TOKEN",
    )
    assert ready.state is ProviderState.READY


def test_gitlab_settings_reject_secret_material(tmp_path: Path) -> None:
    path = tmp_path / "gitlab.json"
    path.write_text(
        '{"schema_version":1,"enabled":false,'
        '"personal_access_token":"secret-token-value"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown settings keys"):
        GitLabProviderSettings.load(path)
