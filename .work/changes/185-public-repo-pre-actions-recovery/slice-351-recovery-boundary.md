# Slice #351 — Exact pre-Actions recovery boundary

Selected recovery authority:

- Commit: `1365d84de30360b880f95bc5c51101ddeab9006c`
- Tree: `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`
- Commit subject: `Merge pull request #319 from NielPieterse0/change/170-workflow-import-cycle`
- Commit time: `2026-08-16T13:20:46+02:00`

## Evidence chain

1. GitHub Canonical Verification run `31946564491` (run 203) completed successfully on `2026-08-16T12:18:02Z` for PR #321 / branch `change/174-skills-mcp-resources`.
2. The immediately following Canonical Verification run `31947054010` (run 204) began at `2026-08-16T12:26:18Z` and failed at `12:26:20Z`; its only job, `Verify exact head`, had `runner_id=0` and an empty runner name, evidence that hosted execution did not allocate a runner.
3. PR #321 records its immutable base SHA as `1365d84de30360b880f95bc5c51101ddeab9006c` and its change record records the same upstream SHA plus tree `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`.
4. First-parent `main` history shows no mainline commit between the successful and first failed Actions runs. The next mainline merges occurred at `2026-08-16T16:07+02:00`, after the loss window. Therefore the default-branch state throughout the success-to-failure transition was exactly `1365d84...` / tree `443a774...`.
5. Issue #331, created `2026-08-16T18:28:37Z`, explicitly establishes the Actions-independent canonical-verification replacement because GitHub Actions was unavailable. Issue #338 later explicitly makes local Windows execution primary while Actions is unavailable. These records distinguish the selected pre-loss baseline from later compensating/replacement work.

## Resolution of alternatives

Later commits on August 16 are not valid boundary candidates: they landed after the observed success-to-runner-unavailable transition. Earlier commits are superseded by `1365d84...`, which was already the exact PR base/default-branch truth at the transition.

No repository mutation was performed in this slice.
