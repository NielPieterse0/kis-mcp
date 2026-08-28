# Change Specification: Defender Safe Agnix

- **Change ID**: `258-defender-safe-agnix`
- **Status**: Active
- **Complexity**: medium
- **Risk triggers**: `external_action`, `persistent_state`, `security`

## Outcome

Restore live agnix validation under Defender/Smart App Control without exclusions or relocation-as-remediation.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, Work #530, rollout #541, operator handover.
- Runtime ownership: KIS-generated tool state under `C:\Projects\.kis-mcp\tools`; do not establish a shared `.tools` standard from this one fix.
- Preserve agnix `0.45.0`, bounded validation arguments, MCP 2026-07-28 repository configuration, and no-fix authority.

## Requirements

- **REQ-001**: Reacquire the exact official Linux x86_64 agnix release and verify its upstream SHA-256 sidecar before promotion.
- **REQ-002**: Execute agnix through configured WSL2 Ubuntu, avoiding the SAC-blocked Windows PE helper and any Node/npm runtime dependency.
- **REQ-003**: Keep installation/staging/quarantine beneath `C:\Projects` with recoverable replacement and provenance metadata.
- **REQ-004**: Classify Windows Application Control launch blocks as `AGNIX_APPLICATION_CONTROL_BLOCKED`, never generic `AGNIX_INCOMPLETE`.
- **REQ-005**: Prove the real repository validation workload and fresh Code Integrity result without weakening Defender/SAC.

## Acceptance

1. Supervised bootstrap verifies checksum, WSL smoke, and promotes `agnix 0.45.0`.
2. `validate_agent_configuration` completes through the KIS surface against `C:\Projects\kis-mcp`.
3. Repository schema exclusion remains exact and malformed agent configuration remains strictly detected.
4. Fresh attributable Code Integrity 3033/3077 blocks are zero for the canonical workload.
5. Focused tests, governance check, exact-head GitHub CI, merge, live proof, documentation reconciliation, and Work #530 closeout pass.

## Risks and recovery

- WSL2/Ubuntu becomes an explicit local prerequisite for this managed tool.
- Revert repository change and restore a quarantined prior installation if required; no Defender policy changes are part of recovery.

## Out of scope

- Full #541 cohort rollout or shared workstation runtime standard.
- General agnix provider/MCP exposure, fix/watch/init/telemetry authority, or Node/runtime relocation unrelated to agnix.
