# Tasks

## Completed in this held slice

- [x] Create and register the isolated branch and worktree.
- [x] Record and obtain operator decisions for HR1-07, HR2-06, and HR3-07.
- [x] Narrow HR1-07 and implement the approved shared command-resolver corrections.
- [x] Freeze pinned Context7 `3.2.5` and Serena `1.6.1` identities and contracts.
- [x] Implement independent Context7 and Serena settings, adapters, descriptors, and effect resolution.
- [x] Add the Tools-module composition seam and contained mount failure behavior.
- [x] Implement scan-gated, offline-capable installers under `C:\Projects\.kis-mcp`.
- [x] Record clean operator scans for the Context7 acquisition and Serena wheelhouse.
- [x] Install Context7 at `C:\Projects\.kis-mcp\context7` without executing it.
- [x] Build Serena from the scanned wheelhouse, scan the complete candidate with Defender, and install it at `C:\Projects\.kis-mcp\serena` without executing it.
- [x] Verify both installed descriptors report `ready`.
- [x] Run focused verification: 71 tests passed.
- [x] Run `scripts/verify.ps1`: complete repository verification passed.
- [x] Preserve prior and failed installation artifacts; no permanent deletion was used.
- [x] Document the exact hold point and close the governance claim.

## Deferred until server modularity work is complete

- [ ] Refactor and reassess the full `server.py` composition boundary.
- [ ] Reconcile this branch onto the resulting modular server composition API.
- [ ] Run live Context7 and Serena MCP contract/smoke verification.
- [ ] Complete HR3 restoration and post-quarantine Serena metadata-consistency evidence.
- [ ] Review the rebased final diff and all activation conditions.
- [ ] Push, raise a PR, review the exact PR head, and merge only if safe.
- [ ] Remove the worktree and branch only after successful integration; do not clean them while this change is held.
