# Discover Final Integration

## Runtime surface

The bounded local Discover v1 runtime exposes four public read-only workflows:

| Tool | Purpose | Request boundary |
|---|---|---|
| `inspect_project` | Build bounded repository, code, verification, contract, instruction, Git, finding, recommendation, unknown, and handoff evidence. | One explicit local project and optional supported inspection limits. |
| `inspect_change` | Inspect a working tree, staged set, commit, range, or branch target. | One explicit local project, one supported source, and only the Git refs required by that source. |
| `get_code_context` | Assemble the smallest sufficient local evidence bundle for one task. | One explicit local project, a non-empty task, and explicit character/file/symbol/relationship budgets. |
| `analyze_change` | Normalize a local or supplied change and combine change inventory, transitive impact, affected tests, verification handoffs, and evidence-backed implementation steps. | A supported local Git target or bounded supplied change metadata, optional normalized GitHub PR metadata, task terms, and explicit impact budgets. |

All four operations are read-only, non-destructive, idempotent, and closed-world. Structural failures return deterministic Discover errors and never introduce additional `HR-*` decisions.

## Composition

The existing top-level server composition remains unchanged:

```text
build_server
├── register_discover_tools
│   ├── inspect_project
│   └── get_code_context
└── register_change_tools
    ├── inspect_change
    └── analyze_change
```

`InspectChangeService` composes the existing hardened Git reader with `ImpactGraphService`. This avoids a shared-file collision with active server work and does not add another runtime, policy authority, tool package, or provider package.

## Unified analysis behavior

`analyze_change` supports:

- working-tree, staged, commit, range, and branch targets through fixed local Git templates;
- arbitrary supplied file-change records normalized to repository-relative paths;
- supplied GitHub repository, pull-request number, base/head SHAs, and changed-file records;
- task terms passed into the impact graph rather than reported as unavailable;
- Python symbol and reverse dependency impact plus bounded static JavaScript/TypeScript relationships;
- contract and configuration path relationships using explicit heuristic provenance and confidence;
- deterministic affected-test selection and non-executable verification handoffs;
- evidence-backed implementation steps tied to changed paths, relationships, tests, and verification declarations.

GitHub context is input normalization only. Discover does not call a connector, access the network, or infer missing remote evidence.

## Internal foundations

Raw `inspect_impact`, provider admission, and explicit project-catalog services remain internal. They are composed by the public workflows or reserved for later approved integration rather than registered as separate tools.

## Completion boundary

The local Discover solution is complete for the approved donor capability set when public workflows, local and supplied change normalization, impact relationships, task terms, implementation steps, schemas, parity tests, and repository verification pass together.

Still excluded by design:

- executing GitHub or other forge connectors from Discover;
- dynamic JavaScript imports, alias/package resolution, and external module resolution;
- installing or activating semantic providers, tool packages, or provider packages;
- executing verification commands inside Discover;
- background indexing or implicit scans of `C:\Projects`.

## Verification contract

Completion requires:

- request/response schema validation for `analyze_change` and `inspect_impact`;
- public tool registration and annotations;
- local target, supplied change, and GitHub metadata normalization tests;
- task-term, contract/configuration relationship, implementation-step, affected-test, and verification-handoff tests;
- full Discover regression, governance scope, whitespace, syntax, and repository verification on the published head.
