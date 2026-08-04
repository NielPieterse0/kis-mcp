# 024 Discover Change Tool Registration Specification

## Status

Approved bounded implementation slice. Development level: **Medium** because it changes the public FastMCP catalogue and server composition across multiple files, while remaining additive, read-only, stateless, and readily reversible.

## Outcome

Expose the merged internal working-tree `InspectChangeService` through one public read-only `inspect_change(path)` tool without changing `inspect_project`, expanding supported change sources, modifying Work policy, or overlapping the active Discover response-hardening slice.

## Design decision

Use a dedicated `change_tools.py` binder rather than extending `discover/tools.py` or creating a combined Discover facade. The binder accepts an injected `InspectChangePort`; `build_server()` constructs the existing `GitReader`, `ReadAuthority`, and `InspectChangeService`, then registers the new tool additively.

## Requirements

- **R1** — Register exactly one tool named `inspect_change` from the new binder.
- **R2** — The public request accepts only a non-empty local `path`; the implementation constructs `InspectChangeRequest(path=path)` and therefore supports only the fixed `working_tree` source.
- **R3** — Return the service response through its exact `to_json_dict()` contract without reshaping fields.
- **R4** — Mark the tool read-only, non-destructive, idempotent, and closed-world through FastMCP annotations.
- **R5** — Convert structural request `ValueError` failures into deterministic JSON `ToolError` payloads using a `DISCOVER_CHANGE_REQUEST_INVALID` code and no `HR-*` code.
- **R6** — Compose the service from the current runtime project boundary and Discover settings using the existing `ReadAuthority` and `GitReader`; do not add network, repository-code execution, settings, persistent state, or policy behavior.
- **R7** — Preserve the existing `inspect_project`, gateway, Skills, and provider registration behavior.
- **R8** — Keep refs, commits, ranges, branch comparisons, pull requests, semantic symbols, dependant mapping, verification handoffs, and remote evidence outside this slice.

## Acceptance evidence

- Test-first binder tests prove exact tool registration, annotations, request delegation, exact response passthrough, and structural error normalization.
- Server composition tests prove `inspect_change` appears additively beside the existing local tools.
- Scope validation proves no overlap with active change `016-discover-response-hardening` or provider change `022-supabase-oauth-commissioning`.
- Focused Discover tests, architecture checks, whitespace checks, and serialized full verification pass on the final branch state.

## Documentation integration constraint

`SPEC.md` and `docs/OPERATIONS.md` are currently owned by active change `022-supabase-oauth-commissioning`. This slice must not edit those files concurrently. Before merge, ownership must be released and the current public-interface documentation must be reconciled, or the branch must remain unmerged.

## Recovery

Remove the `register_change_tools()` call and delete the additive binder and tests. No migration, setting, credential, generated state, or persistent data is created.
