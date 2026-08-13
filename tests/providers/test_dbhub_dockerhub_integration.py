from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.projects import (
    DatabaseBinding,
    ProjectDefinition,
    ProjectRegistry,
    load_project_registry_settings,
)
from kis_mcp.providers import ProviderBoundary, ProviderState
from kis_mcp.providers.dbhub import (
    DBHubSettings,
    binding_environment,
    operation_name,
    render_binding_toml,
)
from kis_mcp.providers.dbhub import provider as dbhub_provider_module
from kis_mcp.providers.dbhub.provider import dbhub_provider_descriptor
from kis_mcp.providers.dockerhub import DockerHubSettings
from kis_mcp.providers.dockerhub import provider as dockerhub_provider_module
from kis_mcp.providers.dockerhub.adapter import DockerHubAdapter, INTERNAL_PAT_ENV
from kis_mcp.providers.dockerhub.provider import dockerhub_provider_descriptor


ROOT = Path(__file__).resolve().parents[2]


def test_source_aware_provider_boundary_is_stable() -> None:
    assert ProviderBoundary.SOURCE_AWARE_CONNECTOR.value == "source_aware_connector"


def test_checked_in_project_registry_has_only_evidenced_database_binding() -> None:
    registry = load_project_registry_settings(ROOT / "settings" / "projects.settings.json")
    college = registry.project("college")
    commodity = registry.project("commodity")

    assert [item.to_json_dict() for item in college.databases] == [
        {
            "binding_id": "results",
            "engine": "sqlite",
            "boundary": "local",
            "location": r"results\college.db",
            "secret_ref": None,
        }
    ]
    assert commodity.databases == ()
    assert college.dockerhub is None
    assert commodity.dockerhub is None


def test_database_binding_contract_rejects_mixed_local_external_state() -> None:
    with pytest.raises(ValueError, match="secret_ref null"):
        DatabaseBinding("results", "sqlite", "local", "results\\college.db", "secret://db/x")
    with pytest.raises(ValueError, match="location null"):
        DatabaseBinding("prod", "postgres", "external", "prod", "secret://db/prod")
    with pytest.raises(ValueError, match="canonical secret_ref"):
        DatabaseBinding("prod", "postgres", "external", None, None)
    with pytest.raises(ValueError, match="relative"):
        DatabaseBinding("results", "sqlite", "local", "..\\college.db", None)


def test_project_registry_json_remains_credential_free() -> None:
    payload = json.loads((ROOT / "settings" / "projects.settings.json").read_text(encoding="utf-8"))
    rendered = json.dumps(payload).casefold()
    assert "password" not in rendered
    assert "token" not in rendered
    assert "postgres://" not in rendered
    assert "mysql://" not in rendered


def _dbhub_settings() -> DBHubSettings:
    return DBHubSettings(
        schema_version=1,
        provider_id="dbhub",
        authoritative_source="https://github.com/bytebase/dbhub",
        release_tag="v1.2.0",
        source_revision="1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0",
        transport="stdio",
        node_executable="node",
        entry_point=Path(r"C:\Projects\.kis-mcp\providers\dbhub\v1.2.0\dist\index.js"),
        runtime_root=Path(r"C:\Projects\.kis-mcp\dbhub\runtime"),
        max_rows=500,
        enabled_tools=("search_objects", "execute_sql"),
    )


def test_dbhub_public_names_are_stable_and_do_not_depend_on_upstream_suffixing() -> None:
    assert operation_name("college", "results", "search_objects") == "db_college_results_search_objects"
    assert operation_name("college", "results", "execute_sql") == "db_college_results_execute_sql"


def test_dbhub_generated_local_toml_is_read_only_bounded_and_credential_free() -> None:
    project = load_project_registry_settings(ROOT / "settings" / "projects.settings.json").project("college")
    rendered = render_binding_toml(project, project.databases[0], _dbhub_settings())
    assert 'id = "results"' in rendered
    assert 'readonly = true' in rendered
    assert 'max_rows = 500' in rendered
    assert "search_objects" in rendered and "execute_sql" in rendered
    assert "password" not in rendered.casefold()
    assert "secret://" not in rendered


def test_dbhub_external_toml_uses_only_runtime_environment_interpolation() -> None:
    external = DatabaseBinding("prod", "postgres", "external", None, "secret://database/prod")
    project = load_project_registry_settings(ROOT / "settings" / "projects.settings.json").project("college")
    project = type(project)(
        project_id=project.project_id,
        display_name=project.display_name,
        local_root=project.local_root,
        github=project.github,
        supabase=project.supabase,
        databases=(external,),
        dockerhub=project.dockerhub,
    )
    rendered = render_binding_toml(project, external, _dbhub_settings())
    assert 'dsn = "${DBHUB_DSN}"' in rendered
    assert "secret://database/prod" not in rendered
    assert binding_environment(project, external, {"KIS_MCP_DBHUB_COLLEGE_PROD_DSN": "postgres://opaque"}) == {
        "DBHUB_DSN": "postgres://opaque"
    }


