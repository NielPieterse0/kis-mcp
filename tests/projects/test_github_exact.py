from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError

from kis_mcp.projects import (
    GitHubProjectBinding,
    GitHubProjectResource,
    ProjectDefinition,
    ProjectRegistry,
)
from kis_mcp.projects.github_exact import (
    RegisteredGitHubOperations,
    execute_registered_github_operation,
)


@dataclass(frozen=True)
class Result:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class QueueRunner:
    def __init__(self, results=()) -> None:
        self.results = list(results)
        self.calls = []

    def __call__(self, args, cwd, env):
        self.calls.append((tuple(args), cwd, dict(env)))
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        return self.results.pop(0)

def _registry() -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="kis-mcp",
        projects=(
            ProjectDefinition(
                project_id="kis-mcp",
                display_name="kis-mcp",
                local_root=r"C:\Projects\kis-mcp",
                github=GitHubProjectBinding(
                    repository="NielPieterse0/kis-mcp",
                    projects=(
                        GitHubProjectResource(
                            binding_id="work-management",
                            owner="NielPieterse0",
                            owner_type="user",
                            project_number=1,
                        ),
                    ),
                ),
            ),
        ),
    )


def test_project_schema_commissioning_requires_approval_and_registered_binding() -> None:
    operations = RegisteredGitHubOperations(
        _registry(),
        runner=QueueRunner(()),
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
    )
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="work-management",
            approved=False,
        )
    with pytest.raises(ToolError, match="REGISTERED_GITHUB_PROJECT_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="unknown",
            approved=True,
        )

def _registry() -> ProjectRegistry:
    return ProjectRegistry(
        default_project_id="kis-mcp",
        projects=(
            ProjectDefinition(
                project_id="kis-mcp",
                display_name="kis-mcp",
                local_root=r"C:\Projects\kis-mcp",
                github=GitHubProjectBinding(
                    repository="NielPieterse0/kis-mcp",
                    projects=(
                        GitHubProjectResource(
                            binding_id="work-management",
                            owner="NielPieterse0",
                            owner_type="user",
                            project_number=1,
                        ),
                    ),
                ),
            ),
        ),
    )


def test_project_schema_commissioning_requires_approval_and_registered_binding() -> None:
    operations = RegisteredGitHubOperations(
        _registry(),
        runner=QueueRunner(()),
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
    )
    with pytest.raises(ToolError, match="APPROVAL_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="work-management",
            approved=False,
        )
    with pytest.raises(ToolError, match="REGISTERED_GITHUB_PROJECT_REQUIRED"):
        operations.commission_project_schema(
            project_id="kis-mcp",
            project_binding_id="unknown",
            approved=True,
        )

def test_project_schema_commissioning_uses_only_registered_manifest(monkeypatch) -> None:
    runner = QueueRunner((Result(),))
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        def commission(self, target, manifest):
            captured["target"] = target
            captured["manifest"] = manifest
            return {
                "ready": True,
                "project_node_id": "project-id",
                "created_fields": [],
                "updated_fields": [],
                "created_views": [],
                "field_count": 24,
                "view_count": 12,
            }

    monkeypatch.setattr("kis_mcp.projects.github_exact.GitHubProjectSchemaClient", FakeClient)
    operations = RegisteredGitHubOperations(
        _registry(),
        runner=runner,
        gh_config_dir=Path(r"C:\Projects\.kis-mcp\github-cli"),
    )

    result = operations.commission_project_schema(
        project_id="kis-mcp",
        project_binding_id="work-management",
        approved=True,
    )

    assert result["ready"] is True
    assert captured["target"].project_number == 1
    assert captured["target"].owner == "NielPieterse0"
    assert captured["manifest"].portfolio_id == "default"
    assert runner.calls[0][0][:3] == ("gh", "auth", "status")

def test_project_schema_operation_rejects_arbitrary_api_inputs_before_dispatch() -> None:
    with pytest.raises(ToolError, match="unknown fields: query"):
        execute_registered_github_operation(
            "kis_github_commission_registered_project_schema",
            {
                "project_id": "kis-mcp",
                "project_binding_id": "work-management",
                "approved": True,
                "query": "mutation { arbitrary }",
            },
            operations=RegisteredGitHubOperations(_registry()),
        )
