# State Ownership Namespace Implementation Plan

**Goal:** Deliver #278's reusable state-ownership and namespace foundation without migrating consumers.

**Architecture:** Add an isolated `kis_mcp.state` module with immutable ownership metadata, deterministic source identities, typed request/result/error contracts, namespace resolution, and collision checks. Publish equivalent JSON contracts/schemas. Existing consumers remain unchanged until #279.

**Constraints**

- Stay inside `scope.json`.
- Preserve `C:\Projects\.kis-mcp` and the existing quarantine/auth compatibility boundaries.
- Do not touch #270, #241/#251, existing persistence consumers, secrets/auth, quarantine, or recovery implementations.
- Worktree identity derivation is pure path normalization + hashing; no Git lookup or process-source changes.

## Execution

1. **Contract tests first**
   - Define all ten ownership classes and identity requirements.
   - Cover two projects, linked worktrees, runtime isolation, stale/missing identities, collisions, Windows boundaries, compatibility anchors, wire schemas, diagnostics, and immutability.
2. **Resolver implementation**
   - Implement ownership specs, source IDs, typed errors, canonical serialization, expected-identity checks, deterministic namespaces, and overlap rejection.
3. **Machine/public contract**
   - Publish ownership, identity/canonicalization, fingerprint, request/result/error, and compatibility contracts under `contracts/state/`.
4. **Documentation**
   - Document namespace grammar, no-migration boundary, and #241/#251 consumption rule.
5. **Closeout**
   - Run focused tests, `change-workflow.ps1 check`, exact-source specialist reviews, PR exact-head canonical CI, governed merge, #278 reconciliation, and cleanup.
