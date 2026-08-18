# KIS-MCP Historical and End-State Audit — 2026-08-18

> **Historical engineering evidence only.** This document records the outcome of GitHub issue #375. It does not define current product behavior. For current authority, follow `AGENTS.md` to root `SPEC.md`, `docs/TRUST-MODEL.md`, `docs/OPERATIONS.md`, settings, contracts, source, and tests.

## Audit identity

- Source audit: GitHub issue **#375**, `Audit: reconstruct complete KIS-MCP history, decisions, gaps, and current-state truth`.
- Remediation umbrella: GitHub issue **#378**, `TASK: reconcile #375 audit findings and commissioned KIS end-state`.
- Audit date: **2026-08-18**.
- Historical starting boundary: root commit `5ab2aa1e71852363b0a872e1d9a44f3c70298a42`.
- Final repository/live boundary audited: `5f5a319b389715ef9b5283e999ef33322ae5ff51` — PR #377 / Change 194.
- Pre-Actions recovery authority: commit `1365d84de30360b880f95bc5c51101ddeab9006c`, tree `443a77461e5dabdb53cdf0a904c135ea0b8d8baa`.
- Running instances at final live check: `kis-op` and `kis-dev`, both healthy at `5f5a319...` with identical contract fingerprint `9efa18600dabdf5b8b2f279e0f48d78f30c81058404788d144f2f5e60b0c51a0`.

## Executive conclusion

The audit reconstructed KIS-MCP forward from repository state zero to the current repository, then performed a separate semantic current-state and live-tool reconciliation. The architecture has a traceable lineage: the major removals, reversals, and recovery-era disappearances are mostly explicit decisions rather than unexplained loss.

The audit also proves that **current repository authority, current documentation, and the commissioned tool are not yet fully aligned**. The most material remaining problems are documentation authority drift, Work Management view commissioning/observability disagreement, a Serena capability-catalogue exposure leak, merge-commit Discover/review failure, stale merge-queue state, and provider commissioning-state under-reporting.

The audit itself is complete with findings. #378 owns remediation coordination; existing narrower issues remain authoritative where they already own a finding.

## Audit method and evidence rules

The historical traversal was forward: original authoritative specification/state zero -> each material engineering era -> current repository. A historical slice was judged against the requirements and authority available in its own era, then obligations were traced forward to a terminal disposition.

For each material unit the audit considered: intended outcome, implementation/removal, architecture decisions, assumptions, risks, holds/deferments, code/contracts/settings/tests, documentation consequences, commissioning obligations, defects/contradictions, and recommendation.

Historical evidence precedence was:
1. exact historical tree, governed change record, source/config/contracts/tests;
2. immutable commit/merge evidence;
3. contemporaneous PR comments/reviews and issue evidence;
4. current mutable issue/PR prose as supporting evidence only.

The final comparison was deliberately separate:
`final intended-current state -> current repository -> current documentation -> actually running MCP/tool behavior`.

Terminal dispositions used by the audit are `active-current`, `completed`, `superseded`, `intentionally-removed`, `cancelled`, `deferred`, `partially-completed`, `lost-or-unexplained`, and `unverifiable`.

Decision provenance is conservative. `Consultation not evidenced` means a material engineering decision is visible but no explicit operator consultation record was found; it does **not** mean unauthorized.

## Checkpoint evidence chain

Issue #375 contains append-only checkpoints 001-011. Checkpoint 003 explicitly corrects an omission in checkpoint 002 instead of rewriting history. Two checkpoint-005 comments cover different boundaries: first write-side Work Management commissioning through Change 113, and the earlier Change085-092 transition into live writes/exact publication/reviewer commissioning.

## Semantic history and architecture milestones

