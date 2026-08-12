# Change Specification: DBHub and Docker Hub Provider Integration

- **Change ID**: `109-db-docker-provider-integration`
- **Status**: Review
- **Development level**: Complex
- **Risk profile**: rigorous
- **Dependency**: `108-current-baseline-sweep-hardening`

## Outcome

Integrate Bytebase DBHub and Docker Hub MCP as first-class modular KIS providers without vendoring or reimplementing either upstream MCP server. Preserve the existing Provider, Project, capability, readiness, progressive-exposure, secret, commissioning, and three-rule boundaries.

The completed change must provide a low-friction user experience: stable operation names, project-aware database routing, accurate readiness/status guidance, bounded installation and commissioning commands, discoverable long-tail capability, and no stale current-state documentation after merge.

## Authority and source evidence

Repository authority remains, in order: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`. `docs/PROVIDER-MODULE-PRODUCT-SPEC.md` is the durable provider-domain specification subordinate to those authorities.

Upstream implementation sources are evidence only:

- DBHub: `https://github.com/bytebase/dbhub`, approved target release `v1.2.0`, source commit `1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0`.
- Docker Hub MCP: `https://github.com/docker/hub-mcp`, exact approved source commit `ad806e2cab0489a296aec0f32f3d3eea807d65c2`.
- DBHub npm/release identity must be reconciled during bootstrap design; runtime MUST NOT resolve `latest` or combine unmatched source/package versions.

## Coordination and implementation gate

108 currently owns `src/**`, `tests/**`, `docs/**`, `settings/**`, `scripts/**`, `contracts/**`, `policy/**`, `SPEC.md`, `README.md`, `AGENTS.md`, `pyproject.toml`, and `uv.lock`. 109 MUST NOT edit those paths while 108 remains active.

Before implementation begins, 109 MUST:

1. confirm 108 is merged/closed and its worktree claim is released;
2. update the 109 branch/worktree from the resulting current `main` without discarding 109 change records;
3. rerun change-claim validation and expand `scope.json` to exact implementation/test/documentation paths;
4. reread all canonical authorities changed by 108;
5. rerun a stale-provider/documentation sweep before the first implementation edit.

## Architectural decisions

### AD-001 — Thin provider adapters

KIS MUST own only provider settings, project routing, secret indirection, lifecycle, readiness, capability metadata, namespace composition, commissioning, and verification. DBHub and Docker Hub MCP remain upstream-owned implementations and MUST NOT be copied into `src/kis_mcp`.

### AD-002 — Pinned local stdio runtime

Both providers MUST run as supervised local Node/stdio processes behind FastMCP. Normal KIS startup MUST NOT install, update, clone, pull, or resolve provider dependencies from the network.

Provider bootstrap MUST activate only an exact verified source/artifact identity beneath `C:\Projects\.kis-mcp`, record the digest/version in strict JSON, and retain replaced installations recoverably rather than permanently deleting them.

### AD-003 — Stable database operation names

DBHub native naming changes when a deployment moves from one source to multiple sources. KIS MUST prevent that upstream detail from renaming existing user-facing operations.

The DBHub adapter MUST start one isolated upstream DBHub stdio process per registered database binding and mount each process beneath a deterministic internal namespace derived from the registered IDs. The outer KIS provider namespace is `db`. Internal namespace normalization replaces the hyphens in the lower-case kebab-case `project_id` and `binding_id` with underscores and joins them as `<project_slug>_<binding_slug>`; because registry IDs cannot contain underscores, this mapping is deterministic and collision-free for valid IDs. Configuration MUST fail rather than truncate if a resulting MCP operation name exceeds the supported name contract.

Expected stable names therefore follow this shape:

```text
db_<project_slug>_<binding_slug>_search_objects
db_<project_slug>_<binding_slug>_execute_sql
db_<project_slug>_<binding_slug>_explain_sql
db_<project_slug>_<binding_slug>_health_check
```

Only tools enabled for that binding may appear. Adding another database MUST NOT rename or remove an existing binding's operations.

### AD-004 — Source-aware database boundary

The project registry owns database routing. A database binding declares whether its target is `local` or `external`; this is routing/effect evidence, not a fourth Work policy rule.

The Provider model MUST add `ProviderBoundary.SOURCE_AWARE_CONNECTOR` with serialized value `source_aware_connector` so one DBHub descriptor can accurately contain both local and approved-external bindings without misclassifying either. Per-binding capabilities MUST carry exact operation effects: local bindings are `read_only`; external bindings are `read_only` plus `external`.

DBHub configuration remains read-only in this change for every source. Database mutation, writable custom SQL tools, schema migration, DDL, `INSERT`, `UPDATE`, and `DELETE` are out of scope.

