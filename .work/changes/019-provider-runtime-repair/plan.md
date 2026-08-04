# Provider Runtime Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore provider startup failure containment and make the provider-runtime JSON Schema enforce the same namespace uniqueness as the Python loader.

**Architecture:** Keep connector internals untouched. Make Supabase registration lazy at the provider composition boundary and treat configuration/import failures as an absent registry entry, which the existing runtime composer already reports as `unregistered`. Enforce the authoritative public namespace mapping (`github-mcp` to `github`, `supabase` to `supabase`) in both the Python loader and Draft 2020-12 schema, because standard JSON Schema cannot generically compare one property across array items.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.4.2, JSON Schema Draft 2020-12, PowerShell verification.

## Global Constraints

- Exactly HR-001, HR-002, and HR-003 remain the Work decision set.
- Do not edit connector-owned GitHub or Supabase packages.
- Do not modify authentication, credentials, settings values, server composition ordering, or Work policy.
- Use test-first red/green evidence for both defects.
- Keep the repair bounded to the declared scope.

---

### Task 1: Contain Supabase Registration Failures

**Files:**
- Modify: `tests/providers/test_platform_composition.py`
- Modify: `src/kis_mcp/providers/platform.py`

**Interfaces:**
- Consumes: `build_platform_provider_registry(...) -> ProviderRegistry`
- Produces: the same public function signatures; invalid Supabase configuration yields no Supabase descriptor rather than an exception.

- [ ] Add a subprocess-style or isolated-import test that redirects the repository root/config lookup to missing and malformed Supabase settings and proves platform module/service construction fails on the merged code.
- [ ] Run only the new tests and confirm the expected configuration/import failure.
- [ ] Replace the module-scope Supabase import with a private lazy registration helper in `platform.py` that imports and registers Supabase inside `build_platform_provider_registry()` and catches provider registration/configuration exceptions without touching connector code.
- [ ] Assert GitHub and Desktop Commander remain registered while Supabase is absent after the contained failure.
- [ ] Run platform and runtime composition tests to green.

### Task 2: Enforce Stable Namespace Mapping

**Files:**
- Modify: `tests/providers/test_runtime_composition.py`
- Modify: `src/kis_mcp/providers/runtime_settings.py`
- Modify: `contracts/providers/runtime/platform-runtime.schema.json`

**Interfaces:**
- Consumes: Draft 2020-12 schema validation and `ProviderMountSetting` construction.
- Produces: schema and loader accept only `github-mcp`/`github` and `supabase`/`supabase` namespace pairs.

- [ ] Add actual schema-validation assertions for the canonical document, a duplicate-namespace document, and provider-mismatched namespace documents.
- [ ] Add loader assertions proving alternate unique namespaces are rejected so runtime and schema remain identical.
- [ ] Run the new tests and confirm the merged schema accepts duplicate/mismatched namespaces and the merged loader accepts alternate unique namespaces.
- [ ] Add one immutable provider-to-namespace mapping in `runtime_settings.py` and validate each `ProviderMountSetting` against it.
- [ ] Add provider-specific conditional constraints to the schema item so each approved provider requires its stable namespace while preserving the existing closed item shape and exact provider membership.
- [ ] Run runtime settings/composition tests to green.

### Task 3: Review, Verify, and Deliver

**Files:**
- Modify: `.work/changes/019-provider-runtime-repair/tasks.md`
- Modify: `.work/changes/019-provider-runtime-repair/closeout.md`
- Review: all changed files

**Interfaces:**
- Produces: exact test, review, rollback, and PR evidence for the final branch head.

- [ ] Confirm merge history for changes 011 and 014, mark only their current-checkout scope status fields `closed`, and land change 019 closed.
- [ ] Review the final diff against R1-R7, active-agent boundaries, exception containment, schema/runtime parity, stale-claim closure, and test quality.
- [ ] Run focused provider tests.
- [ ] Run `pwsh -NoProfile -File .\scripts\verify.ps1`.
- [ ] Run the current-change scope check; record the known recursive historical-claim validator failure separately if it remains.
- [ ] Run `git diff --check` and confirm a clean staged/committed branch.
- [ ] Complete task and closeout evidence, commit, push, create a PR, re-read its exact head, and merge only if the reviewed head remains unchanged and all blocking findings are resolved.

## Traceability

| Requirement | Task | Evidence |
|---|---|---|
| R1-R3 | Task 1 | failing import/config tests, platform registry assertions |
| R4-R5 | Task 2 | real Draft 2020-12 validation tests |
| R6 | Tasks 1-3 | scoped diff, review, full verification |

## Stop Conditions

Stop when both regressions have failing-then-passing tests, no connector-owned or policy paths changed, full verification is green, the exact PR head is reviewed, and remaining commissioning work is still explicitly out of scope.