| Era | Boundary | Reconstructed outcome |
|---|---|---|
| State zero | `5ab2aa1...` | Desktop Commander + FastMCP enforcement, exactly HR-001/002/003, recoverable quarantine; broader Discover/Govern/Work existed as target architecture. |
| Early hardening | Changes 001-019 | Governed worktrees/path claims, quarantine integrity, live Desktop Commander proxy, dual HTTP instances, provider registry/composition, GitHub/Supabase adapters, first Discover and shared Skills. |
| Discover/provider maturation | Changes 017-048 | GitHub/Supabase OAuth commissioning, deterministic Git evidence, context/impact/contract/project intelligence, Tools foundation, Secrets kernel, Control Center, managed support tooling, cleanup/lifecycle hardening. |
| Capability + WM read-only | Changes 047-058 | Progressive capability composition; Work Management P0-P5 contracts including typed Decision/Assumption/Risk/Approval/Hold; Project #1 read-only commissioning with zero items. |
| First WM mutation | Change 085 onward | Live GitHub Project add/update commissioned; bounded reconciliation becomes real operational mutation while unrestricted automation remains prohibited. |
| Exact publication + reviewers | Changes 086-092 | Exact registered Git publication, Serena state/lifecycle repair, semantic-generation recovery, NVIDIA and Codex independent reviewer commissioning. |
| PR-first delivery | Changes 093-114 | Rich change intelligence, deterministic verification/review workflow, Work documentation lifecycle, exact-head provider-native GitHub Actions landing, schema-v3 simplification. |
| Shared command plane | Changes 115-125 | Shared portfolio, operator-state/repository-state separation, speculative queue, canonical Skills, tree-equivalent cleanup, and restoration of Work Management operational command-plane authority. |
| Commissioning/coherence | Changes 126-170 | Provider commissioning persistence, rich Project schema, Project Tasks programme, acquisition, review hardening, hybrid state architecture research, repeated live defect discovery. |
| Pre-Actions terminal | `1365d84...` | Last known-good normal architecture before GitHub Actions loss. |
| Actions-loss crisis | post-`1365d84` | Temporary Hyper-V/VirtualBox/local verification paths kept work moving but created parallel verification architecture. |
| Exact-tree recovery | Change 185 | Exact pre-Actions tree restored while later Git history remained evidence; repository visibility changed to public. |
| Semantic reconstruction | Changes 186-193 | Retained features rebuilt on fresh main; crisis verification authority retired; exact-target Work, default-off Control Center, repo-scoped Work, acquisition, Skills MCP resources, coordinator Slice 6 restored. |
| Current delta | Change 194 / `5f5a319...` | Deterministic housekeeping added. The implementation is repository-delivered but its durable documentation consequence was classified as `Documentation Impact: none`, creating a new documentation finding. |

## Final intended-current architecture used for commissioning comparison

The final comparison used these durable intended-current boundaries:

- **Work policy:** exactly HR-001 write boundary, HR-002 external network through ordinary Work, and HR-003 recoverable quarantine/permanent-delete prevention. No fourth hard rule is permitted.
- **Trust model:** directly supervised single-operator runtime beneath `C:\Projects`; public source visibility is distinct from the private/supervised runtime boundary.
- **Work Management:** Project fields own operational command facts such as Work State, priority, effort, scheduling, hold/defer, and execution claims. `.work`, Git/GitHub, PRs and Actions retain implementation/revision/verification authority.
- **Delivery:** freeze one exact source head; bind required specialist review and provider-native GitHub Actions to it; exact-head merge; administrative alignment after landing must not manufacture a new verification head.
- **Skills:** one canonical shared catalogue; KIS-native tools and MCP Resources are delivery surfaces over the same validated snapshot; resource delivery grants no execution authority.
- **Acquisition:** approval-gated registered profile + immutable recipe/hash authorization; provider policy owns network containment; ordinary Work HR-002 remains unchanged.
- **Providers:** readiness, mounted/current-process liveness, authentication, historical commissioning and current live verification are distinct evidence states.
- **Control Center:** available but disabled in checked-in gateway composition by default.
- **Coordinator:** reconstructed deterministic reservation/lease/fence/planning/worker/reconciliation/integration core through Slice 6; no public coordinator MCP tool is required at this boundary; Slice 7 remains separate.
- **State ownership:** centrally partitioned namespace foundation exists; consumer migration/commissioning remains #279/#280.
- **MCP authority:** current reconstructed authority remains FastMCP 3.x / MCP 2025-11-25 until the separately governed future migration.

## Final live-tool surface

Both `kis-op` and `kis-dev` were checked at `5f5a319...`; they had identical health policy and direct MCP surface. No restart was performed after the operator directed that the already-current runtimes must not be restarted.

Direct MCP surface on each instance contained **23 tools**, which matches the configured direct profile of 24 minus the intentionally disabled Control Center direct operation. Both exposed identical Skills/GitHub resources and resource templates and the same two GitHub prompts.

