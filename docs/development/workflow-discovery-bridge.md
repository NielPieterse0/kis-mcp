# Workflow / Discover Bridge

## Batch 1 — bounded change planning

`plan_change` is a read-only Discover operation that composes existing project, task-context, local Git change, impact, verification, and governed change-claim evidence.

It does not execute repository commands. It filters `.work/changes/**` lifecycle records from implementation paths, while reading active claim metadata through the same bounded `ReadAuthority` used by Discover.

The result includes:

- instruction/documentation authority paths;
- current implementation paths, or task context when no implementation change exists;
- relevant modules, symbols, tests, and contracts;
- verification IDs/handoffs discovered for Work;
- active change claims and overlapping owned paths;
- implementation steps, risks, unknowns, confidence, truncation, and a stable fingerprint.

`plan_change` remains discoverable instead of direct so progressive exposure is preserved. No policy, network, provider-authentication, or execution boundary changes are introduced by Batch 1.

## Batch 2 — verification execution bridge

`run_verification(project, verification_id, timeout_ms)` is the Work-side execution bridge for verification IDs already discovered by Discover. It does not accept command text. Work re-discovers the declaration by stable ID, permits only the known semantic profiles `python`, `uv`, `npm`, and `powershell_verify`, and derives the process command from the fixed executable plus the discovered argument vector.

The nested `start_process` and any `read_process_output` call run through the normal server middleware. HR policy errors are propagated unchanged; structural verification errors use `VERIFICATION_*` codes instead of impersonating HR decisions. The result contract is `verification-result-v1` with command identity, status, exit code, duration, bounded evidence, failure classification, and truncation state.

The provider process schema remains exact: `start_process` receives only `command`, `timeout_ms`, and `shell`. The project directory is selected inside the PowerShell command with `Set-Location -LiteralPath` and escaped literal tokens. `run_verification` is discoverable through the runtime surface and does not consume a new direct-profile slot.
