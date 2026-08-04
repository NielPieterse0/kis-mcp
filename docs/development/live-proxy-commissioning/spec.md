# Change Specification: Live Proxy Commissioning

- **Change ID**: `004-live-proxy-commissioning`
- **Status**: Implemented and commissioned
- **Risk Profile**: rigorous

## Outcome

Prove the installed Desktop Commander `0.2.46` and the real `kis-mcp` stdio gateway work end to end without modifying policy or production gateway behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `settings/kis-mcp.settings.json`, and the approved operator design in this change.
- Owned paths: commissioning change artifacts, commissioning documentation, one PowerShell entry point, one integration test, and one test-support module.
- Shared paths: none.
- Excluded paths: all `src/kis_mcp/**`, runtime settings, `docs/OPERATIONS.md`, and files owned by other active changes.
- Dependencies: current `main` includes the provider-state atomicity fix merged through PR `#4`; no branch dependency remains.
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

1. **Given** the pinned provider installation, **when** the commissioning script runs, **then** the gateway starts and lists the expected local provider surface.
2. **Given** a unique commissioning workspace, **when** read, write, block, quarantine, restore, and process calls run, **then** each expected result is observed through the real proxy.
3. **Given** provider shutdown, **when** the client session closes, **then** the shared provider state remains valid without snapshot restoration.
4. **Given** a failed stage, **when** the harness exits, **then** it returns nonzero and preserves a bounded stderr log.
5. **Given** normal repository verification, **when** the live flag is absent, **then** the live integration test is skipped and all existing tests remain green.

## Commissioning result

The integrated branch passes every live stage on current `main`: gateway and provider startup, surface import, hidden feedback and URL mode, local read, in-boundary write, HR-001 rejection, gateway quarantine and restoration, harmless local process execution, and post-shutdown provider-state integrity.

`pwsh -File scripts/commission-live-proxy.ps1` exits successfully. Because the harness restores the snapshot and raises `PROVIDER_STATE_INTEGRITY` whenever post-shutdown validation fails, the successful exit confirms the provider state remained valid without restoration.

## Risks and recovery

- Risk: future provider, FastMCP, or lifecycle changes could regress the real stdio chain.
- Mitigation: retain the gated commissioning test and run it after provider or lifecycle changes.
- Recovery: the branch changes only tests, scripts, and documentation; revert the commissioning commits if necessary.
- Failure recovery: if provider-state corruption reappears, the harness atomically restores the exact pre-run bytes before reporting failure.

## Out of scope

- Production gateway fixes.
- Provider adapter or policy changes.
- Runtime settings or implementation-status changes.
- Permanent quarantine disposal.
