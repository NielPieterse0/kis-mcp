# Skills Module Development Evidence

## Delivery summary

The Skills module adds a bounded reusable-procedure catalogue at `C:\Projects\.agents\skills` and exposes nine public operations. Reads use an immutable validated snapshot. Create and improve operations re-enter the existing FastMCP server with middleware enabled and invoke Desktop Commander's normal `create_directory`, `write_file`, `move_file`, and `edit_block` contracts.

No provider fork, runtime dependency, external network operation, permanent-delete path, command allowlist/denylist, capability tier, or fourth policy rule was added.

## Architecture

```text
ChatGPT
   |
   v
skills.tools
   |
   v
skills.service
   |--------------------------|
   v                          v
skills.catalogue        SkillsWorkBackend
   |                          |
   v                          v
skills.source           FastMcpWorkBackend
   |                          |
   +-- skills.frontmatter     v
   +-- skills.config     FastMCP.call_tool
                              run_middleware=True
                                  |
                                  v
                         ThreeRuleMiddleware
                                  |
                                  v
                         Desktop Commander
```

| Unit | Responsibility |
|---|---|
| `config.py` | Closed JSON configuration and canonical roots. |
| `frontmatter.py` | Conservative parser for the accepted `SKILL.md` metadata subset. |
| `source.py` | Traversal safety, file collection, content limits, and normalized skill sources. |
| `catalogue.py` | Immutable snapshots, pagination, queries, evaluation, and mutation candidate validation. |
| `backend.py` | Narrow mutation protocol and middleware-reentering FastMCP adapter. |
| `service.py` | Create/improve orchestration, staging, refresh, and SHA-256 concurrency checks. |
| `tools.py` | Thin FastMCP registration for the nine public operations. |
| `models.py` | Explicit versioned public response records. |
| `errors.py` | Corrective `SKILLS_*` structural and backend failures. |

## Live smoke evidence

Command:

```text
pwsh -NoProfile -File scripts/smoke-skills-module.ps1
```

Observed result:

- composed live server tool count: 38;
- Skills operation count: 9;
- shared catalogue count before smoke: 17;
- `modularity-assessment` loaded and evaluated from the real shared root;
- a temporary skill was created through Desktop Commander;
- the skill was improved with the active SHA-256 precondition;
- the temporary skill was moved to recoverable quarantine;
- quarantine operation: `20260804T173108366085Z-68e85d0e9d9a`;
- policy remained exactly HR-001, HR-002, and HR-003.

Desktop Commander emitted its existing notification-validation warnings during local in-process proxy calls. They did not alter the successful tool results, and this slice does not modify provider notification handling.

# Modularity assessment

## Conclusions and risks

1. **REC** Preserve the final module boundary. Catalogue querying, source ingestion, mutation orchestration, and public registration have separate named responsibilities and explicit interfaces.
2. **FACT** The initial `catalogue.py` combined parsing, traversal, normalization, snapshot management, queries, and mutation validation in 681 lines.
3. **REC** The pre-release design correction extracted `frontmatter.py` and `source.py`; `catalogue.py` is now 368 lines and retains only snapshot/query responsibilities.
4. **FACT** Architecture tests enforce dependency direction and prohibit direct filesystem mutation in `backend.py` and `service.py`.
5. **RISK** The units are new, so independent rate-of-change history is insufficient to compute RFC or a defensible MAS.
6. **REC** Defer further splitting until at least three materially different changes show a repeated seam or one focused change requires reading more than four Skills units.

## Scope and evidence strength

- Subject class: Python implementation modules in `src/kis_mcp/skills`.
- Units: nine implementation files; `__init__.py` excluded as an export-only package file.
- Horizon: 90 days ending August 4, 2026.
- Mode: A, safe read-only Git collection plus direct source and test inspection.
- Sampling: all enumerated units.
- Strength: **MEDIUM for current structure**, because cohesion, dependency edges, size, and isolation are measured; **LOW for rate-of-change decisions**, because the module has no mature independent history.

Collector command:

```text
python <modularity-assessment>/scripts/seams.py --repo . --since "90 days ago" --granularity file --top 25 --top-peers 5 --format md --unit <each src/kis_mcp/skills file>
```

## Evidence

