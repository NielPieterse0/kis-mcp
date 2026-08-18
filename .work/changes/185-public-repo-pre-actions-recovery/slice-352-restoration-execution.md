# Slice 352 — Exact-tree restoration execution evidence

- **Issue**: `#352`
- **Authority commit**: `1365d84de30360b880f95bc5c51101ddeab9006c`
- **Authority tree**: `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`
- **Current-main parent before restoration**: `3bd13309827affab06b194c054541f65af89f001`

## Method and governance

- Restoration is an ordinary additive commit on the Change 185 branch; no reset, force push, rebase of `main`, ref deletion, or history rewrite is used for landing.
- Commit `04d5cf894d69153277e8b7e2ba87803124b16fb7` expands Change 185 ownership to every path changed between current `main` and the selected baseline.
- The changed top-level path set is exactly `.work`, `AGENTS.md`, `contracts`, `docs`, `scripts`, `settings`, `SPEC.md`, `src`, and `tests`; all are covered by the claim.
- Provisional local commit `2506c111efd2ebbfc1bf1231828e8638bb8fa8f2` proved that an ordinary child commit can reproduce the authority tree exactly.
- Final publication will regenerate the exact-tree commit after this evidence checkpoint so the PR head itself has tree `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`.
- The active Change 185 record necessarily disappears from that final tree because it did not exist at the authority boundary; its evidence remains reachable in the parent history.

## Pre-publication ref preservation snapshot

- Remote heads: `44`; SHA-256 `7B70326BBB2CD91DF78ECB34442CEDC4E910A233AF95EA5208C664DDE6B5D63B`.
- Remote tag refs: `0`; SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- GitHub releases: `0`; SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- GitHub pull-request head refs: `226`; SHA-256 `361C8ECEDEB9EC8EBC312CCA9A8A8E5CF2BACCC7585BE7976B63CBB3325F4AFD`.
- Snapshot files are retained under `C:\Projects\.kis-mcp\temp\change185-*-before.txt` for post-merge comparison.

## Remaining gate

Publish exact head, run the restored verifier surface, review the full base-to-head change, merge only the verified PR head, compare refs/tags/releases, align local `main`, reconcile Work Management, and clean the change worktree.
