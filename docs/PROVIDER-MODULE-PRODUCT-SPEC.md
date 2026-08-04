# kis-mcp Provider Module Product Specification

## Document status

| Field | Value |
|---|---|
| Product | `kis-mcp` Platform |
| Module | Provider |
| Repository | `C:\Projects\kis-mcp` |
| Status | Approved architecture; common foundation implemented in change 010; connector integration remains dependent on changes 008 and 009 |
| Date | 2026-08-04 |
| Parent authority | [`PLATFORM-CONCEPT.md`](PLATFORM-CONCEPT.md) |

This specification defines the Provider module boundary, contracts, dependency direction, extension model, readiness model, and relationship to Work, Discover, and Govern. The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Approved platform architecture

```text
ChatGPT
   |
   v
kis-mcp FastMCP platform
├── shared tool catalogue / routing
├── provider registry
├── health and readiness
│
├── Work Module
│     └── three-rule middleware
│           ├── HR-001: no writes outside C:\Projects
│           ├── HR-002: no external network through Work
│           └── HR-003: no permanent deletion
│                 |
│                 v
│        Desktop Commander MCP
│        ├── filesystem
│        ├── editing
│        ├── search
│        ├── terminal
│        ├── process
│        └── document operations
│
├── Providers Module
│     ├── GitHub MCP provider
│     ├── Supabase MCP provider
│     └── future provider adapters
├── Govern Module
└── Discover Module
```

The platform has one shared catalogue, one provider registry, and one readiness model. Provider adapters remain independently testable modules beneath the Provider boundary.

## 2. Purpose

The Provider module supplies a stable platform boundary for external MCP connectors, local backends, semantic engines, and future platform providers.

It answers four questions:

1. Which providers are registered?
2. Which provider capabilities are available for discovery and routing?
3. Is each provider enabled and ready without starting unrelated providers?
4. How does the platform explicitly build a selected provider?

The Provider module does not replace provider implementations. It normalizes their identity and lifecycle contracts.

## 3. Module structure

```text
src/kis_mcp/providers/
├── __init__.py        explicit public Provider module surface
├── contracts.py       provider-neutral identity, capability, and readiness records
├── registry.py        deterministic registration and lookup
├── catalogue.py       immutable progressive catalogue projection
├── health.py          aggregate readiness without provider construction
├── service.py         thin provider-neutral facade
├── github/            GitHub MCP adapter owned by change 008
├── supabase/          Supabase MCP adapter owned by change 009
└── <future-provider>/ isolated provider-specific adapter
```

The common files MUST NOT import provider-specific adapter packages. Adapter packages MAY import the common Provider contracts.

## 4. Responsibility boundary

### 4.1 Provider module ownership

The Provider module owns:

- provider identity and kind;
- provider boundary classification;
- provider capability metadata;
- authoritative source and revision metadata;
- enabled state;
- deterministic registration and lookup;
- progressive catalogue projection;
- readiness probe contracts and aggregate readiness;
- explicit provider construction through a selected descriptor;
- stable JSON contract snapshots.

### 4.2 Adapter ownership

Each provider adapter owns:

- provider-specific settings and JSON configuration;
- authentication indirection and environment-variable names;
- transport construction;
- provider-specific scope validation;
- authoritative package, binary, or endpoint identity;
- provider-specific health evidence;
- FastMCP proxy construction;
- provider-specific smoke and conformance tests.

### 4.3 Responsibilities outside Provider

The Provider module MUST NOT own:

- HR-001, HR-002, or HR-003 enforcement;
- Desktop Commander Work middleware;
- provider credentials or secret values;
- provider installation or upgrade actions;
- arbitrary provider network requests;
- Discover evidence normalization or repository analysis;
- Govern admission, policy, or compliance decisions;
- task workflow orchestration beyond provider selection and construction;
- provider-specific tool wrappers.

## 5. Dependency direction

```text
Platform routing / workflows
          |
          v
ProviderService
├── ProviderRegistry
├── ProviderCatalogue
└── ProviderHealthSummary
          |
          v
ProviderDescriptor contract
          ^
          |
provider adapters
├── github
├── supabase
└── future adapters
```

Dependencies point inward toward provider-neutral contracts. The common Provider core never reaches outward into an adapter to discover it implicitly.

