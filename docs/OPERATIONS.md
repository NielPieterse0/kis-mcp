# Operations

## Prerequisites

- Windows with PowerShell.
- Python 3.11 or newer.
- `uv` for the Python environment.
- Node.js 18 or newer with npm.
- Direct operator supervision for bootstrap and upgrades.

## Generated state
All generated state remains inside the approved write boundary and outside the repository:

```text
C:\Projects\.kis-mcp\
├── .claude-server-commander\
├── desktop-commander\
├── python-env\
├── uv-cache\
├── python-cache\
├── pytest-cache\
├── npm-cache\
├── quarantine\
├── temp\
└── logs\
```

Do not commit this state. Repository-local `.venv`, `.pytest_cache`, PowerShell module cache, provider state, or command-state directories are not authoritative project artifacts.

## Install Python dependencies
Run the operator-supervised bootstrap from `C:\Projects\kis-mcp`:

```powershell
pwsh -File .\scripts\bootstrap-python.ps1
```

The script may use external network access, generates or updates `uv.lock`, and synchronizes the locked development environment beneath `C:\Projects\.kis-mcp\python-env`. It also keeps uv, Python bytecode, pytest, and temporary state outside the repository.

Normal startup and verification never resolve or update dependencies from the network. `scripts\verify.ps1` requires `uv.lock` and performs an offline frozen synchronization before testing.

## Install Desktop Commander
Desktop Commander is installed from the scanned `@wonderwhy-er/desktop-commander` archive, not copied into this repository and not downloaded again by the installer.

Archive acquisition and security scanning are explicit operator-supervised actions outside the normal Work path. The repository installer itself performs no external network access:

```powershell
pwsh -File .\scripts\install-desktop-commander.ps1
```

The script reads the exact archive file name and SHA-256 from `settings/kis-mcp.settings.json`, resolves that archive beneath the current user's `Downloads` directory, verifies the digest before creating installation state, resolves `node.exe` and `npm.cmd`, and invokes npm with `--offline` and `--ignore-scripts`.

Installation is staged beneath `C:\Projects\.kis-mcp\temp` and activated beneath `C:\Projects\.kis-mcp\desktop-commander` only after package identity, version, and entry-point checks pass. Any prior installation is retained as a recoverable backup beneath the project temporary root.

The scanned Desktop Commander `.tgz` does not bundle its runtime dependency closure. Every dependency must therefore already exist in the project-local, separately scanned npm cache at `C:\Projects\.kis-mcp\npm-cache`. If any dependency is absent, the installer fails with `DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED`; do not remove `--offline` or allow a registry fallback.

Prepare the dependency cache in a separate operator-supervised network stage:

```powershell
pwsh -File .\scripts\prepare-desktop-commander-cache.ps1
```

This script verifies the same local archive and SHA-256, uses that archive as the root package source, downloads its dependency closure into a unique temporary acquisition area beneath `C:\Projects\.kis-mcp\temp`, disables package scripts, verifies the installed package identity and version, scans the complete acquisition tree with Microsoft Defender, and promotes only the clean npm cache. It retains any previous cache as a recoverable temporary backup. It does not download a second Desktop Commander root package.

After the preparation succeeds, rerun the unchanged offline installer:

```powershell
pwsh -File .\scripts\install-desktop-commander.ps1
```

Normal startup uses the installed package without downloading or updating it.

## Configure

Edit only the canonical JSON files:

- `settings/kis-mcp.settings.json` for identity, paths, provider version and launch settings, transport, and informational implementation status.
- `policy/kis-mcp.policy.json` for the exact three-rule declaration.

The policy file must contain exactly HR-001, HR-002, and HR-003. Adding, removing, or weakening a rule requires explicit operator approval.

The normal approved boundary is `C:\Projects`. State and quarantine roots must remain true descendants of it.

Configuration status fields report what has been verified; they do not disable otherwise permitted Desktop Commander tools.

## Start
Run:

```powershell
pwsh -File .\scripts\start.ps1
```

Startup does not install or update packages. It requires the external locked Python environment and the pinned Desktop Commander entry point to exist, validates the exact three-rule set and canonical state paths, validates provider offline readiness, and then starts `kis-mcp` over stdio using `C:\Projects\.kis-mcp\python-env\Scripts\python.exe`.

Provider readiness rejects enabled telemetry, a missing or non-loopback feature-flag URL, and missing local Chrome when configured as required because the pinned provider source proves those states cause automatic external activity. It also requires Desktop Commander's persisted `blockedCommands` and `allowedDirectories` fields to remain empty so the provider cannot add independent command or directory restrictions beneath FastMCP.

The feedback tool and `read_file.isUrl` mode are absent from the exposed Work contract. Terminal and process tools remain available; the gateway blocks or transforms only concrete HR-001, HR-002, or HR-003 effects.

## Parallel change worktrees

Create implementation worktrees only from a clean primary `main` checkout. The workflow supports any number of parallel agents; it rejects duplicate outcomes and conflicting scope claims rather than imposing a concurrency limit.

Create a change:

