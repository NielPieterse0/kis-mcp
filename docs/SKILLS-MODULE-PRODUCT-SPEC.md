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
   |-- record attributed outcomes and report usage evidence
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
| `record_skill_outcome` | Record caller-attributed `applied`, `completed`, or `failed` evidence only when it matches a prior observed load for the exact skill/package hash and activation identity. |
| `skill_telemetry_report` | Return the backwards-compatible bounded usage/outcome aggregates grouped by skill package hash and project. |
| `skill_delivery_telemetry_report` | Compare bounded usage/outcome evidence for the same canonical skill/package hash across `kis_native` and `mcp_resource` delivery. |

## MCP Skills extension delivery

The same immutable validated catalogue is also exposed through the draft SEP-2640 `io.modelcontextprotocol/skills` extension. This is a read-only delivery surface, not a second catalogue or lifecycle authority.

| Extension surface | Meaning |
|---|---|
| `skills/list` | Paginated active-snapshot entries with verbatim frontmatter, `resultType: complete`, private zero-TTL cache metadata, and a complete per-file `{uri, digest, size}` manifest. |
| `skills/get` | URI-keyed retrieval of one canonical skill entry independent of whether it appeared in a prior listing. |
| `resources/read` on `skill:///<skill-id>/<relative-path>` | Exact bytes for one file represented by the active validated snapshot. |
| `resources/directory/read` | Optional `directoryRead` enumeration of direct children only; directory resources use `inode/directory`. |

The extension advertises the pinned draft baseline `draft-v1-2026-08-25` through FastMCP's extension capability surface, and its methods require per-request client negotiation. Individual resources use canonical direct `skill:///` URIs; archives and alternate package carriers are not exposed. Before returning bytes, KIS revalidates the path boundary and verifies size plus SHA-256 against the active snapshot, so post-snapshot mutation, traversal, link/reparse escape, unsupported package content, or other integrity drift fails closed.

The advertised manifest is content-binding evidence. Host-side verification helpers reject unlisted resources, digest/size mismatches, and `SKILL.md` frontmatter that differs from the advertised entry. A persisted approval fingerprint binds the host-assigned originating-server identity, canonical skill URI, and complete resource URI/digest/size set, so server identity changes or adding, removing, or changing a file requires reapproval. KIS serves only stable manifest-backed skills and rejects SEP-2640 exposure above 512 resources or 16,777,216 total bytes; the stricter configured catalogue size limits still apply first.

The runtime also exposes reusable in-process MCP-extension commissioning. Commissioning uses FastMCP's real client/session dispatcher against the running server object; it does not call extension handlers directly and does not use localhost or outbound HTTP. A receipt binds the process/server identity fingerprint, source revision, negotiated MCP protocol version, extension ID/settings, profile ID, timestamp, method-level outcomes, and overall PASS/FAIL. Receipt reuse fails closed when any bound identity changes; the SEP-2640 profile additionally invalidates prior evidence when its deterministically selected canonical skill or complete advertised resource set drifts. The SEP-2640 profile proves advertised settings, `skills/list`, `skills/get`, entrypoint resource integrity, optional directory enumeration, and the negative unnegotiated `METHOD_NOT_FOUND` control.

Resource delivery grants no execution authority. Script files and other executable-looking assets are returned only as data. Existing KIS-native Skills tools, mutation routing through Work middleware, catalogue authority, and telemetry remain unchanged.

## Usage telemetry

KIS observes discovery, load, resource discovery/read, refresh, evaluation, creation, and improvement without retaining prompts, skill/file contents, search text, credentials, or arbitrary tool arguments. Package-level SHA-256 from the immutable catalogue is the version identity; resource reads do not create separate file-hash versions.

Loads are not treated as applications. `record_skill_outcome` is the only public path for application/completion attribution, and reported evidence is kept distinct from observed runtime evidence. A reported outcome must match an earlier observed load by skill ID, activation ID, snapshot ID, package SHA-256, project identity when supplied, and delivery path. For `mcp_resource`, that prior load must also carry the current canonical `skill:///<skill-id>/SKILL.md` identity; stale or mismatched canonical identity is not valid attribution. The backwards-compatible default delivery path is `kis_native`.

