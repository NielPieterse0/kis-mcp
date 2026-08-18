# Post Actions Reconstruction Implementation Plan

**Goal:** Recover the intended post-outage product state without replaying obsolete workaround architecture, while improving the verification lifecycle before repeated reconstruction merges.

## Serial delivery model

### Slice 1 — classify + optimize workflow

- Build the authoritative post-boundary register from Change 185 evidence, Git/PR history, Project records, archived branches, and host state.
- Classify each item: `reimplement`, `reassess`, `harvest-only`, `superseded`, `retire`, or `future`.
- Trace dependencies and identify the minimum safe reconstruction order.
- Audit PR #329 Hyper-V, #336 VirtualBox, #339 local Windows runner and all dependent workaround-only changes.
- Inventory host installations/state created for those paths without removing anything until ownership/use is proven.
- Audit canonical change workflow ordering and eliminate evidence-invalidating sequencing where safely possible.
- Encode workflow/tooling/tests changes before using the optimized lifecycle for subsequent slices.

### Slice 2 — retire workaround stack

- Apply approved retirement/harvest decisions.
- Clean confirmed-unused host software/artifacts/state safely and record evidence.
- Reconcile obsolete Project/roadmap direction.

### Slices 3+ — reconstruct retained value

- One fresh child change per bounded outcome or tightly coupled dependency group.
- Start each from current merged `main`.
- Reuse preserved implementation/tests selectively; do not replay old merge commits.
- Complete each child before creating the next dependent child.

## Evidence-efficient child lifecycle

Target lifecycle for each later slice, subject to Slice 1 validation:

1. Implement and run focused development checks.
2. Finalize all code and evidence-bearing change documentation on the branch.
3. Run the governed pre-publication/change check and freeze the candidate head.
4. Publish/update the PR without further branch mutation.
5. Run required specialist reviews and canonical repository verification against the same exact head; parallelize independent evidence where tooling safely permits.
6. Resolve findings only by creating a new final head; if that occurs, previous head-bound evidence is invalid and is rerun once on the new head.
7. Merge only when exact-head evidence is complete.
8. Perform post-merge alignment, Work reconciliation and safe cleanup without metadata-only source commits.

This lifecycle explicitly avoids verify → change closeout metadata → review → change metadata → reverify loops.

## Final programme reconciliation

- Re-author the MCP architectural programme after retained functional foundations are reconstructed.
- Verify the final runtime source against merged `main`.
- Reconcile Project records into intentional active/future/retired states.
- Preserve historical evidence without allowing obsolete architecture to remain current authority.
