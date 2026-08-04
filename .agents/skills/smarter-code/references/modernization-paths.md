# Modernization Path Selection

Use this reference only after the system boundary, business outcome, current stack, target intent, behavior oracle, and major dependencies are known.

## Path Matrix

| Path | Choose when | Required proof before execution | Reject or reconsider when |
|---|---|---|---|
| Retain and repair | The system still meets business needs and bounded defects dominate cost | Targeted defect evidence, maintainability baseline, operational acceptance | Structural constraints prevent required outcomes |
| Rehost | The main need is an environment move with intentionally unchanged application behavior | Reproducible build, environment contract, performance and rollback checks | Application changes are required to run safely |
| Same-stack uplift | A newer version of the same ecosystem can preserve most structure and code | Exact version pair, code-specific delta catalog, source-runtime baseline, target build proof | The delta catalog shows pervasive API or behavior replacement |
| Cross-stack transform | Business behavior remains valuable but implementation technology must change | Business-rule inventory, characterization or contract tests, mapping from legacy modules to target components | Behavior cannot be established or coexistence is impossible |
| Rearchitect incrementally | Coupling or scale blocks required outcomes and stable seams can be introduced | Domain and data ownership map, seam selection, coexistence contract, rollback | Proposed boundaries are organizational fashion rather than code and data reality |
| Rebuild | Existing implementation has low reuse value but business capability remains necessary | Approved behavior specification, migration and cutover plan, acceptance oracle | Hidden rules or operational dependencies remain material |
| Replace | A maintained product or service satisfies the required capability with lower lifecycle risk | Fit-gap evidence, data migration proof, exit strategy, vendor or service constraints | Lock-in, compliance, or missing behavior outweighs the benefit |

## Common Proof Gates

1. **Scope gate:** confirm whether the assessed directory is the whole system and identify inbound and outbound dependencies.
2. **Oracle gate:** record current observable behavior before proposing transformation.
3. **Data gate:** identify authoritative stores, ownership, migration, reconciliation, retention, and rollback.
4. **Integration gate:** enumerate synchronous, asynchronous, batch, file, and human workflows.
5. **Security gate:** identify trust boundaries, identity propagation, secret handling, and compliance constraints without exposing values.
6. **Pilot gate:** migrate one representative slice that exercises the highest-risk assumptions, not merely the easiest slice.
7. **Widening gate:** update the plan from pilot evidence and stop if success criteria or rollback no longer hold.

## Sequencing Rules

- Use dependency-leaf-first ordering for a genuine same-stack uplift, except when shared test infrastructure or a coordinated compatibility cut must come first.
- Use a bounded seam or strangler sequence for cross-stack transformation and rearchitecture.
- Keep optional cleanup separate from required compatibility changes so behavior drift remains reviewable.
- Define entry criteria, exit evidence, rollback, and a circuit-break condition for every phase.
- Treat estimates as ranges tied to assumptions. Do not derive exact time or cost from lines of code or generic complexity formulas.

## Behavior Contract

Record inputs, outputs, error behavior, side effects, state transitions, ordering, timing constraints, data formats, and known legacy quirks. Classify each quirk as preserve, deliberately change, or unresolved; do not silently normalize it during modernization.