Registration MUST be explicit. Import side effects MUST NOT register or start providers.

## 6. Public contracts

The public Python contract is exposed through `kis_mcp.providers`.

### 6.1 Provider descriptor

A `ProviderDescriptor` declares:

- `provider_id` using lower-case kebab-case;
- human-readable `display_name`;
- `provider_kind`;
- execution or trust `boundary`;
- `authoritative_source`;
- pinned or declared `source_revision`;
- zero or more `ProviderCapability` records;
- explicit `builder` callback;
- explicit `readiness_probe` callback;
- `enabled` state;
- `schema_version`.

Builder and readiness callbacks are runtime implementation references and are excluded from serialized metadata.

### 6.2 Provider capability

A `ProviderCapability` declares a stable capability ID, description, effect labels, and provider-native tool names. Capability metadata supports discovery and routing; it does not create a Work authorization rule.

### 6.3 Provider readiness

A `ProviderReadiness` record declares one state:

- `ready`;
- `degraded`;
- `disabled`;
- `unavailable`.

Readiness is operational evidence. It MUST NOT be interpreted as HR-001, HR-002, or HR-003 policy authority.

### 6.4 Versioned JSON schema

The contract snapshot is stored at:

```text
contracts/providers/module/provider-module.schema.json
```

Public record objects are closed with `additionalProperties: false`. Runtime callbacks are not represented in the schema.

## 7. Registry

`ProviderRegistry` is a deterministic in-memory registry of descriptors.

It MUST:

- reject duplicate provider IDs;
- return providers in stable provider-ID order;
- provide exact lookup and presence checks;
- store descriptors without invoking builders or readiness probes;
- remain independent of provider-specific code.

It MUST NOT:

- scan packages for providers;
- import adapters dynamically from caller input;
- activate providers during registration;
- accept credentials;
- perform network access;
- silently replace an existing provider.

## 8. Catalogue

`ProviderCatalogue` projects immutable metadata from the registry.

It supports:

- stable provider listing;
- capability-based filtering;
- progressive tool or workflow discovery;
- provider source and revision inspection;
- enabled-state visibility.

Catalogue operations MUST NOT invoke provider builders or readiness probes.

The catalogue reports what is registered and declared. It does not prove runtime readiness, provider trust, or governance approval.

## 9. Health and readiness

`aggregate_provider_health` evaluates provider readiness probes in stable provider-ID order.

Rules:

1. Disabled providers are reported as `disabled` and are not probed.
2. Probe failures are contained as `unavailable` with the exception type only; raw error messages are not exposed.
3. A probe that reports another provider ID is contained as `unavailable`.
4. Provider builders are never called during health aggregation.
5. No providers produces aggregate `unavailable`.
6. All disabled providers produces aggregate `disabled`.
7. All active providers ready produces aggregate `ready`.
8. Mixed ready, degraded, or unavailable active providers produces aggregate `degraded`.
9. All active providers unavailable produces aggregate `unavailable`.

Provider-specific probes MUST avoid unnecessary external calls when local configuration and credential presence can establish readiness.

## 10. Provider service

`ProviderService` is a thin facade over registry, catalogue, readiness, and explicit construction.

It exposes four responsibilities:

- return the catalogue;
- filter catalogue entries by capability;
- aggregate health;
- build one explicitly selected provider.

The service MUST NOT contain `if provider == "github"` or equivalent provider-specific branches. Provider selection is data-driven through descriptors.

## 11. GitHub and Supabase integration

### 11.1 Current placement

The active connector slices already use the intended adapter locations:

```text
src/kis_mcp/providers/github/
src/kis_mcp/providers/supabase/
```

This means the connectors are physically housed beneath the Provider module boundary.

### 11.2 Coordinated migration

Change 010 does not edit active connector-owned files. After changes 008 and 009 are integrated, each adapter SHOULD expose one registration function that returns or registers a common `ProviderDescriptor`.

Expected pattern:

```python
def register_provider(registry: ProviderRegistry) -> ProviderDescriptor:
    descriptor = ProviderDescriptor(
        provider_id="github",
        display_name="GitHub MCP",
        provider_kind=ProviderKind.CONNECTOR,
        boundary=ProviderBoundary.APPROVED_EXTERNAL_CONNECTOR,
        authoritative_source="...",
        source_revision="...",
        capabilities=(...),
        builder=build_server,
        readiness_probe=provider_health,
    )
    return registry.register(descriptor)
```

