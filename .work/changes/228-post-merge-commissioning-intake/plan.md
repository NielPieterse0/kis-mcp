# Post-Merge Commissioning Intake Implementation Plan

**Goal:** Deliver #453 without changing housekeeping authority or source-delivery semantics.

**Architecture:** A dedicated `kis-op` FastMCP lifecycle service polls bounded recent closed PR candidates through the already-authenticated GitHub provider, verifies exact merge truth/identity, loads exact landed change-governance evidence, runs a pure settings-driven classifier, performs idempotent commissioning-issue intake, and persists bounded local receipts/checkpoints.

**Tech stack:** Python 3.13, FastMCP lifecycle/providers, existing KIS operation dispatch, strict JSON settings, pytest, repository governance scripts.

## Global constraints

- Stay inside amended `scope.json`.
- Tests precede behavior changes.
- No GitHub Actions write authority or new credentials.
- No timer-driven housekeeping apply.
- No source `Live Verification` projection in this slice.
- No historic backfill on initial activation.

## Task matrix

| Task | Requirements | Primary outputs | Test-first evidence | Review/verification |
| --- | --- | --- | --- | --- |
| T1 policy/contracts | R5-R7,R9,R11 | settings loader, models, classifier | invalid settings + classification/key tables fail first | API/contracts + architecture |
| T2 merge evidence | R2-R4 | provider observation resolver | closed-only, wrong merge, markers/scope mismatch fail first | architecture + security |
| T3 idempotent intake | R7-R10 | duplicate search + deterministic issue creation | replay/all-state duplicate/source-preservation tests fail first | security + API/contracts |
| T4 durable runtime | R1,R12 | checkpoint/receipt store + lifecycle scheduler | host, first-start, retry/overlap/state-corruption tests fail first | architecture + code quality |
| T5 gateway/status | R1,R12 | composition + read-only status/receipt tools | composition/tool exposure tests fail first | API/contracts |
| T6 docs/release | all | SPEC/operator docs/closeout | documentation assertions where applicable | documentation + full verify |

### T1 — Define policy, evidence, and classifier contracts

- Create `settings/post-merge-commissioning.settings.json` with strict host/cadence/state bounds, repository targets, high-risk ambiguity triggers, and live-surface rules.
- Create immutable domain models for PR observation, landed change evidence, classification, obligation, intake outcome, and bounded receipt identity.
- Implement a strict loader that rejects unknown keys, duplicate surface IDs, invalid glob/risk references, incomplete procedures, and unsafe cadence/state limits.
- Implement deterministic path/risk matching, surface de-duplication/order, `not_required`/`required`/`blocked_ambiguous`, and canonical key derivation.

### T2 — Resolve exact merged-change evidence

- Candidate listing is only discovery; each candidate is re-read with `github_pull_request_read(get)` and must report `merged=true`.
- Resolve the merge commit from default-branch commits in a bounded time window around `merged_at`; require exactly one merge-commit message naming the PR.
- Fetch `github_get_commit(detail=stats)` for exact changed paths and `github_get_file_contents` for the exact landed scope file.
- Parse strict `Issue: #N` and `Change: <change-id>` markers and cross-check scope `schema_version=4`, change ID, source repository, source number, and source kind.
- Treat missing/ambiguous evidence as a typed blocked result, never as `not_required`.

### T3 — Perform deterministic commissioning intake

- Render issue title/body solely from obligation data and static templates.
- Search repository issues across open/closed state for the exact commissioning key before creating.
- Create exactly one issue with `github_issue_write`; after creation, re-read/search the key to verify durable identity.
- Do not update/close/reopen the source issue or Project evidence fields.
- Persist the existing/new commissioning issue reference in the run receipt.

### T4 — Add bounded `kis-op` lifecycle and durable state

- Mirror only the lifecycle pattern of housekeeping: separate provider/service/state/platform modules with independent authority semantics.
- On first activation, atomically store `initialized_at/current checkpoint` and process no prior merge.
- On later runs, query from `checkpoint - overlap`, process candidates deterministically, and advance checkpoint only when the bounded scan is complete and all candidate outcomes are durably accounted for.
- Store atomic bounded receipts and typed failures beneath a dedicated KIS state namespace with retention.
- Scheduler performs only this registered intake workflow; it cannot invoke housekeeping apply or arbitrary changes.

### T5 — Compose and expose read-only observer diagnostics

- Compose the service after provider/workflow registration so it reuses the parent authenticated operation surface.
- Activate scheduler only for configured `kis-op`; `kis-dev` exposes status/receipt reads but does not schedule mutations.
- Expose `kis_post_merge_commissioning_status` and `kis_post_merge_commissioning_receipt` as bounded read-only diagnostics.
- Add capability metadata and gateway composition coverage without broadening unrelated exposure.

### T6 — Documentation, review, verification, and live release

- Update `SPEC.md`, `docs/OPERATIONS.md`, and a focused operator runbook with authority boundaries, cadence, receipt semantics, and recovery.
- Run focused unit/integration tests, governed scope check, `git diff --check`, Ruff for changed Python, and full `scripts/verify.ps1`.
- Run required code-quality, architecture, safety-security, and API-contract reviews against the exact final diff; fix blocking findings and re-run affected evidence.
- Prepare/publish the PR through governed KIS paths and require exact-head Actions success plus Work merge readiness.
- After merge and normal closeout, restart/refresh `kis-op`, create one fresh governed runtime-affecting merge, and prove exactly one deterministic commissioning intake. That live proof is the terminal acceptance for #453.

## Integration and recovery sequence

1. Pure policy/classifier contracts.
2. Exact provider evidence resolver.
3. Idempotent issue intake.
4. Durable scheduler/state.
5. Gateway/status composition.
6. Documentation/reviews/full verification.
7. Merge, restart, fresh-merge commissioning proof.

If any task reveals a new authority boundary, persistent-data semantic, or unresolved product choice, update spec/plan before implementation continues. If live commissioning fails, leave #453 Active/Blocked with evidence; do not reinterpret source merges as failed delivery.

## Plan review approval

Approved by the operator's explicit `go` after the exact planning-diff architecture review completed with no findings or unknowns. Implementation proceeded test-first in the approved T1 → T6 sequence; later scope amendments added only the existing gateway/runtime-generation exact-surface tests required by the selected architecture.
