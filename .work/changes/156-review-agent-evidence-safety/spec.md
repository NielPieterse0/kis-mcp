# Change Specification: Review Agent Evidence Safety

- **Change ID**: `156-review-agent-evidence-safety`
- **Status**: Approved for execution by operator request to close #267
- **Risk Profile**: rigorous (`large`; `architecture_boundary`, `public_contract`)

## Outcome

Make advisory code review source-bound, deadline-bounded, strict-result validated, and evidence-safe for #267 without changing unrelated review-model benchmarking or Work policy.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, GitHub issue #267.
- Owned paths: code-review workflow, change-execution workflow, verification selection source identity, NVIDIA/Codex timeout adapters, review settings/schema, focused tests, and affected authoritative docs.
- Shared paths: none.
- Excluded paths: unrelated coordinator/work-management/runtime work, model benchmarking changes, and fixes for #261/#265 except compatibility required by this contract.
- Dependencies: #261 and #265 are coordination evidence only; neither is silently treated as resolved by this change.
- Integration owner: this governed change only.

## Requirements

- **REQ-001 Source binding**: `review_change_with_agent` accepts the same Git source selector as verification (`working_tree`, `staged`, `commit`, `range`, `branch`) and collects evidence for that exact selector. Results include deterministic source fingerprint and refs. `execute_change_workflow` must pass the selected source through and reject a completed review whose fingerprint differs from verification selection.
- **REQ-002 Deadline budget**: one configured review deadline bounds all backend attempts/retries/fallback for a review, and change execution additionally bounds the aggregate specialist-review phase. Each backend call receives only the remaining budget. Deadline exhaustion returns a typed non-success result before the host timeout.
- **REQ-003 Strict result contract**: a successful review requires a non-empty summary, a list of structurally valid findings, a string-list of unknowns, and KIS-owned provenance. Empty, malformed, truncated, or schema-invalid backend output cannot become `completed`.
- **REQ-004 Evidence coverage**: evidence packaging is deterministic and file-aware. It preserves source/file provenance, includes only whole evidence sections, and reports included/omitted files and completeness instead of blindly truncating text.
- **REQ-005 Compatibility**: existing backend selection/model benchmarking semantics remain intact; timeout adapters accept an optional tighter per-call budget without widening authority.
- **REQ-006 Documentation**: authoritative operator/spec text describes source-bound review and typed incomplete behavior.

## Acceptance

1. **Given** a committed change and a clean working tree, **when** change execution selects `source=commit`, **then** the reviewer receives that commit selector and returns the same source fingerprint as verification selection.
2. **Given** unrelated working-tree dirt, **when** a commit/range review is requested, **then** that dirt does not replace the selected immutable review source.
3. **Given** retries/fallback whose cumulative time consumes the review budget, **when** the budget reaches zero, **then** later attempts are not started and the result is typed `incomplete`/deadline-exhausted.
4. **Given** malformed, empty, or over-limit model output, **when** normalization runs, **then** it is never reported as a completed review.
5. **Given** evidence larger than the configured budget, **when** packaging runs, **then** complete file sections are retained deterministically, omissions are named, `complete=false` is explicit, and change execution does not treat that review as successful.
6. **Given** a completed review with mismatched source fingerprint, **when** change execution aggregates it, **then** the workflow is incomplete with a typed source-mismatch error.

## Risks and recovery

- Risk: public review-tool arguments and result provenance change; mitigate with additive parameters, focused API-contract tests, exact-head CI, and docs.
- Risk: tighter time budgets expose previously hidden backend latency; this is intentional fail-closed behavior.
- Recovery: revert the single landed change/PR; no durable data migration is introduced.

## Out of scope

- Selecting or benchmarking replacement NVIDIA models.
- Reworking Codex mutation detection tracked by #261 beyond accepting the same remaining timeout budget.
- Fixing worktree Python import/source identity tracked by #265.
- Unrelated Work Management, coordinator, provider, or runtime changes.
