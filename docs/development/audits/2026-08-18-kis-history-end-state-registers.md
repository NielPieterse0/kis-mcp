# KIS-MCP #375 Historical Audit Registers — 2026-08-18

> **Historical engineering evidence only.** These registers preserve the decision, assumption, risk/approval, hold/deferred, and gap/correction evidence reconstructed by issue #375. Current product authority remains with the owners routed by `AGENTS.md`.

## Register conventions

- Source checkpoints are the append-only #375 comments 001-011 plus the final live-tool pass at `5f5a319b389715ef9b5283e999ef33322ae5ff51`.
- Historical checkpoint identifiers are preserved even when they collide. The stable key in this file is `checkpoint + original identifier`, for example `CP006-D-0041`.
- `Consultation not evidenced` means the engineering decision is visible in durable evidence but the audit did not find an explicit operator-consultation record. It does not mean the decision was unauthorized.
- `Superseded` means later architecture replaced the decision; it does not erase the decision as historical evidence.
- Live findings `L-*` are end-state commissioning findings, distinct from historical `F-*` findings.

## Decision register

| Key | Decision | Consultation provenance | Terminal disposition |
|---|---|---|---|
| CP001-D-0001 | Greenfield KIS; predecessor/SDK2 material is evidence only. | Consultation not evidenced. | Active lineage. |
| CP001-D-0002 | Desktop Commander remains authoritative ordinary local Work tooling; KIS wraps rather than forks it. | Consultation not evidenced. | Active current. |
| CP001-D-0003 | FastMCP is the sole Work policy boundary. | Consultation not evidenced. | Active current. |
| CP001-D-0004 | Work has exactly HR-001/HR-002/HR-003; no fourth hard rule. | Approved baseline recorded; consultation trail not independently evidenced. | Active current. |
| CP001-D-0005 | Enforcement is effect-based on the concrete invocation; uncertainty is not a hard-rule violation. | Consultation not evidenced. | Active current. |
| CP001-D-0006 | Delete-like Work becomes recoverable quarantine; permanent disposal is outside Work. | Consultation not evidenced. | Active current. |
| CP001-D-0007 | Provider-native command/directory allowlists stay empty and cannot become a second policy boundary. | Consultation not evidenced. | Active current. |
| CP001-D-0008 | Product target is one shared Discover/Govern/Work platform. | Approved target recorded; consultation trail not independently evidenced. | Partially realized; Govern lifecycle remains open. || CP002-D-0009 | Provider schema fingerprints are conformance evidence, not runtime permission gates. | Consultation not evidenced. | Active current. |
| CP002-D-0010 | Public KIS MCP records are explicitly versioned contracts. | Consultation not evidenced. | Active current. |
| CP002-D-0011 | Quarantine evidence is authenticated/versioned and transaction-compensated. | Consultation not evidenced. | Active current. |
| CP002-D-0012 | Parallel work uses stable change IDs, explicit path claims, isolated worktrees, validation, and non-force cleanup. | Consultation not evidenced. | Active current, with later identity refinements. |
| CP002-D-0013 | Narrow gateway preload adapters may repair provider lifecycle compatibility without forking providers or policy. | Consultation not evidenced. | Active pattern. |
| CP002-D-0014 | Local and remote ChatGPT transports share the same gateway/policy; op/dev are independent instances with no automatic failover. | Consultation not evidenced. | Active current. |
| CP002-D-0015 | Providers use a provider-neutral registry/catalogue/readiness/service foundation with side-effect-free registration. | Consultation not evidenced. | Active current. |
| CP002-D-0016 | GitHub/Supabase are external provider boundaries; provider auth/scoping does not widen ordinary Work HR-002. | Consultation not evidenced. | Active current. |
| CP002-D-0017 | Provider composition is failure-contained; mount/readiness/auth/discovery/live verification are distinct states. | Consultation not evidenced. | Active current. |
| CP002-D-0018 | Discover starts bounded/read-only/deterministic; semantic/remote execution remains deferred. | Consultation not evidenced. | Superseded by broader read-only Discover, execution separation retained. |
| CP002-D-0019 | Skills are centralized; catalogue/read ownership is KIS and mutation reuses Work. | Consultation not evidenced. | Superseded/refined by canonical shared Skills-only policy. |
| CP002-D-0020 | Narrow structural parsers may resolve HR outcomes; they cannot become broad executable deny rules. | Consultation not evidenced. | Active current. |
| CP002-D-0021 | Tunnel secrets use supervised secret storage; checked-in configuration contains references only. | Consultation not evidenced. | Mechanism later migrated; no-plaintext principle active. |
| CP003-D-0022 | Git/Discover evidence disables external diff/textconv/attributes/excludes and stays bounded/deterministic. | Consultation not evidenced. | Active current. |
| CP003-D-0023 | Provider prerequisites such as auth/init are distinct from genuine provider failure. | Consultation not evidenced. | Active current. |
| CP003-D-0024 | Discover emits verification handoffs but does not execute verification. | Consultation not evidenced. | Active separation. |
| CP003-D-0025 | Provider admission is evidence-first and pending authority; Discover cannot self-authorize Work execution. | Consultation not evidenced. | Active lineage. |
| CP003-D-0026 | Tools have a provider-neutral foundation distinct from Providers and workflow ownership. | Consultation not evidenced. | Active current. |
| CP003-D-0027 | AgentSys/agnix/MCP Inspector are managed support tooling, not silently normal gateway capabilities. | Consultation not evidenced. | Active current. |
| CP003-D-0028 | Application Secrets is a shared-kernel service with `secret://` identity and no plaintext public surface. | Consultation not evidenced. | Active current. |
| CP003-D-0029 | Vault crypto is versioned authenticated encryption with recoverable prior vaults and no self-unlocking key file. | Consultation not evidenced. | Active lineage. |
| CP003-D-0030 | Runtime secret exposure is process-local/supervised; provider migrations remain separate bounded work. | Consultation not evidenced. | Active current. |
| CP003-D-0031 | Control Center is a read-only derived projection, not a second authority or raw prompt/result store. | Consultation not evidenced. | Active current. |
| CP003-D-0032 | Local Git workflow tooling may inspect/prepare/clean recoverably but not perform arbitrary remote mutation/force/history rewrite/permanent delete. | Consultation not evidenced. | Active lineage. |
| CP003-D-0033 | Cleanup and lifecycle closure are separate gates. | Consultation not evidenced. | Later simplified under schema-v3; separation principle retained where applicable. || CP004-D-0034 | Capability composition is the shared runtime façade; eligibility/readiness precede scoring and runtime state is instance-scoped. | Consultation not evidenced. | Active current. |
| CP004-D-0035 | Work Management programme authority lives under `.work/programmes/work-management`, not ordinary documentation prose. | Consultation not evidenced. | Active current. |
| CP004-D-0036 | Work Management contracts are provider-neutral; GitHub Projects is an adapter/back end. | Consultation not evidenced. | Active current. |
| CP004-D-0037 | Decision/Assumption/Risk/Approval/Hold become explicit typed Work Management record classes. | Consultation not evidenced. | Active current contract lineage. |
| CP004-D-0038 | Implementation traceability is exact-identity based across spec/change/branch/worktree/PR/head verification/merge/closeout/docs. | Consultation not evidenced. | Active current principle. |
| CP004-D-0039 | Review evidence uses manifests under `.work/reviews`, not an arbitrary second evidence database. | Consultation not evidenced. | Active lineage. |
| CP004-D-0040 | Work reconciliation is preview-first, idempotency-bound, narrow, and has no delete/unrestricted GraphQL surface. | Consultation not evidenced. | Active current principle. |
| CP004-D-0041 | Provider auth lifetime is separate from selected repository routing identity. | Consultation not evidenced. | Active current. |
| CP004-D-0042 | Runtime lifecycle is per-instance and process-identity/ancestry bound. | Consultation not evidenced. | Active current. |
| CP004-D-0043 | Repository delivery completion does not imply external Project commissioning. | Consultation not evidenced. | Active current. |
| CP004-D-0044 | First live Project commissioning is read-only; mutation is a later governed step. | Consultation not evidenced. | Historical boundary; superseded by commissioned writes. |
| CP005-D-0045 | Work Management initialization becomes a precondition for governed slices while Project remains operational authority, not source-code truth. | Consultation not evidenced. | Later refined by command-plane restoration. |
| CP005-D-0046 | Stable Work Management identity is recorded locally so local validation does not require network access. | Consultation not evidenced. | Active lineage. |
| CP005-D-0047 | Project mutation remains narrow, preview-first/idempotent, with no delete or unrestricted API bypass. | Consultation not evidenced. | Active current principle. |
| CP005-D-0048 | Rich Project field/view commissioning is a separate acceptance obligation. | Consultation not evidenced. | Active commissioning principle. |
| CP006-D-0041 | Exact provider-native GitHub Actions evidence on the exact PR head becomes the normal landing gate. | Consultation not evidenced. | Active current. |
| CP006-D-0042 | Merged Git/GitHub state is sufficient delivery authority; routine post-merge metadata-only PRs are unnecessary. | Consultation not evidenced. | Active current. |
| CP006-D-0043 | Work Management initialization is mandatory for new governed slices without giving local governance network authority. | Consultation not evidenced. | Active lineage. |
| CP006-D-0044 | Desired Project schema is repository-owned/drift-detectable; provider inability is a commissioning gap, not bypass authority. | Consultation not evidenced. | Active current. |
| CP006-D-0045 | Review backend failure is never a pass; manual fallback/operator waiver must be explicit. | One explicit operator waiver is evidenced for Change 093; general decision consultation otherwise not evidenced. | Active current. |
| CP007-D-0046 | Local path-claim lifecycle and operator Work lifecycle are independent but reconciled authorities. | Consultation not evidenced. | Active current. |
| CP007-D-0047 | `complexity` and additive `risk_triggers` replace coupled `risk_profile` for new changes. | Consultation not evidenced. | Active current. |
| CP007-D-0048 | Speculative integration advances `main` only from frozen members, exact candidate Actions evidence, and exact-base CAS. | Consultation not evidenced. | Active current queue principle. |
| CP007-D-0049 | Canonical shared Skills are the sole reusable-skill runtime source; repository-local reusable catalogues are prohibited. | Consultation not evidenced. | Active current. |
| CP007-D-0050 | Work Management is the operational command plane; issues, repository/Git, and Actions retain their bounded authority domains. | Historical issue explicitly records architectural correction; separate operator consultation record not evidenced. | Active current. || CP007-D-0051 | Generated queue/runtime state is reconstructible and subordinate to Git/GitHub/Project authorities. | Consultation not evidenced. | Active current. |
| CP008-D-0052 | Project live schema truth requires provider read-back; repository migration code alone is insufficient commissioning proof. | Consultation not evidenced. | Active current. |
| CP008-D-0053 | Historical commissioning and current-process liveness are separate evidence states. | Consultation not evidenced. | Active current. |
| CP008-D-0054 | Repo-local recovery capsules are reconstructible hints, not competing state authority. | Consultation not evidenced. | Active current. |
| CP008-D-0055 | Correctness-sensitive state uses hybrid central partitioning; safe installs/cache/auth/registry/quarantine may remain shared. | Programme decision recorded; explicit operator consultation trail not evidenced. | Active target; migration incomplete. |
| CP008-D-0056 | Review acceptance binds to exact immutable source/evidence identity; backend success alone is insufficient. | Consultation not evidenced. | Active current. |
| CP008-D-0057 | Change/spec sequence allocation must be globally collision-safe rather than conversational. | Consultation not evidenced. | Active architectural requirement; historical collisions remain. |
| CP009-D-0058 | Temporary verification architecture may exist during provider-native outage and be explicitly retired when canonical authority returns. | Recovery programme decision recorded; separate consultation trail not evidenced. | Crisis-only; superseded. |
| CP009-D-0059 | Disaster recovery restores an exact evidence-backed tree while preserving later history. | Explicit recovery programme authority recorded; separate consultation trail not evidenced. | Completed by Change 185. |
| CP009-D-0060 | Post-reset reconstruction semantically harvests old evidence into fresh changes rather than treating cherry-picks as authority. | Explicit reconstruction programme authority recorded; separate consultation trail not evidenced. | Active recovery rule. |
| CP009-D-0061 | Canonical landing authority is provider-native GitHub Actions on the exact frozen PR head; local/VM execution is not merge authority. | Reconstruction programme decision recorded; separate consultation trail not evidenced. | Active current. |
| CP009-D-0062 | Current MCP authority remains FastMCP 3.x / MCP 2025-11-25 until a separately governed migration lands. | Consultation not evidenced. | Active current; #342 future. |

