# Change: Registered Mutation Approval Authority

- **Change ID**: `208-registered-mutation-approval-authority`
- **Risk Profile**: lean

## Outcome

Prove and document the authoritative approval boundary for registered approval-required mutations, add reproducible direct/workflow tests, and identify any bounded remediation without importing private-repository Actions requirements.

## Scope and acceptance

- Trace every current approval-required registered mutation family from capability entry to execution.
- Record an explicit authority matrix distinguishing supervised self-attestation from independent mechanical authority.
- Add reproducible direct-dispatch and workflow-mediated approval tests.
- Reconcile future #241 assignment/fencing authority without duplicating it or importing #391 private-repository Actions requirements.
- Open a remediation defect only if a currently required authority decision is bypassable.

## Implementation and verification

- Implementation notes: classified registered GitHub/acquisition direct calls as intentionally supervised `approved=true` self-attestation; merge-queue enqueue/land add Work Management readiness evidence; housekeeping apply uses fresh preview receipt/host/preflight/idempotency authority. No runtime enforcement change is required.
- Focused checks: 146 focused pytest cases passed across capability dispatch, acquisition, completion, merge-queue governance, housekeeping authority, and registered publication; Ruff passed on both changed test files.
- Review findings: required safety-security review passed on the complete substantive diff with no findings; final metadata-only evidence recording is rechecked before publication.
- Decisions: no remediation issue opened because no required authority decision is bypassed under the current supervised contract; #241 remains the separate repository work-packet mutation authority programme.
- Assumptions / risks: direct registered virtual mutations intentionally do not independently resolve user identity, Work records, or assignment keys; if future autonomous workers invoke them, #241 authority must be enforced by the calling workflow first.
- Holds / deferred: none. #391 is explicitly excluded and contributes no KIS requirement.
- Residual risk: the supervised self-attestation model depends on the documented single-operator supervision boundary; changing that operating model requires a new authority decision.
- Closeout state: implementation complete; pre-publication governance, review, exact-head Actions, merge, Work Management completion, and cleanup remain.
