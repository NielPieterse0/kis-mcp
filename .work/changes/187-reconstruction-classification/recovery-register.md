# Post-Actions Recovery Register

Boundary: `1365d84de30360b880f95bc5c51101ddeab9006c` through restored pre-reset tip `3bd13309827affab06b194c054541f65af89f001`, plus preserved unmerged/local refs.

## Reimplement

| Historical work | Source evidence | Decision | Dependency/order |
|---|---|---|---|
| Change 173 / PR #320 — exact-target Work resolution | merge `979666f`, implementation commit `af501c9` | Reimplement the bounded resolution fix and regressions. | First functional slice; Work foundation for later projection/housekeeping. |
| Change 171 / PR #312 — Control Center UI default-off | merge `9adf1ca`, implementation commit `553a23c` | Reimplement the small opt-in UI default. | Independent; land immediately after Work fix. |
| Change 177 / PR #326 — repository-scoped Work projection | branch `b07a74c` | Reimplement the repository-binding isolation defect fix. | After Change 173 behavior is restored. |
| Change 175 / PR #323 — governed acquisition envelope | branch `208b81a` | Reimplement authorization/profile-hash envelope. | Independent after Work fixes. |
| Change 174 / PR #321 — Skills MCP resources | branch `5cf2406` | Reimplement read-only canonical Skills resources and delivery telemetry. | Must be reviewed against FastMCP 3.x + normative MCP `2025-11-25`. |
| Change 150 / PRs #328 + #337 — parallel-agent coordinator | merges `6a5e843`, `5c924a9`; preserved final ref `archive/185-preserved/150-parallel-agent-coordinator` | Reimplement coordinator contracts/state/planning/reconciliation only. | After basic Work/project fixes; exclude execution-runner workaround coupling. |
| Change 176 / PR #327 — deterministic housekeeping | branch `aac840b` | Reimplement after Work provider correctness is restored. | After 173 + 177; validate live provider prerequisite first. |

## Retire / supersede

| Historical work | Source evidence | Decision |
|---|---|---|
| Change 172 — ignore local agent runtime dirs | branch `7bb71c0` | Retire; obsolete `.kis-mcp-agent-doc/.kis-mcp-agent-gov` topology is not part of current runtime. |
| Change 175 — register local tool-user projects | branch `4c83f4b` | Retire; obsolete `kis-mcp-doc` / `kis-mcp-gov` local tool-user projects are not required. |
| Change 178 aliases — correctness/search regression | refs `change/178-*` at `9adf1ca` | Superseded; refs contain no unique commits beyond already classified 171/173 work. |
| Change 174 / PR #329 — disposable Hyper-V execution | merge `b68da37` | Retire as Actions-loss workaround; preserve history only. || Change 179 / PR #332 — local verification landing authority | merge `fc85e35` | Retire; GitHub Actions is restored exact-head merge authority. |
| Change 180 / PR #336 — VirtualBox disposable provider | merge `8cc759d` | Retire; optional VM provider is not required for hosted verification. |
| Change 179 / PR #339 — local Windows runner | merge `238431c` | Retire; local runner is no longer primary verification/landing authority. |
| Change 182 / PR #345 — detached verifier claim projection | merge `e3bd107` | Retire with detached local verifier path. |
| Change 183 / PR #346 — Serena exact-verifier isolation | merge `f162247` | Retire with detached verifier path; reintroduce only if an independent isolation defect recurs. |
| Change 184 stopped implementation ref | `change/184-mcp-authority-source-execution` at `3bd1330` | Superseded; contains no approved implementation beyond the old 181 programme state. |
| Debug backup `backup/182-timeout-experiment-6a28694` | local ref | Historical/debug only; not reconstruction authority. |

## Re-author / future

| Historical work | Source evidence | Decision |
|---|---|---|
| Change 181 / PR #344 — MCP authority/platform reliability programme | merge `3bd1330` | Re-author after retained foundations land; preserve FastMCP 3.x → normative MCP `2025-11-25`; do not replay stale assumptions. |
| Dependabot PR #150 — setup-uv | GitHub PR | Future dependency maintenance; regenerate/re-evaluate against reconstructed `main`. |
| Dependabot PR #152 — FastMCP 3.x patch | GitHub PR | Future dependency maintenance; remain on FastMCP 3.x and separately validate MCP authority before any bump. |
| Dependabot PR #153 — pytest | GitHub PR | Future dependency maintenance; regenerate/re-evaluate against reconstructed test graph. |

## Stale PR handling

- PRs #321, #323, #326, and #327 remain historical harvest sources until their fresh replacement slices land; then close them as superseded.
- PRs #329, #332, #336, #339, #345, and #346 are merged historical evidence but their architecture is intentionally absent from restored `main`.
- No historical commit is cherry-picked as merge authority; selected files/behavior may be ported into fresh changes and reverified.
## Host/runtime residue

- VirtualBox is installed and exposes one host-only adapter (`192.168.56.1`); `VBoxManage list vms` returned no registered VMs.
- No VM image/ISO evidence was established as required product state; system software uninstall is not justified by this programme.
- `C:\Projects\.kis-mcp\execution\local\runs` contains historical detached local-verifier/commissioning workspaces referenced by `git worktree list`; these are KIS-owned generated residue and are retirement-slice quarantine candidates after confirming no live owner process.
- Preserved Git branches and Change 185 archive refs are evidence, not runtime residue, and must not be deleted for cleanup aesthetics.

## Verification/merge workflow decision

The restored baseline already implements the lean lifecycle requested by the operator. No workflow code change is required in this slice:

1. Run focused development checks only while editing.
2. Finalize code plus evidence-bearing change metadata and run `change-workflow.ps1 check`.
3. Freeze one immutable candidate head and publish/create the PR.
4. Run required specialist reviews and GitHub Actions canonical verification against that same head; these independent gates may run concurrently.
5. If the head changes, rerun invalidated head-bound evidence once; otherwise do not reverify.
6. Merge only the approved exact head, refresh/align `main`, then perform administrative reconciliation and safe cleanup without a metadata-only source commit.

For this serial programme, GitHub/KIS merge-queue integration is unnecessary overhead because each child must start from the previously merged `main`. Direct exact-head merge after Actions success is the fastest compliant path.

## Frozen serial order

1. 188 — exact-target Work resolution.
2. 189 — Control Center UI default-off.
3. 190 — repository-scoped Work projection.
4. 191 — governed acquisition envelope.
5. 192 — Skills MCP resources under FastMCP 3.x / MCP `2025-11-25`.
6. 193 — parallel-agent coordinator, excluding Actions-loss execution runners.
7. 194 — deterministic housekeeping after live Work-provider prerequisite check.
8. 195 — retirement reconciliation: quarantine confirmed stale KIS execution residue and close superseded stale PRs.
9. 196 — re-author MCP/platform reliability programme against reconstructed `main`.
10. 197 — parent-programme final reconciliation and Change 186 closeout evidence.