### Decision-register integrity finding

The original checkpoint chain reuses D-series numbers across checkpoints, notably `D-0041` through `D-0048`. The duplicate numbers are historical audit identifiers, not proof that the underlying decisions are duplicates. Consumers MUST use the checkpoint-qualified key above when referring to this register.

## Assumption register

| Key | Assumption | Evidence/disposition |
|---|---|---|
| A-0001 | Runtime is private/single-operator/directly supervised. | Still active trust-model assumption; public source visibility is separate. |
| A-0002 | `C:\Projects` is the canonical mutable Work boundary. | Still active and machine-enforced by HR-001. |
| A-0003 | Pinned provider contracts/source are sufficient evidence for bounded adaptation. | Narrowed: runtime/auth/live state must be modeled separately from installation/schema evidence. |
| A-0004 | Supervised bootstrap/connectors are separate from ordinary Work HR-002. | Still active. |
| A-0005 | Narrow positive structural resolution can identify prohibited outcomes without making uncertainty a denial rule. | Strengthened by later parser hardening; still active. || A-0006 | Flat/shared mutable state is safe for all consumers. | Invalidated by cross-project/worktree/runtime evidence; replaced by hybrid partitioned-state architecture. |
| A-0007 | PR ancestry alone proves successful landing/cleanup eligibility. | Invalidated by tree-equivalent reconciliation; deterministic equivalence proof was added. |
| A-0008 | Merged local metadata will remain coherent without explicit reconciliation. | Invalidated by repeated stale claims and stale closeout evidence. |
| A-0009 | Repository tests imply live runtime/provider commissioning. | Invalidated repeatedly by live commissioning defects. |
| A-0010 | One bounded review package can cover arbitrarily large changes. | Invalidated; #335 remains the current batching gap. |
| A-0011 | Provider capability absence and credential absence are equivalent blockers. | Invalidated during rich Project commissioning; they require distinct diagnosis. |
| A-0012 | Exact source/revision identity is mechanically observable enough to bind verification/review/landing. | Validated and active. |
| A-0013 | Project can own operational command facts only while repository/Git/PR/Actions evidence remains separately authoritative. | Validated and active. |

