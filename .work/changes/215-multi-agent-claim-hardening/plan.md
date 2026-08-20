# Multi-Agent Claim Hardening Implementation Plan

**Goal:** Make governed-change admission atomic and collision-proof for #412.

**Architecture:** Harden both admission layers without creating a second authority model. `change-governance.py` serializes direct governed-change creation under a repository-scoped OS lock, re-reads scope/ref/worktree truth inside the critical section, reserves numeric identities permanently, and projects stale path ownership out of live collision truth. The existing coordinator reservation/work-packet path remains authoritative for orchestrated execution; extend its packet/worker contracts with generation-specific `run_id`, exact governed root/base/scope, lifecycle phase, optional Work Management/external provenance, predecessor lineage, and reassignment fencing while preserving stable packet/task identity.

**Tech stack:** Python stdlib, Git CLI through existing helpers, pytest, PowerShell wrapper.

## Constraints

- No network access from local governance.
- No permanent deletion or historical rename.
- Generated lock state remains under the KIS state root.
- Existing schema-v3/v4 records remain readable.
- Test behavior before implementation and preserve failure atomicity.

## Tasks

1. Add regressions for duplicate numeric prefixes from historical scopes, refs, and worktrees plus a deterministic concurrent creator race.
2. Add adversarial three-creator path-overlap diagnostics and stale-claim projection regressions.
3. Complete repository-scoped OS admission locking, re-read state inside the critical section, and optional execution-owner evidence without breaking schema-v3/v4 scopes.
4. Extend coordinator packet/worker tests first for stable task/packet identity, generation-specific run identity, exact governed envelope fields, bounded provenance, and predecessor lineage.
5. Add reassignment tests proving assignment generation increments, prior run/key is revoked for mutation, and the new run preserves packet/task lineage.
6. Implement the bounded planner/worker contract and schema updates required by those tests; keep Work authorization/lease-fence authority unchanged and fail closed on mismatches.
7. Update canonical governance/operator docs for atomic admission and task/run envelope semantics.
8. Run focused tests, Ruff, governance check, required reviews, then exact-head Actions/merge/cleanup.