### Live commissioning matrix

| Plane | Live evidence | Result |
|---|---|---|
| Health/policy | both instances report source `5f5a319...`, same contract fingerprint, HR-001/002/003 only | **match** |
| Direct capability surface | 23 direct tools on both instances; identical resources/templates/prompts | **match** |
| GitHub provider | authenticated issue read for #375 succeeded | **match** |
| Supabase provider | registered project `mmxuicfrdalymczdapjq` read succeeded | **functional; status reporting gap** |
| Context7 | FastMCP library-resolution read succeeded | **match** |
| DBHub | College `results` SQLite object search returned seven tables | **functional; status reporting gap** |
| Docker Hub | public `library/python` repository check succeeded | **functional; status reporting gap** |
| Serena approved surface | `get_symbols_overview` read succeeded | **approved read works** |
| Serena capability catalogue | mutation-capable upstream operations appear eligible/discoverable despite three-tool read-only contract | **mismatch** |
| NVIDIA review | exact non-merge commit review with `nano` completed with structured evidence | **match** |
| Skills MCP Resources | catalogue read succeeded; 38 skills; `kis-mcp` resource bytes matched catalogue SHA-256 | **match** |
| Skills delivery telemetry | `mcp_resource` load/digest evidence recorded for the same `kis-mcp` package hash | **match** |
| Registered acquisition | valid registered request with `approved=false` failed closed with `APPROVAL_REQUIRED`; no acquisition executed | **match** |
| Work Management contract | live contract exposes **21** `project_management_*` operations | **tool works; root SPEC stale** |
| Work Management bounded reads | default 100-item `inventory`/`current_work` reproduce `inventory_incomplete`; explicit `item_limit=1000` completes, finds #378, and confirms #237 remains agentB-owned | **functional with pagination-contract defect** |
| Work Management fields | 25 managed fields present, no missing/type/option drift | **match** |
| Work Management views | tool reports views 02-05 unverified; operator reports Decisions, Assumptions/Risks and Holds also not commissioned | **mismatch/unresolved evidence** |
| Workflow recommendation/execution | `recommend_workflow` resolves eligible verification/review workflows; `execute_change_workflow` live-dispatches Change 198 and launches selected verification | **dispatch works; short audit smoke intentionally incomplete** |
| Speculative merge queue | empty queue base `c762d623...` vs live main `5f5a319...`, state `stale` | **mismatch** |
| Discover project/context | `inspect_project` and `get_code_context` return bounded current evidence | **match with normal truncation disclosures** |
| Discover non-merge commit | `inspect_change`/`analyze_change` on `3fd93ec...` return changed paths and impact | **match** |
| Discover merge commit | `inspect_change` on `5f5a319...` returns zero changed files although Git shows 14 files/2,119 insertions | **mismatch** |
| Review merge commit | review receives zero changed files and fails strict output contract because Discover supplies empty merge evidence | **mismatch propagated from Discover** |

## Live end-state findings

### L-001 — Serena long-tail capability exposure contradicts the declared provider boundary

Current Serena authority advertises a three-tool local read-only semantic surface: `get_symbols_overview`, `find_symbol`, and `find_referencing_symbols`. Provider readiness reports the same list. However the normalized live capability catalogue also advertises upstream mutation-capable Serena operations such as memory deletion/editing and symbol insert/replace/rename/safe-delete as eligible discoverable operations.

Source tracing identifies the mechanism: `PersistentClientProxyProvider.lifespan` publishes the raw upstream `list_tools()` snapshot; `provider_runtime_tools()` imports every tool from the runtime snapshot into capability composition. The Serena server's visibility transform constrains the provider MCP surface, but the normalized capability catalogue does not apply that approved public-tool boundary.

**Recommendation:** make provider runtime/capability composition consume the provider-approved exposed tool set, not the raw upstream snapshot; regression-test that hidden Serena mutation tools are neither discoverable nor dispatchable. Do not expand Serena authority to match the leak.

### L-002 — Discover commit inspection silently misreads merge commits as empty

`inspect_change(source="commit", commit_ref="5f5a319...")` returns `available=true`, high confidence and zero changed files. Local Git shows the same merge commit changed 14 files with 2,119 insertions. A non-merge control commit `3fd93ec...` is inspected correctly.

