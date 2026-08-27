# Reviewer Ensemble Implementation Plan

**Goal:** Add opt-in bounded reviewer ensembles without changing KIS authority or the default single-reviewer path.

**Architecture:** Extend change execution with validated reviewer profiles and a deterministic local aggregation layer. Every nested reviewer receives the same exact source selector. KIS validates each returned fingerprint/evidence envelope, records provenance, aggregates candidate findings without suppressing dissent, and exposes ensemble telemetry only when ensemble mode is requested.

**Tech Stack:** Python 3.13, FastMCP 4, pytest, existing KIS reviewer adapter.

## Global constraints

- Stay inside `scope.json`.
- Preserve existing single-reviewer result shape and semantics by default.
- No new mutation, verification, merge, or nested-agent authority.
- Reviewer profiles, rounds, calls, and elapsed review phase must be hard bounded.
- All reviewer evidence must remain exact-source-bound and fail closed.

### Task 1: Contract and validation

- Add reviewer-profile and ensemble-summary contracts.
- Validate profile identity/backend/model, reviewer/round bounds, and incompatible legacy/ensemble options.
- Add failing contract and request-validation tests first.

### Task 2: Ensemble execution and aggregation

- Execute independent reviewer passes under one aggregate deadline.
- Preserve exact-source checks for every pass.
- Add deterministic finding fingerprinting, corroboration, dissent tracking, and telemetry.
- Add optional bounded adjudication dispositions without gate authority.

### Task 3: Public tool and verification

- Expose only explicit bounded ensemble options on `execute_change_workflow`.
- Keep legacy options working unchanged when ensemble mode is absent.
- Run focused change-execution tests, Ruff, governance check, `git diff --check`, independent contract/architecture review, then canonical verification.
