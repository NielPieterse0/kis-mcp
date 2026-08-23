# Change Specification: Registered Project Schema UTF-8

- **Change ID**: `235-registered-project-schema-utf8`
- **Source defect**: `kis-mcp#409`
- **Development level**: Small
- **Risk trigger**: `external_action`

## Outcome

Make registered GitHub Project schema commissioning decode `gh api` JSON/HTTP output explicitly as UTF-8 on Windows, without changing unrelated registered Git/GitHub command capture.

## Reproduced failure

The exact saved-view REST request returns a valid `HTTP/2.0 200` UTF-8 response. Under Python `subprocess.run(..., text=True, capture_output=True)` on this Windows host, locale `cp1252` decoding fails on a legitimate UTF-8 byte, leaving `stdout=None`; the verifier then reports `unverified:malformed_http`.

## Requirements

- **REQ-001**: The Project schema client's production subprocess capture MUST read raw stdout/stderr bytes and decode them explicitly as UTF-8 with strict error handling.
- **REQ-002**: Registered Project schema commissioning MUST use that schema-specific UTF-8 runner when no custom runner is injected.
- **REQ-003**: Injected runners used by tests/callers MUST remain supported unchanged.
- **REQ-004**: Unrelated registered Git/GitHub operations MUST retain their current runner behavior.
- **REQ-005**: Existing HTTP/body-only parsing and fail-closed malformed/pagination behavior MUST remain unchanged.

## Acceptance

1. Regression proves valid non-ASCII UTF-8 bytes decode correctly and invalid UTF-8 fails synchronously.
2. Regression proves production registered commissioning selects the schema-specific runner while custom runners remain injectable.
3. Focused and affected tests pass; scope/governance checks pass.
4. After landing, live registered Project commissioning succeeds and `project_management_schema_status` reports all canonical views ready.
