# Generic Acquisition Envelope Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Complete the KIS authorization side of the generic governed external-acquisition envelope for Commodity using the landed `import-isolate` v3 profile contract without widening ordinary Work network authority.

**Architecture:** Keep `import-isolate` as the single semantic owner of provider-profile network/auth/resource rules. KIS authorizes the exact provider record by profile ID, provider schema version, and canonical profile SHA-256, then emits the configured provider request schema version. This avoids a second host/auth/limit registry while making profile drift fail closed. Extend parameter normalization only enough for request-v2 bounded scalar arrays; all recipe/provider execution semantics remain provider-owned.

**Tech Stack:** Python 3.11+, pytest, JSON configuration/contracts, PowerShell change governance.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not alter unrelated authority or policy.
- Do not modify Commodity or `import-isolate`; consume their current authoritative contracts only.
- Preserve existing v1 Firecrawl/public HTTP behavior and the fixed approval-gated external operation.

---

### Task 1: Lock the shared profile/request contract with failing tests

**Files:**
- Modify: `tests/acquisition/test_registered_acquisition.py`
- Modify: `tests/capabilities/test_registered_acquisition_dispatch.py` if public schema coverage is needed

- [ ] Add a provider-policy fixture whose profile has a canonical schema version/hash identity.
- [ ] Add failing tests for exact profile binding, changed/missing/duplicate/disabled profile denial, and request-v2 list parameters.
- [ ] Add failure tests for list bounds/unsupported values/secret-like keys and retain v1 expectations.
- [ ] Run focused tests and record the expected failures before implementation.

### Task 2: Implement provider-profile binding and request-v2 normalization

**Files:**
- Modify: `src/kis_mcp/acquisition/settings.py`
- Modify: `src/kis_mcp/acquisition/service.py`
- Modify: `src/kis_mcp/acquisition/contracts.py`
- Add if separation improves cohesion: `src/kis_mcp/acquisition/profiles.py`

- [ ] Extend strict settings with provider policy path and per-authorization provider schema/hash plus request schema version.
- [ ] Resolve/read the provider policy only inside the registered provider project; bound JSON size and reject malformed/ambiguous profiles.
- [ ] Compute the same canonical record hash as `import-isolate` and deny schema/hash/enablement drift before provider invocation.
- [ ] Normalize request-v2 scalar arrays with fixed list/item/string/count bounds while retaining v1 scalar-only behavior.
- [ ] Emit the configured request schema version and keep the external operation free of URL/tool/credential fields.
- [ ] Run focused acquisition/capability tests.

### Task 3: Reconcile configuration and machine-readable contracts

**Files:**
- Modify: `settings/external-acquisition.settings.json`
- Modify: `contracts/external-acquisition/settings.schema.json`

- [ ] Bind current authorized provider profiles to exact landed `import-isolate` profile schema/hash identities and explicit request versions.
- [ ] Keep commercial/licensed generic profiles disabled/unconfigured until separate licensing/cost authority exists.
- [ ] Validate strict configuration parsing and schema compatibility.

### Task 4: Reconcile durable module documentation

**Files:**
- Modify: `docs/EXTERNAL-ACQUISITION-MODULE-PRODUCT-SPEC.md`

- [ ] Replace the old three-independent-registry description with shared exact-profile binding semantics.
- [ ] Document request-v2 bounded list support and configuration-only source onboarding.
- [ ] Preserve HR-002 and provider/consumer ownership boundaries without duplicating provider execution details.

### Task 5: Review, verify, and prepare exact reviewable change

**Files:**
- Change record under `.work/changes/175-generic-acquisition-envelope/**`

- [ ] Run focused tests.
- [ ] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [ ] Run affected verification through KIS and required rigorous specialist reviews.
- [ ] Resolve blocking findings and rerun invalidated evidence.
- [ ] Commit the bounded change and prepare the exact reviewable pull request through registered KIS GitHub workflow.
- [ ] Reconcile Work Management only through available supported operations; do not work around #269 truncation behavior.
