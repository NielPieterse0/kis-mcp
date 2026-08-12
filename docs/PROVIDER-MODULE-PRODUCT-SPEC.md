# kis-mcp Provider Module Product Specification

## Document status

| Field | Value |
|---|---|
| Product | `kis-mcp` Platform |
| Module | Provider |
| Repository | `C:\Projects\kis-mcp` |
| Status | Current architecture and implemented provider foundation, composition, and runtime status model |
| Date | 2026-08-05 |
| Parent authority | [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md) |
| Current implementation authority | [`../SPEC.md`](../SPEC.md) |

This specification defines the Provider module boundary, contracts, dependency direction, extension model, readiness model, and current integration state. **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Current architecture

```text
kis-mcp FastMCP platform
├── shared gateway and tool catalogue
├── ProviderRegistry
│   ├── control-center     local read-only MCP App
│   ├── desktop-commander  local Work backend
│   ├── context7-mcp       approved external documentation connector
│   ├── github-mcp         approved external connector
│   ├── nvidia-nim         workflow-only external provider
│   ├── serena-mcp         local read-only semantic provider
│   └── supabase           approved external connector
├── provider runtime composition
│   ├── context7_*         mounted when enabled and successfully built
│   ├── controlcenter_*    mounted when enabled and successfully built
│   ├── github_*           mounted when enabled and successfully built
│   ├── serena_*           mounted when enabled and successfully built
│   └── supabase_*         mounted when enabled and successfully built
├── Tools registry
│   └── codex-cli          local executable adapter, not a Provider connector
└── kis_provider_status
```

The platform has one provider registry, one provider-neutral catalogue and health model, and one deterministic runtime-composition path. Provider adapters remain independently testable modules beneath the Provider boundary.

Desktop Commander remains the Work backend. Context7 is the bounded external-documentation connector; GitHub and Supabase use approved external connector boundaries; Serena is the bounded local semantic provider with offline-enforced startup; Control Center is the local read-only MCP App. NVIDIA NIM is registered for the advisory code-review workflow and is not mounted as a general provider passthrough. Codex CLI belongs to the Tools module.

## 2. Purpose

The Provider module answers four questions:

1. Which providers are registered?
2. Which capabilities and trust boundaries do they declare?
3. What is their local readiness without starting unrelated providers?
4. Which selected providers built and mounted in the current gateway process?

The module normalizes identity and lifecycle contracts. It does not replace provider implementations or prove authentication, upstream connectivity, tool discovery, or live commissioning.

## 3. Module structure

```text
src/kis_mcp/providers/
├── __init__.py        explicit public Provider surface
├── contracts.py       provider-neutral identity, capability, and readiness records
├── registry.py        deterministic registration and lookup
├── catalogue.py       immutable metadata projection
├── health.py          aggregate readiness without provider construction
├── service.py         provider-neutral facade and explicit construction
├── runtime.py         deterministic external-provider build and mount results
├── runtime_settings.py strict runtime JSON settings
├── platform.py        explicit composition root
├── control_center.py
├── context7/
├── desktop_commander.py
├── github/
├── nvidia/
├── serena/
└── supabase/
```

The provider-neutral contracts, registry, catalogue, health, and service modules MUST NOT depend on provider-specific adapters. The explicit `platform.py` composition root MAY import approved adapters to register them.

## 4. Responsibility boundary

### 4.1 Provider core

The Provider core owns:

- provider identity, kind, and boundary classification;
- capability metadata and provider-native tool names;
- authoritative source and revision metadata;
- enabled state;
- deterministic registration, lookup, and catalogue projection;
- readiness probe contracts and aggregate health;
- explicit provider construction;
- deterministic runtime build and mount results;
- stable JSON contract snapshots.

### 4.2 Provider adapters

Each adapter owns:

- provider-specific JSON settings;
- authentication indirection and environment-variable names;
- transport construction;
- provider-specific use of explicit routing coordinates supplied by the shared project registry;
- source, version, endpoint, package, or executable identity;
- provider-specific readiness and user-status evidence;
- builder behavior and adapter-specific smoke tests.

### 4.3 Outside the Provider module

The Provider module MUST NOT own:

- HR-001, HR-002, or HR-003 enforcement;
- Desktop Commander Work middleware;
- credential or secret values;
- provider installation or upgrade actions;
- arbitrary caller-selected provider URLs, commands, arguments, or environment maps;
- Discover evidence normalization;
- Govern admission decisions;
- general workflow orchestration;
- the Codex CLI Tool adapter.

## 5. Dependency direction

```text
Gateway and workflows
        |
        v
ProviderService and runtime composition
├── ProviderRegistry
├── ProviderCatalogue
├── aggregate_provider_health
└── ProviderDescriptor
        ^
        |
explicit platform composition
├── desktop_commander
├── github
├── nvidia
└── supabase
```

Registration MUST be explicit. Import side effects MUST NOT start, authenticate, probe, or contact a provider.

## 6. Public contracts

The public Python contract is exposed through `kis_mcp.providers` and represented by `contracts/providers/module/provider-module.schema.json`.

