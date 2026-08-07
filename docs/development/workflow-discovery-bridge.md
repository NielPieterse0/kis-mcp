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
