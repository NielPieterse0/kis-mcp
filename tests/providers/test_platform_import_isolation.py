from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_provider_platform_imports_in_fresh_interpreter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import kis_mcp.providers.platform"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
