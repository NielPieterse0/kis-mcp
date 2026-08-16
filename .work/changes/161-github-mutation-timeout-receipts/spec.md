# Change Specification: GitHub Mutation Timeout Receipts

- **Change ID**: `161-github-mutation-timeout-receipts`
- **Status**: Approved by source issue #274 and operator lane assignment
- **Risk Profile**: rigorous

## Outcome

Make registered GitHub delivery publication and pull-request preparation timeout-safe with deterministic stateless operation identities, bounded deadlines, conclusive receipts where GitHub authority can be observed, and an explicit reconciliation mode after timeout.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `docs/OPERATIONS.md`, GitHub issue #274, and the completed #272 architecture decision.
- Owned paths: the exact registered-GitHub delivery implementation, reviewable-PR completion coordinator/contracts/tools, their focused tests, this change record, and `docs/OPERATIONS.md`.
- Shared paths: none.
- Excluded paths: #241 coordinator implementation, #270/#159 Work Management authority work, #261 Codex wrapper, #273 Discover Git semantics, #237 transport work, #271 composition work, and all state-ownership implementation under #278/#277.
- Dependencies: no implementation dependency on #278 because this change creates no durable receipt store. If persistence is added later, it must consume #278 ownership rules.
- Integration owner: none; this change is isolated by governed path claims.

## Requirements

- **REQ-001 — Total deadline:** `prepare_reviewable_pull_request` must enforce one bounded end-to-end deadline across verification, registered publication, PR creation, and reconciliation/status work. Remaining time must be propagated to nested operations rather than refreshed per stage.
- **REQ-002 — Mutation deadline:** registered review-branch publication, exact commit publication, and PR creation must use one bounded per-operation deadline across their command sequences; mutation commands must reserve time for authoritative post-timeout reconciliation.
- **REQ-003 — Stable identity:** each high-level preparation request and each targeted registered GitHub mutation must expose a deterministic operation ID derived from normalized exact intent, excluding retry/status/deadline controls.
- **REQ-004 — Receipt state:** receipts must use exactly `not_started`, `in_progress`, `applied`, `failed`, or `unknown` for operation state. Successful normal completion is `applied`; partial preparation after publication but before PR creation is `in_progress`.
- **REQ-005 — Query/reconcile:** callers must be able to re-submit the same exact preparation request in reconciliation-only mode, and targeted registered mutations must support status-only observation without performing a remote mutation.
- **REQ-006 — Ack-loss recovery:** if publication or PR creation times out but GitHub authority proves the exact requested mutation was applied, the operation must converge without duplicating a push or PR. If authority proves the mutation did not start, return `not_started`; if authority cannot be established, return `unknown` rather than guessing.
- **REQ-007 — Exact authority:** repository registration, exact source commit, expected remote base/default/head, branch lease, PR head/base/title/body, and existing fail-closed conflict behavior remain authoritative.
- **REQ-008 — Stateless boundary:** do not add new durable/local receipt persistence. #278 owns future state namespace contracts.
- **REQ-009 — Telemetry:** high-level results/errors must expose bounded elapsed time and per-stage timings; lower mutation receipts expose bounded elapsed time.

## Acceptance

1. **Given** a mutation command times out after the remote push/PR succeeds, **when** the same operation is reconciled or retried, **then** GitHub authority yields `applied` and no duplicate mutation is created.
2. **Given** a mutation command times out before remote mutation, **when** authority is re-read within the reserved budget, **then** the receipt reports `not_started` and retry is safe.
3. **Given** publication is applied but PR creation is not, **when** the preparation request is reconciled, **then** the high-level receipt reports `in_progress` with the same operation ID.
4. **Given** authority cannot be read conclusively after an ambiguous timeout, **then** the receipt/error reports `unknown` and never claims success or blindly retries.
5. **Given** the same normalized intent is retried with different deadline/status controls, **then** operation identity remains stable; changing exact mutation intent changes identity.
6. **Given** the total preparation deadline expires during verification, **then** no external mutation begins and the error is `not_started`; expiry during a mutation is `unknown` unless lower-level authority reconciliation produced a conclusive receipt.
7. Focused tests prove timeout-before-mutation, ack-loss-after-mutation, partial multi-stage state, safe retry/status reconciliation, exact authority conflicts, deadline propagation, stable IDs, and bounded public schemas.

## Risks and recovery

- Risk: status reconciliation could accidentally mutate GitHub. Mitigation: `status_only` follows read/preflight paths only and never reaches push/create commands.
- Risk: aggressive timeouts could create false failures. Mitigation: deadlines are caller-adjustable within a bounded maximum; timeout receipts preserve safe retry/reconciliation.
- Risk: a transport timeout may outlive the coordinator response. Mitigation: deterministic operation IDs plus stateless GitHub-authority reconciliation; no blind retry assumption.
- Recovery: revert the isolated change. No persisted receipt/state migration exists and no credential/state layout changes are made.

## Out of scope

- Durable operation-receipt persistence or namespace migration (#278/#279).
- Post-review merge, branch deletion, repository configuration, Project schema commissioning, merge queue, GitHub auth lifecycle, generic transport reliability (#237), or Work Management changes.
- Increasing transport timeouts as the primary fix.
