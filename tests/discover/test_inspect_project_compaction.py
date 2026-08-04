from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from kis_mcp.discover.contracts import InspectProjectRequest


def test_inspect_project_compacts_large_local_result(
    project_root: Path,
    discover_settings,
) -> None:
    from kis_mcp.discover.service import InspectProjectService

    for index in range(60):
        path = project_root / "src" / "pkg" / f"module_{index:03}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"def function_{index:03}():\n    return '{'x' * 100}'\n",
            encoding="utf-8",
        )
    (project_root / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    settings = replace(
        discover_settings,
        limits=replace(
            discover_settings.limits,
            max_output_chars=8_000,
            max_evidence=100,
        ),
    )
    service = InspectProjectService(boundary=Path(r"C:\Projects"), settings=settings)

    response = service.inspect(InspectProjectRequest(path=str(project_root)))
    payload = response.to_json_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert len(encoded) <= 8_000
    assert response.truncated is True
    assert "max_output_chars" in response.truncation_reasons
    assert payload["code_atlas"]["summary"]["modules"] == 60
    assert payload["unknowns"]
    assert payload["schema_version"] == 1
    assert payload["tool"] == "inspect_project"
