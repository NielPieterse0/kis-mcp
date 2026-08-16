# Change Specification: State Ownership Namespace

- **Change ID**: `163-state-ownership-namespace`
- **Status**: Approved by issue #278
- **Complexity**: `medium`
- **Risk Triggers**: `architecture_boundary`, `persistent_state`, `public_contract`

## Outcome

Implement #278's centrally partitioned KIS state-ownership contract without migrating any existing consumer.

## Authority and scope

Authority: `AGENTS.md`, trust/platform specs, #278/#277/#272, and the #265 source-isolation handoff. Owned paths are `src/kis_mcp/state/**`, `contracts/state/**`, `tests/state/**`, this change record, and `docs/STATE-OWNERSHIP-MODULE-PRODUCT-SPEC.md`. No shared paths. Existing consumers, #270, #241/#251 implementation, auth/secrets, quarantine, provider/Discover/queue persistence, and recovery writers/readers are excluded.

## Requirements

1. Define the ten approved ownership classes and exact required identity keys.
2. Publish deterministic namespaces rooted at `C:\Projects\.kis-mcp`, with generic project/source/runtime state structurally disjoint from specialized state.
3. Provide deterministic linked-worktree and governed-change source IDs without Git lookup.
4. Reject missing, extra, stale, malformed, escaping, colliding, or overlapping identity/namespace input with closed typed errors and bounded diagnostics.
5. Publish strict ownership, identity/canonicalization, fingerprint, request/result/error, and compatibility machine contracts.
6. Preserve the existing quarantine, vault/secrets, GitHub CLI auth, safe global installation/cache, and repo-local recovery compatibility rules.
7. Expose one reusable contract for later #241/#251 consumption; do not implement consumer durability here.
8. Do not migrate, rewrite, delete, commission, or create existing runtime state.

## Acceptance

- Equivalent canonical inputs resolve identically; different project/source/runtime identities do not collide.
- Global/scoped ownership cannot silently widen or narrow identity scope.
- Worktree normalization covers Windows boundary, prefix, traversal, and linked-worktree cases.
- All resolved paths remain under the approved state root; quarantine remains exact.
- Checked-in contracts match the Python projection and public serializers validate against their schemas.
- Tests cover two projects, stale/missing identities, overlap/collision, diagnostics bounds, serialization, immutability, and compatibility anchors.
- Only declared #278 paths change.

## Recovery / out of scope

Rollback is removal/revert of this isolated code and documentation because #278 performs no migration or state write. #279 migration, #280 commissioning, #281 GC/diagnostics, #251 lifecycle implementation, Work Management, credential relocation, and existing persistence implementation remain out of scope.