### 6.1 Provider descriptor

`ProviderDescriptor` declares:

- lower-case kebab-case `provider_id`;
- `display_name`;
- `provider_kind`;
- execution or trust `boundary`;
- `authoritative_source` and `source_revision`;
- zero or more `ProviderCapability` records;
- explicit `builder` and `readiness_probe` callbacks;
- `enabled` state;
- `schema_version`.

Runtime callbacks are excluded from serialized metadata.

### 6.2 Provider capability

`ProviderCapability` declares a stable capability ID, description, effect labels, and provider-native tool names. Capability metadata supports discovery and routing. It does not authorize Work or create another policy rule.

### 6.3 Provider readiness

`ProviderReadiness` uses one provider-neutral state:

- `ready`;
- `degraded`;
- `disabled`;
- `unavailable`.

Readiness is local operational evidence. It is not equivalent to authentication or commissioning and MUST NOT be interpreted as HR policy authority.

### 6.4 Runtime mount result

`ProviderMountResult` records one external-provider composition attempt:

- registration and runtime enablement;
- whether build was attempted and succeeded;
- whether mount succeeded;
- one state: `disabled`, `unregistered`, `build_failed`, `invalid_builder_result`, `mount_failed`, or `mounted`;
- bounded exception type when a failure occurs.

Mount state does not prove upstream authentication or live provider behavior.

## 7. Registry, catalogue, and health

`ProviderRegistry` MUST reject duplicate provider IDs, return stable provider-ID order, support exact lookup, avoid implicit package scans, and store descriptors without invoking callbacks.

`ProviderCatalogue` MUST project immutable descriptor metadata without building or probing providers.

`aggregate_provider_health` MUST:

1. skip probes for disabled providers;
2. contain probe exceptions as `unavailable` without exposing raw error messages;
3. reject mismatched provider IDs from probes;
4. avoid provider builders;
5. aggregate empty, disabled, ready, degraded, and unavailable states deterministically.

## 8. Provider service and explicit composition

`ProviderService` exposes catalogue access, capability filtering, aggregate health, and explicit construction of one selected provider. It MUST remain provider-neutral.

`build_platform_provider_registry()` explicitly registers Control Center, Desktop Commander, Context7 MCP, GitHub MCP, NVIDIA NIM, Serena MCP, and Supabase. `build_platform_provider_service()` wraps that registry.

`settings/providers/platform-runtime.provider.json` selects the FastMCP adapters that the primary gateway attempts to mount. The current selection mounts Context7 under `context7`, Control Center under `controlcenter`, GitHub MCP under `github`, Serena under `serena`, and Supabase under `supabase`. Desktop Commander is already the Work proxy. NVIDIA is consumed by the advisory workflow.

Runtime composition processes settings in stable provider-ID order and contains unregistered, disabled, builder, invalid-result, and mount failures. One optional provider failure MUST NOT prevent the core Work, Discover, Skills, agent-registration, or gateway surfaces from starting.

## 9. User status and commissioning

`kis_provider_status` keeps these evidence layers separate:

| Layer | Meaning |
|---|---|
| Registration | Descriptor exists in the Provider registry. |
| Runtime enablement | Provider is selected in runtime JSON. |
| Readiness | Local preflight evidence from the adapter. |
| Build and mount | Current gateway-process composition result. |
| User status | Current next action in bounded user-facing language. |
| Commissioning | Installation, configuration, authentication, upstream connection, tool discovery, and live verification evidence. |

Normal onboarding states include:

- **GitHub — Ready, authentication required:** executable, configuration, OAuth mode, and mount prerequisites are ready; supervised sign-in remains.
- **Supabase — Ready, authentication required:** the unscoped account endpoint, Windows credential storage, and provider configuration are ready; one browser OAuth login remains for the running KIS runtime.
- **Supabase — Ready, authenticated:** the persistent runtime client is connected and tools are discovered; explicit registered-project live verification may still be pending.
- **NVIDIA NIM — unavailable or degraded without `NVIDIA_API_KEY`:** the optional review backend may fall back to Codex; the gateway remains available.

Use degraded, unavailable, build-failed, or mount-failed states for genuine local faults. Do not present expected onboarding as breakage.

## 10. Provider-specific boundaries

### 10.1 Control Center

Control Center is a local read-only MCP App. It is mounted under `controlcenter_*` and may also run standalone. It receives instance-scoped runtime evidence and exposes no Work mutation authority.

### 10.2 Desktop Commander

Desktop Commander is a `local_backend` at the `work_backend` boundary. Its builder creates the existing Work server. HR-001, HR-002, and HR-003 remain enforced through the Work adapter and middleware, not through Provider metadata.

### 10.3 Context7 MCP

Context7 is the pinned external-documentation connector. It is mounted under `context7_*` with its bounded documentation-read surface and remains independent from Discover project memory.

### 10.4 GitHub MCP