## Risk and approval register

| Key | Risk or approval boundary | Disposition |
|---|---|---|
| R-0001 | Effect-resolution incompleteness may miss concrete mutation/network/delete forms. | Materialized in known parser defects; mitigated iteratively, structural risk remains regression-sensitive. |
| R-0002 | Provider version/schema drift can invalidate resolver assumptions. | Mitigated by exact pins, conformance evidence, and commissioning; still active lifecycle risk. |
| R-0003 | Quarantine metadata/payload/rollback correctness is safety-sensitive. | Historical defects resolved by authenticated metadata, hashing, and compensation. |
| R-0004 | Provider startup may have external effects before ordinary Work invocation interception. | Contained by provider-specific configuration/supervised lifecycle; remains architectural consideration. |
| R-0005 | Live proxy/provider behavior may remain uncommissioned after repository delivery. | Repeatedly validated as a real risk; live commissioning is now a separate acceptance state. |
| R-0006 | Human-facing numeric change identity is not globally unique under concurrency. | Confirmed historically; collision-safe allocation remains the correct direction. |
| R-0007 | Encrypted vault introduces key-loss, process-memory, persistent-state, and format-drift risks. | Accepted with explicit recovery/format boundaries. |
| R-0008 | Runtime/support-tool commissioning evidence can lag implementation. | Confirmed repeatedly; status must distinguish historical verification and current liveness. |
| R-0009 | Correctness-sensitive state migration is incomplete across consumers. | High current risk under #277/#279/#280. |
| R-0010 | Merge queue has authentication and concurrent-state correctness defects. | High current risk under #237/#289; live queue proof remains required. |
| R-0011 | Oversized reviews can exceed complete evidence packaging. | High current review-completeness risk under #335. |
| R-0012 | Historical evidence/backlog drift can mislead humans and automation. | Current medium risk; examples include Change 093/190 and stale reconstructed issues. || AP-0001 | Registered external acquisition requires exact approved profile/recipe/hash authority; `approved=false` must fail closed. | Live end-state test returned `APPROVAL_REQUIRED`; no acquisition executed. |
| AP-0002 | Project mutation apply-path requires explicit idempotency; preview remains non-mutating. | Historical commissioning evidence confirms bounded write use; current contract still declares the rule. |
| AP-0003 | Change 093 used an explicit operator review waiver only after reviewer attempts failed/unreliable. | Historical exception; correctly recorded as waiver, not independent review pass. |
| AP-0004 | Public repository exposure followed an explicit exposure audit during Change 185 recovery. | Completed historical approval boundary; runtime trust assumptions remained separate. |
| AP-0005 | Rich Project commissioning proceeded only after the provider/credential prerequisite distinction was resolved. | Completed; final historical target reached 25 fields/12 views, with current view evidence now disputed. |

