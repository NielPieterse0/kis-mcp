# Public Repo Pre Actions Recovery Implementation Plan

> Execute one child issue at a time and keep `scope.json` current for the paths owned by that slice.

**Goal:** Publish safely, restore the exact pre-Actions repository tree, then inventory later work without reimplementing it.

## Programme sequence

1. **#349 — Publication safety audit**
   - Audit current tree and relevant Git history for publication-sensitive content.
   - Produce explicit GO/NO-GO and bounded remediation requirements.
2. **#350 — Public transition**
   - Requires #349 GO.
   - Configure the approved minimum-exposure public posture and change visibility.
   - Verify critical repository settings after publication.
3. **#351 — Exact recovery boundary**
   - Establish the immutable commit SHA and tree SHA immediately before Actions availability was lost.
   - Use Git/GitHub evidence; do not infer from memory.
4. **#352 — Exact baseline restoration**
   - Requires #351.
   - Restore the selected tree without permanently deleting later history.
   - Verify exact tree equality after landing.
5. **#353 — Post-boundary value inventory**
   - Requires #351.
   - Inventory and classify later work only.
   - Recommend later reimplementation order; implement nothing from the inventory.
