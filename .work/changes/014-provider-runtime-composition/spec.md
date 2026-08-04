# Provider Runtime Composition Specification

## Specification

- **Outcome, actors, and current state:** The shared `kis-mcp` FastMCP server currently exposes Desktop Commander, gateway tools, and Discover, while the approved GitHub and Supabase descriptors remain unused in an in-memory Provider registry. This slice makes the composition root construct and mount enabled external provider adapters without changing either adapter's authentication design. ChatGPT is the downstream client; `build_server()` is the composition root; `ProviderService` supplies registered descriptors and builders; each adapter remains responsible for its own transport and scope middleware.

- **Requirements and invariants:**
  - **R1 — Strict runtime configuration:** Add one closed JSON document that selects only the approved external provider IDs `github-mcp` and `supabase`, assigns each a unique lower-case namespace, and records whether runtime mounting is enabled. Unknown, duplicate, missing, or malformed entries fail configuration loading before server construction.
  - **R2 — Deterministic explicit composition:** Build external providers only through `ProviderService.build(provider_id)` in stable provider-ID order. Desktop Commander remains the existing Work backend and is never rebuilt through the external-provider mount loop.
  - **R3 — Namespaced mounting:** A successfully built FastMCP adapter is mounted into the shared server with its configured namespace so upstream tool names cannot collide with gateway, Discover, Skills, Desktop Commander, or another provider.
  - **R4 — Failure containment:** Missing binaries, credentials, invalid builder results, or other adapter-construction failures do not prevent the core server from starting. Public status records expose only the exception type, never raw exception text or credential values.
  - **R5 — Truthful status:** Expose a versioned `kis_provider_status` tool that distinguishes registration, enablement, build attempt, builder success, mount success, and provider-neutral readiness. Catalogue membership or a successful mount must not be reported as authentication, upstream connectivity, tool discovery, or live verification.
  - **R6 — Boundary preservation:** The existing `ThreeRuleMiddleware` and Desktop Commander resolver remain unchanged. Mounted connector middleware and scope rules remain active. External connectors continue to operate through the approved connector boundary, not through Desktop Commander Work networking.
  - **R7 — Testability and integration:** `build_server()` accepts injectable Provider service and runtime settings for isolated tests while preserving the default production path. Existing public tools and Desktop Commander behavior remain additive and compatible.
  - **R8 — Documentation accuracy:** Current-state documentation must say that runtime composition exists while GitHub and Supabase OAuth commissioning remains incomplete. No PAT, token, OAuth, installer, or smoke-test behavior is changed or claimed complete in this slice.

- **System, trust, data, compatibility, and operational boundaries:**
  - Exactly HR-001, HR-002, and HR-003 remain the Work decision set.
  - Provider credentials stay outside Git and outside the new runtime settings.
  - The new settings contain only provider IDs, enabled flags, and namespaces.
  - Provider construction may prepare local or remote transports but must not perform implicit installation or credential persistence.
  - A mounted FastMCP proxy may connect lazily when tools are listed or called; mounting alone is not live commissioning evidence.
  - The slice depends on `012-skills-module` for final shared `server.py` integration and must preserve its additive registrations.

- **Explicit exclusions:**
  - GitHub binary acquisition, GitHub OAuth/device flow, PAT removal, token persistence, and GitHub live smoke.
  - Supabase OAuth/DCR, encrypted token storage, PAT removal, and Supabase live smoke.
  - Startup/tunnel hardening files, remote-runtime behavior, Work middleware, policy, quarantine, and adapter-specific settings or code.
  - Automatic retries, background monitoring, auto-installation, auto-enablement, or hidden fallback authentication.

- **Architecture and data flow:**

  ```text
  build_server()
      |
      +--> Desktop Commander proxy (existing Work backend)
      +--> Discover / Skills / gateway tools
      +--> build_platform_provider_service()
              |
              +--> catalogue + readiness probes
              +--> ProviderRuntimeComposer
                      |
                      +--> enabled github-mcp -> build -> mount namespace `github`
                      +--> enabled supabase   -> build -> mount namespace `supabase`
                      +--> contain failures as status records
  ```

  `ProviderRuntimeSettings` validates the JSON selection. `compose_provider_runtime()` returns immutable composition records. `kis_provider_status` combines those mount records with fresh provider-neutral readiness from `ProviderService.health()`.

- **Security, privacy, failure, migration, and reversibility risks:**
  - Raw builder exceptions could expose paths or credentials; only `type(exc).__name__` is public.
  - Unnamespaced mounts could shadow tools; unique namespaces are mandatory.
  - Treating registry/readiness as authorization could create a fourth rule; status remains informational.
  - Parent middleware could accidentally become connector policy; no middleware changes are allowed and tests prove external namespaced calls are not interpreted as Desktop Commander effects.
  - Default enabled providers may fail to build on uncommissioned machines; failure containment keeps the core server usable and makes the missing commissioning visible.
  - Rollback is a branch revert or disabling provider entries in the runtime JSON; no persistent data migration is introduced.

- **Acceptance and release evidence:**
  - Strict settings/schema tests pass.
  - Disabled providers are not built.
  - Enabled fake FastMCP providers mount under deterministic namespaces and expose namespaced tools.
  - Builder exceptions and invalid builder returns are contained and redacted.
  - `build_server()` remains usable when all external providers fail.
  - `kis_provider_status` reports registration, enablement, build, mount, and readiness distinctly.
  - Existing public contract tests and complete `scripts/verify.ps1` pass on the final state.
  - Change-scope and `git diff --check` pass, or any pre-existing governance defect is recorded with bounded evidence.

- **Rollback/recovery strategy and trigger:** Revert the slice commit or set both runtime provider entries to `enabled: false` if provider mounting causes catalogue, startup, or middleware regressions. No provider state or credentials are deleted.

- **Open decisions with owner and implementation impact:** None. The operator-approved review decomposed runtime composition from GitHub and Supabase OAuth commissioning; this slice implements only runtime composition.

- **Specification review approval:** Approved by the operator through the attached provider-module review and the explicit instruction to continue with the slice on 2026-08-04.