| ID | Evidence | Strength |
|---|---|---|
| E-01 | Collector measured LOC, commits, subjects, Python fan-in/fan-out, and co-change for all nine files. | M |
| E-02 | `tests/skills/test_architecture.py` measures the allowed local-import graph and absence of direct filesystem mutation in mutation layers. | M |
| E-03 | 30 focused Skills tests independently exercise configuration, parsing, source safety, catalogue behavior, backend routing, service mutation, fail-open registration, and public tools. | M |
| E-04 | Full repository verification passed after integration with one existing skip. | M |
| E-05 | Live smoke exposed 38 tools and completed create, improve, load, evaluate, quarantine, and refresh against the installed provider and real shared root. | M |
| E-06 | Distinct commit subjects are too new and too implementation-concentrated to classify as stable RFC kinds. | U |
| E-07 | Long-term independent release cadence is unavailable for a new module. | U |

## Unit scoring

`MAS = n/a` for every unit because RFC history remains `U`; unknowns are not converted into scores.

| Unit | COH | CPL | BLR | RFC | AGT | Decision |
|---|---:|---:|---:|---:|---:|---|
| U-01 `config.py` | 4 (C6, E-01/E-02) | 4 (K1, plain immutable data) | 4 (bounded readers) | U | 4 (focused config tests) | Preserve |
| U-02 `frontmatter.py` | 4 (C6) | 4 (K1, mapping return) | 4 | U | 4 (standalone parser tests) | Preserve |
| U-03 `source.py` | 4 (C6) | 3 (K3, `SkillSourceReader`) | 4 | U | 3 (source behavior covered through catalogue tests) | Preserve; monitor size |
| U-04 `catalogue.py` | 4 (C6 after extraction) | 3 (K3, normalized source contract) | 3 | U | 3 (isolated catalogue tests) | Preserve; split only on repeated query seam |
| U-05 `backend.py` | 4 (C6) | 3 (K3, mutation protocol) | 4 | U | 4 (backend-only tests) | Preserve |
| U-06 `service.py` | 4 (C6) | 3 (K3, catalogue/backend contracts) | 4 | U | 4 (service-only tests) | Preserve |
| U-07 `tools.py` | 4 (C6) | 3 (K3, service facade) | 4 | U | 4 (tool-contract tests) | Preserve |
| U-08 `models.py` | 4 (C6) | 4 (K1, explicit records) | 4 | U | 4 (schema tests) | Preserve |
| U-09 `errors.py` | 4 (C6) | 4 (K1, one corrective type) | 3 (fan-in 9) | U | 4 | Accepted shared infrastructure |

Hard-fail audit: no K4 dependency, hidden mutable state, unenforced ordering, public internal-layout exposure, or isolation requiring more than half the system was found. `errors.py` has measured fan-in 9 but remains a stable data-only exception contract, so HF-1 does not apply.

## Finding

F-01 | UD-2 God module risk, resolved before delivery | U-04 initial catalogue | Severity: medium x medium

**FACT** E-01/direct line count showed the initial catalogue at 681 lines with parsing, source safety, normalization, snapshots, queries, and mutation validation.

**INFER** The honest-name test required multiple independent purposes, so C6 cohesion was not supportable before extraction.

**REC** Completed extraction of `frontmatter.py` and `source.py`; architecture tests now enforce the dependency direction.

**RISK** Further splitting without change history could create OD-1 micro-module sprawl.

## Proposal and status

P-01 | From U-04 | Strategy: domain responsibility | **COMPLETED**

New units: `frontmatter.py` for metadata parsing and `source.py` for safe source normalization. Interface: `parse_skill_frontmatter()` and `SkillSourceReader`. Catalogue querying and snapshot semantics remain behind `SkillCatalogue`. Evidence: E-01, E-02, E-03. Sequence: extract pure parser, extract source reader, rerun all focused tests. Reversal cost: LOW. Verify: 30 focused tests and full verification pass.

## Deferred trigger

`DEFER - trigger:` split `catalogue.py` again only when at least three distinct change requests repeatedly modify one query family independently, or a representative focused change requires reading more than four Skills units. Merge micro-units only if two units repeatedly change together and one cannot be tested without the other's internals.

## Verification record

```text
pwsh -NoProfile -File .temp/run-focused-tests.ps1 tests/skills
30 passed

pwsh -NoProfile -File scripts/smoke-skills-module.ps1
ok=true; tool_count=38; skills_tool_count=9; catalogue_skill_count=17

pwsh -NoProfile -File scripts/verify.ps1
full locked repository verification passed; one existing skip
```
