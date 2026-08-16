from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "statement",
    [
        "import kis_mcp.tools; import kis_mcp.workflows",
        "import kis_mcp.workflows; import kis_mcp.tools",
        "from kis_mcp.workflows import workflow_descriptors; assert callable(workflow_descriptors)",
        "import kis_mcp.tools; from kis_mcp.workflows import workflow_descriptors; assert callable(workflow_descriptors)",
    ],
)
def test_workflow_and_tool_imports_are_order_independent_in_clean_process(
    statement: str,
) -> None:
    result = subprocess.run(
        [sys.executable, "-c", statement],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
