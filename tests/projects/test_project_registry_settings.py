from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kis_mcp.projects import load_project_registry_settings


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPOSITORY_ROOT / "settings" / "projects.settings.json"


def _checked_in() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "projects.settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_project_registry_schema_matches_checked_in_contract() -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "contracts" / "projects" / "project-registry.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    payload = _checked_in()

    assert list(validator.iter_errors(payload)) == []

    invalid = json.loads(json.dumps(payload))
    invalid["projects"][0]["github"]["unexpected"] = True
    assert list(validator.iter_errors(invalid))


def test_checked_in_registry_has_college_gpt_os_and_kis_bindings() -> None:
    registry = load_project_registry_settings(REGISTRY_PATH, boundary="C:\\Projects")

    assert registry.default_project_id == "kis-mcp"
    assert tuple(project.project_id for project in registry.projects) == (
        "college",
        "gpt-os",
        "kis-mcp",
    )
    kis = registry.project("kis-mcp")
    gpt = registry.project("gpt-os")
    college = registry.project("college")
    assert kis.local_root == "C:\\Projects\\kis-mcp"
    assert kis.github is not None
    assert kis.github.repository == "nielpieterse0/kis-mcp"
    assert kis.github.projects[0].project_number == 1
    assert kis.supabase is not None
    assert kis.supabase.project_ref == "mmxuicfrdalymczdapjq"
    assert gpt.local_root == "C:\\Projects\\GPT-OS"
    assert gpt.github is not None
    assert gpt.github.repository == "nielpieterse0/gpt-os"
    assert gpt.supabase is None
    assert college.local_root == "C:\\Projects\\college"
    assert college.github is not None
    assert college.github.repository == "nielpieterse0/college"
    assert college.github.projects == ()
    assert college.supabase is None


def test_registry_rejects_unknown_keys_and_boundary_escape(tmp_path: Path) -> None:
    payload = _checked_in()
    payload["extra"] = True
    with pytest.raises(ValueError, match="unknown project registry keys"):
        load_project_registry_settings(_write(tmp_path, payload), boundary="C:\\Projects")

    payload = _checked_in()
    projects = list(payload["projects"])
    projects[0] = dict(projects[0], local_root="C:\\Elsewhere\\gpt-os")
    payload["projects"] = projects
    with pytest.raises(ValueError, match="approved project boundary"):
        load_project_registry_settings(_write(tmp_path, payload), boundary="C:\\Projects")


def test_registry_rejects_duplicate_provider_resource_identity(tmp_path: Path) -> None:
    payload = _checked_in()
    projects = list(payload["projects"])
    second = dict(projects[1])
    second["github"] = dict(second["github"], repository=projects[0]["github"]["repository"])
    projects[1] = second
    payload["projects"] = projects

    with pytest.raises(ValueError, match="duplicate GitHub repository"):
        load_project_registry_settings(_write(tmp_path, payload), boundary="C:\\Projects")
