# Discover Project Catalog Implementation Plan

**Goal:** Build an internal bounded catalog for an explicit set of selected local projects and detect narrow static cross-project relationships without implicit root scanning.

**Architecture:** A self-contained `discover.project_catalog` package owns immutable request/response contracts and one service. The service resolves only caller-selected projects through `ReadAuthority`, snapshots only those projects, reads a fixed manifest set, parses JSON/TOML/XML in-process, normalizes selected-target relationships, and returns bounded deterministic evidence.

## Tasks

### Task 1: Contracts and schemas
- Add immutable budget, request, project, manifest, relationship, unknown, omission, and response contracts.
- Add strict Draft 2020-12 request/response schemas.
- Add serialization, duplicate-selection, budget, and schema tests before production code.

### Task 2: Explicit project selection and manifest inventory
- Resolve each selected project through `ReadAuthority`.
- Reject duplicate canonical projects.
- Snapshot only selected roots and inventory only `package.json`, `pyproject.toml`, and root-level `*.csproj` manifests under configured bounds.
- Add tests proving unselected siblings are not enumerated or read.

### Task 3: Static relationship parsers
- Parse npm `file:`/`link:` dependency values.
- Parse supported Python path-dependency tables from `pyproject.toml`.
- Parse .NET `ProjectReference` elements.
- Add explicit nested-selection relationships.
- Resolve targets only against the canonical selected-project map; record unselected/unresolved targets as unknowns without scanning them.

### Task 4: Bounds, determinism, and hardening
- Apply project, manifest, relationship, and unknown budgets with exact omissions.
- Normalize ordering, provenance, confidence, truncation, and fingerprint.
- Add malformed-manifest, escaping-reference, unsafe-path, deterministic-repeat, and forbidden-dependency tests.

### Task 5: Documentation and integration
- Document the explicit-selection trust boundary, supported relationships, unknown behavior, and final-integration seam.
- Run focused tests, full Discover regressions, change scope/whitespace checks, and serialized full repository verification.
- Review security, modularity, simplicity, schemas, and no-implicit-scan guarantees; commit, PR, merge, close, and clean safely.
