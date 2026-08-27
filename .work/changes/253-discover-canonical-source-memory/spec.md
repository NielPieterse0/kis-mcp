# Change Specification: Discover Canonical Source Memory

- **Change ID**: `253-discover-canonical-source-memory`
- **Status**: Active
- **Complexity**: medium
- **Risk Triggers**: migration, persistent_state

## Outcome
Route Discover persisted generations through the canonical source-scoped KIS state namespace with identity-safe legacy compatibility.

## Authority and scope
- Authoritative sources: `AGENTS.md`, `SPEC.md`, canonical state ownership contract/resolver, Work #554.
- Owned paths: `src/kis_mcp/discover/intelligence.py`, `tests/discover/**`, `SPEC.md`, this change record.
- Shared paths: none.
- Dependencies: canonical state resolver already landed; Work #552 canonical queue migration is complete.

## Requirements
- **REQ-001:** Production Discover persistence uses the existing canonical state resolver, not a parallel namespace model.
- **REQ-002:** Derived Discover atlases use source-scoped `reconstructible-cache` ownership with canonical project/source identity.
- **REQ-003:** Full existing applicability fingerprints continue to gate reuse.
- **REQ-004:** Legacy Discover generations are retained; only exact identity-safe generations may migrate.
- **REQ-005:** Cross-project and cross-worktree generation reuse is impossible.

## Acceptance
1. Registered repositories and linked worktrees resolve distinct canonical source namespaces.
2. Matching legacy generations migrate without deletion; stale/mismatched generations are retained and rebuilt.
3. Existing corruption recovery, provider/settings/Git invalidation, and bounded EvidenceStore behavior remain covered.
4. Focused verification and governed scope checks pass before publication.

## Risks and recovery
- Risk: trusting legacy state under the wrong source identity. Recovery: require the complete current applicability fingerprint before migration.
- Risk: canonical state corruption. Recovery: retain corrupt pointer and rebuild under existing configured handling.

## Out of scope
- Other #548 state consumers owned by later slices #555/#556.
- State ownership diagnostics and cleanup owned by #550.
