# agnix Bootstrap Evidence

## Defender-safe runtime decision

Windows Smart App Control blocked the upstream Windows `agnix-binary.exe` even after authoritative npm/GitHub acquisition and relocation. The previously pinned 0.45.0 PE was Authenticode `NotSigned`; a fresh 0.52.1 probe was also `NotSigned` and was blocked at launch. This proved that Node was only the parent process and that moving the same Windows binary was not remediation.

The current bounded solution keeps agnix `0.45.0` but changes the execution artifact and runtime boundary:

```text
authoritative agent-sh/agnix release
    -> agnix-x86_64-unknown-linux-gnu.tar.gz
    -> published SHA-256 sidecar verification
    -> staged WSL2/Ubuntu smoke test
    -> C:\Projects\.kis-mcp\tools\agnix\0.45.0
    -> validate_agent_configuration via wsl.exe
```

Node/npm are not part of the agnix runtime path. Defender/SAC remain enabled; no exclusion, policy weakening, trusted-folder assumption, or copied Windows executable is used.

## Provenance and recovery

The supervised installer records the source repository/tag/URLs, exact archive SHA-256, WSL distribution, installed paths, and version smoke result in `installation.json`. Replaced installations are moved recoverably beneath `C:\Projects\.kis-mcp\quarantine\agnix`.

The Linux artifact has no Windows Authenticode publisher because it is an ELF executable; its executable identity is established by the authoritative upstream release plus the upstream-published SHA-256. Windows launches the configured Microsoft WSL host, while the agnix executable runs inside the WSL2 Linux environment.

## KIS exposure

KIS continues to expose only bounded `validate_agent_configuration` with fixed JSON output, target, strict, and max-file arguments. It exposes no fix, watch, init, telemetry, schema, arbitrary-command, or general agnix provider surface. Application-Control launch text is classified explicitly as `AGNIX_APPLICATION_CONTROL_BLOCKED` rather than the misleading `AGNIX_INCOMPLETE` fallback.
