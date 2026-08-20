# Change Specification: Purpose Specific Reviewer

- **Change ID**: `211-purpose-specific-reviewer`
- **Status**: Implemented; publication/closeout pending
- **Complexity**: Large
- **Risk triggers**: architecture_boundary, external_action, public_contract, security

## Outcome

Replace #403's obsolete universal reviewer path with the qualified purpose-specific external reviewer architecture while preserving source-bound, read-only semantics.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, #403 qualification record, strict settings/schema/source/tests.
- Owned: reviewer workflow/tests; NVIDIA client/tests; reviewer settings/schema; scoped operator/provider/current-product docs; this change record.
- Excluded: Discover implementation and Serena implementation/tests (#407/#408 lanes).
- Dependency boundary: #395 owns verification-grade review-evidence qualification; #403 only produces strict source-bound reviewer evidence.

## Requirements

- **REQ-001**: Route each public review purpose to the exact qualified primary/backup model pair.
- **REQ-002**: Shape evidence deterministically by review purpose and treat repository content as untrusted data.
- **REQ-003**: Use provider SSE deltas for liveness; comments/textual heartbeats do not count.
- **REQ-004**: Fail closed on incomplete/stale evidence, stalls, truncation, malformed output, unexpected tools, or unusable provider responses.
- **REQ-005**: Apply typed retry/fallback policy: bounded retry for rate/transport pressure; route backup for unusable primary; never implicit Codex fallback.
- **REQ-006**: Safety/security uses Lightning discovery, deterministic corroboration, then complete Super adjudication with Ultra fallback and exact cardinality.
- **REQ-007**: Return bounded reviewer telemetry without credentials, raw provider errors, or reasoning traces.

## Acceptance

1. Automatic review selects the exact purpose route and emits SSE telemetry.
2. Invalid/stalled/truncated/tool-call/stale responses cannot report `completed`.
3. Security candidate loss or malformed adjudication fails closed.
4. Explicit Codex/legacy-model overrides remain direct compatibility paths only.
5. Focused reviewer/NVIDIA regression, Ruff, governance scope check, independent review, and exact-head GitHub Actions all pass.

## Risks and recovery

- Risk: provider drift or route-specific model outage. Recovery: typed failure plus only the qualified lane backup; otherwise fail closed.
- Risk: source mutation during external review. Recovery: post-review fingerprint re-read rejects the result.
- Risk: security candidate loss. Recovery: cardinality gate rejects adjudication and retries only with qualified Ultra.

## Out of scope

- #395 verification-grade evidence policy and merge-readiness semantics.
- #407 merge-commit delta inspection.
- #408 Serena capability boundary.
- Promotion of experimental/watchlist models to authoritative review roles.
