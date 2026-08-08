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

## Batch 3 — workflow integration primitives

The verification package owns conflict-free workflow specifications for `verify-current-change` and `triage-exact-head-ci`, plus the exact-head CI failure-class contract. It also owns deterministic helpers for executable-step resolution and weighted workflow matching across workflow identity/title, activation terms, description, and capability names.

After change 063 released its exclusive catalogue paths, the final adapter integrated those primitives into the shared workflow surface. `WorkflowDescriptor` now carries optional `executable_steps`; the platform catalogue adapts both verification specs into shared descriptors; the resolver requires each declared executable step to resolve to an enabled runtime operation or nested workflow before recommendation; and workflow matching delegates to the deterministic weighted scorer. Existing workflows with symbolic procedure steps keep empty executable-step metadata, so their legacy eligibility behavior is unchanged.
