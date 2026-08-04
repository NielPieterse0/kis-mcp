# Skills Module Product Specification

## Status

Implemented current capability of `kis-mcp`.

## Purpose

The Skills module exposes reusable procedure packages stored beneath the operator-approved shared root:

```text
C:\Projects\.agents\skills
```

A skill is a directory containing a required `SKILL.md` entrypoint and optional bounded supporting files. Skills are reusable instructions, not repository-specific authority and not executable server plugins.

```text
ChatGPT
   |
   v
kis-mcp Skills interface
   |-- list, search, load, read, evaluate
   |-- create and improve
   |
   +-- immutable bounded catalogue
   |       |
   |       v
   |   C:\Projects\.agents\skills
   |
   +-- mutation service
           |
           v
      FastMCP.call_tool(run_middleware=True)
           |
           v
      ThreeRuleMiddleware
           |
           v
      Desktop Commander Work backend
```

ChatGPT loads skill instructions and performs the described workflow by calling ordinary kis-mcp Work tools. The Skills module does not import, evaluate, or automatically execute arbitrary skill code.

## Public operations

| Operation | Responsibility |
|---|---|
| `list_skills` | Return paginated skill cards from the immutable active snapshot. |
| `search_skills` | Search canonical skill identity and metadata. |
| `load_skill` | Return the `SKILL.md` entrypoint and bounded structural evidence. |
| `search_skill_files` | Search bounded relative file paths within one skill. |
| `read_skill_file` | Read one file represented by the active snapshot. |
| `refresh_skills` | Rebuild and atomically replace the active snapshot after complete validation. |
| `evaluate_skill` | Return bounded structural evidence derived from the active snapshot. |
| `create_skill` | Validate, stage, and publish one new skill through the Work backend. |
| `improve_skill` | Replace one existing text file using an expected SHA-256 precondition through the Work backend. |

## Module boundaries

```text
skills.config       strict JSON configuration and limits
skills.frontmatter  conservative SKILL.md metadata parser
skills.source       path safety, file collection, and source normalization
skills.catalogue    immutable snapshots and read/query operations
skills.backend      narrow Work mutation protocol and FastMCP adapter
skills.service      create/update orchestration and optimistic concurrency
skills.tools        thin public FastMCP registration
skills.models       explicit versioned response contracts
skills.errors       corrective SKILLS_* structural failures
```

Dependency direction is enforced by architecture tests. Public tools depend on the service; the service depends on the catalogue and backend protocol; the backend adapter re-enters the already-configured FastMCP server. The Skills module has no dependency on Desktop Commander internals or provider-specific implementation code.

## Catalogue and validation

- `settings/skills.settings.json` is the canonical configuration.
- `contracts/skills/settings.schema.json` defines its closed schema.
- Canonical IDs are lowercase hyphenated `name` values from `SKILL.md` frontmatter.
- `name` and `description` are required.
- Files, total skill bytes, result counts, suffixes, and query limits are JSON-configured.
- Traversal, absolute paths, backslashes, symbolic links, reparse points, and configured hard-link cases are rejected.
- Text files must be UTF-8; configured PNG files are represented as binary metadata without returning binary content.
- A refresh is atomic: any invalid source rejects the candidate refresh and preserves the prior active snapshot.
- Initial catalogue failure is fail-open for the wider server: ordinary Work/gateway tools remain available, the nine Skills operations remain discoverable, and Skills calls return the corrective initialization failure until the source is repaired and the server is restarted.
- Snapshot IDs are deterministic SHA-256-derived fingerprints of normalized skill metadata and file evidence.

These are retrieval and structural correctness boundaries. They do not add a fourth Work policy rule.

## Mutation model

### Create

1. Refresh the current catalogue.
2. Validate the proposed `SKILL.md` as a complete single-file skill.
3. Create a unique staging directory beneath `C:\Projects\.kis-mcp\temp\skills`.
4. Call Desktop Commander `create_directory` and `write_file` through `FastMCP.call_tool(..., run_middleware=True)`.
5. Publish with Desktop Commander `move_file` to the shared Skills root.
6. Refresh and return the new snapshot ID and SHA-256.

A failed create may leave recoverable staging residue beneath the configured temp root. No permanent cleanup operation is introduced.

### Improve

1. Refresh the current catalogue.
2. Validate the complete proposed skill after substituting the candidate file.
3. Compare the caller-provided SHA-256 with the active file hash.
4. Call Desktop Commander `edit_block` with the exact previous content and `expected_replacements=1`, through the server middleware.
5. Refresh and return before/after hashes and the new snapshot ID.

The hash precondition prevents silent overwrite after concurrent external edits.

## Policy and authority

Skills mutations remain ordinary Work invocations and are governed only by:

- HR-001 — no writes outside `C:\Projects`;
- HR-002 — no unrestricted external network through Work;
- HR-003 — no permanent deletion.

Skill presence, status, category, metadata, evaluation evidence, catalogue membership, or validation state cannot become an independent reason to block an otherwise permitted Work invocation.

Repository-local `.agents/skills` remains development guidance for this repository. Runtime skills are resolved only from the separate shared root `C:\Projects\.agents\skills`.

## Errors

Structural and application failures use corrective `SKILLS_*` codes, including invalid settings, unsafe paths, malformed frontmatter, unsupported files, stale cursors, unknown skills/files, hash mismatches, rejected refreshes, and backend failures. HR policy failures continue to originate from the existing Work middleware.

## Non-goals

The module does not:

- execute arbitrary skill scripts automatically;
- download, install, publish, or synchronize skills over a network;
- introduce a replacement filesystem or terminal;
- bypass the Work middleware for mutations;
- treat skills as repository authority;
- add capability tiers, approval rules, allowlists, denylists, or another policy prohibition.