The temporary root-level `src/kis_mcp/provider_registry.py` introduced by change 008 SHOULD become a compatibility shim or be removed through a coordinated follow-up after imports migrate to `kis_mcp.providers.registry`. It is not modified in this slice to avoid an ownership clash.

### 11.3 Connector independence

GitHub and Supabase MUST remain independently startable, testable, and replaceable. Their settings, transports, credentials, scope rules, and smoke tests MUST remain in their adapter packages.

## 12. Relationship to Work

The Work module owns Desktop Commander and the three-rule middleware.

Provider boundaries do not alter Work policy:

- HR-001 applies to writes outside `C:\Projects` through Work.
- HR-002 applies to external network effects through Work.
- HR-003 transforms permanent deletion into recoverable quarantine.

Approved external connectors such as GitHub and Supabase use separate supervised provider boundaries. Their existence does not authorize network access through Desktop Commander Work tools.

Provider state, catalogue membership, provider kind, or capability labels MUST NOT become a fourth Work restriction.

## 13. Relationship to Discover

Discover consumes normalized provider evidence and capability availability. It does not own provider lifecycle or connector transport.

```text
Provider module -> exposes registered capability and readiness
Discover        -> selects and normalizes relevant evidence
```

Discover MAY report provider unavailability as an unknown or degraded evidence source. It MUST NOT start or install a provider implicitly.

## 14. Relationship to Govern

Govern evaluates provider admission, provenance, compatibility, declared effects, licensing, trust, and required verification.

```text
Provider module -> declares source, revision, capabilities, boundary, readiness
Govern          -> evaluates whether that declaration satisfies standards
```

The Provider module records operational state. Govern owns compliance decisions.

## 15. Adding a future provider

A new provider slice SHOULD:

1. create `src/kis_mcp/providers/<provider-id>/`;
2. keep configuration in JSON;
3. isolate credentials behind environment-variable indirection;
4. implement provider-specific settings, transport, health, and server construction;
5. declare common capabilities and a common descriptor;
6. register explicitly through `ProviderRegistry`;
7. add provider-specific contracts and tests;
8. verify that catalogue and health do not build the provider;
9. avoid changes to Work policy, Discover internals, and unrelated adapters;
10. use an isolated governed worktree and non-overlapping claim.

## 16. Non-goals

The Provider module will not:

- merge all provider code into one large registry file;
- duplicate complete GitHub, Supabase, Desktop Commander, or semantic-provider implementations;
- create provider-specific public wrappers for every upstream tool;
- auto-install, auto-update, or auto-enable providers;
- dynamically import caller-selected modules;
- accept arbitrary provider URLs, executables, arguments, or environment maps through the common contract;
- store credentials;
- hide provider-specific validation inside the common registry;
- make provider readiness an authorization decision;
- add restrictions beyond HR-001, HR-002, and HR-003.

## 17. Acceptance criteria

The Provider module foundation is accepted when:

1. provider-neutral records are immutable, validated, and JSON-safe;
2. duplicate provider IDs and duplicate capability IDs are rejected;
3. registry and catalogue ordering is deterministic;
4. catalogue filtering does not build or probe providers;
5. health aggregation contains probe failures and does not build providers;
6. disabled providers are not probed;
7. provider construction occurs only through explicit selection;
8. the common core imports no provider adapter;
9. the public JSON schema is valid, versioned, and closed;
10. GitHub and Supabase remain isolated beneath the Provider package;
11. the approved platform diagram is versioned in this document;
12. no provider-specific active slice, Work policy file, Discover implementation, settings file, credential, network operation, or dependency is changed by the foundation slice.

## 18. Delivery sequence

1. **P0 — Common foundation:** contracts, registry, catalogue, health, service, schema, tests, and this specification.
2. **P1 — GitHub conformance:** migrate change 008 descriptor and registration to the common contract after dependency integration.
3. **P2 — Supabase conformance:** add common descriptor and registration to change 009 after dependency integration.
4. **P3 — Platform composition:** register approved providers in the shared platform catalogue and health surface without changing Work enforcement.
5. **P4 — Future adapters:** add semantic, forge, database, testing, or documentation providers through isolated slices.

Each phase remains independently reviewable and reversible.
