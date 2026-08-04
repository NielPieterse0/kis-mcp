# Closeout: 012-skills-module

## Status

Implementation complete, locally verified, and open as PR #14: `https://github.com/NielPieterse0/kis-mcp/pull/14`.

## Implemented scope

- Added the runtime Skills package under `src/kis_mcp/skills` with strict configuration, conservative frontmatter parsing, safe source normalization, immutable snapshots, bounded list/search/load/read/evaluate operations, and explicit versioned response records.
- Added nine FastMCP operations: `list_skills`, `search_skills`, `load_skill`, `search_skill_files`, `read_skill_file`, `refresh_skills`, `evaluate_skill`, `create_skill`, and `improve_skill`.
- Fixed the runtime root at `C:\Projects\.agents\skills` and the staging root at `C:\Projects\.kis-mcp\temp\skills` through closed JSON settings and schema contracts.
- Routed create and improve mutations through `FastMCP.call_tool(..., run_middleware=True)` to Desktop Commander `create_directory`, `write_file`, `move_file`, and `edit_block`; no direct mutation exists in the Skills service or backend adapter.
- Added optimistic SHA-256 preconditions for improvement and validated complete proposed skills before mutation.
- Made initial Skills catalogue failure fail-open for the wider server: Work, gateway, and Discover remain available while Skills calls return the corrective initialization error.
- Added an end-to-end smoke script that loads and evaluates a real shared skill, creates and improves a temporary skill, then moves it to recoverable quarantine.
- Integrated PR #13 merge commit `0915bfa`; the composed server exposes 39 tools: the 30-tool Work/gateway/Discover surface plus nine Skills operations.
- Closed the stale merged change-005 claim and updated its additive tool-registration expectation without changing Discover implementation behavior.

## Review

- TDD covered configuration, schemas, parsing, source safety, deterministic snapshots, pagination, queries, file reads, stale cursors, malformed sources, size/suffix limits, mutation prevalidation, backend routing, exact middleware re-entry, structured tool output, fail-open initialization, and additive server composition.
- The modularity assessment found the initial 681-line catalogue combined unrelated parsing, traversal, normalization, snapshot, query, and mutation-validation responsibilities. `frontmatter.py` and `source.py` were extracted; `catalogue.py` now owns snapshot/query behavior only.
- Final read-only review found one availability defect: malformed shared Skills data could prevent the complete server from starting. This was repaired and regression-tested.
- Landing review found two additional correctness defects: configured-root ancestry was resolved before link/reparse validation, and `improve_skill` could report the proposed SHA after a backend no-op or non-exact result. Both were repaired with failing-first regression tests, ancestor checks before resolution, and an exact post-mutation SHA verification.
- No critical, important, or moderate Skills-specific correctness findings remain after repair.

## Verification

Fresh integrated evidence:

```text
pwsh -NoProfile -File .temp/run-focused-tests.ps1 tests/skills
32 passed

pwsh -NoProfile -File scripts/smoke-skills-module.ps1
ok=true; tool_count=39; skills_tool_count=9; catalogue_skill_count=17
quarantine_operation_id=20260804T174952575845Z-3fd25703ea91

pwsh -NoProfile -File scripts/verify.ps1
64 Python files parsed
change governance passed with 10 claims
all tests passed with two existing skips
policy rules: HR-001, HR-002, HR-003

pwsh -NoProfile -File scripts/change-workflow.ps1 check
passed with only declared owned/shared paths

git diff --check
passed
```

## Recovery

Close the draft PR and abandon `change/012-skills-module`. Repository tests do not mutate the shared runtime Skills root. The live smoke quarantined its temporary skill recoverably. A failed runtime create may leave recoverable staging residue beneath the configured kis-mcp temp root; no permanent cleanup operation is added.

## Residual risks and deferred work

- Desktop Commander continues to emit existing notification-validation warnings during local in-process proxy calls. Tool results remain successful; provider notification handling is outside this slice.
- The initial conservative frontmatter parser intentionally supports a bounded YAML subset. Expand it only with a concrete shared-skill compatibility case and tests.
- Further catalogue splitting is deferred until repeated independent change reasons establish a real seam; premature micro-modules would add indirection without evidence.
- The user-supplied post-merge review of PR #13 identifies separate Discover defects: strict schema omission of `recent_commits`, unvalidated effective Git metadata paths, nondeterministic cutoff selection, silent Python diagnostic truncation, and missing diagnostic evidence links. Those findings are inherited from `origin/main`, are not caused or modified by this Skills slice, and require a separate Discover hardening change.
