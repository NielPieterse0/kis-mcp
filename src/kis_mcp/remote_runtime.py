from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Any

from .config import RuntimeConfig, load_runtime_config
from .server import build_server


ServerFactory = Callable[[RuntimeConfig], Any]


def run_remote_instance(
    config: RuntimeConfig,
    instance_name: str | None = None,
    *,
    server_factory: ServerFactory = build_server,
) -> None:
    instance = config.remote_instance(instance_name)
    server = server_factory(config)
    server.run(
        transport="http",
        host=instance.host,
        port=instance.port,
        path=instance.path,
        stateless_http=True,
        json_response=True,
        show_banner=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one settings-defined kis-mcp streamable HTTP instance."
    )
    parser.add_argument(
        "--instance",
        choices=("operation", "development"),
        help="Remote instance to run; defaults to settings.remote_mcp.active_instance.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    config = load_runtime_config()
    run_remote_instance(config, args.instance)


if __name__ == "__main__":
    main()