### AD-005 — KIS JSON remains configuration authority

KIS MUST NOT add a checked-in authoritative `dbhub.toml`. Provider and project configuration remain JSON.

For each DBHub binding, KIS generates a bounded runtime TOML beneath `C:\Projects\.kis-mcp\dbhub\runtime\<project_id>\<binding_id>\`. The generated file is runtime state, not repository authority.

For local SQLite, the configured relative path MUST resolve inside the registered project root and the generated DBHub source MUST open it read-only. For external databases, repository JSON stores only a non-secret vault reference; the generated TOML uses environment interpolation and the resolved DSN exists only in process-scoped environment state.

Every generated `execute_sql` tool MUST set `readonly = true` and a JSON-owned positive `max_rows`. Optional `explain_sql` and `health_check` enablement is JSON-owned per provider policy, not caller-selected at startup.

The project-registry database shape MUST be strict and credential-free. Each project gains `databases` as an array. Each binding contains exactly `binding_id`, `engine`, `boundary`, `location`, and `secret_ref`. `engine` is one of `sqlite`, `postgres`, `mysql`, `mariadb`, or `sqlserver`. A `local` binding requires a non-empty relative `location` and `secret_ref: null`; an `external` binding requires `location: null` and a valid `secret://...` reference. Binding IDs are lower-case kebab-case and unique within the project.

Example local binding:

```json
{"binding_id":"results","engine":"sqlite","boundary":"local","location":"results\\college.db","secret_ref":null}
```

### AD-006 — Docker Hub is not Docker Engine

Docker Hub MCP is an approved external connector for Docker Hub repository/image metadata and supported Hub management operations. Local Docker Engine actions such as `docker build`, `run`, `exec`, `logs`, `inspect`, `pull`, and `push` remain ordinary local process/Work capabilities and MUST NOT be reimplemented by this provider.

The Docker Hub provider uses outer namespace `dockerhub` and preserves the approved upstream tool names beneath that namespace. Its source revision is fixed to `ad806e2cab0489a296aec0f32f3d3eea807d65c2`.

### AD-007 — Docker Hub authentication and project routing

Public Docker Hub discovery MUST remain usable without credentials where the upstream provider supports it. Authenticated/private-account capability MUST use the KIS secret boundary; no PAT value may appear in repository JSON, generated profiles, logs, status output, or retained command arguments.

The provider settings may store non-secret authentication metadata and a canonical vault reference.

Project-specific Docker Hub routing belongs in `settings/projects.settings.json`, not provider authentication settings. Each project gains `dockerhub`, either `null` or an object containing exactly `namespace`. KIS MUST NOT invent Docker Hub bindings for Commodity, College, or another project when the repository does not establish them.

Provider authentication settings MUST use an explicit mode: `public` or `pat`. `public` stores no username or secret reference and exposes only operations that can succeed without authentication. `pat` stores a non-secret account username plus a canonical PAT secret reference. Provider adapter code MUST NOT unlock or read the KIS vault directly. The supervised launcher secret boundary used today for runtime secrets MUST be generalized and shared by local stdio and ChatGPT launchers: it resolves configured DBHub/Docker Hub secret references using the verified runtime unlock, injects only opaque KIS-internal environment names into the parent KIS process, and clears launcher-held values after process creation. The provider builder maps only its resolved internal value into the upstream child environment (`DBHUB_DSN` for one DBHub binding or `HUB_PAT_TOKEN` for Docker Hub) and MUST NOT forward the full parent environment. The adapter MUST suppress or mark status-only any upstream operation whose required authentication/routing prerequisites are not satisfied.

If authenticated tools require an account identity that is not configured or commissioned, status and capability exposure MUST make that limitation visible rather than presenting failing operations as ready.

### AD-008 — Progressive exposure and tool UX

Neither provider may inflate the normal direct tool list. Provider operations are discoverable long-tail operations unless an existing direct-profile rule explicitly promotes them.

`search_capabilities`, `describe_capability`, `recommend_workflow`, and the effect-specific dispatchers MUST expose accurate operation descriptions, input schemas, effects, readiness, and project/binding identity.

DBHub's descriptor MUST be constructed from the immutable central project registry so every configured binding/tool is predeclared with its exact final KIS operation name and exact effects before generic runtime-surface augmentation. Generic name/annotation inference MUST NOT decide whether a database operation is local or external. DBHub operation descriptions MUST identify the project, binding ID, database engine, local/external boundary, and read-only status; database-query guidance SHOULD lead with schema discovery (`search_objects`) before free-form SQL when the schema is not already known.

