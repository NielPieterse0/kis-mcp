# Closeout: Discover Context Broker

## Implemented scope

- Added strict immutable `get_code_context` request, budget, provenance, file, module, symbol, relationship, unknown, omission, and response contracts.
- Added strict draft-2020-12 request and response schemas with stable schema version and tool identity.
- Added deterministic task tokenization, category intent, path/module/symbol/relationship scoring, stable tie-breaking, and canonical fingerprints.
- Added `ContextBrokerService` composition over the existing `ReadAuthority`, `RepositoryScanner`, `PythonProjectIndexer`, and `GitReader` boundaries.
- Ranked repository metadata before content reads and read only the selected top-ranked repository-relative files.
- Added line-aware bounded excerpts, AST-confirmed modules/symbols/imports/calls/inheritance, compact local Git state, provider readiness, explicit unknowns, omission counters, confidence, and truncation reasons.
- Added deterministic serialized-character compaction that shrinks excerpts and removes lowest-ranked relationships, symbols, modules, and files until the exact caller budget is met or fails explicitly when the minimum contract cannot fit.

## Validation evidence

- Contract/schema tests passed: 4.
- Pure ranking/determinism tests passed: 5.
- Broker real-repository fixture tests passed: 8.
- Context plus architecture gate passed: 20 tests.
- Full Discover suite passed with one expected skip.
- `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed with all changed paths inside the declared claim.
- `git diff --check` passed.
- Final `pwsh -NoProfile -File .\scripts\verify.ps1` passed: all tests passed with 2 expected skips, 81 Python files passed syntax validation, and line-ending, configuration, interpreter, dependency, governance, and exact three-rule checks passed.

## Review

- Reviewed request maxima before repository resolution, scanner/read/Git/Python adapter reuse, metadata-first ranking, excerpt boundaries, relationship connectivity, deterministic ordering, fingerprint identity, schema strictness, output compaction, failure degradation, and the Discover/Work boundary.
- Found and repaired unbounded local Git changed-path context by narrowing it to `budget.max_files`, reporting omitted changed paths, and marking Git context truncated.
- Found and repaired misleading omission reasons: unreadable or character-compacted evidence no longer claims `max_files`, `max_symbols`, or `max_relationships` unless those explicit limits were reached.
- Found and repaired the no-file compaction edge case so the final response always reports `NO_RELEVANT_FILE_CONTEXT` when character compaction removes all file evidence.
- No unresolved P0-P2 findings remain.

## Git and merge

- Branch: `change/028-discover-context-broker`
- Worktree: `.work/worktrees/028-discover-context-broker`
- Commit: pending publication
- Pull request or merge: pending publication
- Cleanup: pending merge

## Residual items

- Public FastMCP registration and shared runtime composition remain intentionally deferred to the Discover integration slice because active change `026-commissioning-refresh` owns the shared integration files.
- External semantic providers, remote forge evidence, persistent indexes, vector retrieval, and cross-repository context remain later roadmap slices and are reported through provider state and unknowns rather than inferred.
