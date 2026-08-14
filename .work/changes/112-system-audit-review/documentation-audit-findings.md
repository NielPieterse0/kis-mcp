# Current Documentation / Specification Audit

## Audit basis

Current authority was evaluated in repository order: `AGENTS.md` → `TRUST-MODEL.md` → `SPEC.md` → `PLATFORM-CONCEPT.md` → policy JSON → `OPERATIONS.md`, with module product specs owning only durable module contracts. Historical `.work/changes/**` and `docs/development/**` were used as evidence, not current truth.

| Document | Result |
|---|---|
| `AGENTS.md` | Aligned; authority and documentation-routing rules are clear. |
| `SPEC.md` | Two current-state contradictions found: Govern existence; commissioning status vs runtime. |
| `README.md` | Aligned; acts as navigation/projection and defers to canonical owners. |
| `docs/TRUST-MODEL.md` | Aligned with exact three-rule semantics and policy verification. |
| `docs/HARD-BLOCK-APPROVAL-REGISTER.md` | Aligned; named evidence tests exist and operator decisions are complete. |
| `docs/NON-HARD-CONTROLS.md` | Boundary separation from HR decisions remains consistent. |
| `docs/PLATFORM-CONCEPT.md` | Correctly target-state, but Govern target wording now overlaps substantial dormant implementation. |
| `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` | No material current implementation contradiction found. |
| `docs/PROVIDER-MODULE-PRODUCT-SPEC.md` | One commissioning-status drift finding. |
| `docs/SKILLS-MODULE-PRODUCT-SPEC.md` | No material current implementation contradiction found. |
| `docs/OPERATIONS.md` | Procedures/evidence are coherent; DB/Docker commissioned claims conflict with live status output because of CR-01. |
| `docs/STARTUP-HARDENING.md` | Correctly labels itself historical and defers current procedure. |
| `docs/LESSONS-APPLICABILITY.md` | Multiple stale current-state summaries found; supporting guidance crosses into volatile product status. |
## Findings

**DA-01 | Govern wording contradicts repository contents | Severity: Medium.** `SPEC.md:22` says the repository does not contain a governance subsystem and `SPEC.md:36` says Govern remains target-state. Current source contains `govern/**`, settings, schema, tests, six advisory rules and four tool registrations. Current wording should distinguish the implemented foundation from the fact that it is not composed/exposed.

**DA-02 | Provider module commissioning state is stale | Severity: Medium.** `PROVIDER-MODULE-PRODUCT-SPEC.md:333` says P6 is “Implemented, commissioning pending,” while `SPEC.md:340`, `OPERATIONS.md:310-311/340`, and change 111 record completed DBHub/Docker commissioning. Durable connector contracts belong in the module spec; live commissioning status belongs in `OPERATIONS.md`.
**DA-03 | Commissioned documentation conflicts with live status output | Severity: High user-impact / code-rooted.** Both live instances are mounted/ready, but `kis_provider_status` reports DBHub/Docker `live_verified=pending` and asks for live commissioning. `SPEC.md` and `OPERATIONS.md` retain the successful change-111 commissioning evidence. CR-01 is the root implementation issue; repeating the commissioning procedure is not evidence of a missing original commissioning step.

**DA-04 | `LESSONS-APPLICABILITY.md` repeats stale current-state summaries | Severity: Medium-Low.** Line 55 says progressive exposure remains target; line 165 labels current change-target capabilities as internal/not public; lines 174-181 still frame Govern and bounded Work planning/workflows as deferred. Current `SPEC.md` and implementation show progressive exposure, generalized `inspect_change`, planning/workflow operations, and a substantive Govern foundation. Supporting guidance should retain durable lessons and reference canonical current-status owners.

## Authority/boundary judgment

No duplicate hard-rule authority was found across Trust, Hard-Block, and Non-Hard documents. The main boundary issue is volatile/current implementation status being repeated in Provider and Lessons documents rather than projected from `SPEC.md` / `OPERATIONS.md`. Dated `docs/development/**` evidence is correctly subordinate where current authorities explicitly reference it.