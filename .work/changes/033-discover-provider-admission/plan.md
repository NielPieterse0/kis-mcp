# Discover Provider Admission Implementation Plan

**Goal:** Convert one explicitly selected checked-in JSON provider manifest into bounded candidate evidence, unresolved risk findings, a pending Govern request, and a non-executing Work conformance plan.

**Architecture:** A self-contained `discover.provider_admission` package owns immutable contracts and one service. The service uses existing `ReadAuthority`, strict JSON-object validation, deterministic normalization, bounded collections, and content/output fingerprints. It has no runtime, installer, network, credential, policy, or server dependency.

## Tasks

### Task 1: Contracts and schemas
- Create immutable request, budget, candidate, risk, admission-request, conformance-step, omissions, and response contracts.
- Add strict JSON schemas for candidate evidence and Govern admission request.
- Add serialization/schema tests before implementation.

### Task 2: Strict manifest loading and normalization
- Read one explicit repository-relative manifest through `ReadAuthority`.
- Enforce exact keys, version 1, types, enum values, and bounded arrays.
- Normalize ordering, compute raw-content digest, omissions, diagnostics, unknowns, confidence, and response fingerprint.
- Add red/green tests for valid, malformed, unsupported, unknown-key, unsafe-path, oversized, truncation, and determinism cases.

### Task 3: Risk, Govern, and Work handoffs
- Classify network, write, execute, credential, license, compatibility, readiness, overlap, and conformance gaps.
- Produce decision `pending_govern` only.
- Produce declarative, non-executing Work steps with `execution_available=false` and no command/executable fields.
- Add red/green tests proving no silent approval or execution capability.

### Task 4: Documentation, verification, and integration
- Document manifest format, trust boundary, provenance, limitations, and integration seam.
- Run provider-admission tests, Discover regression tests, scope/whitespace checks, and serialized full repository verification.
- Review for schema compatibility, security, modularity, simplicity, and forbidden dependencies; then commit, PR, merge, close, and clean safely.
