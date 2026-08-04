# Provider Module Modularity Assessment

## Conclusions and risks

1. **REC** Establish one common Provider core for identity, capability, registry, catalogue, readiness, and explicit construction.
2. **REC** Preserve GitHub, Supabase, Discover, and Work as separate domain modules behind declared contracts.
3. **FACT** GitHub and Supabase already reside beneath `src/kis_mcp/providers/`; no connector directory move is required.
4. **RISK** GitHub currently introduces a temporary root registry while Supabase defines a separate local descriptor, creating contract drift until both adopt the common core.
5. **REC** Defer connector import migration until changes 008 and 009 are integrated; editing those active paths now would create an ownership clash.
6. **FACT** MAS is unavailable because blast radius, change-reason clusters, and agent read/edit ratios are unmeasured for the active branches.

## Scope and evidence strength

| Field | Value |
|---|---|
| Subject class | Python modules and provider adapter boundaries |
| Units | Common Provider core, GitHub adapter, Supabase adapter, Discover module, Work module |
| Horizon | Current repository state and active change branches on 2026-08-04 |
| Mode | Mode A direct inspection with Mode B operator declaration; collector measurements incomplete |
| Sampling | Five explicitly selected units; no sampling |
| Evidence strength | LOW because fewer than three of five measures are measured or declared for most units |

Collector command attempted from the Discover worktree:

```text
uv run --offline --no-sync python .agents/skills/modularity-assessment/scripts/seams.py --repo . --since "90 days ago" --top 25 --format md --unit src/kis_mcp/discover
```

The command exited `2` because the active Discover files were not tracked and therefore were not available to the tracked-file collector. The generated local environment artifact was moved to recoverable quarantine. No collector output was used for scoring.

## Evidence

| ID | Strength | Evidence |
|---|---|---|
| E-01 | M | Direct inspection of change 010 common files shows separate contracts, registry, catalogue, health, and service responsibilities beneath `src/kis_mcp/providers/`. |
| E-02 | M | `change/008-github-mcp-provider` places connector logic beneath `src/kis_mcp/providers/github/` and imports a temporary root `provider_registry.py`. |
| E-03 | M | `change/009-supabase-mcp-provider` places connector logic beneath `src/kis_mcp/providers/supabase/` and defines provider-local descriptor and readiness shapes. |
| E-04 | M | `change/005-discover-foundation` defines a focused `src/kis_mcp/discover/` package and a separate Discover product specification. |
| E-05 | D | The operator approved the platform diagram with Work, Providers, Govern, and Discover as peer modules under the FastMCP platform. |
| E-06 | M | `AGENTS.md`, `docs/TRUST-MODEL.md`, and `SPEC.md` declare Desktop Commander and three-rule middleware as the Work boundary, not the Provider boundary. |
| E-07 | U | Comparable change read sets and edit sets are unavailable for the active branches. |
| E-08 | U | Change-reason clusters are unavailable because the modules are new and branch history is insufficient. |
| E-09 | U | Confirmed dependency fan-in and representative blast-radius measurements are unavailable. |

## Evidence matrix

| Unit | COH | CPL | BLR | RFC | AGT |
|---|---|---|---|---|---|
| U-01 Common Provider core | M: E-01 | M: E-01 | U: E-09 | U: E-08 | U: E-07 |
| U-02 GitHub adapter | M: E-02 | M: E-02 | U: E-09 | U: E-08 | U: E-07 |
| U-03 Supabase adapter | M: E-03 | U: common contract not integrated | U: E-09 | U: E-08 | U: E-07 |
| U-04 Discover module | M: E-04 | D: E-05 | U: E-09 | U: E-08 | U: E-07 |
| U-05 Work module | M: E-06 | D: E-05 | U: E-09 | U: E-08 | U: E-07 |

## Scoring

| Unit | COH | CPL | BLR | RFC | AGT | RAW | MAS | Band |
|---|---:|---:|---:|---:|---:|---:|---|---|
| U-01 Common Provider core | 4, C6, E-01 | 3, K3, E-01 | U | U | U | n/a | n/a (U: BLR, RFC, AGT) | n/a |
| U-02 GitHub adapter | 4, C6, E-02 | 3, K3, E-02 | U | U | U | n/a | n/a (U: BLR, RFC, AGT) | n/a |
| U-03 Supabase adapter | 4, C6, E-03 | U | U | U | U | n/a | n/a (U: CPL, BLR, RFC, AGT) | n/a |
| U-04 Discover module | 4, C6, E-04 | 3, K3, E-05 | U | U | U | n/a | n/a (U: BLR, RFC, AGT) | n/a |
| U-05 Work module | 4, C6, E-06 | 3, K3, E-05 | U | U | U | n/a | n/a (U: BLR, RFC, AGT) | n/a |

The unweighted and size-weighted means are `n/a` because every unit has unmeasured inputs. No hard-fail override is applied without measured fan-in, hidden shared state, or public-layout evidence.

## Findings

### F-01 | OD-6 Missing shared infrastructure | U-02 and U-03 | Severity: likely x moderate

**FACT** E-02 and E-03 show separate provider descriptor, registry, and readiness concepts.

**INFER** Shared lifecycle semantics will drift if each connector defines its own public shape.

