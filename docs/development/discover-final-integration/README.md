# Discover Final Integration

## Runtime surface

The bounded local Discover v1 runtime exposes exactly three public workflows:

| Tool | Purpose | Public request boundary |
|---|---|---|
| `inspect_project` | Build bounded repository, code, verification, contract, instruction, Git, finding, recommendation, unknown, and handoff evidence. | One explicit local project and optional supported inspection limits. |
| `inspect_change` | Inspect a bounded working tree, staged set, commit, range, or branch target and return change/impact/verification evidence. | One explicit local project, one supported source, and only the Git refs required by that source. |
| `get_code_context` | Assemble the smallest sufficient local evidence bundle for one task. | One explicit local project, a non-empty task, and complete explicit character/file/symbol/relationship budgets. |

All three tools are registered as read-only, non-destructive, idempotent, and closed-world. Structural request failures and Discover retrieval failures return deterministic JSON `ToolError` payloads and never introduce additional `HR-*` decision codes.

## Composition

The existing top-level server already owns the composition seams:

```text
build_server
├── InspectProjectService
│   └── register_discover_tools
│       ├── inspect_project
│       └── get_code_context
└── change FastMCP mount
    └── register_change_tools
        └── inspect_change
```

`InspectProjectService` remains the server-created façade. Its context method delegates to `ContextBrokerService` using the same configured Discover boundary and settings. No import from Discover into `server.py` was added, and no second runtime or policy authority was introduced.

## Change target contract

`inspect_change` preserves the existing working-tree default and exposes all already-supported local target shapes:

| Source | Required refs | Rejected refs |
|---|---|---|
| `working_tree` | none | `commit_ref`, `base_ref`, `head_ref` |
| `staged` | none | `commit_ref`, `base_ref`, `head_ref` |
| `commit` | `commit_ref` | `base_ref`, `head_ref` |
| `range` | `base_ref`, `head_ref` | `commit_ref` |
| `branch` | `base_ref`, `head_ref` | `commit_ref` |

Git refs continue to use the strict existing validation contract and fixed non-shell Git templates.

## Internal foundations

These completed Discover services remain internal and are intentionally not additional public tools:

- provider-candidate evidence, risk classification, pending Govern admission request, and non-executing Work conformance plan;
- explicit selected-project catalog and static local cross-project relationship evidence;
- analyzer registry, architecture components, Python and JavaScript/TypeScript dependency and impact evidence;
- OpenAPI JSON, JSON Schema, and checked-in MCP contract intelligence.

This preserves the small public surface while allowing later approved workflows to compose the evidence services.

## Completion boundary

The deterministic local Discover v1 runtime is complete when the three tools, local fallbacks, explicit degradation, internal evidence foundations, contracts, and verification pass together.

Optional semantic providers, remote forge evidence, provider registries, background indexes, process-backed analyzers, and additional contract formats remain separately governed expansion work. They must not be represented as installed or ready until admitted and verified.

## Shared-document ownership

During this slice, active change `035-llm-capability` owns `src/kis_mcp/server.py`, `SPEC.md`, and `docs/OPERATIONS.md`. Final Discover runtime composition therefore uses the existing server seams and updates only Discover-owned implementation, tests, the Discover product specification, and this integration record. Shared-document synchronization must occur through the active shared-file owner or after that ownership is released; this slice does not overwrite or bypass it.

## Verification contract

The final integration requires:

- exact Discover registration and annotation tests;
- façade delegation tests;
- all supported `inspect_change` request shapes and invalid-shape tests;
- top-level server membership tests proving the three public operations and excluding internal service names;
- full Discover regressions;
- governance scope and whitespace checks;
- serialized full repository verification on the exact published head.