## Hold and deferred register

| Key | Hold/deferred item | Reason | Current disposition |
|---|---|---|---|
| H-0001 | External ChatGPT/dual-instance commissioning from early runtime changes. | Credential/supervised live-smoke prerequisites. | Later live runtime evidence exists; current end-state was rechecked on both instances. |
| H-0002 | Python SDK provider central composition from Change 044. | Explicitly deferred integration lifecycle. | Survives as historical/open lifecycle concern; no current proof of full composition in this audit. |
| H-0003 | Secrets server/NVIDIA/Supabase/documentation integrations from early vault work. | Separate bounded migrations required. | Partially resolved over later eras; historical debt must not be assumed fully closed without exact evidence. |
| H-0004 | NVIDIA/Codex reviewer live commissioning. | Credentials/install/auth initially unavailable. | Resolved historically by Changes 091-092; later reliability/scalability debt remains separate. |
| H-0005 | Rich Work Management field/view provisioning. | Bounded provider and later credential gaps. | Historical 25/12 commissioning succeeded; current operator/tool view evidence disagrees. |
| H-0006 | Govern public composition. | Lifecycle choice unresolved. | Open under #192: compose, explicitly stage, or defer/remove. |
| H-0007 | Coordinator Slice 7 observability/evaluation/operator UX/live commissioning. | Explicitly excluded from reconstructed Slice 6. | Open under #253. |
| H-0008 | Hybrid state consumer migration and commissioning. | Foundation landed before consumer migration. | Open under #277/#279/#280. |
| H-0009 | FastMCP 4 / MCP 2026 migration. | Deliberate future protocol migration. | Deferred under #342; must not redefine current authority. |
| H-0010 | Historical MCP programme issues #341/#343/#347. | Deferred evidence after recovery/reset. | Await durable disposition by the reconstruction/reconciliation programme. |
| H-0011 | Provider upgrades/compatibility #144/#145/#148. | Non-blocking bounded residuals. | Open/deferred. |
| H-0012 | Documentation/context and verification optimization #283/#340. | Requires measured evidence; not current correctness authority. | Deferred investigation. |## Gap and correction register

