# Modularity Assessment Findings

## Conclusion

Read-only assessment of the current `52465b2` tree, using the adopted modularity-assessment skill and 180 days / 224 relevant commits of measured Git evidence. The architecture is generally modular: domain packages have strong source/test co-change seams and the gateway is a thin explicit composition root. The main debt is not broad coupling; it is a small number of oversized orchestration units plus checked-in modules that are not composed into the runtime.

No MAS is claimed because the adopted rubric requires BLR, RFC-kind clustering, and AGT read/edit-set measurements; the seam tool measures fan/co-change and explicitly states that commit subjects are not RFC kinds. Those measures remain `U`, so numeric MAS would be invalid.

## Evidence

| ID | Evidence | Strength |
|---|---|---|
| E-01 | `modularity-seams-depth3.json`: 224 commits; Discover 14,604 LOC, fan-in 28/fan-out 4; Providers 8,763 LOC, 15/14; Work Management 5,604 LOC, 10/7. | M |
| E-02 | Source/test co-change: Discover→tests/discover 0.778; Work Management→tests/work_management 0.889; Providers→provider tests are dominant peers. | M |
| E-03 | `gateway/composition.py` explicitly composes Projects, Providers, Discover, Workflows, Skills, Tools and capability exposure; `server.py` is 40 lines. | D |
| E-04 | AST hotspot scan: `evaluate_traceability` 378 lines/47 branch nodes; Discover `inspect` 325 lines; detector/intelligence builders ~249–250 lines. | M |
| E-05 | `govern/**` and enabled `governance.settings.json` exist but no gateway/catalogue registration; live capability search returns no Govern operations. | M |
| E-06 | `providers/python_sdk/**` plus `enabled=true` settings exist but only tests/package-local imports reference the descriptor; platform registry omits it. | M |
| E-07 | `providers/desktop_commander.py` lazily imports `server.build_server`, creating a composition back-edge into the root. | D |
## Unit assessment

| Unit | COH | CPL | BLR | RFC | AGT | MAS | Assessment |
|---|---:|---:|---:|---:|---:|---|---|
| Discover | 4 | 3 | U | U | U | n/a | Cohesive domain, but size/orchestrator complexity warrants monitoring. |
| Providers | 4 | 3 | U | U | U | n/a | Explicit adapter contracts; high fan-out is largely intrinsic composition. |
| Work Management | 4 | 3 | U | U | U | n/a | Strong source/test seam; traceability evaluator is an oversized local hotspot. |
| Gateway/composition | 4 | 3 | U | U | U | n/a | Clear composition purpose; one lazy Desktop Commander back-edge weakens directionality. |
| Govern | 4 | 3 | U | U | U | n/a | Internally cohesive but not part of runtime composition. |

## Findings

**F-01 | OD-2 incomplete boundary | Govern and Python SDK provider | Severity: Medium.** FACT E-05/E-06. INFER substantial isolated packages/configuration exist without runtime composition; `python-sdk` is configured enabled. REC choose and document one supported lifecycle state for each module: current runtime, intentionally staged, or intentionally inactive. RISK inert code/config creates false affordances and maintenance cost.

**F-02 | UD-2 orchestration hotspot | Discover / Work Management | Severity: Low-Medium.** FACT E-01/E-04. INFER the domains are cohesive, but several single functions carry many deterministic cases and require large review context. REC avoid broad restructuring; extract only when the same sub-responsibility changes independently in repeated slices. RISK review cost and regression surface grow faster than domain size.

**F-03 | UD-4 directionality leak | Desktop Commander Provider | Severity: Low-Medium.** FACT E-07. INFER a provider descriptor reaches back into the top-level server composition root rather than a narrower Work-server factory contract. REC introduce a bounded injected builder/factory only if this descriptor becomes executable outside its current role. RISK future ProviderService use can create surprising composition dependencies.

## Decision

Preserve the current domain/package architecture. Do not perform broad modular refactoring. Prioritize explicit disposition of uncomposed modules/configuration; monitor Discover/traceability hotspots using repeated change evidence before cutting new seams.