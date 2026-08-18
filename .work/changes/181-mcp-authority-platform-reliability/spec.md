# Change Specification: MCP Authority and Platform Reliability

## Goal

Make official MCP protocol authority machine-enforced for MCP-relevant KIS work, then remediate the fifteen commissioning failures as seven coordinated cross-repository slices under one umbrella programme. Each slice is a separate governed child change/branch and pull request, landed in strict sequence.

`doc-solution` is acceptance evidence only. No repository-specific runtime, toolchain, or execution special case is permitted.

## Authority and sources

For MCP protocol truth, the official MCP protocol schema and applicable normative MCP specification are authoritative over KIS product prose, plans, implementation, and tests. Repository governance and trust rules govern how KIS changes and operates; they do not redefine MCP semantics.

Authoritative sources for this change:

- `AGENTS.md` for repository workflow and authority routing.
- The installed product dependency `fastmcp==3.4.4`; implementation guidance MUST remain on the FastMCP 3.x documentation/release line.
- MCP protocol revision `2025-11-25` only, using the official `modelcontextprotocol/modelcontextprotocol` release and `schema/2025-11-25/schema.ts` plus matching normative specification pages.
- `.kis-mcp-gov/AGENTS.md` for MCP reference discovery, updated by Slice 1 to make the FastMCP-major/protocol-revision binding fail closed.
- `.kis-mcp-gov/docs/mcp-full-documentation/000-index.md` for progressive discovery within the `2025-11-25` authority set.
- The matching `2025-11-25` schema reference when exact wire types, fields, request/result shapes, errors, capability contracts, or protocol metadata matter.
- `settings/tools/mcp-spec.tool.json`, updated by Slice 1 to pin the official `2025-11-25` authority rather than an unversioned/current specification head.

MCP `2026-07-28`, FastMCP 4.x migration/design material, draft protocol material, and later protocol primitives are explicitly non-authoritative for current KIS implementation. They MAY be consulted only to identify and exclude incompatible future behavior. Adopting them requires a separately approved FastMCP 4.x migration change that changes the repository's version authority deliberately.

The `2025-11-25` specification defines its authoritative protocol requirements from its TypeScript schema. KIS therefore treats that versioned schema and matching normative specification prose as one protocol-authority set, not as independent optional references.

## Global prerequisite: MCP authority gate

**MCP-001:** Every governed slice MUST classify whether it affects MCP protocol behavior, server/client interfaces, capabilities, transports, methods, messages, or extensions.

**MCP-002:** An MCP-impacting slice MUST resolve the applicable official schema types/methods/capabilities and normative specification sections before implementation begins.

**MCP-003:** KIS MUST persist a machine-readable MCP authority receipt containing the exact specification/schema revision or fingerprint, mapped MCP primitives, applicable normative sources, MCP-native behavior, KIS-specific extensions, and planned conformance evidence.

**MCP-004:** Change validation and canonical verification MUST fail closed when an MCP-impacting slice has no current authority receipt or the receipt no longer matches the governed source/change state.

**MCP-005:** The KIS MCP server SHOULD expose the pinned `2025-11-25` specification/schema through MCP Resources and SHOULD advertise concise agent guidance through the `InitializeResult.instructions` field defined by that protocol revision. These protocol affordances reinforce discovery; they do not replace the fail-closed KIS lifecycle gate.

**MCP-006:** When MCP `2025-11-25` already defines the required primitive or contract, the implementation MUST use that native protocol construct unless the change records an explicit, bounded KIS extension that does not contradict the protocol. No implementation may import a `2026-07-28` or FastMCP 4.x construct into the FastMCP 3.x product line by treating newer documentation as current authority.

**MCP-007:** Protocol-conformance tests MUST be derived from the mapped schema and normative behavior, in addition to ordinary unit, integration, safety, and repository tests.

## Mandatory sequential landing rule

**SEQ-001:** Slice 1 through Slice 7 MUST be implemented as separate governed child changes/branches and pull requests under this umbrella programme.

**SEQ-002:** Slice `N+1` MUST NOT start implementation, receive implementation commits, or open a pull request until Slice `N` is merged, reconciled, cleaned up, and verified as part of registered local `main` at the exact GitHub merged head.

