# Change Specification: Registered External Acquisition

- **Change ID**: `144-registered-external-acquisition`
- **Source**: issue #214 / `SPEC-144`
- **Status**: Active

## Outcome

Authorize registered KIS projects to invoke approved `import-isolate` acquisition profiles by immutable consumer recipe identity and SHA-256, without exposing arbitrary URLs or widening ordinary Work HR-002 authority.

## Boundary

- KIS owns registered-project authorization, approval, recipe location/hash verification, request bounding, and receipt validation.
- `import-isolate` owns provider/network containment and recipe-to-provider dispatch. Companion issue: `NielPieterse0/import-isolate#2`.
- Consumer repositories own immutable acquisition recipe JSON and may only narrow provider privileges.
- Project Tasks issue #215 / PR #221 is unrelated and is excluded from this change.

## Requirements

- **REQ-001**: Strict schema-versioned JSON settings map registered project IDs to permitted provider profiles, consumer recipe directories/namespaces, allowed parameter keys, and approval requirements.
- **REQ-002**: `kis_acquire_registered_evidence` is discoverable only as an approval-gated external virtual operation with fixed project/profile/recipe/hash/parameters/approved fields.
- **REQ-003**: KIS resolves the project from the central registry, derives the recipe path from configured project-relative authority, verifies containment and exact SHA-256, and never accepts a caller URL or raw recipe path.
- **REQ-004**: KIS sends only the normalized acquisition request plus the verified immutable recipe to the registered `import-isolate` host boundary; credential values never cross this interface.
- **REQ-005**: The provider result is strictly validated for project/profile/recipe/hash identity, artifact hash/size/path, implementation/image identity, credential-reference names, and success state before caller exposure.
- **REQ-006**: Existing registered-GitHub virtual dispatch and ordinary Work HR-002 behavior remain unchanged.
- **REQ-007**: Unsupported schemas, unregistered projects, unauthorized profiles/recipes/parameters, missing approval, hash mismatch, provider absence, malformed results, and path escape fail closed.

## Acceptance

1. An authorized registered project with `approved=true`, an allowed profile, immutable recipe identity/hash, and bounded parameters reaches only the configured `import-isolate` dispatcher.
2. An unauthorized or malformed request fails before provider execution.
3. The caller cannot submit a URL, provider tool, recipe path, secret value, or unrestricted network argument.
4. Firecrawl remains recipe-bound: the provider side resolves only the recipe-authorized `search`, `scrape`, or `map` operation under `firecrawl-web` policy.
5. Existing registered-GitHub virtual-operation tests remain green.
6. Final closeout requires exact-head KIS CI and provider-side allowed/denied commissioning evidence; unavailable commissioning is not represented as success.