| Key | Gap/correction | Classification | Recommendation / owner |
|---|---|---|---|
| C-0001 | Checkpoint 002 omitted Changes 019 and 018 although its endpoint already contained them; Checkpoint 003 records the correction. | Audit-record correction. | Preserve append-only correction; do not rewrite CP002. |
| G-0001 | Numeric Change IDs collide (`025`, `029`, `031`, `057`, later other prefixes). | Historical identity defect. | Use exact slug + issue/PR/commit identity; collision-safe allocation for new work. |
| G-0002 | D-series audit identifiers collide across checkpoints. | Audit-register identity defect. | Use checkpoint-qualified keys in this file. |
| G-0003 | Changes 086-109 have weak/no first-class issue history because mandatory Work initialization did not yet exist. | Historical traceability gap. | Use governed change + PR/commit evidence; do not infer missing delivery. |
| G-0004 | Change 093 current closeout is stale. | Historical evidence drift. | Bounded historical-record reconciliation. |
| G-0005 | Change 190 evidence is malformed/stale despite proven landing. | Historical evidence drift. | Existing #367/Change197 ownership remains authoritative. |
| G-0006 | Completed 112 audit nearly remained untracked in a residual worktree. | Evidence durability failure. | Durable audit/review evidence must be committed or stored before retirement. |
| G-0007 | Reconstructed payload can leave source issues apparently open/stale. | Backlog/current-truth drift. | Reconcile acceptance and close/supersede/narrow exact residuals. |
| L-001 | Serena capability catalogue exposes mutation-capable upstream operations beyond the declared three-tool read-only surface. | Current live authority mismatch. | Compose only provider-approved exposed tools; regression-test hidden tools as undiscoverable/undispatchable. |
| L-002 | Discover commit inspection returns a high-confidence empty delta for merge commit `5f5a319...`; review inherits the empty evidence. | Current live Discover/review defect. | Define merge semantics, normally first-parent landed delta, and add merge fixtures. |
| L-003 | Work Management schema/view evidence disagrees with operator-visible Project UI for Decisions, Assumptions/Risks, Holds and other views. | Current commissioning/observability mismatch. | Reconcile provider read-back with actual UI behavior; no false ready claim. |
| L-004 | Speculative merge queue reports stale base versus current `main`. | Current runtime-state mismatch. | Reconcile through existing queue owners; prove current empty and queued behavior. |
| L-005 | DBHub/Docker/Supabase successful current reads do not fully update commissioning status. | Current observability mismatch. | Consume successful current-process evidence while retaining historical-vs-live distinction. |
| L-006 | Root/module documentation understates current Work/Skills and reconstructed Acquisition/Coordinator/State/Housekeeping behavior. | Current documentation drift. | Canonical-owner reconciliation under #378; audit remains historical only. |
| L-007 | Default `project_management_inventory` and `project_management_current_work` fail at the 100-item bound with `inventory_incomplete` instead of paging; `item_limit=1000` succeeds. | Current public Work read-contract defect. | Add cursor/pagination support or deterministic complete read behavior; preserve fail-closed truncation semantics. |
| L-008 | `execute_change_workflow` is genuinely dispatchable, but short audit deadlines can leave verification/review phases incomplete while child verification processes continue. | Live workflow execution/operability observation. | Treat timeout as incomplete, never pass; ensure callers can observe/cancel spawned verification cleanly. |