**REC** Use U-01 as the common contract and keep transport-specific behavior inside each adapter.

**RISK** Catalogue, health, and routing consumers would otherwise need provider-specific branches.

### F-02 | OD-2 Premature boundary | U-02 and U-03 | Severity: likely x high

**FACT** Changes 008 and 009 actively own their connector paths.

**INFER** Migrating their imports inside change 010 would violate parallel ownership and make branch integration fragile.

**REC** `DEFER - trigger: changes 008 and 009 are integrated or explicitly coordinated for shared edits`.

**RISK** Immediate migration could create merge conflicts or duplicate connector work.

### F-03 | OD-1 Micro-module sprawl check | U-01 | Severity: unlikely x low

**FACT** E-01 shows six small files, each with one named responsibility and direct contracts.

**INFER** The split is functional rather than layer-only: registry mutation, catalogue projection, readiness evaluation, and construction have different side effects and test seams.

**REC** Preserve the split; merge only if a file becomes a pass-through with no independent contract or test.

**RISK** Uncontrolled future wrappers could add indirection without value.

### F-04 | UD-2 God module prevention | U-01 | Severity: possible x high

**FACT** E-05 requires GitHub, Supabase, and future providers beneath one Provider module.

**INFER** “One Provider module” could be misread as one implementation file or one provider-specific registry.

**REC** Keep common lifecycle contracts in U-01 and provider transports in isolated adapter packages.

**RISK** A combined provider file would couple credentials, transports, network behavior, and release cadence.

## Proposals

### P-01 | From U-02 and U-03 | Strategy: domain

**New unit:** Common Provider core; **Purpose:** normalize provider identity and lifecycle; **Interface:** `ProviderDescriptor`, `ProviderRegistry`, `ProviderCatalogue`, `ProviderHealthSummary`, and `ProviderService`.

**Stays behind:** connector settings, credentials, transport, scope, and server construction; **Evidence:** E-01, E-02, E-03, E-05; **Sequence:** core first so adapters migrate to one stable contract.

**Reversal cost:** LOW; **Verify:** focused synthetic-provider tests pass and common files import no adapter package.

### P-02 | From U-02 and U-03 | Strategy: rate-of-change

**New unit:** Adapter registration seam; **Purpose:** let each connector publish one common descriptor; **Interface:** `register_provider(registry) -> ProviderDescriptor`.

**Stays behind:** provider-native health, configuration, and builder functions; **Evidence:** E-02, E-03; **Sequence:** after changes 008 and 009 integrate to avoid active ownership conflict.

**Reversal cost:** LOW; **Verify:** GitHub and Supabase connector tests pass unchanged except common-contract assertions.

## Independently verifiable tasks

### T-01 | Depends on: none

**Goal:** create the common Provider contract; **Read set:** authority docs and active provider branch structures; **Change:** immutable contracts and explicit exports.

**Verify:** contract tests; **Done when:** duplicate IDs fail and JSON projection is stable; **Out of scope:** connector imports and runtime activation.

### T-02 | Depends on: T-01

**Goal:** add deterministic registration and discovery; **Read set:** common contracts; **Change:** registry and catalogue.

**Verify:** sorted listing and capability-filter tests; **Done when:** no builder is invoked; **Out of scope:** provider scanning and dynamic imports.

### T-03 | Depends on: T-01, T-02

**Goal:** aggregate readiness and provide explicit construction; **Read set:** descriptors and registry; **Change:** health and service facade.

**Verify:** ready, degraded, disabled, unavailable, probe-failure, and explicit-build tests; **Out of scope:** connector network calls.

### T-04 | Depends on: T-01

**Goal:** version the public records; **Read set:** contract projections; **Change:** closed JSON Schema.

**Verify:** JSON validation and schema identity test; **Done when:** all public records require schema version 1.

### T-05 | Depends on: T-01 through T-04

**Goal:** preserve architecture authority; **Read set:** operator diagram, platform concept, active connector scopes; **Change:** Provider module product specification and this assessment.

**Verify:** document review, exact diagram presence, and no unsupported implementation claims.

## Open items and unmeasured evidence

- **O-01** BLR remains unmeasured until the common module and adapters are integrated and a representative change exists.
- **O-02** RFC remains unmeasured until commit subjects can be clustered into real change reasons.
- **O-03** AGT remains unmeasured until a comparable provider addition records bounded read and edit sets.
- **O-04** The temporary root `provider_registry.py` migration remains deferred to P-02.
- **O-05** Repository-wide change-governance validation remains blocked by duplicate historical claims copied into each worktree; this is unrelated to the Provider module seam.

## Self-audit

- [x] Scope, horizon, mode, sampling, evidence strength, and subject class are explicit.
- [x] Every evidence cell is labelled `M`, `D`, or `U`.
- [x] No `U` value enters MAS arithmetic.
- [x] RAW, MAS, means, and hard-fail limitations are visible.
- [x] Under-decomposition and over-decomposition were both checked.
- [x] Proposed boundaries include contracts, order, verification, and reversal cost.
- [x] Low-strength migration work is deferred with a concrete trigger.
- [x] Tasks have bounded reads, one outcome, verification, and exclusions.
- [x] Failed collection and open measurements are disclosed.
