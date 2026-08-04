from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"


def test_discover_imports_without_donor_repositories_on_pythonpath() -> None:
    script = "\n".join(
        [
            "import json, sys",
            f"sys.path.insert(0, {str(SOURCE_ROOT)!r})",
            "import kis_mcp.discover",
            "import kis_mcp.discover.service",
            "import kis_mcp.discover.tools",
            "donors = ['sdk_tool', 'dev_intel', 'dev_intel_tool', 'mcp_tool']",
            "print(json.dumps({'loaded_donors': [name for name in donors if name in sys.modules]}))",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"loaded_donors": []}