The empty merge result propagates: `analyze_change` rejects the merge commit because there are no changed paths, and `review_change_with_agent` receives an empty file set. This is especially material because current `main` commonly advances by merge commits.

**Recommendation:** define merge-commit semantics explicitly (normally first-parent/current-main delta for landed-change inspection), add merge-commit fixtures, and prevent a silent high-confidence empty result when the commit has a material first-parent diff.

### L-003 — Work Management view commissioning evidence disagrees with operator-visible Project state

Both runtimes report `fields_ready=true`, `views_ready=false`, no missing fields/options, and views 02-05 as unverified. The desired manifest includes 12 views, including `06 Decisions`, `07 Assumptions and Risks`, and `08 Holds and Deferred`. The operator reports the Decisions, Assumptions/Risks, and Holds views are also not commissioned even though schema status does not flag 06-08.

**Recommendation:** reconcile tool readback against the actual Project UI and strengthen view observability so schema status cannot claim behavioral verification for a view that is not actually available/usable to the operator.

### L-004 — Speculative merge-queue state is stale against current main

The live queue reports `state=stale`, queue base `c762d6230230c74f8d22a79c0ff1d16752455c6b`, live base `5f5a319...`, and zero entries. This does not prove unsafe landing, because the queue is empty, but it prevents a truthful claim that reconstructed queue state is current/commissioned.

**Recommendation:** preserve the existing Change197 live queue proof requirement; reconcile from exact current GitHub truth and demonstrate normal empty/current and queued behavior without bypassing #237 or #289.

### L-005 — Provider commissioning status under-reports successful current-process reads

Representative live reads succeeded for DBHub, Docker Hub, and the registered Supabase project. `kis_provider_status` nevertheless continues to report DBHub/Docker current upstream/tool discovery as pending and Supabase `live_verified=pending_registered_project_read` after the successful registered-project read.

**Recommendation:** make commissioning state consume successful current-process evidence consistently, while retaining the valid distinction between historical commissioning and process-local liveness.

### L-006 — Root and module documentation do not fully describe current implementation

The live Work Management contract proves 21 public operations while root `SPEC.md` still describes eight. The current Skills module exposes 12 operations while root `SPEC.md` describes eleven. Root current-product truth also does not durably summarize reconstructed Acquisition, Skills MCP Resources/delivery telemetry, Coordinator Slice 6, State Ownership foundation, or Change194 Housekeeping.

Other confirmed documentation drift includes stale Work Management projection-only wording after Change125, stale Provider module Control Center/commissioning status, stale State Ownership status, stale `LESSONS-APPLICABILITY.md` target claims, and inaccurate absolute wording that the repository contains no governance subsystem even though a dormant advisory `kis_mcp.govern` implementation exists.

**Recommendation:** perform one canonical-owner reconciliation after this historical audit record lands. Keep module detail in module specs and add only concise repository-wide current truth to root `SPEC.md`.

### L-007 — Default Work Management reads do not page beyond the public 100-item bound

The current Project exceeds 100 items. Live `project_management_inventory(project_id="kis-mcp")` and `project_management_current_work(project_id="kis-mcp", execution_owner="agentB")` both fail with `inventory_incomplete` because the public operations do not accept the returned `next_cursor`. Repeating the same reads with explicit `item_limit=1000` succeeds: the full board is complete, #378 is `Ready` / `High` / `Large` / unclaimed, and #237 remains `Active` under `agentB`.

This reproduces historical #375 Checkpoint 005 finding F-0026 and is distinct from the exact-target truncated-inventory repair lineage: exact-target resolution can be correct while the general default inventory/current-work contract still cannot page.

**Recommendation:** add cursor-aware pagination or deterministic complete-read behavior to the public Work operations while retaining fail-closed handling for genuinely incomplete provider data. Add a live regression with a Project larger than the default page bound.

## Live Work and workflow action coverage

The final audit did not infer action readiness from schemas alone. It executed the Work contract, default and enlarged Work reads, workflow recommendation, and the executable change-workflow dispatcher. The minimal workflow execution returned a real `change-execution-result-v2`, selected `scripts/verify.ps1`, and launched verification against Change 198. Because the audit deliberately imposed a short deadline, the workflow result was `incomplete`; that is execution evidence, not a passing verification claim. Audit-spawned verifier processes were then stopped and the worktree was checked for unintended edits.

