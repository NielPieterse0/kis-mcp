# Change: Merge Queue Live Commissioning

- **Change ID**: `123-merge-queue-live-commissioning`
- **Risk Profile**: lean

## Outcome

Live-commission the KIS speculative landing queue by landing this governed commissioning slice through exact candidate CI and exact-base queue CAS.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- This lifecycle record is the commissioning payload; no product/source behavior changes are included.
- Source PR Canonical Verification must pass at its exact head before queue enqueue.
- The new queue must publish a generation-scoped cumulative candidate and Canonical Verification must pass at that exact candidate SHA.
- Governed landing must use fresh SPEC-123 Work Management record/trace evidence and exact generation/base CAS.
- GitHub must observe this PR merged after the candidate becomes reachable from `main`.
- Registered `origin/main` tracking must refresh to the exact landed candidate.

## Implementation and verification

- Implementation notes: evidence-only live commissioning slice for the queue landed by change 120.
- Focused checks: change scope governance and exact GitHub source-head/candidate-head Canonical Verification.
- Review findings: no source-code review surface; verify lifecycle record and exact identities only.
- Residual risk: commissioning fails closed if source head, candidate head, queue generation, base, Actions evidence, or Work Management readiness changes.
- Closeout state: pending live queue commissioning.
