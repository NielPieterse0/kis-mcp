from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kis_mcp.housekeeping import (  # noqa: E402
    FastMCPInvoker,
    HousekeepingRunConfig,
    HousekeepingTrigger,
    RunMode,
    RunnerKind,
    TriggerKind,
    run_backlog_readiness,
    run_work_management_reconciliation,
)
from kis_mcp.server import build_server  # noqa: E402

_RUNNERS = {
    "work-management-reconciliation": RunnerKind.WORK_MANAGEMENT_RECONCILIATION,
    "backlog-readiness": RunnerKind.BACKLOG_READINESS,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic KIS repository housekeeping workflows."
    )
    parser.add_argument("runner", choices=tuple(_RUNNERS))
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--mode", choices=[item.value for item in RunMode], default="preview")
    parser.add_argument(
        "--trigger-kind",
        choices=[item.value for item in TriggerKind],
        default="manual",
    )
    parser.add_argument("--trigger-id", default="manual")
    parser.add_argument("--scheduled-for")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--item-limit", type=int, default=1000)
    parser.add_argument("--max-findings", type=int, default=200)
    parser.add_argument("--max-mutations", type=int, default=20)
    parser.add_argument("--max-external-reads", type=int, default=100)
    return parser


async def _run(args: argparse.Namespace, server: object) -> int:
    trigger = HousekeepingTrigger(
        runner=_RUNNERS[args.runner],
        mode=RunMode(args.mode),
        trigger_kind=TriggerKind(args.trigger_kind),
        trigger_id=args.trigger_id,
        idempotency_key=args.idempotency_key,
        scheduled_for=args.scheduled_for,
    )
    config = HousekeepingRunConfig(
        project_id=args.project_id,
        repository=args.repository,
        repository_root=args.repository_root,
        item_limit=args.item_limit,
        max_findings=args.max_findings,
        max_mutations=args.max_mutations,
        max_external_reads=args.max_external_reads,
    )
    invoker = FastMCPInvoker(server)
    if trigger.runner is RunnerKind.WORK_MANAGEMENT_RECONCILIATION:
        receipt = await run_work_management_reconciliation(invoker, config, trigger)
    else:
        receipt = await run_backlog_readiness(invoker, config, trigger)
    print(json.dumps(receipt.to_json_dict(), indent=2, sort_keys=True))
    return 0 if receipt.complete else 2


def main() -> int:
    args = _parser().parse_args()
    server = build_server()
    return asyncio.run(_run(args, server))


if __name__ == "__main__":
    raise SystemExit(main())
