# Output contract

Use this reference while drafting findings, proposals, tasks, and closeout.

## Order and IDs

Use stable IDs within a report: `U-nn` unit, `E-nn` evidence, `F-nn` finding,
`P-nn` proposal, `T-nn` task, and `O-nn` open item. Mark withdrawn IDs `WITHDRAWN`;
do not reuse them.

Order the report:

1. conclusions and risks;
2. scope, mode, horizon, sampling, and evidence strength;
3. evidence table with `M`/`D`/`U` per cell;
4. scoring table ordered by ascending MAS, then unit path;
5. findings;
6. decomposition proposals and migration order;
7. independently verifiable tasks;
8. open items and unmeasured evidence.

## Records

Finding:

```text
F-01 | <defect code and name> | U-01 <unit> | Severity: <likelihood x consequence>
FACT  <E-nn evidence>
INFER <rubric-backed interpretation>
REC   <bounded correction or DEFER trigger>
RISK  <residual risk if unactioned>
```

Proposal:

```text
P-01 | From U-01 | Strategy: <domain | layer | rate-of-change>
New unit: <name>; Purpose: <one outcome>; Interface: <contract>
Stays behind: <scope>; Evidence: <E-ids>; Sequence: <dependency reason>
Reversal cost: <LOW | MEDIUM | HIGH>; Verify: <observable check>
```

Task:

```text
T-01 | Depends on: <IDs or none>
Goal: <one outcome>; Read set: <bounded paths>; Change: <exact boundary change>
Verify: <check in this task>; Done when: <observable criterion>
Out of scope: <explicit exclusions>
```

Use claim labels for analytical prose in findings and proposals. Do not prefix headings,
metadata, table headers, or purely structural fields.

## Self-audit

- [ ] Scope, horizon, mode, sampling, evidence strength, and subject class are explicit.
- [ ] Every evidence cell is `M`, `D`, or `U`; commands or declarations are recorded.
- [ ] Every score cites evidence and an anchor; no `U` enters MAS arithmetic.
- [ ] RAW, MAS, weighting, rounding, band, and all hard-fail checks are visible.
- [ ] Both under- and over-decomposition were checked.
- [ ] Every proposed cut has change evidence, verification, and reversal cost.
- [ ] Low-strength or evidence-free units receive `DEFER` with a measurement trigger.
- [ ] Each task has bounded reads, one outcome, in-task verification, and exclusions.
- [ ] Assumptions and failed checks appear in Open items.

Keep conclusions within 12 lines and each finding or task within 8 lines. Split the
assessment when the 25-unit cap prevents a reviewable report.
