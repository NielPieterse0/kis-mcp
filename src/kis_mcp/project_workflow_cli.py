from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from kis_mcp.work_management import (
    ReviewArtifactKind,
    build_portfolio_status,
    create_review_evidence_manifest,
    evaluate_merge_readiness,
    evaluate_traceability,
    load_project_schema_manifest,
    load_work_management_settings,
    plan_reconciliation,
)
from kis_mcp.workflows.project_management import (
    desired_projection_from_json,
    implementation_trace_from_json,
    observed_projection_from_json,
    traceability_stage,
    work_record_from_json,
)

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_UNAVAILABLE = 3
EXIT_GATE_FAILED = 4
DEFAULT_MAX_OUTPUT_BYTES = 1_048_576


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _revision(explicit: str | None, repository_root: str | None = None) -> str:
    if explicit:
        return explicit
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _emit(document: dict[str, Any], *, max_output_bytes: int) -> int:
    encoded = (json.dumps(document, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > max_output_bytes:
        encoded = (
            json.dumps(
                {
                    "ok": False,
                    "error_code": "output_budget_exceeded",
                    "actual_bytes": len(encoded),
                    "max_output_bytes": max_output_bytes,
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        sys.stdout.buffer.write(encoded)
        return EXIT_GATE_FAILED
    sys.stdout.buffer.write(encoded)
    return EXIT_OK


def _settings_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    settings = load_work_management_settings(Path(args.settings))
    return EXIT_OK, {
        "ok": True,
        "command": "settings",
        "revision": _revision(args.revision, args.repository_root),
        "settings": settings.to_json_dict(),
    }


def _reconcile_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if args.apply and not args.idempotency_key:
        return EXIT_INPUT, {
            "ok": False,
            "command": "reconcile",
            "error_code": "idempotency_key_required",
        }
    desired_document = _read_json(args.desired)
    observed_document = _read_json(args.observed)
    if not isinstance(desired_document, list) or not isinstance(observed_document, list):
        raise ValueError("desired and observed documents must be arrays")
    desired = tuple(desired_projection_from_json(item) for item in desired_document)
    observed = tuple(observed_projection_from_json(item) for item in observed_document)
    decisions = plan_reconciliation(
        desired,
        observed,
        supported_fields=tuple(args.supported_field),
    )
    if args.apply:
        return EXIT_UNAVAILABLE, {
            "ok": False,
            "command": "reconcile",
            "mode": "apply",
            "revision": _revision(args.revision, args.repository_root),
            "error_code": "runtime_service_required",
            "message": "Apply mode is available through the composed project-management workflow service.",
            "idempotency_key": args.idempotency_key,
            "decisions": [item.to_json_dict() for item in decisions],
        }
    return EXIT_OK, {
        "ok": True,
        "command": "reconcile",
        "mode": "preview",
        "revision": _revision(args.revision, args.repository_root),
        "decisions": [item.to_json_dict() for item in decisions],
    }


def _schema_manifest_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    manifest = load_project_schema_manifest(Path(args.manifest))
    return EXIT_OK, {
        "ok": True,
        "command": "schema-manifest",
        "revision": _revision(args.revision, args.repository_root),
        "schema": manifest.to_json_dict(),
    }


def _merge_readiness_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    readiness = evaluate_merge_readiness(
        work_record_from_json(_read_json(args.record)),
        implementation_trace_from_json(_read_json(args.trace)),
        args.pull_request_number,
    )
    return (EXIT_OK if readiness.ready else EXIT_GATE_FAILED), {
        "ok": readiness.ready,
        "command": "merge-readiness",
        "revision": _revision(args.revision, args.repository_root),
        "readiness": readiness.to_json_dict(),
    }


def _traceability_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    report = evaluate_traceability(
        implementation_trace_from_json(_read_json(args.trace)),
        traceability_stage(args.stage),
        pull_request_number=args.pull_request_number,
    )
    return (EXIT_OK if report.valid else EXIT_GATE_FAILED), {
        "ok": report.valid,
        "command": "verify-traceability",
        "revision": _revision(args.revision, args.repository_root),
        "traceability": report.to_json_dict(),
    }


def _status_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    settings = load_work_management_settings(Path(args.settings))
    records_document = _read_json(args.records)
    if not isinstance(records_document, list):
        raise ValueError("records document must be an array")
    status = build_portfolio_status(
        settings,
        tuple(work_record_from_json(item) for item in records_document),
    )
    return EXIT_OK, {
        "ok": True,
        "command": "status",
        "revision": _revision(args.revision, args.repository_root),
        "status": status.to_json_dict(),
    }


def _evidence_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    root = Path(args.repository_root).resolve()
    manifest = create_review_evidence_manifest(args.review_id)
    selected = (
        tuple(ReviewArtifactKind(value) for value in args.kind)
        if args.kind
        else tuple(item.kind for item in manifest.artifacts)
    )
    artifacts = []
    missing = []
    for kind in selected:
        artifact = next(item for item in manifest.artifacts if item.kind is kind)
        path = (root / artifact.path).resolve(strict=False)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("evidence path escapes repository root") from exc
        exists = path.is_file()
        artifacts.append(
            {
                "kind": kind.value,
                "path": artifact.path,
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else None,
            }
        )
        if not exists:
            missing.append(kind.value)
    valid = not missing
    return (EXIT_OK if valid else EXIT_GATE_FAILED), {
        "ok": valid,
        "command": "verify-evidence",
        "revision": _revision(args.revision, args.repository_root),
        "review_id": manifest.review_id,
        "artifacts": artifacts,
        "missing": missing,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="project-workflow")
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    subparsers = parser.add_subparsers(dest="command", required=True)

    settings = subparsers.add_parser("settings")
    settings.add_argument("--settings", required=True)
    settings.add_argument("--repository-root")
    settings.add_argument("--revision")
    settings.set_defaults(handler=_settings_command)

    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("--desired", required=True)
    reconcile.add_argument("--observed", required=True)
    reconcile.add_argument("--supported-field", action="append", default=[])
    reconcile.add_argument("--apply", action="store_true")
    reconcile.add_argument("--idempotency-key")
    reconcile.add_argument("--repository-root")
    reconcile.add_argument("--revision")
    reconcile.set_defaults(handler=_reconcile_command)

    schema_manifest = subparsers.add_parser("schema-manifest")
    schema_manifest.add_argument("--manifest", required=True)
    schema_manifest.add_argument("--repository-root")
    schema_manifest.add_argument("--revision")
    schema_manifest.set_defaults(handler=_schema_manifest_command)

    merge_readiness = subparsers.add_parser("merge-readiness")
    merge_readiness.add_argument("--record", required=True)
    merge_readiness.add_argument("--trace", required=True)
    merge_readiness.add_argument("--pull-request-number", type=int, required=True)
    merge_readiness.add_argument("--repository-root")
    merge_readiness.add_argument("--revision")
    merge_readiness.set_defaults(handler=_merge_readiness_command)

    traceability = subparsers.add_parser("verify-traceability")
    traceability.add_argument("--trace", required=True)
    traceability.add_argument("--stage", required=True)
    traceability.add_argument("--pull-request-number", type=int)
    traceability.add_argument("--repository-root")
    traceability.add_argument("--revision")
    traceability.set_defaults(handler=_traceability_command)

    status = subparsers.add_parser("status")
    status.add_argument("--settings", required=True)
    status.add_argument("--records", required=True)
    status.add_argument("--repository-root")
    status.add_argument("--revision")
    status.set_defaults(handler=_status_command)

    evidence = subparsers.add_parser("verify-evidence")
    evidence.add_argument("--repository-root", required=True)
    evidence.add_argument("--review-id", required=True)
    evidence.add_argument("--kind", action="append", default=[])
    evidence.add_argument("--revision")
    evidence.set_defaults(handler=_evidence_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if args.max_output_bytes <= 0:
            raise ValueError("max-output-bytes must be positive")
        exit_code, document = args.handler(args)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        exit_code = EXIT_INPUT
        document = {
            "ok": False,
            "error_code": "invalid_input",
            "error_type": type(exc).__name__,
        }
        max_output_bytes = DEFAULT_MAX_OUTPUT_BYTES
    else:
        max_output_bytes = args.max_output_bytes
    emitted = _emit(document, max_output_bytes=max_output_bytes)
    return emitted if emitted != EXIT_OK else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
