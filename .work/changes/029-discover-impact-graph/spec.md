# Change Specification: Discover Impact Graph

## Outcome

Add deterministic bounded impact evidence that maps explicit changed repository paths to Python symbols, reverse module/symbol dependants, affected tests, and typed discovered verification handoffs.

## Requirements

- Require a project path, non-empty normalized changed paths, and explicit positive budgets.
- Reuse `ReadAuthority`, `RepositoryScanner`, `PythonProjectIndexer`, and `VerificationDiscoveryService`.
- Treat symbols declared in changed Python files as changed symbols.
- Derive reverse dependants from internal imports, call names, and inheritance names using deterministic conservative matching.
- Identify affected tests through graph connections and conventional module-name matching.
- Return discovered verification declarations as non-executing Work handoffs only.
- Preserve provenance, confidence, unknowns, omissions, truncation reasons, and a stable fingerprint.
- Never execute repository code, verification commands, tests, builds, hooks, package managers, or network operations.
- Keep Work policy and shared runtime files unchanged.

## Acceptance

1. Changed Python paths produce deterministic changed-symbol records.
2. Importing modules, callers, and subclasses are returned as typed dependant edges.
3. Connected and conventionally matching tests rank before unrelated tests.
4. Verification declarations remain `execution_available=false` and are represented as Work handoffs.
5. Unsupported languages and incomplete parses remain explicit unknowns.
6. Budgets truncate deterministically with exact omission counters.
7. Repeated identical inputs produce identical substantive JSON and fingerprint.
8. Full repository verification and exact three-rule checks pass.
