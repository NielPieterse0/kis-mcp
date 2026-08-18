# Change Specification: Housekeeping Operationalization

- **Change ID**: `199-housekeeping-operationalization`
- **Status**: Active
- **Complexity**: medium
- **Risk triggers**: `architecture_boundary`, `deployment`, `external_action`, `persistent_state`, `public_contract`
- **Owning programme obligation**: Change 194 / issue #364 / Hold #379

## Outcome

Commission the already-landed Change 194 housekeeping runners as unattended operational capability without changing their reconciliation/readiness decision algorithms or restoring obsolete execution authority.

## Authority and scope

- Authorities: `AGENTS.md`, current `SPEC.md`, `docs/OPERATIONS.md`, `docs/operations/work-discover.md`, issue #364, Hold #379, and merged Change 194 evidence.
- `kis-op` is the sole authoritative unattended housekeeping host because it owns the long-lived authenticated GitHub/Work Management provider session.
- `kis-dev` must never start the scheduler, preventing duplicate unattended execution.
- GitHub Actions remains canonical exact-head verification authority only; it is not a housekeeping mutation host.
- The Change 194 runner package and algorithms remain the valid landed baseline and are not rewritten by this change.

## Requirements

- **REQ-199-01 — Host binding.** Add one lifecycle-owned scheduler that activates only in the `kis-op` runtime and reuses the parent KIS server/provider session.
- **REQ-199-02 — Durable cadence.** Strict versioned settings must define enabled targets, project/repository identity, initial delay, interval, freshness threshold, retention, and runner bounds.
- **REQ-199-03 — Automatic preview.** Every unattended invocation must use `scheduled` + `preview`; automatic apply is prohibited.
- **REQ-199-04 — Governed apply.** Apply is explicit and supervised only. It must reference a fresh complete preview, re-preview current authority, require unchanged actionable-plan identity, and derive a stable idempotency key from that plan identity.
- **REQ-199-05 — Durable observability.** Persist bounded atomic preview/apply receipts, failure receipts, and per-runner status beneath the configured KIS state root, never in repository authority.
- **REQ-199-06 — Freshness.** Read-only status must expose host activation, configured cadence, last attempt/success/failure, next due time, receipt identity, age, and `never|fresh|stale|failed|disabled` state.
- **REQ-199-07 — Failure isolation.** Provider/runtime failures must produce bounded failure evidence and keep later scheduled runs alive; failure must not trigger mutation fallback or change HR semantics.
- **REQ-199-08 — Authority separation.** The legacy Work Management `scheduled_reconciliation` automation flag remains false; the new housekeeping runtime is the explicit scheduler authority and its own status is the commissioning signal.
- **REQ-199-09 — Live proof.** Completion requires both runners to execute unattended on live `kis-op`, persist receipts/status, and report fresh health after the merged revision is running.
- **REQ-199-10 — Programme boundary.** Successful repository delivery alone does not complete #364/#379; those records close only after live unattended commissioning evidence passes.

## Acceptance

1. Starting a `kis-dev` gateway never creates housekeeping scheduler tasks; starting `kis-op` creates exactly one task per enabled target.
2. Both targets run scheduled previews at configured cadence through the parent server and persist deterministic bounded evidence.
3. A scheduled invocation cannot apply mutations even if settings or caller input is malformed.
4. Explicit apply refuses a missing, stale, incomplete, conflicting, or changed preview; an unchanged fresh plan receives the same derived idempotency key on retry.
5. A runner exception persists a typed failure and status becomes `failed` while the scheduler remains available for the next interval.
6. Status becomes `stale` after the configured freshness threshold and reports enough evidence to diagnose a dormant host.
7. Focused tests, Ruff, governance checks, required reviews, and one canonical GitHub Actions run pass on the exact published head.
8. After merge, live `kis-op` proves unattended successful attempts for `work-management-reconciliation` and `backlog-readiness`; only then may Hold #379 and #364 be reconciled complete.

## Risks and recovery

- **Risk:** a duplicate runtime could execute the same schedule. **Control:** exact `kis-op` host binding plus one lifecycle service per gateway process.
- **Risk:** unattended mutation could override operator intent. **Control:** timer is preview-only; apply requires a fresh unchanged preview and stable deterministic key.
- **Risk:** persistent evidence could grow without bound or leak provider data. **Control:** bounded normalized receipts, typed error class only, fixed retention, atomic replacement beneath `C:\Projects\.kis-mcp`.
- **Recovery:** disable `settings/housekeeping.settings.json`, restart `kis-op`, and retain existing receipts for diagnosis; no runner source rollback or alternative execution authority is required.

## Out of scope

- Changing Change 194 reconciliation/readiness algorithms.
- Implementing Change 195 handoff/completion hardening.
- Scheduling through GitHub Actions, PAT authentication, Hyper-V, VirtualBox, local-runner, or the retired local execution subsystem.
- Automatic successor release, merge authority, or verification authority changes.