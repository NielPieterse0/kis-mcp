# External Acquisition Module Product Specification

This document is the durable module-specific contract for KIS registered external acquisition. It is subordinate to `AGENTS.md`, `docs/TRUST-MODEL.md`, and root `SPEC.md`; it does not redefine Work policy or provider containment.

## Current capability

KIS exposes one discoverable approval-gated external operation, `kis_acquire_registered_evidence`, for registered projects that have explicit authorization in `settings/external-acquisition.settings.json`. Authorization settings schema v2 carries the exact provider-profile binding and provider request-schema selection.

The public operation accepts exactly:

- registered project ID;
- authorized provider profile ID;
- immutable consumer recipe ID;
- exact `sha256:<hex>` recipe identity;
- configured bounded non-secret parameters;
- explicit `approved=true`.

It does not accept a URL, network target, provider tool name, recipe path, executable path, credential value, or arbitrary HTTP request.

## Shared authorization boundary

External acquisition preserves three distinct responsibilities without maintaining two semantic provider registries:

1. **KIS authorization JSON** — registered project/profile/recipe namespace, parameter keys, approval requirement, request schema version, request budgets, and an exact binding to the selected provider-profile schema version and canonical SHA-256.
2. **`import-isolate` provider policy** — the single semantic owner of network/provider containment, allowed tools/hosts/methods/redirects/authentication/resources, isolated execution, and raw evidence acquisition.
3. **Consumer recipe JSON** — source/dataset/web evidence semantics. A recipe may only narrow provider authority.

KIS resolves both the consumer and registered provider projects through the central project registry. Before delegation it resolves the configured provider-policy path inside `import-isolate`, reads bounded policy bytes, requires one exact selected profile, verifies that profile's configured schema version and canonical SHA-256, and rejects disabled profiles. It separately derives the configured project-relative consumer recipe path, resolves effective Windows containment, reads bounded recipe bytes, and verifies the caller-declared recipe SHA-256.

This profile binding makes provider-policy drift fail closed without duplicating host, authentication, retry, redirect, content-type, or resource-limit semantics in KIS. A normal newly supported source shape therefore changes declarative provider configuration, KIS authorization configuration, and the consumer recipe/adapter rather than KIS acquisition core code.

## Provider boundary

The registered provider project is `import-isolate`. KIS invokes only the fixed host script configured by `provider.script_relative_path`; the current entry point is `scripts\\Invoke-RegisteredExternalAcquisition.ps1`.

The provider receives a normalized request containing only the configured request schema version, project/profile/recipe/hash identity, and bounded parameters plus the already-verified recipe path. KIS strips its `approved` control field before delegation. Request schema v1 remains scalar-only. Request schema v2 permits arrays of 1-64 bounded non-secret scalar values for provider-supported list/date iteration; the configured KIS parameter allowlist and total request JSON budget remain cumulative limits.

`import-isolate` independently re-verifies request/recipe identity and hash against its checked-in provider policy and dispatches through its existing isolated runtime:

- legacy HTTP recipe schema v1 remains available only through compatible provider profiles and request v1;
- generic HTTP recipe schema v3 requires a schema-v3 provider profile and supports the bounded transport/authentication/pagination/iteration/discovery envelope owned by `import-isolate`;
- Firecrawl recipe schema v2 uses only provider-authorized `firecrawl_search`, `firecrawl_scrape`, or `firecrawl_map` through the existing Firecrawl container boundary and request v1.

The checked-in generic HTTP template in `import-isolate` is disabled by default. KIS does not turn that template, or any commercial/licensed source, into execution authority merely because the transport class is supported; an enabled exact provider profile plus explicit KIS authorization and consumer recipe remain required.

Ordinary Work HR-002 remains unchanged. This external action is an explicit approval-gated connector path, not a new Work network capability.

## Result contract

KIS accepts only the strict result defined by `contracts/external-acquisition/result.schema.json`. The result must identify the exact project/profile/recipe/hash request and contain bounded provenance:

- provider and provider type;
- content class;
- artifact SHA-256 and byte count;
- provider-relative artifact path;
- provider implementation revision;
- container image digest;
- logical credential-reference names;
- successful state with no failure code.

Unexpected fields, mismatched request identity, malformed hashes, absolute/traversing/drive-qualified artifact paths, credential-value-shaped data, or unsuccessful state are rejected before caller exposure.

## Failure and compatibility rules

Unsupported settings schema, unregistered projects, unauthorized profiles/recipe namespaces/parameters, provider-policy path escape/unavailability, missing/duplicate/disabled provider profiles, provider-profile schema/hash drift, missing approval, recipe hash mismatch, missing provider project/script, provider process failure, and malformed provider results fail closed as structural/external-operation errors. They do not create a fourth Work hard rule.

The existing registered-GitHub virtual approval/dispatch contract remains independent and unchanged. Schema-bound `approved=true` is accepted only for explicitly registered virtual families; unrelated virtual operations cannot opt into that mechanism by adding an `approved` field.

## Commissioning

Repository verification proves authorization, normalization, approval handling, provider adapter behavior, registered-GitHub compatibility, strict result validation, and fail-closed cases. `import-isolate` independently verifies its registered boundary and full repository baseline.

Real Firecrawl commissioning additionally requires current `import-isolate` live containment evidence for the landed provider security fingerprint and any required operator-managed credential. Stale containment evidence or an unavailable runtime must not be represented as successful live commissioning.