```powershell
pwsh -File .\scripts\change-workflow.ps1 new 002-example-change `
    --outcome "Implement one bounded result" `
    --owned "src/example/**" `
    --owned "tests/test_example.py" `
    --exclude "policy/**"
```

The command creates branch `change/002-example-change`, worktree `.work/worktrees/002-example-change`, and the five required artifacts beneath `.work/changes/002-example-change/`.

List or validate active claims:

```powershell
pwsh -File .\scripts\change-workflow.ps1 list
pwsh -File .\scripts\change-workflow.ps1 validate
```

Before committing or requesting review, run the scope check from the change worktree:

```powershell
pwsh -File .\scripts\change-workflow.ps1 check
```

The check compares committed, staged, unstaged, and untracked paths with `owned_paths`, `shared_paths`, and `excluded_paths`. Exact paths and recursive `/**` claims are supported; other glob forms are rejected.

After the branch is merged into its declared base, return to the clean primary checkout and run:

```powershell
pwsh -File .\scripts\change-workflow.ps1 cleanup 002-example-change
```

Cleanup refuses a dirty worktree or an unmerged branch. It performs only normal `git worktree remove`, `git branch -d`, and `git worktree prune` operations; it never forces deletion.

## Verify
Run:

```powershell
pwsh -File .\scripts\verify.ps1
```

Verification requires `uv.lock`, synchronizes the external Python environment offline with `--frozen`, and invokes `scripts\verify.py` through that environment's exact Python executable. The Python verifier confirms the interpreter location, FastMCP 3.4.4, pytest `>=8.4,<9`, Python syntax, configuration, and the full test suite.

The repository checks also confirm:

1. the policy contains exactly HR-001, HR-002, and HR-003;
2. repository skills are not referenced by runtime or configuration;
3. Desktop Commander is not vendored;
4. generated-state paths remain canonical and outside the repository;
5. predecessor runtime identities are absent from authoritative and runtime files;
6. path, exact network-target, allowed negative-case, quarantine, provider-readiness, exposed-schema, and middleware regression tests pass.

Verification improves confidence in resolved intent and boundary behavior. It does not create a separate permission gate and does not replace live provider end-to-end testing.

## Upgrade Desktop Commander

1. Check the authoritative package release outside Work.
2. Update only `desktop_commander.version` in `settings/kis-mcp.settings.json`.
3. Run the operator installation script.
4. Capture the provider tool list and compare schemas.
5. Update only the narrow adapter mappings that changed.
6. Run the complete verification suite.
7. Record the verified version in the implementation-status documentation.

Do not use `latest` during normal startup.

## Quarantine and restore

Quarantine records are stored beneath the configured quarantine root. Each operation has a unique ID, intact payload, and restoration metadata.

Restore only when the original path is absent. A restore operation fails rather than overwrites.

Permanent disposal is intentionally not exposed as a normal Work tool.

## Troubleshooting

- `DESKTOP_COMMANDER_ARCHIVE_NOT_FOUND`: place the configured scanned `.tgz` in the current user's `Downloads` directory.
- `DESKTOP_COMMANDER_ARCHIVE_HASH_MISMATCH`: stop; the archive differs from the recorded scanned digest.
- `DESKTOP_COMMANDER_OFFLINE_INSTALL_FAILED`: the scanned project-local npm cache does not contain the complete runtime dependency closure; run `prepare-desktop-commander-cache.ps1`, then retry without enabling registry fallback.
- `DESKTOP_COMMANDER_DEPENDENCY_ACQUISITION_FAILED`: the supervised dependency download failed; inspect the retained acquisition directory and npm log before retrying.
- `DESKTOP_COMMANDER_DEPENDENCY_SCAN_FAILED`: Defender did not return a clean result; nothing was promoted. Keep the acquisition tree isolated for operator review.
- `DESKTOP_COMMANDER_CACHE_PROMOTION_FAILED`: cache activation failed; the prior cache is restored when possible and the clean acquisition tree remains recoverable.

- `DESKTOP_COMMANDER_NOT_INSTALLED`: run the supervised install script outside Work.
- `POLICY_RULE_SET_INVALID`: restore the exact three-rule JSON file.
- `HR-001_WRITE_OUTSIDE_PROJECTS`: choose a destination beneath `C:\Projects`.
- `HR-002_EXTERNAL_NETWORK`: remove the concrete external target, use an approved connector, or use an explicit operator action outside Work.
- `UNSUPPORTED_PROVIDER_TOOL` or `UNSUPPORTED_PROVIDER_MODE`: use the exposed local provider contract; the named external-only provider surface is not part of Work.
- `PROVIDER_CONFIGURATION_INVARIANT`: leave Desktop Commander's provider-native restriction fields gateway-managed and empty.
- `INVALID_INVOCATION_PATH`: provide a concrete path that can be resolved and safely transformed.
- `HR-003_QUARANTINE_REQUIRED`: allow the gateway to move the target to quarantine rather than delete it.
- `HR-003_QUARANTINE_FAILED`: inspect quarantine availability and retry without permanent deletion.
