from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def decide(payload: dict[str, Any]) -> dict[str, Any]:
    package = payload["package"]
    runtime = payload["runtime"]
    corpus = payload["corpus"]
    if package["version"] != "1.11.2":
        raise ValueError("OCR version must remain pinned to 1.11.2")
    if not corpus:
        raise ValueError("qualification corpus must not be empty")

    executable = runtime.get("executable", False)
    successful_reviews = int(runtime.get("successful_reviews", 0))
    raw_incremental = runtime.get("incremental_validated_findings")
    if not executable:
        if successful_reviews or raw_incremental is not None:
            raise ValueError("blocked runtime cannot report OCR review metrics")
        incremental_findings = None
        metric_status = "not_measurable"
        decision = "not_adopted"
    else:
        incremental_findings = int(raw_incremental or 0)
        metric_status = "measured"
        decision = (
            "adapter_candidate"
            if successful_reviews > 0 and incremental_findings > 0
            else "not_adopted"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "open-code-review",
        "package": package,
        "runtime": runtime,
        "corpus": corpus,
        "metrics": {
            "status": metric_status,
            "successful_ocr_reviews": successful_reviews,
            "incremental_validated_findings": incremental_findings,
        },
        "decision": decision,
        "product_integration_authorized": False,
    }


def main(source: Path, target: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    result = decide(payload)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys

    main(Path(sys.argv[1]), Path(sys.argv[2]))
