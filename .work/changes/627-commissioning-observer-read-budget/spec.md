# Change Specification: Commissioning Observer Read Budget

- **Change ID**: `627-commissioning-observer-read-budget`
- **Status**: Active
- **Risk Profile**: standard; `external_action`, `persistent_state`

## Outcome

Fix issue 641 so the bounded post-merge commissioning observer can process the configured candidate window without deterministic external-read starvation, while preserving exact identity, checkpoints, and fail-closed candidate evidence.

## Authority and scope

- Authoritative sources: `AGENTS.md`, issue #641, `docs/operations/post-merge-commissioning.md`, checked-in commissioning settings/contracts/tests.
- Owned paths: commissioning runtime budget/service, focused tests, settings/parser if required, canonical runbook, and this change record.
- Shared paths: none.
- Excluded paths: merge identity/evidence semantics, Work policy rules, runtime restart scripts, housekeeping.
- Dependencies: current `main` at `3adc4351282cf9e0cd0e6e9c2fbeb2a4273c3366` including #620 per-candidate failure isolation.
- Integration owner: none.

## Requirements

- **REQ-001**: Candidate external-read consumption must not cumulatively starve later candidates in the configured `max_candidates` window.
- **REQ-002**: External reads remain bounded per discovery/candidate phase and total scan reads remain deterministically bounded by `1 + max_candidates * max_external_reads`.
- **REQ-003**: Mutation consumption remains one shared scan-wide budget and must still fail the scan when exhausted.
- **REQ-004**: A candidate that exhausts only its read budget becomes bounded `unresolved_candidate` evidence; later candidates still run and the checkpoint remains unadvanced.
- **REQ-005**: Exact merge/source/change identity, checkpoint recovery, blocked evidence, and existing candidate failure isolation remain unchanged.

## Acceptance

1. **Given** 26 candidates that each require eight reads, **when** the per-candidate limit is eight, **then** all 26 candidates are processed instead of the shared counter starving later candidates.
2. **Given** one candidate exceeds its read allowance, **when** later candidates remain valid, **then** the over-budget candidate is unresolved, later candidates continue, and the run stays incomplete without advancing the checkpoint.
3. Focused post-merge commissioning tests, change governance checks, review, and exact-head CI pass before merge.
4. After deployment, live observer evidence reaches PR #628 and a fresh governed follow-up merge without checkpoint manipulation.

## Risks and recovery

- Risk: isolating read counters can increase the maximum reads of one scan. The configured candidate/read bounds make that ceiling explicit and deterministic; mutations remain globally bounded.
- Recovery: revert the change to restore prior shared-read behavior; no state migration is introduced and checkpoints are not rewritten.

## Out of scope

- Changing merge/source/change identity algorithms, historical backfill, arbitrary checkpoint edits, or increasing mutation authority.
