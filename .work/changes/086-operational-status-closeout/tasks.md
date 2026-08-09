# Tasks: Operational Status Closeout

- [x] Confirm authority, development level, and non-overlapping scope.
- [x] Add RED tests for Supabase registered-project live verification.
- [x] Add RED tests for remote MCP health status evidence.
- [x] Implement Supabase process-local commissioning state and success marking.
- [x] Implement selected-instance process context and ready-state health override.
- [x] Run focused tests: 31 passed, exit 0.
- [x] Run `pwsh -File scripts/change-workflow.ps1 check`.
- [x] Review final diff against spec and policy boundaries; specialist backends unavailable, direct review completed.
- [x] Run canonical `pwsh -File scripts/verify.ps1`: exit 0.
- [x] Record implementation and verification closeout evidence.
- [ ] Commit the change and merge locally to `main`.
- [ ] Safely clean change 086 from primary `main`.
- [ ] Restart only `kis-op` and verify both corrected statuses through the actual tool.
