# Change Specification: Generic Acquisition Envelope

- **Change ID**: `175-generic-acquisition-envelope`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Complete the KIS authorization side of the generic governed external-acquisition envelope for Commodity using the landed `import-isolate` v3 profile contract without widening ordinary Work network authority.

## Authority and scope

- Authoritative sources: repository `AGENTS.md`; `docs/TRUST-MODEL.md` HR-002; issue `kis-mcp#258`; Commodity `AGENTS.md`, `docs/data-manifest.md`, `config/data_sources.json`, and `docs/THIRD_PARTY.md`; landed `import-isolate#13` contract at main tree `43951f329c14c728edb80d9ae0dc9e568e0f76a9`, especially `policy/provider-profiles.schema.json`, `contracts/acquisition-request.schema.json`, and `contracts/acquisition-recipe.schema.json`.
- Owned paths: the paths declared in `scope.json` only.
- Shared paths: none.
- Excluded paths: Work Management exact-target resolution, merge-queue authentication, other active changes, Commodity adapter implementation, and `import-isolate` implementation.
- Dependencies: `import-isolate#13` is already merged and verified; its v3 provider-profile and request-v2 contracts are the provider-side dependency.
- Integration owner: this change owns only the KIS authorization/contract side of issue #258.

## Requirements

- **REQ-001 — Exact shared profile binding:** KIS authorization must bind a project/profile permission to the exact canonical provider-profile record used by `import-isolate`, using provider-owned profile schema version plus canonical SHA-256 identity rather than duplicating host/auth/limit semantics in a second KIS registry.
- **REQ-002 — Provider policy authority:** The provider policy location is fixed by KIS provider configuration, resolved inside the registered `import-isolate` project, bounded in size, and fail-closed on missing/duplicate profile identity, malformed policy, schema mismatch, or profile-hash mismatch.
- **REQ-003 — Request v2 compatibility:** A profile authorization may declaratively select provider request schema v1 or v2. V2 permits bounded arrays of non-secret scalar parameters for generic date/list iteration while preserving existing scalar limits and denying secret-like parameter names.
- **REQ-004 — Configuration-only extensibility:** A normal new Commodity source must require only a provider profile/configuration record, a KIS authorization/configuration entry, and a consumer recipe/adapter. Adding an already-supported source shape must not require another KIS core code change.
- **REQ-005 — Backward compatibility:** Existing Firecrawl and legacy public HTTP authorizations remain valid through explicit v1 request bindings and exact current provider-profile identities.
- **REQ-006 — Deny by default:** Unknown profiles, new/changed provider profile semantics, unauthorized parameters, unregistered projects, recipe namespace/hash mismatch, missing approval, or malformed provider results must fail before external execution. Ordinary Work HR-002 behavior remains unchanged.
- **REQ-007 — Contract reconciliation:** The durable external-acquisition module specification and machine-readable KIS settings schema must describe the shared profile-binding/request-version contract without duplicating provider execution semantics owned by `import-isolate`.

## Acceptance

1. **Given** a KIS authorization whose schema version/hash matches the exact provider profile, **when** an approved immutable recipe is requested, **then** KIS delegates only the configured request version and bounded parameters.
2. **Given** a v2 authorization, **when** bounded scalar arrays are supplied for an allowed parameter, **then** KIS emits request schema v2 and preserves the bounded list for `import-isolate` iteration.
3. **Given** an unauthorized, missing, duplicate, modified, disabled, or schema-mismatched provider profile, **when** acquisition is requested, **then** KIS fails before invoking the provider.
4. **Given** a secret-like parameter name/value channel or an oversized/unsupported scalar/list, **when** normalization runs, **then** KIS fails closed without provider invocation.
5. **Given** current Firecrawl/public HTTP configuration, **when** settings and focused acquisition tests run, **then** existing v1 behavior remains compatible.
6. **Given** the landed `import-isolate#13` generic executor, **when** its already-verified compatibility fixtures are reconciled with KIS request-v2/profile binding, **then** the combined architecture covers the issue #258 source classes without granting commercial/licensed authority.

## Risks and recovery

- Risk: profile drift could silently widen external authority. Mitigation: KIS binds authorization to the canonical profile record hash and schema version before provider execution.
- Risk: request-v2 arrays could create an unbounded fan-out channel. Mitigation: fixed item count, scalar type/string size limits, configured allowed keys, and provider-side request/request-byte/resource ceilings remain cumulative.
- Risk: cross-repository contract drift. Mitigation: version/hash mismatch fails closed and requires an explicit configuration reconciliation.
- Recovery: revert this bounded change or restore prior authorization entries; no persistent data migration or destructive transition is involved.

## Out of scope

- Implementing or modifying `import-isolate` transport/executor behavior already delivered by #13.
- Adding source-specific Commodity adapters or enabling/licensing commercial sources.
- Changing HR-001/HR-002/HR-003 semantics, Work networking, Work Management #269, merge-queue #237, or unrelated active lanes.
