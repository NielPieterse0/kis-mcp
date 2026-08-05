from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

from kis_mcp.providers.github.smoke import run_live_smoke as run_github_live_smoke
from kis_mcp.providers.supabase.smoke import run_live_smoke as run_supabase_live_smoke
from kis_mcp.server import build_server

Runner = Callable[[Callable[[], Any]], dict[str, Any]]

_RUNNERS: dict[str, Runner] = {
    "github": run_github_live_smoke,
    "supabase": run_supabase_live_smoke,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a provider smoke check in the shared KIS runtime.")
    parser.add_argument("provider", choices=tuple(_RUNNERS))
    arguments = parser.parse_args()

    report = _RUNNERS[arguments.provider](build_server)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
