# Provider Runtime Repair Specification

## Outcome

Repair the two verified post-merge defects in PR #15 while preserving its intended provider-runtime behavior and all active-agent boundaries.

## Requirements

- **R1 — Startup containment:** Importing and constructing the core `kis-mcp` server must not load Supabase configuration at module import time. Missing or malformed Supabase configuration must be contained as an unavailable/unregistered external provider rather than preventing Work, Discover, Skills, or gateway startup.
- **R2 — Disabled-provider containment:** Supabase runtime disablement must not require valid Supabase provider configuration.
- **R3 — Provider ownership:** Do not edit `src/kis_mcp/providers/supabase/**`, which remains owned by change `009-supabase-mcp-provider`; repair the composition boundary in `src/kis_mcp/providers/platform.py`.
- **R4 — Stable namespace parity:** The checked-in provider-runtime JSON Schema and `ProviderRuntimeSettings` must both enforce the documented public namespace mapping: `github-mcp` uses `github` and `supabase` uses `supabase`. This prevents duplicate namespaces without relying on a non-standard JSON Schema extension.
- **R5 — Executable schema tests:** Tests must validate representative documents against the actual checked-in schema, not only inspect schema structure, and must prove both schema and loader reject mismatched or duplicate namespace assignments.
- **R6 — Boundary preservation:** Do not change authentication, OAuth, credentials, provider settings files, Work middleware, policy, quarantine, or `server.py`.
- **R7 — Claim closure:** Mark only the merged `011-provider-composition` and `014-provider-runtime-composition` claims closed so current verification no longer treats their landed paths as active ownership, and land `019-provider-runtime-repair` as closed so it cannot become a new stale claim. Do not alter historical scope, outcome, or evidence.

## Root Cause

`src/kis_mcp/providers/platform.py` imports the Supabase package at module scope. The Supabase package imports `server.py`, whose module-level descriptor calls `load_supabase_provider_config()`. That configuration load occurs before `compose_provider_runtime()` can contain failures. Separately, the JSON Schema uses `uniqueItems`, which only rejects identical provider objects. Draft 2020-12 cannot generically compare one property across array items, while the loader allowed arbitrary unique namespaces despite the authoritative public prefixes being fixed as `github_*` and `supabase_*`.

## Acceptance Evidence

1. A focused test reproduces missing and malformed Supabase configuration while importing/building the platform provider service and fails on the merged implementation.
2. After repair, platform service construction succeeds, GitHub remains registered, and Supabase is absent/unregistered when its configuration cannot be loaded.
3. A disabled Supabase runtime can build the core server without valid Supabase configuration through the existing unregistered/disabled containment path.
4. Actual JSON Schema validation and the Python loader accept the canonical document and reject duplicate or provider-mismatched namespace assignments.
5. Existing provider-runtime, platform-composition, public-contract, and complete repository verification pass.
6. The merged `011` and `014` scope records and the landing `019` scope record are marked closed without other historical changes.
7. Change-scope and whitespace checks pass or the pre-existing recursive cross-worktree claim validator defect is recorded separately.

## Exclusions

- No Supabase adapter refactor or credential model change.
- No GitHub commissioning change.
- No new provider status fields or public API version change.
- No policy or permissions change.
- No package/dependency addition unless the locked environment already exposes the repository-declared schema validator.

## Recovery

Revert the repair commit. The change has no persistent data migration and does not modify credentials or provider state.

## Approval

The operator accepted the two post-merge findings and instructed the repair to continue on August 4, 2026.
