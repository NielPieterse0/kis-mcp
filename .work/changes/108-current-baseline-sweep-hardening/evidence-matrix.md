# Evidence Matrix: Current Baseline Sweep Hardening

| Domain / current claim | Evidence exercised | Sweep result |
|---|---|---|
| HR-001/002/003 policy and hard-block register | Baseline canonical verifier; 17 operator decisions parsed from current register | Green; approvals now fully reflected in Control Center parser |
| Desktop Commander / startup containment / quarantine | Baseline canonical verifier; provider-domain regression sweep | Green; no policy expansion |
| Remote KIS transport | Existing dual-instance health plus stateless transport contract tests | Green; process-stable health fingerprint added |
| Long-chat diagnostics | Middleware/runtime-observability tests; Control Center render tests | Added bounded initialize/tools-list/tools-call correlation without payload logging |
| Registered project routing | Most-specific nested-root regression tests | Fixed; nested app-builder projects resolve deterministically |
| Discover inspect/analyze/context | Discover regression suite plus live verification-selection probe | Green; public non-working-tree inspect_change reader wiring repaired |
| Verification selection/execution | Selection live probe + workflow/verification tests | Green; selector remains read-only by contract |
| Python quality discovery | Discover/workflow regression suite and canonical verifier | Green; existing Ruff/coverage/Vulture/LibCST/mypy/Pyright evidence retained |
| agnix validation | Real 0.45.0 binary low/normal budget runs + agent-validation tests | Fixed plain-text file-limit classification |
| Provider registry/composition | Provider/capability regression sweep; live kis-op/kis-dev provider status | Fixed current docs to seven registered providers and five mounted adapter families |
| Context7 | Live provider smoke, exact exit 0 | Passed local startup/discovery; external docs query intentionally not exercised through Work |
| Serena | Live provider smoke, exact exit 0; runtime-tool eligibility regression | Fixed catalogue exposure seam; semantic read/quarantine-restore/offline state passed |
| GitHub MCP | Live provider status both instances + provider tests | Authenticated/commissioned; fixed hard-coded kis-op label for kis-dev |
| Supabase | Live registered-project read on kis-dev + status | Commissioned to registered-project-read on both instances |
| NVIDIA/Codex advisory review | Workflow/provider regression suite; final specialist review pending | Current implementation retained; no mutation authority |
| Skills module | Full Skills domain regression group | Green; shared catalogue model unchanged |
| Capability catalogue/progressive exposure | Capability/runtime regression group | Green; Serena runtime snapshot now participates correctly |
| P5 work management | Work-management/project-management regression suites; live inventory/reconcile preview/portfolio status | Green; persistence mutation covered deterministically by tests |
| Exact registered GitHub operations | Registered-GitHub/workflow regression suites; final delivery pending | Current exact-head/tree semantics retained |
| Seven-slice completion coordinator | Completion/workflow regression suites; final coordinator delivery pending | Current implementation retained and will be exercised for this change |
| Control Center structured snapshot | Control Center full tests + actual worktree snapshot | Fixed approval parsing and standalone mount-state truthfulness |
| Control Center UI | Headless Chrome at 1440x1000 and actual 390x844 | Fixed narrow responsive grid/navigation; no mojibake/external scripts |
| Current documentation authority | 12-owner stale phrase/encoding scan + manual spec sweep | Provider/startup/Discover/current-state drift reconciled; historical docs left untouched |
| AgentSys managed bootstrap | Baseline/current canonical verification and existing bootstrap tests | No new defect found; general provider mounting remains out of scope |
| Govern plane / broader target roadmap | Target-state docs inspected against current claims | Not implemented by this sweep; remains explicitly target-state |

## Verification notes

- Baseline canonical verification passed before implementation.
- Main platform-domain regression sweep passed on the exact locked interpreter with one expected skip.
- Context7/Serena live smoke exits 0 when provider stderr is captured separately from PowerShell error records.
- Final changed-area regression: 66 passed. Canonical verifier passed with two expected skips and 268 Python files syntax-checked; scope and diff checks passed.
- Ruff is not installed in the locked environment, so no Ruff pass is claimed. Codex CLI and NVIDIA NIM review attempts failed before findings; manual spec/diff/test/authority review found no blocking issue.
- Exact GitHub delivery, merge, lifecycle reconciliation, and cleanup remain to be recorded in `closeout.md`.
