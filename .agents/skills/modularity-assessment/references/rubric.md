# Scoring rubric

Use only after evidence collection. Assign the lowest anchor honestly supported. If a
required measure is `U`, do not compute MAS.

## Cohesion (COH)

| ID | Recognition test | Score |
|---|---|---:|
| C0 | Coincidental location; catch-all contents span unrelated responsibilities | 0 |
| C1 | Same kind of thing, but no shared purpose | 1 |
| C2 | Grouped because operations occur at the same time | 1 |
| C3 | Steps in a procedure rather than one responsibility | 2 |
| C4 | Multiple operations on the same data | 2 |
| C5 | Output-to-input sequence is the reason for the unit | 3 |
| C6 | One nameable task without joining independent purposes | 4 |

Catch-all names are only C0 evidence when actual contents are unrelated. Cross-cutting
infrastructure may be C1 `ACCEPTED-BY-DESIGN`. A unit whose honest name needs multiple
independent purposes cannot be C6.

## Coupling (CPL)

Score the tightest material edge.

| ID | Recognition test | Score |
|---|---|---:|
| K1 | Simple data passed by parameters and returns | 4 |
| K2 | Events/messages; sender does not know receivers | 3 |
| K3 | Declared contract hides implementation | 3 |
| K4 | Consumer depends on layout, private behavior, ordering, or side effects | 0 |

Hidden shared state or implicit ordering caps CPL at 1. Coupling through a shared mutable
third node subtracts 1, floor 0. Necessary domain coupling is `INTRINSIC`, not a defect.

## Counted measures

| Measure | Count | 4 | 3 | 2 | 1 | 0 |
|---|---|---:|---:|---:|---:|---:|
| BLR | Other units read before a safe change | <=2 | 3-5 | 6-10 | 11-20 | >20 |
| RFC | Distinct change-reason kinds | 1 | 2 | 3 | 4-5 | >=6 |
| AGT | Read-set/edit-set ratio | <=2 | <=4 | <=8 | <=16 | >16 |

AGT also requires single-session fit; if fit is no, cap AGT at 1. Use RFC clusters, not
raw commit-subject counts.

## MAS and bands

```text
RAW = 0.25*COH + 0.25*CPL + 0.20*BLR + 0.15*RFC + 0.15*AGT
MAS = round-half-away-from-zero(RAW*25)
```

Show RAW to two decimals. With any `U`, use `MAS = n/a (U:<measures>)`. Report both the
unweighted mean and the size-weighted mean using the declared size unit.

| MAS | Band | Decision |
|---|---|---|
| 80-100 | B1 Sound | Preserve |
| 60-79 | B2 Acceptable debt | Monitor named triggers |
| 40-59 | B3 Restructure candidate | Cut only with seam evidence |
| 20-39 | B4 Structural failure | Sequence decomposition |
| 0-19 | B5 Collapse | Contain before extending |

## Hard-fail overrides

| ID | Condition | Worst permitted band |
|---|---|---|
| HF-1 | K4 on a node with measured fan-in >=5 | B3 |
| HF-2 | Hidden shared state or unenforced ordering | B3 |
| HF-3 | Measured fan-in >=10 and RFC score <=1 | B4 |
| HF-4 | Honest-name test fails and RFC kind count >=3 | B3 |
| HF-5 | Isolation requires more than half the system | B3 |
| HF-6 | Public surface exposes internal data layout | B3 |

Do not apply a fan-based override when fan evidence is `U` or unconfirmed heuristic data.

## Defect codes

| Code | Defect | Typical correction |
|---|---|---|
| UD-1 | Catch-all accretion | Name evidenced categories and relocate intact behavior |
| UD-2 | God module/object | Split along change reasons |
| UD-3 | Layer-only grouping | Re-slice by domain purpose |
| UD-4 | Implementation coupling | Introduce and verify a contract |
| UD-5 | Hidden mutable state/order | Encapsulate and enforce the invariant |
| UD-6 | Unrelated release cadences | Split by cadence behind a contract |
| UD-7 | Junk-drawer inheritance | Prefer composition or explicit behavior |
| UD-8 | Control-flow tangle | Linearize before splitting |
| UD-9 | Read-set explosion | Bound responsibility and required context |
| OD-1 | Micro-module sprawl | Merge into the owning purpose |
| OD-2 | Premature boundary | Defer and gather change evidence |
| OD-3 | Wrong abstraction | Delay or replace the contract |
| OD-4 | Excessive indirection | Collapse pass-through layers |
| OD-5 | Fictional boundary | Merge units that share internals |
| OD-6 | Missing shared infrastructure | Permit clearly named logical infrastructure |

When two anchors remain defensible, choose the lower score and record what evidence would
settle the dispute. Re-score only when evidence changes.
