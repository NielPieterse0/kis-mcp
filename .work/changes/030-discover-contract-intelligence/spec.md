# Change Specification: Discover Contract Intelligence

## Outcome

Add deterministic bounded contract topology for local OpenAPI JSON, JSON Schema, and checked-in MCP schema documents, including documents, operations, schemas, references, omissions, provenance, confidence, and explicit unsupported-format unknowns.

## Requirements

- Require a project path and explicit positive document, operation, schema, and relationship budgets.
- Validate caller budgets against configured Discover maxima before repository resolution.
- Reuse `ReadAuthority` and `RepositoryScanner`; do not add independent traversal or file-read logic.
- Detect candidate contract documents by bounded path and filename conventions.
- Parse JSON only with the standard library. YAML contract documents must remain explicit unknowns in this slice.
- Extract OpenAPI operations, component schemas, request/response schema references, and stable operation identities.
- Extract JSON Schema roots, `$defs`/`definitions`, required properties, property counts, and local/external `$ref` relationships.
- Classify checked-in MCP request/response/tool schemas without executing or importing repository code.
- Preserve per-document diagnostics so one invalid document does not invalidate independent evidence.
- Return deterministic ordering, provenance, confidence, omissions, truncation reasons, and a stable fingerprint.
- Never use the network, resolve remote refs, execute repository code, mutate artifacts, or change Work policy/shared runtime files.

## Acceptance

1. OpenAPI JSON fixtures yield stable operations, component schemas, and request/response relationships.
2. JSON Schema fixtures yield root/definition schema records and reference relationships.
3. MCP contract schemas are classified from checked-in local evidence.
4. Invalid JSON and YAML candidates produce bounded unknowns while valid documents remain available.
5. Caller budgets truncate after safe configured discovery with truthful omission counts.
6. Repeated identical inputs produce identical substantive JSON and fingerprint.
7. Response and request JSON satisfy strict checked-in schemas.
8. Full Discover and repository verification pass with the exact HR-001/HR-002/HR-003 implementation unchanged.
