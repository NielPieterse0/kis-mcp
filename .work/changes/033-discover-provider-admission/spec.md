# Change Specification: Discover Provider Admission

- **Change ID**: `033-discover-provider-admission`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Add bounded, deterministic provider-candidate evidence and governed admission handoffs without installation, activation, credentials, provider execution, or network access.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, and the operator-approved closed-system principles.
- Owned implementation: `src/kis_mcp/discover/provider_admission/**`.
- Owned tests: `tests/discover/provider_admission/**`.
- Owned schemas: `contracts/discover/provider-candidate.schema.json` and `contracts/discover/provider-admission-request.schema.json`.
- Owned documentation: `docs/development/discover-provider-admission/**`.
- Public registration and shared server composition are reserved for the later final-integration change.

## Requirements

- **REQ-001**: Accept one explicitly selected, repository-relative JSON provider-candidate manifest beneath one explicitly selected project and read it only through Discover `ReadAuthority`.
- **REQ-002**: Require a strict versioned manifest with deterministic identity, provider type, revision, license, maintainer, capabilities, effects, authentication, installation, compatibility, readiness, and evidence declarations. Unknown keys and invalid types fail structurally.
- **REQ-003**: Produce normalized candidate evidence with a SHA-256 content digest, stable ordering, bounded collections, explicit omissions, diagnostics, unknowns, confidence, and a deterministic fingerprint.
- **REQ-004**: Classify security, licensing, compatibility, readiness, overlap, and operational risks without inventing approval. Network, write, execution, credential, unresolved-license, and missing-conformance evidence must remain visible.
- **REQ-005**: Produce a Govern admission request whose decision is always pending and which contains requested capabilities/effects, unresolved risks, required evidence, and provenance. Discover must not approve or reject admission.
- **REQ-006**: Produce a non-executing Work conformance plan containing bounded declarative validation steps only. No shell command, arbitrary executable, provider invocation, package installation, or activation is allowed.
- **REQ-007**: Preserve closed-system constraints: no network access, no external registry lookup, no credentials, no package manager, no provider runtime loading, and no policy/settings mutation.

## Acceptance

1. **Given** a valid checked-in provider candidate manifest, **when** it is inspected, **then** normalized evidence, risk findings, a pending Govern request, and a non-executing Work plan are deterministic and schema-valid.
2. **Given** network, write, execution, or credential effects, **when** admission evidence is produced, **then** each effect appears as an unresolved risk and is never silently approved.
3. **Given** unknown or missing license, compatibility, readiness, or conformance evidence, **when** inspection completes, **then** the gap appears explicitly in unknowns and required evidence.
4. **Given** an absolute, escaping, symlinked, oversized, malformed, unsupported-version, or unknown-key manifest, **when** inspection is attempted, **then** it fails safely with a Discover structural error.
5. **Given** bounded collection limits, **when** the manifest exceeds them, **then** output is deterministically truncated with exact omission counts and reasons.
6. **Given** identical manifest bytes and budgets, **when** inspection repeats, **then** ordering, digest, substantive output, and fingerprint are identical.

## Risks and recovery

- Risk: a manifest can make unsupported self-claims.
- Mitigation: all fields are candidate-declared evidence with provenance; readiness and compatibility remain evidence-backed findings rather than trusted facts.
- Risk: broad admission semantics could become a second policy authority.
- Mitigation: Discover only assembles a pending Govern request and declarative Work plan; it does not decide, configure, install, or activate.
- Recovery: revert the implementation commit. No persistent state, credentials, provider installation, policy change, or external effect is introduced.

## Out of scope

- Provider installation, activation, runtime health checks, credentials, package resolution, or network verification.
- Govern approval/rejection or policy mutation.
- Work execution or command generation.
- Public FastMCP registration and shared server composition.
- Implicit scanning for candidate manifests.