**SEQ-003:** Every slice MUST independently complete exact-head verification, required risk-trigger review, authoritative Work Management readiness, merge, registered default-branch refresh/alignment, landing reconciliation, and worktree/branch cleanup before the next child change is created.

**SEQ-004:** The umbrella change records programme-level requirements and cross-slice traceability only. Implementation path ownership belongs to the currently active child slice.

## Slice 1 — MCP authority gate, canonical source, and project execution environment

**S1-001:** Introduce one canonical resolved source identity shared by discovery, verification, review, completion, and execution. It MUST retain registered project identity, immutable head SHA/tree, optional base SHA, source kind, source fingerprint, and materialized workspace identity.

**S1-002:** Range verification MUST execute the immutable resolved head while preserving base-to-head provenance used to select affected checks.

**S1-003:** Separate the KIS-owned tool/runtime environment under configured KIS state from each product repository's execution environment.

**S1-004:** Resolve `ProjectExecutionContract -> ResolvedExecutionEnvironment` generically from repository declarations and registered policy. Python `.venv`/version requirements are one adapter; Node, .NET, Java, Go, Rust, PowerShell, and future stacks use the same contract pattern.

**S1-005:** KIS's own Python or tool runtime MUST NOT become the implicit runtime of a registered product repository. Missing compatible runtimes MUST produce a typed unavailable result; KIS MUST NOT silently install dependencies or guess through ambient PATH.

**S1-006:** Execution receipts MUST record the exact resolved runtime/toolchain identity and requirement provenance. `doc-solution` MUST remain only a real-repository acceptance case.

## Slice 2 — Review orchestration v2

**S2-001:** Replace fixed reviewer fallback assumptions with a provider-neutral review backend pool that records health, typed failures, consecutive failures, cooldown state, and bounded retry/backoff policy.

**S2-002:** Overall review deadlines MUST reserve time for fallback. A failing preferred provider MUST NOT consume the full review budget before another healthy backend can be attempted.

**S2-003:** Automated review MUST support at least two independent failure domains when configured. Manual exact-diff review remains a final safety fallback, not the normal automated architecture.

**S2-004:** Reuse existing issue #335 for deterministic, complete semantic review batching. Every required review type and changed file MUST be covered with exact provenance; any unrecovered batch makes the aggregate review incomplete.

**S2-005:** Provide bounded relevant unchanged context through a deterministic review context manifest. Findings MUST resolve to supplied evidence, and ungrounded findings MUST NOT be represented as proven defects.

**S2-006:** Add negative calibration fixtures for known-valid constructs and measure false-positive suppression as well as true-positive detection.

**S2-007:** Do not create a new reviewer architecture on deprecated MCP Sampling.

## Slice 3 — Complete Work Management pagination

**S3-001:** Introduce a first-class inventory page contract with items, continuation cursor, and explicit completeness.

**S3-002:** Operations that require complete Work Management authority MUST drain pages within configured page/item bounds and MUST fail or explicitly report incomplete authority when those bounds are reached.

**S3-003:** Apply complete inventory semantics to board inventory, current/next work selection, readiness, and exact-target lookup. Increasing a single item limit is not an accepted fix.

## Slice 4 — Durable reviewable PR and pre-merge readiness

**S4-001:** Model PR preparation as an idempotent durable sequence: `resolve -> verify -> review -> publish -> create_pr`.

**S4-002:** Persist stage receipts keyed by operation, source, and configuration fingerprints so retries resume from the last proven stage. Each stage MUST have its own deadline.

**S4-003:** Preserve the public outcome: stop at an open exact-head reviewable PR. Increasing the composite timeout alone is not an accepted fix.

**S4-004:** Add an authoritative pre-merge Work Management stage that resolves the registered project binding, creates or reconciles only missing machine-owned state, fetches authoritative record/trace state, binds exact-head verification/review evidence, and evaluates readiness.

**S4-005:** Ambiguous or human-owned conflicting Work Management metadata MUST fail closed rather than be overwritten.

## Slice 5 — Registered repository and Windows worktree lifecycle

**S5-001:** Keep low-level registered default-branch refresh semantics unchanged. Add an explicit higher-level alignment operation owned by serialized integration/landing flow.

**S5-002:** Default-branch alignment MUST fetch verified remote truth and advance local `main` only by safe fast-forward when the primary worktree is clean and ancestry permits it. Dirty or diverged state MUST return a typed stop; force/reset is prohibited.