State-changing Work transitions were not re-run merely to create audit evidence. Historical Changes 085/113 already preserve live Project-mutation commissioning, and the current #378 issue plus Project enrollment provide current write-side operational evidence. The audit did not alter #237 or any unrelated Work lifecycle state.

## Important positive controls

The audit intentionally preserves what is already coherent so remediation does not reopen settled boundaries:

- `AGENTS.md` current authority routing is clear and remains the top repository instruction owner.
- Exactly HR-001/HR-002/HR-003 are present in both running instances and current policy.
- Control Center is correctly registered but disabled in checked-in gateway composition.
- Acquisition's registered approval boundary is live and fails closed when approval is absent.
- Skills MCP resource delivery uses the canonical catalogue and exact package hash; resource delivery does not create execution authority.
- Coordinator absence from public MCP tools is correct through reconstructed Slice 6; its module spec explicitly keeps that surface internal pending Slice 7.
- State Ownership is an internal namespace contract, so absence of a public state MCP tool is not a defect.
- All six enabled mounted connectors completed representative current reads.
- NVIDIA advisory review works on correctly supplied non-merge change evidence.
- Discover non-merge commit inspection/analysis works; the defect is bounded to merge-commit semantics from the evidence tested.
- Change189 demonstrates correct canonical documentation promotion: implementation/settings/tests and root `SPEC.md` were updated together for Control Center default-off.

## Current terminal-disposition summary

**Completed/current foundations:** three-rule Work policy, quarantine, Discover foundations, provider/tool/capability composition, shared Skills, Work Management command plane, registered acquisition, Skills MCP Resources/telemetry, coordinator core through Slice 6, and GitHub Actions exact-head landing authority.

**Active/partial:** coordinator Slice 7 (#253), hybrid state migration/commissioning (#277/#279/#280), review batching (#335), merge-queue correctness (#237/#289), non-SPEC merge-readiness identity (#309), approval-authority investigation (#290), and current commissioning mismatches recorded above.

**Superseded/intentionally removed:** crisis-era Hyper-V/VirtualBox/local canonical verification, detached local-verifier projection, verifier-specific Serena isolation, and obsolete agent/runtime topology.

**Deferred:** FastMCP4/MCP2026 migration (#342), historical MCP programme records pending durable disposition, Govern public-composition lifecycle, provider upgrades/compatibility, and measured optimization investigations.

**Historical evidence defects:** Change093 stale closeout; Change190 malformed evidence (already assigned to #367/Change197); weak issue history for Changes086-109; duplicate numeric change prefixes.

## Remediation routing

Issue #378 is the audit-remediation umbrella. It should coordinate, not absorb, already-owned bounded work. At minimum:

1. fix the Serena runtime-tool/capability exposure contradiction with regression coverage;
2. fix merge-commit Discover semantics and prove inspect/analyze/review receive the intended merge delta;
3. reconcile Work Management views against actual Project UI, explicitly including Decisions, Assumptions/Risks, Holds/Deferred and views 02-05;
4. repair default Work Management pagination so inventory/current-work reads remain usable beyond the 100-item bound without weakening fail-closed truncation handling;
5. reconcile provider current-process commissioning status after successful live reads;
6. complete the existing queue proof/repair path, including #237/#289 where applicable;
7. reconcile root `SPEC.md` and stale module/current-status documentation through their canonical owners;
8. preserve existing historical repair ownership for Change190 (#367/Change197) and reconcile Change093 separately;
9. rerun the same end-spec-to-live-tool matrix on both instances before #378 is complete.

The detailed Decision, Assumption, Risk/Approval, Hold/Deferred, and Gap/Correction registers are in `2026-08-18-kis-history-end-state-registers.md`.

## Audit completion statement

The historical audit is complete from state zero through Change194/current `5f5a319...`, including the final commissioned-tool verification requested by the operator. That verification did **not** conclude that intended current state and live tool state are identical; it produced the live mismatches recorded above.

Accordingly, the correct terminal audit statement is:

> **Audit complete with material findings; remediation remains open under #378 and narrower existing owners.**

Future changes after `5f5a319...` are post-audit history. They should be reconciled as new deltas rather than rewriting this historical record.