Docker Hub operation descriptions/status MUST make public-versus-authenticated availability clear and retain the upstream input schema. Capability search terms SHOULD include `database`, the configured database engine, `docker`, `dockerhub`, `image`, `repository`, and `tag` so users can find the tools without knowing provider-native names.

User-facing status MUST distinguish at least: installed, configured, credential/authentication requirement, upstream process connection/tool discovery, project/binding availability, and live verification. A provider failure MUST remain contained and MUST NOT prevent Work, deterministic Discover, Skills, Control Center, or unrelated providers from starting.

## Functional requirements

- **REQ-001 — Provider modules:** add isolated `dbhub` and `dockerhub` provider packages with strict settings, readiness, builder/runtime, registration, and focused tests.
- **REQ-002 — Runtime registration:** extend explicit platform registration and runtime settings with approved provider IDs/namespaces; no dynamic arbitrary provider import.
- **REQ-003 — Project contracts:** extend the central project registry/schema with optional database bindings and optional Docker Hub routing while preserving exact-key validation and existing project compatibility.
- **REQ-004 — Stable DBHub composition:** construct one DBHub child process per registered binding, aggregate them behind one provider FastMCP server, and guarantee deterministic stable operation names.
- **REQ-005 — Read-only DB policy:** enable only read-only DBHub SQL/search/optional explain/health operations and enforce row/query bounds from JSON-owned settings.
- **REQ-006 — Secret isolation:** use canonical KIS vault references for remote DB DSNs and Docker Hub PAT material; redact secret values from exceptions, status, commissioning artifacts, and tests.
- **REQ-007 — Offline normal startup:** startup/readiness may validate installed provider state but may not download, install, update, or resolve `latest`.
- **REQ-008 — Supervised bootstrap:** provide bounded install/bootstrap commands that verify exact provider identity, version/revision, integrity, Node compatibility, and staged activation under `C:\Projects\.kis-mcp`.
- **REQ-009 — Capability accuracy:** all mounted tools must have correct read-only/external effects and dispatch through the matching existing effect-specific dispatcher.
- **REQ-010 — Failure containment:** missing installation, missing optional credentials, malformed generated runtime config, child-process failure, or mount failure must produce bounded corrective provider status without taking down unrelated KIS capabilities.

- **REQ-011 — College binding:** add only the database binding supported by current College repository evidence: the local `results/college.db` SQLite registry. Do not modify College repository code.
- **REQ-012 — Commodity restraint:** do not add a database or Docker Hub binding for Commodity unless current repository evidence at implementation time proves a concrete binding. Provider support may exist without a project binding.
- **REQ-013 — Docker Hub surface:** preserve the exact approved upstream Docker Hub MCP surface under the KIS namespace; classify account/repository mutations as external operations and keep local Docker Engine work separate.
- **REQ-014 — No new Work rule:** provider settings, database source type, authentication state, project routing, and capability exposure must not alter HR-001, HR-002, or HR-003 semantics or add another Work rejection reason.
- **REQ-015 — User guidance:** provider status and operations documentation must tell the operator the next actionable step for install, credential setup, project binding, commissioning, and recovery without requiring knowledge of internal adapter classes.
- **REQ-016 — Drift prevention:** all current-authority documents, schemas, settings, tests, examples, generated-state diagrams, provider rosters, counts, and KIS skill guidance affected by this integration must be reconciled in the same delivered change.

## Documentation and artifact reconciliation

After implementation is current and verified, reconcile durable facts into their existing owners rather than creating new overlapping top-level documents.

At minimum review and update when affected:

- `SPEC.md` — current implemented provider/project/configuration truth;
- `docs/PROVIDER-MODULE-PRODUCT-SPEC.md` — provider boundary, module structure, registration, runtime and adapter rules;
- `docs/OPERATIONS.md` — generated state, configuration, bootstrap, startup, commissioning, troubleshooting and recovery;
- `docs/PLATFORM-CONCEPT.md` — current-capability/status projections only where implementation changes those sections;
- `README.md` — orientation/navigation only if the new providers change the useful quick-start surface;
- `settings/projects.settings.json` and its schema/contracts — project routing;
- `settings/providers/platform-runtime.provider.json` and its schema/contracts — approved runtime mounting;
- new provider JSON settings/contracts — exact non-secret provider identities and runtime limits;
- `.agents/skills/kis-mcp/SKILL.md` and only the applicable references — user-facing provider/tool operation guidance;
- Control Center/status tests or projections — only where provider/project status presentation changes;
- commissioning/bootstrap scripts and tests — exact operator workflow and recovery behavior.

The implementation closeout MUST run a repository-wide current-authority stale-string sweep for old provider rosters/counts, old generated-state trees, superseded project-registry shapes, and obsolete installation/commissioning guidance. Historical `.work` records and intentionally historical development evidence are not rewritten merely to match current state.