MCP delivery is attributed at the `resources/read` boundary as `mcp_resource`. An entrypoint read records a load; a supporting-resource read records a resource read; reading a catalogue page records catalogue exposure only. Passive `resources/list` and `resources/templates/list` enumeration records no meaningful skill use. MCP events retain the canonical package SHA-256 plus resource URI, resource class, server/origin identity, and digest-verification result. Digest attribution compares the already-returned resource bytes with immutable snapshot metadata and does not reread the filesystem. Telemetry persistence is observational: a telemetry-write failure is logged but cannot overturn an otherwise successful canonical resource response. Optional activation/project correlation is accepted only from request `_meta` keys `kis_activation_id` and `kis_project_id`; ordinary request correlation continues to use the runtime request identity.

Production composition persists the redacted event contract beneath `<state_root>\telemetry\skills.sqlite3` with bounded retention. Existing databases migrate additively: prior rows remain `kis_native`, while new MCP-only attribution columns are added without rewriting the existing native event/report contract. Live evidence also appears in the existing bounded `RuntimeObservability`/Control Center snapshot. Optional duration, token, tool-call, retry, verification, and MCP digest metrics are stored only when actually observed or explicitly reported; absent values remain not observable.

`skill_telemetry_report` preserves the existing version/project grouping and counters. `skill_delivery_telemetry_report` groups the same canonical skill/package hash/project by `kis_native` versus `mcp_resource` and reports whether an exact-hash cross-path comparison is valid. A comparison requires at least one successful observed entrypoint load on both delivery paths. Missing counterparts, missing path-specific loads, different package hashes, failed digest verification, or unverified MCP digests are explicitly non-comparable rather than silently pooled. MCP reporting separately exposes protocol list/get/directory observations, negative-negotiation evidence, ordinary digest-verified loads, commissioning-correlated loads, authoritative live commissioning proof, and uncommissioned loads. Commissioning correlation binds the receipt ID, server identity fingerprint, protocol version, extension identity/settings, canonical skill URI, and complete resource-set fingerprint without retaining prompts, resource contents, search text, credentials, or arbitrary tool arguments. Neither report calculates one opaque quality score or decides whether a skill should be admitted, retained, or withdrawn; those behavioral decisions belong to downstream skill-evaluation authority.

## Module boundaries

```text
skills.config       strict JSON configuration and limits
skills.frontmatter  conservative SKILL.md metadata parser
skills.source       path safety, file collection, and source normalization
skills.catalogue    immutable snapshots, read/query operations, and snapshot-verified resource bytes
skills.resources    legacy-compatible read-only FastMCP resource index and templates
skills.sep2640      negotiated SEP-2640 list/get/directory methods plus direct resource provider and content-binding verification
skills.delivery_telemetry  MCP resource-boundary attribution and digest evidence
skills.backend      narrow Work mutation protocol and FastMCP adapter
skills.telemetry    bounded redacted live/durable usage, outcome, and delivery comparison evidence
skills.service      query/mutation orchestration, telemetry, and optimistic concurrency
skills.tools        thin public FastMCP tool registration
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
- Text files must be UTF-8; configured binary package resources remain hash/size validated and are returned only through the read-only MCP resource surface as exact bytes.
- A refresh is atomic: any invalid source rejects the candidate refresh and preserves the prior active snapshot.
- Initial catalogue failure is fail-open for the wider server: ordinary Work/gateway tools remain available, the twelve Skills operations remain discoverable, and Skills calls return the corrective initialization failure until the source is repaired and the server is restarted.
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

The repository MUST NOT contain a local skill catalogue. Agents discover, load, and read reusable procedures only through the Skills-module operations; the configured shared catalogue path is owned by the module and is not a supported direct agent-access path.

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
