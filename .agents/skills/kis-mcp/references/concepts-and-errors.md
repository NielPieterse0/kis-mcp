# Concepts, Policy, and Errors

## Load when

Read this reference when interpreting policy outcomes, readiness, eligibility,
quarantine, structural errors, bounded evidence, or result metadata.

## Three capability planes

kis-mcp separates three roles:

```text
Discover -> establish bounded evidence
Govern   -> evaluate evidence against declared standards
Work     -> perform controlled operations
```

Discover and Work are broadly composed. A deterministic advisory Govern core is
also implemented in repository source, but public gateway composition can lag
that source. Use live capability evidence before claiming a Govern operation is
available, and never infer target-state Govern capability from architecture docs.

## The only Work hard rules

### HR-001 — write boundary

Block only a concrete invocation whose resolved effect writes outside
`C:\Projects`. Reads outside that boundary are not independently prohibited by
HR-001.

### HR-002 — external network through Work

Block only a concrete local Work invocation whose resolved operation consumes
an external network target. Approved external connectors operate through their
separate provider boundary.

### HR-003 — permanent deletion

Explicit delete intent must become a recoverable move beneath the configured
quarantine root or be rejected if safe quarantine is impossible.

Do not treat a destructive-looking tool name as proof of HR-003 without the
concrete invocation effect.

## Non-rules

These are evidence or UX state, not independent Work policy reasons:

- tool names or executable names;
- broad capability;
- catalogue/direct-profile membership;
- readiness or provider mount state;
- recommendation score;
- approval metadata;
- uncertainty or lack of a specialized parser.

Structural input validation may still reject malformed requests, but that is not
an HR decision.

## Readiness versus eligibility

Readiness describes whether a contribution/provider is locally usable or what
onboarding/failure state applies. Eligibility combines operation metadata,
readiness, dependencies, effects, and credentials to determine whether the
platform should expose/recommend/dispatch that operation.

Neither concept authorizes a prohibited Work effect.

## Common error families

### `DISCOVER_*`

Bounded repository/change/context request problems such as invalid paths, unsafe
links/reparse evidence, unsupported refs, unreadable content, or exceeded
limits. Correct the request/evidence boundary; do not change Work policy.

### `SKILLS_*`

Skill settings, frontmatter, catalogue, relative-path, hash, refresh, or backend
problems. Correct the skill package or mutation precondition.

### Provider/readiness errors

Authentication required, initialization required, unavailable, build failed,
mount failed, or operation ineligible. Use `kis_provider_status` and exact
capability evidence to identify the next action.

### Verification-selection and change-execution errors

`VERIFICATION_SELECTION_*` outcomes mean the requested change target, handoff,
or selection input could not be reconciled under the bounded selector contract.
`CHANGE_EXECUTION_*` outcomes mean the composed selection/verification/review
request failed or was structurally invalid. Correct the reported project,
source/ref, limit, timeout, or review input; do not bypass the workflow with
arbitrary command text merely to avoid its validation.

### Dispatcher errors

- `UNKNOWN_CAPABILITY_OPERATION`: search/describe the current catalogue.
- `EFFECT_MISMATCH`: use the dispatcher matching the operation's declared effect.
- `DISPATCH_RECURSION_BLOCKED`: call capability-control tools directly.
- `APPROVAL_REQUIRED`: use the original approval workflow.
- `OPERATION_INELIGIBLE`: resolve readiness/dependency/credential reasons first.
- `INVALID_ACTION_ARGUMENTS`: `arguments` must be an object matching the
  original schema.

### Quarantine errors

`HR-003_QUARANTINE_REQUIRED` means permanent deletion is being redirected to the
recoverable path. `HR-003_QUARANTINE_FAILED` means safe quarantine/restore could
not be completed; inspect the target/state rather than falling back to deletion.

## Bounded evidence fields

Many kis-mcp results expose fields such as:

- `schema_version` — response contract revision;
- `confidence` — quality of the available deterministic evidence;
- `unknowns` / diagnostics — facts the current slice could not establish;
- `truncated` — output budget prevented complete return;
- `readiness` / `eligible` — platform state for an operation or contribution;
- `eligibility_reasons` — why an operation is currently unavailable;
- fingerprints/hashes — stable evidence or optimistic-concurrency identities.

Do not convert `confidence=high` into evidence that was never collected. Do not
ignore `truncated=true` when the user asks for exhaustive results.

## Recovery principle

Prefer corrective retries that preserve the original boundary:

- narrow or correct the request;
- resolve the right project/provider target;
- authenticate the intended provider;
- use the correct effect dispatcher;
- refresh stale catalogue/hash evidence;
- restore from quarantine only when the original path is free.

Do not broaden permissions, disable policy, bypass middleware, force-delete
state, or inject credentials into prompts/configuration as a generic recovery
strategy.
