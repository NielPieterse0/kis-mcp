# Closeout: Defender Safe Agnix

## Runtime evidence

- Windows agnix 0.45.0 SHA-256 `60e5400fecb4a4a6a6dbb1be440445ea93c93327852e310ab41a7678292c2e64`: Authenticode `NotSigned`; Smart App Control blocked the helper.
- Fresh upstream Windows 0.52.1 probe SHA-256 `2c27551671ee3e9706fa3f1a058607ee1095b3c2485868da6e82624207d1af1c`: also `NotSigned` and blocked, proving upgrade/relocation/Node reinstall would not solve the native helper trust failure.
- Selected runtime: authoritative `agent-sh/agnix` v0.45.0 Linux x86_64 release in WSL2 Ubuntu, KIS-owned at `C:\Projects\.kis-mcp\tools\agnix\0.45.0`.
- Upstream asset SHA-256 verified from its published sidecar: `48a3363d271198e20a2d341b5d6dad1b448400ff36b4505e59253d70c6e74f2f`.
- Bootstrap smoke: `agnix 0.45.0`.
- Prior repo-local Windows runtime moved recoverably to `C:\Projects\.kis-mcp\quarantine\agnix\legacy-repo-local-20260828T1535Z`.

## Workload and security evidence

- Strict real-worktree validation checked 823 files and returned valid agnix JSON with zero errors; exit 1 represented 11 warnings under strict mode.
- Fresh `Microsoft-Windows-CodeIntegrity/Operational` query from the workload start found zero attributable 3033/3077 events for agnix/WSL/kis-mcp.
- Deliberately malformed `.mcp.json` fixture produced strict `MCP-007` error and exit 1.
- Existing repository tests retain the exact exclusion for `contracts/tools/mcp-sdk-integrations/mcp-spec.schema.json`.
- Defender/SAC remained enabled; no exclusion, policy weakening, trusted-folder assumption, or Windows binary copying was used.

## Remaining delivery gates

Focused tests, change-governance check, review, exact-head GitHub CI, merge, current-revision live KIS validation, Work/documentation closeout, and cleanup must complete before #530 is Done.
