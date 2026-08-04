# Provider Runtime Composition Closeout

## Status

Implementation, review, verification, and remote delivery are complete. Draft PR #15 is open and remains intentionally blocked from landing by the Skills-slice reconciliation and separate OAuth commissioning work.

## Requirement Evidence

| Requirement | Implementation | Verification |
|---|---|---|
| R1 — strict runtime configuration | `runtime_settings.py`, canonical JSON, closed JSON Schema | canonical load, invalid JSON-shape, unknown key/provider, duplicate ID/namespace, type, and missing-provider tests |
| R2 — deterministic explicit composition | `compose_provider_runtime()` builds only through `ProviderService` in provider-ID order | stable build-order and runtime-disabled tests |
| R3 — namespaced mounting | `server.mount(provider, namespace=...)` | aggregate catalogue exposes `github_echo` and `supabase_echo`; namespaced call succeeds |
| R4 — failure containment | redacted immutable states for unregistered, build, invalid-result, and mount failures | core tools remain available; secret-bearing exception messages absent from JSON |
| R5 — truthful status | unnamespaced mounted `kis_provider_status` child server | status distinguishes registration, enablement, build, mount, readiness, and six `not_verified` commissioning fields |
| R6 — boundary preservation | no edits to Work middleware, policy, Desktop Commander resolver, quarantine, or adapter-specific scope middleware | focused parent-middleware call test plus final scoped diff inspection |
| R7 — testable integration | keyword-only Provider service/settings injection in `build_server()` | public signature contract and injected integration tests |
| R8 — accurate documentation | `SPEC.md`, `docs/OPERATIONS.md`, development verification record | documentation diff reviewed against implemented behavior and deferred OAuth scope |

## Review Findings

No blocking code finding remains.

Resolved during review:

- stale historical claim overlaps were removed from the slice scope;
- worktree-wide CRLF normalization was reverted and scoped LF edits reapplied;
- a temporary Unicode console-decoding restoration was corrected from Git with explicit UTF-8 decoding;
- an extra blank line in `SPEC.md` was removed;
- FastMCP aggregate and proxy source was inspected to verify lazy upstream list failures are skipped under the default warning strategy and ProxyProvider does not connect during lifespan startup.

## Verification

Focused runtime and public-contract command: exit code `0`, 26 passed.

Repository command:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

Final pre-commit result after closeout artifacts:

- configuration, interpreter, dependencies, and Python syntax passed;
- change governance passed with 10 claims;
- complete pytest suite: 363 passed, 2 expected skips;
- final repository verification reported `ok: true`;
- change-scope check passed;
- `git diff --check` passed.

Detailed evidence: `docs/development/provider-runtime-composition/verification.md`.

## Recovery

Revert the slice commit or set both external provider entries to `enabled: false`, then restart. Do not delete provider state or credentials.

## Residual Work

- Reconcile `src/kis_mcp/server.py` with `012-skills-module` and preserve `register_skills_tools(server)` before landing.
- Install and commission the official GitHub MCP binary with interactive OAuth/device flow and live scoped repository verification.
- Commission Supabase hosted OAuth/DCR, approved token persistence, and a harmless project-scoped live read.
- Keep `docs/PROVIDER-MODULE-PRODUCT-SPEC.md` unchanged until its historical change-010 ownership is resolved; current behavior is documented in `SPEC.md`, `docs/OPERATIONS.md`, and the verification record.