**S5-003:** Long-lived KIS/provider/agent processes MUST use a neutral KIS-state working directory rather than a governed worktree as inherited CWD.

**S5-004:** Short-lived workspace commands MUST be owned and fully reaped through the existing KIS process-tree/Job Object boundary before cleanup, with only a small bounded handle-release retry.

**S5-005:** Add deterministic worktree-lock diagnostics using KIS run/process ownership metadata first and native Windows best-effort lock inspection second.

**S5-006:** Automated recovery MAY terminate only a process proven KIS-owned by current identity/token/generation evidence. Unknown or external holders MUST be reported and MUST NOT be killed.

## Slice 6 — Post-merge lifecycle reconciliation

**S6-001:** Reconcile stale landed change 179 from authoritative merge evidence.

**S6-002:** Add an idempotent post-merge lifecycle reconciler based on authoritative GitHub merge truth plus exact merged commit/tree evidence.

**S6-003:** Persist a structured landing receipt or equivalent machine-owned closeout facts covering merged identity, local-main alignment, change closure, and cleanup state without rewriting historical human review narrative.

**S6-004:** Integrate with issue #325's scheduled deterministic reconciler direction as a safety net rather than creating a competing housekeeping subsystem.

## Slice 7 — Permanent execution and commissioning acceptance matrix

**S7-001:** Extract a hermetic execution acceptance matrix into the normal verifier for Small, Medium, and Large changes; two concurrent exact runs; distinct product execution environments; exact SHA/tree/fingerprint identity; unique run/workspace namespaces; timeout and parent-loss containment; stale-run recovery; and receipt integrity.

**S7-002:** Keep live provider and real registered product-repository commissioning in a separate optional/live profile. Mandatory hermetic verification MUST NOT depend on live NVIDIA, Codex, or a product repository.

**S7-003:** The acceptance matrix MUST regress the contracts introduced by slices 1–6 where a deterministic hermetic test is possible.

## Explicit non-solutions

The programme MUST NOT close an issue by only increasing reviewer/completion timeouts, increasing Work Management item limits, adding a Python 3.11 or `doc-solution` special case, silently changing low-level refresh semantics, force-resetting local `main`, killing unknown Windows processes, patching stale change 179 without a reconciler, putting live providers/product repos into mandatory hermetic verification, using prompt prose alone to suppress reviewer false positives, duplicating issue #335, basing new review orchestration on deprecated MCP Sampling, or importing FastMCP 4.x/MCP `2026-07-28` design into the current FastMCP 3.x product line.

## Acceptance criteria

- The MCP authority gate is machine-enforced and has negative tests proving an MCP-impacting change cannot pass without fresh exact authority evidence.
- Current FastMCP 3.x work is machine-bound to MCP `2025-11-25`; FastMCP 4.x, MCP `2026-07-28`, draft, unversioned/latest, or otherwise mismatched authority fails closed until an explicit migration changes the binding.
- All fifteen observed commissioning failures map to one of the seven slices and have deterministic regression evidence or a separately identified live commissioning check.
- Product repository execution is stack-agnostic and remains isolated from KIS's own MCP/tool runtime.
- Existing #241 coordinator, #325 reconciliation, and #335 review-batching directions are reused or integrated rather than duplicated.
- No slice weakens HR-001, HR-002, HR-003, exact-head verification, recoverable deletion, or registered-project authority.
- Each slice passes canonical verification and required reviews on its own exact PR head before merge.
- Each slice is merged, reconciled, and reflected in clean registered local `main` before the next slice begins.
- Slice 7 closes only after the final acceptance matrix proves the accumulated behavior of the previously merged slices.

## Risks and controls

- **Programme breadth:** seven slices span several subsystems. Control: one slice at a time, separate child branches/PRs, and mandatory merge/reconciliation before advancing.
- **Active overlap:** existing governed changes may own shared paths. Control: each child slice reconciles claims against current merged `main` immediately before creation; no uncoordinated overlap is permitted.
- **Protocol drift:** official MCP sources can advance. Control: receipts bind exact source revision/fingerprint and stale evidence fails closed.
- **Cross-repository variability:** product stacks differ. Control: adapter-based execution-environment contracts with typed unsupported/unavailable outcomes instead of repository exceptions.
