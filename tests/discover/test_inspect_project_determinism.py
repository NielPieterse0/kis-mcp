from __future__ import annotations

from pathlib import Path

from kis_mcp.discover.contracts import InspectProjectRequest
from tests.discover.test_inspect_project import _fixture, _service


def test_inspect_project_is_deterministic(
    project_root: Path,
    discover_settings,
) -> None:
    _fixture(project_root)
    service = _service(discover_settings)
    request = InspectProjectRequest(path=str(project_root))

    first = service.inspect(request).to_json_dict()
    second = service.inspect(request).to_json_dict()

    assert first == second
