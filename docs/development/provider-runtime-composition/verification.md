# Provider Runtime Composition Verification

> Historical note: the detailed evidence below records change 014 at the time it was delivered. Current runtime composition after change 109 is authoritative in `SPEC.md`, `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`, runtime JSON, and current tests. The Provider registry now contains nine descriptors; runtime JSON selects seven mounted providers: Context7, Control Center, DBHub, Docker Hub MCP, GitHub MCP, Serena, and Supabase. DBHub is a source-aware per-binding read-only connector under `db_*`; Docker Hub is an approved external registry connector under `dockerhub_*`. Their installation/live commissioning is tracked separately from registration and configuration.

## Scope

Change `014-provider-runtime-composition` implements only the shared Provider runtime-composition slice:

- strict JSON selection of the approved GitHub and Supabase providers;
- deterministic build order and unique FastMCP namespaces;
- contained disabled, unregistered, build-failure, invalid-result, and mount-failure states;
- public `kis_provider_status` reporting that separates registry/readiness evidence from runtime build/mount evidence and unverified commissioning states;
- composition through the existing `build_server()` root without changing Work policy or provider authentication internals.

GitHub OAuth commissioning and Supabase OAuth/DCR commissioning remain outside this change.

## Requirement Evidence

| Requirement | Evidence |
|---|---|
| Strict settings and schema | `src/kis_mcp/providers/runtime_settings.py`, `settings/providers/platform-runtime.provider.json`, `contracts/providers/runtime/platform-runtime.schema.json`, invalid-document tests |
| Deterministic explicit composition | `compose_provider_runtime()` iterates validated settings ordered by provider ID and calls only `ProviderService.build(provider_id)` |
| Namespaced mounting | GitHub mounts as `github_*`; Supabase mounts as `supabase_*`; aggregate catalogue and tool-call tests pass |
| Failure containment | Builder exceptions, invalid builder results, and mount failures become immutable redacted status records; core tools remain available |
| Truthful status | `kis_provider_status` reports registration, enablement, build, mount, readiness, and six explicit `not_verified` commissioning fields |
| Work boundary preservation | `src/kis_mcp/middleware.py`, policy files, Desktop Commander adapter, and provider-specific middleware were not changed |
| Testable composition root | `build_server()` accepts keyword-only injected Provider service and runtime settings; default production behavior remains available |
| Documentation accuracy | `SPEC.md` and `docs/OPERATIONS.md` distinguish mounted adapters from authenticated/live-verified providers |

## TDD Evidence

1. Runtime settings tests were written first and failed because the module and artifacts did not exist: 10 expected failures.
2. Settings/schema implementation made the focused set pass: 10 passed.
3. Runtime composer tests were added first and failed because composition contracts did not exist.
4. Runtime composition implementation made the expanded set pass: 16 passed.
5. `build_server()` integration and public-contract tests were added first and produced four targeted failures.
6. Shared-server composition and `kis_provider_status` implementation made the focused integration set pass.

Post-PR14 integration focused command:

```powershell
pwsh -NoProfile -File .\.work\changes\014-provider-runtime-composition\run-focused-tests.ps1 `
  tests/providers/test_runtime_composition.py `
  tests/skills/test_tools.py `
  tests/skills/test_service.py `
  tests/discover/test_tool_registration.py `
  tests/test_public_contracts.py -q
```

Result: exit code `0`; 37 tests passed.

## Full Repository Verification

Command:

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

Post-PR14 integration result:

- configuration: passed;
- canonical locked interpreter: passed;
- FastMCP `3.4.4` and pytest `8.4.2`: passed;
- Python syntax: 66 files passed;
- change governance: 11 claims passed;
- complete pytest suite: 395 passed, 2 expected skips;
- repository verification: passed;
- change-scope check: passed after completing merge commit `91c0534`;
- `git diff --check`: passed.

## Review Findings

### Resolved

1. **Historical claim overlap:** Stale active claims from changes 005 and 010 overlapped the Discover tool-registration test and Provider product specification. The slice was redesigned to avoid both paths. `kis_provider_status` is exposed through an unnamespaced mounted child server, preserving the existing local-registration contract. The Provider product specification remains unchanged.
2. **Worktree-wide CRLF normalization:** Creating the emergency worktree with host Git settings initially marked nearly every tracked file modified. All tracked files were restored with `core.autocrlf=false`; only scoped edits were reapplied in LF form.
3. **Unicode restoration encoding:** A temporary PowerShell restore rendered box-drawing characters incorrectly. The file was restored again from Git with stdout explicitly decoded as UTF-8; its final diff is zero.
4. **Whitespace:** `git diff --check` found one trailing blank line at the end of `SPEC.md`; it was removed.
5. **Lazy upstream availability concern:** FastMCP source inspection confirmed aggregate provider list failures use the default `warn` strategy and are skipped, while ProxyProvider uses an empty lifespan and connects per request. An unavailable upstream therefore does not invalidate root startup merely because its proxy is mounted.
6. **Skills dependency reconciliation:** PR #14 merged at `656228491345a2e24be195d3c492d0670bc745ae`. The branch merged current `main` in `91c0534`, retained `register_skills_tools(server)` after `ThreeRuleMiddleware` registration, retained Provider composition and `kis_provider_status`, and passed the integrated focused and full suites.

### Blocking findings

None after the resolved items above.

## Security and Data Handling

- Runtime settings contain no credentials or token values.
- Raw builder exception text is never returned through Provider runtime status; only exception class names are exposed.
- Provider-specific authentication, scope middleware, and transports remain isolated in their adapter packages.
- No Work policy, middleware, quarantine, or Desktop Commander resolver file changed.
- No live external provider action was performed by this verification slice.

## Residual Work and Dependencies

- GitHub still requires official-binary installation, interactive OAuth/device authorization, scoped repository reads, and main-endpoint live verification in a dedicated follow-up slice.
- Supabase still requires hosted OAuth/DCR, approved persistent token storage, a harmless project-scoped read, and main-endpoint live verification in a dedicated follow-up slice.
- `docs/PROVIDER-MODULE-PRODUCT-SPEC.md` remains unchanged because historical change 010 still owns that path; current implementation status is authoritative in `SPEC.md`, `docs/OPERATIONS.md`, and this evidence record.

## Rollback

Revert the change commit or set both entries in `settings/providers/platform-runtime.provider.json` to `enabled: false`, then restart the server. Do not delete provider state or credentials.
