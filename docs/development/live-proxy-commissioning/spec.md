# Change Specification: Live Proxy Commissioning

- **Change ID**: `004-live-proxy-commissioning`
- **Status**: Implemented; live commissioning blocked
- **Risk Profile**: rigorous

## Outcome

Prove the installed Desktop Commander `0.2.46` and the real `kis-mcp` stdio gateway work end to end without modifying policy or production gateway behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `settings/kis-mcp.settings.json`, approved operator design in this change.
- Owned paths: commissioning change artifacts, commissioning documentation, one PowerShell entry point, one integration test, and one test-support module.
- Shared paths: none.
- Excluded paths: all `src/kis_mcp/**`, runtime settings, `docs/OPERATIONS.md`, and files claimed by changes `002` and `003`.
- Dependencies: changes `002-modularity-contracts` and `003-quarantine-integrity` are integrated into the current `origin/main` baseline; no branch dependency remains.
- Integration owner: none.

## Requirements

- **REQ-001**: Start the real gateway through `C:\Projects\.kis-mcp\python-env\Scripts\python.exe` and stdio.
- **REQ-002**: Confirm provider tools are imported, `give_feedback_to_desktop_commander` is absent, and `read_file.isUrl` is absent.
- **REQ-003**: Prove a real local read and in-boundary write round trip.
- **REQ-004**: Prove an out-of-boundary write is rejected as `HR-001_WRITE_OUTSIDE_PROJECTS` before provider forwarding.
- **REQ-005**: Confirm the pinned provider exposes no direct delete tool, then prove the gateway-owned quarantine and restore path works end to end.
- **REQ-006**: Prove a harmless local process command remains usable.
- **REQ-007**: Keep all generated content under `C:\Projects\.kis-mcp\temp\commissioning` and preserve provider stderr evidence.
- **REQ-008**: Do not update implementation-status claims from this branch.
- **REQ-009**: Validate provider policy-state integrity after shutdown and restore the exact pre-run snapshot atomically before reporting a corruption failure.

## Acceptance

1. **Given** the pinned provider installation, **When** the commissioning script runs, **Then** the gateway starts and lists the expected local provider surface.
2. **Given** a unique commissioning workspace, **When** read, write, block, quarantine, restore, and process calls run, **Then** each expected result is observed through the real proxy.
3. **Given** a failed stage, **When** the harness exits, **Then** it returns nonzero and preserves a bounded stderr log.
4. **Given** normal repository verification, **When** the live flag is absent, **Then** the live integration test is skipped and all existing tests remain green.

## Commissioning result

The functional proxy stages pass on the integrated `origin/main` baseline: live provider startup and surface import, hidden feedback and URL mode, local read, in-boundary write, HR-001 rejection, gateway quarantine and restoration, and local process execution.

The slice is not commissioned because the provider shutdown path repeatedly leaves `C:\Projects\.kis-mcp\.claude-server-commander\config.json` empty. The harness detects this as `PROVIDER_STATE_INTEGRITY`, atomically restores the pre-run valid snapshot, and exits nonzero. Production lifecycle remediation is deferred to a dedicated follow-up because this commissioning-only slice excludes production gateway changes.

## Risks and recovery

- Risk: nested stdio startup may expose provider or FastMCP compatibility defects.
- Recovery: the branch changes only tests, scripts, and documentation; discard or revert the branch. Temporary files remain inside the approved state root and quarantined content is restored during the test.
- Risk: the provider lifecycle defect requires a production change outside this slice.
- Recovery: keep draft PR `#3` unmerged until a dedicated remediation is integrated and the live commissioning script exits successfully without restoring provider state.

## Out of scope

- Production gateway fixes.
- Provider adapter or policy changes.
- Runtime settings or implementation-status changes.
- Permanent quarantine disposal.