## Live Work and workflow action evidence

- `project_management_contract` executed successfully and reported all 21 Work Management operations plus explicit mutation/idempotency semantics.
- Default `project_management_inventory` and `project_management_current_work` reproduced `inventory_incomplete` on both KIS surfaces when the Project exceeded the default 100-item read bound.
- `project_management_inventory(item_limit=1000)` completed; a full board query confirmed #378 as `Ready`, `High`, `Large`, unclaimed.
- `project_management_current_work(item_limit=1000, execution_owner="agentB")` completed and confirmed unrelated #237 remains `Active` and owned by `agentB`.
- `recommend_workflow` live-resolved `verify-current-change`, `review-current-change`, and `execute-current-change` as eligible for Change 198.- `execute_change_workflow` was live-dispatched against the documentation-only Change 198 worktree. A minimal call returned `change-execution-result-v2`, selected `scripts/verify.ps1`, and launched verification; the deliberately short deadline produced `incomplete`, not success.
- Audit-spawned verifier processes were explicitly stopped after evidence capture; the workflow test made no repository edits.
- State-changing Work Management transitions were **not re-exercised merely for audit proof**. Historical Changes 085/113 already contain live mutation evidence, and #378 creation/enrollment is current operational evidence; no unrelated claim/lifecycle state was altered during this end-state pass.

## Register completion statement

These registers are a structured companion to `2026-08-18-kis-history-end-state-audit.md`. They preserve uncertainty, consultation provenance, superseded architecture, and current mismatches instead of flattening the history into a success narrative.

The correct end-state conclusion remains: **audit complete with material findings; remediation remains open under #378 and narrower existing owners.**