GitHub MCP is an approved external connector with isolated settings, OAuth behavior, source identity, persistent runtime client lifecycle, readiness, builder, and smoke evidence. Successful mount exposes upstream tools under `github_*`; user-facing readiness names the selected `kis-op` or `kis-dev` runtime rather than assuming one surface.

### 10.5 Serena MCP

Serena 1.6.1 is the bounded local semantic provider. It mounts only approved read-only symbol/reference tools under `serena_*`, keeps provider state beneath the central KIS state root, and enforces offline language-server startup. Serena memory remains provider-managed state rather than KIS project memory.

### 10.6 Supabase

Supabase is an approved external connector with an unscoped hosted account-OAuth transport, persistent runtime client lifecycle, central-registry project routing, isolated settings, readiness, builder, and smoke evidence. Successful mount exposes upstream tools under `supabase_*`; explicit `project_id` values must be registered, while targetless calls require upstream read-only annotation.

### 10.7 NVIDIA NIM

NVIDIA NIM is an approved external provider used by `review_change_with_agent`. The adapter reads the API key only from the configured environment-variable name, uses the fixed OpenAI-compatible chat-completions endpoint and model settings, and is not mounted for arbitrary provider passthrough.

### 10.8 Codex CLI exclusion

Codex CLI is a local executable Tool adapter behind a fixed PowerShell wrapper. It is not a Provider descriptor and MUST NOT be added to Provider runtime settings merely because the code-review workflow can select it.

## 11. Relationship to Work, Discover, and Govern

Provider metadata does not alter Work policy. HR-001 applies to writes outside `C:\Projects`; HR-002 applies to external network effects through local Work; HR-003 replaces permanent deletion with quarantine. Approved external connectors operate through separate supervised provider boundaries.

Discover MAY consume registered capability, readiness, and normalized evidence. It MUST NOT install, authenticate, or start a provider implicitly.

Govern owns provider-admission and compliance decisions. The existing Discover provider-admission service produces bounded evidence with a fixed `pending_govern` decision; it does not approve, install, or activate a provider.

## 12. Adding a provider

A new provider slice SHOULD:

1. create `src/kis_mcp/providers/<provider-id>/`;
2. keep configuration in strict JSON;
3. keep secrets behind environment or approved credential indirection;
4. isolate settings, transport, readiness, builder, and smoke behavior;
5. declare a common descriptor and capabilities;
6. register through the explicit platform composition root;
7. add contracts and provider-specific tests;
8. prove catalogue and health do not build the provider;
9. decide explicitly whether it is mounted, workflow-only, or internal;
10. avoid changes to Work policy and unrelated adapters;
11. use an isolated governed worktree and non-overlapping ownership claim.

## 13. Non-goals

The Provider module will not:

- merge all provider code into one registry file;
- recreate complete upstream provider surfaces;
- auto-install, auto-update, auto-authenticate, or auto-enable providers;
- dynamically import caller-selected modules;
- store credentials;
- expose arbitrary provider execution parameters;
- make readiness, registration, mount, or commissioning an authorization decision;
- add restrictions beyond HR-001, HR-002, and HR-003.

## 14. Implementation and delivery status

| Phase | Status | Evidence boundary |
|---|---|---|
| P0 — Common foundation | Implemented | Contracts, registry, catalogue, health, service, schema, and tests. |
| P1 — GitHub conformance | Implemented | Descriptor, explicit registration, isolated settings and builder, OAuth and smoke paths. |
| P2 — Supabase conformance | Implemented | Descriptor, explicit registration, unscoped account OAuth, persistent client lifecycle, registered per-call project routing, and smoke paths. |
| P3 — Platform composition | Implemented | Explicit seven-provider registry; Context7, Control Center, GitHub, Serena, and Supabase runtime selection; namespaced mount containment; and `kis_provider_status`. |
| P4 — Workflow provider | Implemented for NVIDIA NIM | Workflow-only descriptor and client for the advisory code-review agent. |
| P5 — Local semantic/UI providers | Implemented | Serena 1.6.1 bounded read-only semantic mounting and the mounted/standalone read-only Control Center. |
| Future adapters | Target | Additional forge, database, testing, or documentation providers added through separate slices. |

Implementation and tests do not by themselves prove live credentials, authentication, upstream connectivity, or current commissioning. Those states require separate supervised evidence.

## 15. Acceptance criteria

The Provider module is accepted when:

1. provider-neutral records are immutable, validated, and JSON-safe;
2. duplicate provider and capability IDs are rejected;
3. registry, catalogue, health, and runtime ordering are deterministic;
4. catalogue operations do not build or probe providers;
5. health contains probe failures and does not build providers;
6. disabled providers are not probed or built;
7. construction occurs only through explicit selection;
8. the provider-neutral core imports no adapter;
9. the platform composition root registers only approved adapters;
10. runtime build and mount failures are contained and redacted;
11. Context7, GitHub, NVIDIA, Serena, Supabase, and Control Center remain isolated behind their Provider adapters;
12. Codex CLI remains in the Tools module;
13. provider state never creates a fourth Work restriction;
14. current guidance distinguishes implementation, readiness, mount, authentication, and commissioning.
