# Evidence protocol

Use this reference only while collecting or grading evidence.

## Modes

- **Mode A:** safe read-only access to a trusted Git repository.
- **Mode B:** user-declared structure and history when instrumentation is unavailable.

Mode A command:

```text
python <skill>/scripts/seams.py --repo . --since "90 days ago" --top 25 --format md
```

Add exact `--unit <name>` selectors after scoping. Add `--include-docs` for document
sets. Preserve the command, exit code, sampling rule, limitations, and output used.

The collector provides tracked size, relevant commit count, distinct commit subjects,
co-change data, and dependency heuristics for supported languages. It does not provide
RFC kinds, hidden coupling, read-set/edit-set, or test isolation.

## Measures

| Measure | Preferred evidence | Mode B substitute | Failure |
|---|---|---|---|
| COH | Actual contents, import span, purpose/rename test | User description and names | Mark unsupported parts `U` |
| CPL | Declared interfaces plus reach-through/shared-state search | User description of interactions | `U` |
| BLR | Representative read-set and confirmed fan-in | Last comparable change | `U` |
| RFC | Commit subjects clustered into change kinds | Last 5-10 changes and purposes | `U` |
| AGT | Representative read-set divided by edit-set; isolated test run | Last task and required reading | `U` |

For RFC, record the clusters, not merely the number of subjects. For AGT, use the same
representative change class across compared units and name it.

## Provenance and strength

- `M`: produced by a recorded command or direct inspection.
- `D`: explicitly declared by the user; quote or summarize the declaration.
- `U`: unavailable, unsupported, incomplete, or unsafe to collect.

| Strength | Condition | Permitted conclusion |
|---|---|---|
| HIGH | At least 4 of 5 measures are `M` for at least 80% of units | Sequenced cut recommendation |
| MEDIUM | At least 3 of 5 are `M` or `D` for at least 80% | Recommendation requiring confirmation |
| LOW | Anything less | Findings and measurement triggers only |

Mode B is LOW unless subsequent measurements raise it. It cannot support an irreversible
cut.

## Non-code subjects

State the substitution in the report:

| Code | Document set | Workflow |
|---|---|---|
| Module | Controlled document or section | Stage or hand-off |
| Import/fan-in | Cross-reference/citation | Input dependency/blocker |
| Co-change | Same change request | Steps that change together |
| Hidden coupling | Undocumented wording dependency | Unstated ordering |
| Test isolation | Standalone review/approval | Standalone validation |

Document and workflow subjects usually require Mode B supplementation even when the
collector measures tracked files.
