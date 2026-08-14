# Change Specification: Workspace Agent Trigger Probe

- **Change ID**: `145-workspace-agent-trigger-probe`
- **Status**: Active experiment
- **Complexity**: `large`
- **Risk triggers**: `architecture_boundary`, `external_action`, `public_contract`, `secrets`, `security`

## Outcome

Validate that an external event can start a published ChatGPT Workspace Agent through OpenAI's Workspace Agents trigger API, using GitHub Actions as the external dispatch boundary and KIS/Workbench as one possible upstream initiator.

## Authority and scope

- Repository authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`.
- Protocol/product evidence: current OpenAI Workspace Agents trigger/authentication docs and GitHub Actions event docs.
- Owned implementation: one probe workflow, one stdlib Python request helper, deterministic tests, and this change record.
- No local Work invocation may perform the OpenAI network call; only GitHub-hosted execution may send it.
- Current user-owned Project #1 is not assumed to support organization-only Project-v2 item webhooks.

## Requirements

- **REQ-001**: Build the exact documented Workspace Agent trigger endpoint and request body.
- **REQ-002**: Accept only HTTP `202`; tolerate an empty body or documented JSON response.
- **REQ-003**: Support stable `conversation_key` and `Idempotency-Key` without logging the bearer token.
- **REQ-004**: Normalize `workflow_dispatch` and `repository_dispatch` into one probe invocation.
- **REQ-005**: Keep access token and trigger ID in GitHub secret/variable state, never tracked repository content.
- **REQ-006**: A missing live credential/trigger ID must be reported as an unmet commissioning prerequisite, never a successful live trigger.

## Acceptance

1. Given representative workflow-dispatch input, when normalized, then the helper receives the expected conversation/input/idempotency values.
2. Given representative repository-dispatch payload, when normalized, then it produces the same trigger contract.
3. Given a mocked 202 with no body, when dispatched, then the helper returns accepted without parse failure.
4. Given a mocked 202 with a documented response body, when dispatched, then conversation/run metadata is retained without requiring beta fields.
5. Given a non-202 response, when dispatched, then execution fails without exposing the bearer token.
6. Given the workflow on GitHub's default branch and configured Workspace Agent credentials, when triggered through GitHub Actions, then a real 202 proves the external wake path.

## Risks and recovery

- Secret exposure: pass credentials only through GitHub secret state and redact diagnostics.
- Duplicate starts: use one stable idempotency key per event.
- Stale events: this slice does not execute work; later production dispatch must re-read KIS authority and claim work atomically.
- Provider/product drift: keep the helper narrow and contract-tested; a failed probe is safe and reversible.
- Recovery: remove/disable the probe workflow; it stores no durable product state.

## Out of scope

- Automatic KIS lifecycle-event generation or durable outbox.
- Unattended task execution/claiming after the agent wakes.
- Project-v2 item webhook support for the current user-owned Project.
- Scheduled Tasks as the primary dispatch path.
- Production operations documentation; change 140 currently owns `docs/OPERATIONS.md`.