## Verification requirements

Focused verification MUST cover:

1. strict DBHub and Docker Hub provider settings parsing, exact source/revision identity, and path containment;
2. central project-registry compatibility plus valid/invalid database and Docker Hub bindings;
3. stable DBHub names before and after adding a second synthetic binding;
4. local SQLite read-only opening and rejection of mutating SQL;
5. generated DBHub TOML containing no resolved remote DSN secret and enforcing read-only/max-row settings;
6. secret redaction for provider readiness, builder errors, commissioning output, and runtime status;
7. Docker Hub public/no-auth readiness and authenticated readiness when a test credential is injected;
8. provider registration, namespace uniqueness, runtime mount containment, capability effects, progressive exposure, and effect-specific dispatch;
9. provider absence/failure not breaking unrelated gateway surfaces;
10. canonical documentation/status assertions that fail when provider roster/configuration guidance drifts.

Repository verification MUST finish with `pwsh -File scripts/change-workflow.ps1 check` and `pwsh -File scripts/verify.ps1` on the final implementation state. Live commissioning is additional evidence and does not replace deterministic verification.

## Acceptance criteria

1. **Given** a clean current `main` after 108, **when** 109 implementation begins, **then** its scope claim names every edited implementation/test/documentation path and has no uncoordinated overlap.
2. **Given** a registered College SQLite binding, **when** the DBHub provider starts, **then** KIS exposes stable `db_college_<binding>_*` read-only operations without creating or modifying the database.
3. **Given** a second database binding is later added, **when** the provider restarts, **then** the first binding's existing KIS operation names are unchanged.
4. **Given** an external database binding, **when** KIS creates DBHub runtime state, **then** no resolved DSN credential is written to tracked or generated configuration and the operation is classified as external read-only.
5. **Given** mutating SQL, **when** it is sent to a 109 DBHub `execute_sql` operation, **then** DBHub rejects it under its configured read-only policy and no database mutation occurs.
6. **Given** Docker Hub MCP is installed, **when** KIS mounts it, **then** the approved upstream tools appear only under `dockerhub_*` and local Docker Engine commands remain unchanged.
7. **Given** Docker Hub credentials are absent, **when** status/capability discovery is requested, **then** public capability remains understandable and credential-dependent limitations have a concrete next action rather than a generic failure.
8. **Given** either new provider fails to build, connect, or mount, **when** KIS starts, **then** unrelated Work/Discover/Skills/Control Center/provider capability remains available and the failure is bounded/redacted.
9. **Given** the final implementation, **when** canonical docs and artifacts are searched, **then** no current authoritative provider roster, count, project-registry shape, generated-state diagram, startup procedure, or commissioning instruction contradicts the implementation.
10. **Given** canonical verification passes, **when** live provider commissioning has not been run, **then** documentation/status says implementation verified but does not claim live upstream commissioning.

## Risks and recovery

- **Upstream package/source mismatch:** fail bootstrap before activation when source revision, package/release identity, or digest does not match the approved JSON. Never fall back to `latest`.
- **Database side effects:** read-only is mandatory in 109; use DBHub's SQL policy plus engine/session read-only behavior where supported and test SQLite explicitly.
- **Credential leakage:** secrets remain in the KIS vault/process environment; redact exceptions and never serialize resolved values.
- **Cross-project data exposure:** every database process is bound to one registered project/binding; local paths must remain inside that project root and external bindings must be explicit.
- **Tool-name drift:** nested per-binding mounts isolate DBHub native single/multi-source naming behavior from the public KIS contract.
- **Provider outage:** optional provider failures are contained; recovery is reinstall/reconfigure/recommission that provider, not weakening gateway policy.
- **Documentation drift:** durable current-state facts are reconciled in the same change and verified by targeted stale scans plus canonical repository verification.

Recovery from an implementation regression is to disable the affected provider in runtime JSON, restore the previous verified provider installation/configuration from recoverable state where applicable, and restart KIS. Recovery MUST NOT require policy changes or permanent deletion.

## Out of scope

- database writes, migrations, DDL, writable DBHub custom tools, or automated database backup/restore;
- replacing project-owned database libraries such as College's `sqlite3` implementation;
- replacing local Docker CLI/Engine operations with Docker Hub MCP;
- Docker Hub repository deletion or any capability not present in the approved upstream revision;
- automatic provider upgrades, `latest` resolution, unsupervised package/network bootstrap, or provider self-update;
- new Work hard rules, capability permission tiers, or provider-specific policy prohibitions;
- modifying Commodity or College application code solely to demonstrate the provider integration.
