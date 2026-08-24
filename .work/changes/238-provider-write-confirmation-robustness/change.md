# Change: Provider Write Confirmation Robustness

- **Change ID**: `238-provider-write-confirmation-robustness`
- **Risk Profile**: lean

## Outcome

Make commissioning provider writes reconcile durable success across transient or harmless provider response variation without weakening identity or duplicate prevention.

## Scope and acceptance

- Mutate a commissioning issue at most once per intake attempt; never blindly repeat an uncertain provider write.
- Reconcile durable success through direct read-back and deterministic-key search with bounded retry/backoff.
- Accept harmless text representation normalization while keeping the full deterministic title/body contract authoritative.
- Recover when the provider response loses the created issue number or the write response itself is lost after a durable mutation.
- Fail closed when no durable matching issue can be confirmed or required content is materially different.

## Implementation and verification

- Implementation notes: provider confirmation is now a bounded reconciliation phase after one mutation.
- Focused checks: 12 intake tests and the full 176-test post-merge commissioning suite pass; Ruff, `git diff --check`, change check, and governance validation pass. Local full-repository verify exceeded the available execution window without a failure result; exact-head GitHub CI remains the publication gate.
- Review findings: automated code-quality review is clean; required exact-diff safety fallback is clean after the automated safety reviewer exhausted its deadline.
- Residual risk: provider visibility can exceed the bounded confirmation window; that remains a retryable observer failure rather than duplicate mutation authority.
- Closeout state: implementation complete and ready for exact-head publication verification.
