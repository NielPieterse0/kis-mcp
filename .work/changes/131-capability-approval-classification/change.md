# Change: Capability Approval Classification

- **Change ID**: `131-capability-approval-classification`
- **Work record**: `SPEC-131` / issue #191
- **Defect resolved**: `BUG-186` / issue #186
- **Risk Profile**: lean

## Outcome

Make required Work Management read/validation gates invokable through the advertised capability dispatcher by deriving approval requirements from actual tool semantics rather than operation-name substring matches.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Runtime-discovered operations do not invent approval requirements from operation-name substrings.
- FastMCP-native runtime tools expose their real `parameters` JSON schema through capability discovery.
- Explicitly registered approval-sensitive workflows retain their descriptor-level approval contract.
- `project_management_merge_readiness` is classified as invokable through `execute_change_action` after the landed runtime is restarted.

## Implementation and verification

- Implementation notes: removed name-substring approval inference and added FastMCP `parameters` schema extraction for runtime-surface augmentation; registered virtual GitHub approval descriptors are unchanged.
- Focused checks: approval and schema regressions both failed before their respective fixes; runtime surface + execution + merge-queue capability tests pass after the fixes.
- Review findings: initial NVIDIA API-contract review found no findings; final NVIDIA retry returned 502 and Codex CLI failed independently after the schema addition, so the final exact diff was manually checked for preservation of static approval descriptors and schema fallback ordering with no finding.
- Residual risk: live dispatcher commissioning requires the landed runtime revision; current running instances still execute the pre-fix revision until restart.
- Closeout state: implementation complete; review, exact-head CI, landing, and live commissioning pending.
