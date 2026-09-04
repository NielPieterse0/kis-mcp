# Historical Scope Compatibility Implementation Plan

**Goal:** Restore read compatibility for pre-current schema-v4 change records while keeping current creation/check semantics strict.

## Approach

1. Add RED tests for known historical shape differences and strict current parsing.
2. Keep `ChangeClaim.from_mapping` strict by default.
3. Add a file-load compatibility projection used only for historical inventory paths.
4. Make current-change `check` resolve and strictly parse only its exact active scope instead of parsing all repository history.
5. Verify against the real commodity #289 checkout plus the full change-governance test module.

## Recovery

Revert this change to restore the previous strict historical reader. No repository scope files are mutated by the compatibility projection itself.
