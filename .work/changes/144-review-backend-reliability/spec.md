# Change Specification: Review Backend Reliability

- **Change ID**: `144-review-backend-reliability`
- **Status**: Implemented; pending exact-head integration
- **Risk Profile**: rigorous

## Outcome

Make advisory review backend failures typed, diagnosable, retry-bounded, and explicitly recoverable through manual exact-diff fallback without ever representing backend failure as review success.

## Authority and scope

- Authoritative sources: issue #210, `AGENTS.md`, checked-in review settings, existing reviewer/provider/tool contracts.
- Owned paths: reviewer settings/runtime, NVIDIA client, Codex adapter, change-execution review mapping, focused tests, this change record.
- Shared paths: none.
- Excluded paths: review policy weakening, unrestricted network/process execution, unrelated workflow orchestration.
- Dependencies: registered NVIDIA NIM and pinned Codex CLI reviewer boundaries.
- Integration owner: change 144.

## Requirements

- **REQ-001**: Backend failures expose typed, redacted provider/process diagnostics.
- **REQ-002**: Retry only allowlisted transient failures within a JSON-configured attempt budget.
- **REQ-003**: Dual-backend failure exposes bounded manual exact-diff fallback without claiming reviewer success.
- **REQ-004**: Change execution counts only `status=completed` reviewer payloads as successful reviews.
- **REQ-005**: Later retries can recover to a normal completed review without stale failure state.

## Acceptance

1. Codex process I/O is explicit UTF-8 and encoding boundary failures are typed without prompt leakage.
2. NVIDIA timeout, transport, retryable HTTP, terminal HTTP, and malformed-response failures remain distinguishable.
3. Transient backend failures retry at most the configured attempt budget; terminal failures do not retry.
4. Exhausted configured backends return failed/unavailable state plus `manual_fallback.mode=exact-diff`.
5. Change execution returns `incomplete` rather than `passed` for any non-completed reviewer result.
6. Focused, repository-wide, exact-head CI, and post-merge reconciliation gates pass.

## Risks and recovery

- Risk: retries could duplicate expensive external review calls or conceal terminal failures.
- Recovery: bounded attempts, explicit retryable classification, redacted attempt history, conservative non-retryable default, and no success coercion.

## Out of scope

- Persistent reviewer job queues or asynchronous retries.
- Treating manual review as an automated reviewer success.
