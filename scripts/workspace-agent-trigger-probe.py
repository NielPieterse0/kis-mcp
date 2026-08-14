from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable
from urllib import error, parse, request


BASE_URL = "https://api.chatgpt.com/v1/workspace_agents"
DEFAULT_TIMEOUT_SECONDS = 30


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"INVALID_TRIGGER_INPUT: {name} must be a non-empty string")
    return value.strip()


def normalize_event(
    event_name: str, event: dict[str, Any], *, run_id: str | None
) -> dict[str, str]:
    if event_name == "workflow_dispatch":
        payload = event.get("inputs", {})
    elif event_name == "repository_dispatch":
        payload = event.get("client_payload", {})
    else:
        raise ValueError(f"UNSUPPORTED_GITHUB_EVENT: {event_name}")

    if not isinstance(payload, dict):
        raise ValueError("INVALID_TRIGGER_INPUT: event payload must be an object")

    mode = str(payload.get("mode", "validate")).strip().lower()
    if mode not in {"validate", "live"}:
        raise ValueError("INVALID_TRIGGER_INPUT: mode must be validate or live")

    conversation_key = _required_text(payload.get("conversation_key"), "conversation_key")
    input_text = _required_text(payload.get("input"), "input")
    idempotency_value = payload.get("idempotency_key")
    if isinstance(idempotency_value, str) and idempotency_value.strip():
        idempotency_key = idempotency_value.strip()
    else:
        source_id = payload.get("event_id") if event_name == "repository_dispatch" else run_id
        source_id = _required_text(source_id, "event_id or run_id")
        idempotency_key = f"github:{event_name}:{source_id}"

    return {
        "mode": mode,
        "conversation_key": conversation_key,
        "input": input_text,
        "idempotency_key": idempotency_key,
    }


def build_request(
    *, trigger_id: str, access_token: str, envelope: dict[str, str]
) -> request.Request:
    trigger_id = _required_text(trigger_id, "trigger_id")
    if not trigger_id.startswith("agtch_"):
        raise ValueError("INVALID_TRIGGER_INPUT: trigger_id must start with agtch_")
    access_token = _required_text(access_token, "access_token")

    body = json.dumps(
        {
            "conversation_key": _required_text(
                envelope.get("conversation_key"), "conversation_key"
            ),
            "input": _required_text(envelope.get("input"), "input"),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    url = f"{BASE_URL}/{parse.quote(trigger_id, safe='')}/trigger"
    return request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Idempotency-Key": _required_text(
                envelope.get("idempotency_key"), "idempotency_key"
            ),
        },
    )


def send_request(
    trigger_request: request.Request,
    *,
    opener: Callable[..., Any] = request.urlopen,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    try:
        with opener(trigger_request, timeout=timeout) as response:
            status_value = getattr(response, "status", None)
            if status_value is None:
                status_value = response.getcode()
            status = int(status_value)
            response_body = response.read()
    except error.HTTPError as exc:
        raise RuntimeError(
            f"WORKSPACE_AGENT_TRIGGER_REJECTED: HTTP {exc.code}"
        ) from None
    except error.URLError as exc:
        raise RuntimeError(
            f"WORKSPACE_AGENT_TRIGGER_TRANSPORT_ERROR: {exc.reason}"
        ) from None

    if status != 202:
        raise RuntimeError(f"WORKSPACE_AGENT_TRIGGER_REJECTED: HTTP {status}")

    result: dict[str, Any] = {"accepted": True, "status": 202}
    if not response_body:
        return result

    try:
        response_data = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return result

    if isinstance(response_data, dict):
        for key in ("conversation_url", "agent_trigger_run_id"):
            value = response_data.get(key)
            if isinstance(value, str) and value:
                result[key] = value
    return result


def _load_event(path: str) -> dict[str, Any]:
    event_path = Path(_required_text(path, "event_path"))
    with event_path.open("r", encoding="utf-8") as handle:
        event = json.load(handle)
    if not isinstance(event, dict):
        raise ValueError("INVALID_TRIGGER_INPUT: GitHub event must be an object")
    return event


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe the Workspace Agents trigger API.")
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        event = _load_event(args.event_path)
        envelope = normalize_event(args.event_name, event, run_id=args.run_id)

        if envelope["mode"] == "validate":
            print(
                json.dumps(
                    {
                        "validated": True,
                        "mode": "validate",
                        "conversation_key": envelope["conversation_key"],
                        "idempotency_key": envelope["idempotency_key"],
                    },
                    sort_keys=True,
                )
            )
            return 0

        trigger_id = os.environ.get("OPENAI_WORKSPACE_AGENT_TRIGGER_ID", "")
        access_token = os.environ.get("OPENAI_WORKSPACE_AGENT_ACCESS_TOKEN", "")
        missing = [
            name
            for name, value in (
                ("OPENAI_WORKSPACE_AGENT_TRIGGER_ID", trigger_id),
                ("OPENAI_WORKSPACE_AGENT_ACCESS_TOKEN", access_token),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "MISSING_WORKSPACE_AGENT_CONFIGURATION: " + ", ".join(missing)
            )

        trigger_request = build_request(
            trigger_id=trigger_id,
            access_token=access_token,
            envelope=envelope,
        )
        result = send_request(trigger_request)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
