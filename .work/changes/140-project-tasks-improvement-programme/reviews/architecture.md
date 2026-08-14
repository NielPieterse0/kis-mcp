# Architecture review — change 140

- Review type: `architecture`
- Implementation reviewed through integrated code head: `55ade2511eff36cfa94e74a923bcb585d8cf5a4f`
- Result: **PASS after corrections**

## Findings and disposition

1. **Control Center originally reached the board bridge from `ControlCenterSnapshot.to_dict()`.** That hid a Work Management dependency inside serialization. The dependency was moved to provider composition: `_WorkBoardSnapshotService` explicitly injects the latest derived projection and `ControlCenterSnapshot` owns a normal `work_board` field. **Resolved.**
2. **Work Management package boundary must remain below FastMCP/provider/workflow composition.** Architecture tests now admit exactly the new core modules while retaining the original forbidden-import prefixes. **Resolved / guarded.**
3. **Recovery-capsule change 136 overlapped conceptually with state/recovery but not with change-140 implementation files.** After PR #222 landed, change 140 was integrated using a two-parent merge commit with the exact landed PR-222 blobs overlaid and no overlapping implementation file. **Resolved.**
4. **Board projection must not become a second authority.** It is derived from `ProjectInventory`, has explicit freshness/completeness metadata, is held only in process memory, and is unavailable until an authoritative board read occurs. **Confirmed.**
5. **Runtime generation evidence must not depend on the recovery capsule or widen project identity authority.** It compares the serving process's import-time Git/config generation with live checked-in state and validates the existing launcher lifecycle evidence. **Confirmed.**

## Architecture invariants preserved

- `.work`, Git/GitHub, configured Work Management backend, and provider-native revisions remain authoritative.
- No TaskPlanner persistence or duplicate task log is added.
- No new Work policy decision is introduced; exactly HR-001/HR-002/HR-003 remain closed.
- Control Center stays read-only.
- Change 140 does not modify EvidenceStore, project registry identity, or repo-local recovery capsule implementation.