def test_dbhub_descriptor_predeclares_college_read_only_effects() -> None:
    descriptor = dbhub_provider_descriptor(repository_root=ROOT, environment={})
    tools = {tool for capability in descriptor.capabilities for tool in capability.tool_names}
    assert tools == {"db_college_results_execute_sql", "db_college_results_search_objects"}
    assert all(capability.effects == ("read_only",) for capability in descriptor.capabilities)


def _dockerhub_settings(mode: str = "public") -> DockerHubSettings:
    return DockerHubSettings(
        schema_version=1,
        provider_id="dockerhub-mcp",
        authoritative_source="https://github.com/docker/hub-mcp",
        source_revision="ad806e2cab0489a296aec0f32f3d3eea807d65c2",
        transport="stdio",
        node_executable="node",
        entry_point=Path(r"C:\Projects\.kis-mcp\providers\dockerhub\ad806e2cab0489a296aec0f32f3d3eea807d65c2\dist\index.js"),
        auth_mode=mode,
        username=None if mode == "public" else "niel",
        secret_ref=None if mode == "public" else "secret://provider/dockerhub/pat",
    )


def test_dockerhub_child_environment_is_minimal_for_public_and_pat_modes() -> None:
    assert DockerHubAdapter(_dockerhub_settings(), environment={"PATH": "ignored"}).child_environment() == {}
    adapter = DockerHubAdapter(
        _dockerhub_settings("pat"),
        environment={INTERNAL_PAT_ENV: "opaque-token", "PATH": "ignored"},
    )
    assert adapter.child_environment() == {"HUB_PAT_TOKEN": "opaque-token"}
    assert adapter.arguments()[-1] == "--username=niel"


def test_dockerhub_public_descriptor_exposes_only_live_verified_public_tools() -> None:
    descriptor = dockerhub_provider_descriptor(repository_root=ROOT, environment={})
    tools = {tool for capability in descriptor.capabilities for tool in capability.tool_names}
    assert tools == {
        "checkRepository",
        "checkRepositoryTag",
        "getRepositoryInfo",
        "getRepositoryTag",
        "listRepositoriesByNamespace",
        "listRepositoryTags",
    }
    assert "search" not in tools
    assert "createRepository" not in tools and "updateRepositoryInfo" not in tools
    assert descriptor.boundary is ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR


def test_commissioning_script_preserves_successful_child_exit_when_stderr_has_diagnostics() -> None:
    text = (ROOT / "scripts" / "commission-db-docker-providers.ps1").read_text(encoding="utf-8")
    assert "Write-Error $ErrorOutput.Trim()" not in text
    assert "[Console]::Error.WriteLine($ErrorOutput.Trim())" in text


def test_checked_in_dbhub_and_dockerhub_settings_match_their_strict_schemas() -> None:
    pairs = (
        ("dbhub", "dbhub-provider.schema.json", "dbhub.provider.json"),
        ("dockerhub", "dockerhub-provider.schema.json", "dockerhub.provider.json"),
    )
    for contract_dir, schema_name, settings_name in pairs:
        schema = json.loads(
            (ROOT / "contracts" / "providers" / contract_dir / schema_name).read_text(encoding="utf-8")
        )
        value = json.loads((ROOT / "settings" / "providers" / settings_name).read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(value)


def test_project_registry_matches_strict_schema_with_database_conditions() -> None:
    schema = json.loads(
        (ROOT / "contracts" / "projects" / "project-registry.schema.json").read_text(encoding="utf-8")
    )
    value = json.loads((ROOT / "settings" / "projects.settings.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(value)


def test_dbhub_names_remain_stable_when_a_second_binding_is_added() -> None:
    first = operation_name("college", "results", "execute_sql")
    second = operation_name("college", "archive", "execute_sql")
    assert first == "db_college_results_execute_sql"
    assert second == "db_college_archive_execute_sql"
    assert operation_name("college", "results", "execute_sql") == first


def test_dbhub_readiness_is_ready_when_installation_and_local_binding_are_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(dbhub_provider_module, "validate_installation", lambda settings: None)
    database = tmp_path / "results" / "college.db"
    database.parent.mkdir()
    database.touch()
    projects = ProjectRegistry(
        default_project_id="college",
        projects=(
            ProjectDefinition(
                project_id="college",
                display_name="College",
                local_root=str(tmp_path),
                databases=(DatabaseBinding("results", "sqlite", "local", r"results\college.db", None),),
            ),
        ),
    )
    readiness = dbhub_provider_module.dbhub_readiness(_dbhub_settings(), projects, {})
    assert readiness.state is ProviderState.READY
    assert readiness.details["commissioning"]["authenticated"] == "not_required"


def test_dockerhub_readiness_distinguishes_public_and_pat_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dockerhub_provider_module, "validate_installation", lambda settings: None)
    public = dockerhub_provider_module.dockerhub_readiness(_dockerhub_settings("public"), {})
    assert public.state is ProviderState.READY
    assert public.details["commissioning"]["authenticated"] == "not_required_public"

    pat = dockerhub_provider_module.dockerhub_readiness(_dockerhub_settings("pat"), {})
    assert pat.state is ProviderState.DEGRADED
    pat_ready = dockerhub_provider_module.dockerhub_readiness(
        _dockerhub_settings("pat"), {INTERNAL_PAT_ENV: "opaque-token"}
    )
    assert pat_ready.state is ProviderState.READY
