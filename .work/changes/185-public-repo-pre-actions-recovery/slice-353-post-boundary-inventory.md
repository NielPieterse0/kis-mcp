# Slice #353 — Post-boundary value inventory

Inventory authority range: `1365d84de30360b880f95bc5c51101ddeab9006c..3bd13309827affab06b194c054541f65af89f001` plus unmerged GitHub branch/PR heads created or advanced after the boundary.

This is inventory/classification only. Nothing below is reimplemented by Change 185.

## A — High-value independent work to reassess first after reset

| Work | State before reset | Why retain | Reimplementation posture |
|---|---|---|---|
| Change 173 / PR #320 — exact-target Work resolution | merged after boundary | Corrects repository-specific Work Management targeting without depending on Actions replacement architecture. | High-priority fresh slice; port behavior/tests deliberately. |
| Change 171 / PR #312 — Control Center UI default-off | merged after boundary | Keeps MCP runtime available while making the UI opt-in. Small and operationally useful. | Small fresh slice if still desired. |
| Change 150 / PRs #328 + #337 — parallel-agent coordinator | merged after boundary | Core safe parallel execution/coordination capability, independent of hosted Actions availability. | Reassess architecture then selectively port tested coordinator contracts/behavior. |
| Change 174 Skills MCP resources / PR #321 | open/unmerged | Completed read-only native MCP Skills resource delivery with integrity/progressive-disclosure tests. | Recreate as a fresh governed feature against restored FastMCP 3.x / MCP 2025-11-25 authority. |
| Change 175 / PR #323 — generic governed acquisition envelope | open/unmerged | Completed bounded authorization/profile-hash work with extensive local verification. | Revalidate current import-isolate contract, then port as a fresh slice. |
| Change 177 / PR #326 — repository-scoped Work Management projection | open/frozen | Defect fix preventing foreign-repository contamination; 100 focused regressions reported green. | High-priority defect reimplementation after reset. |
| Change 176 / PR #327 — deterministic housekeeping | open/frozen | Useful reconciliation/readiness automation; currently fails closed when Project provider authority is unavailable. | Reassess after core Work Management restoration; port only after provider prerequisite is proven. |

## B — Actions-loss workaround infrastructure; preserve as reference, do not automatically restore

| Work | State before reset | Classification |
|---|---|---|
| Change 174 disposable Windows execution foundation / PR #329 | merged | Pre-existing clean-room/Hyper-V execution architecture. Potentially useful as optional isolation, but not needed to replace public-repo hosted Actions. |
| Change 179 local verification landing authority / PR #332 | merged | Direct Actions-unavailable landing workaround. Do not restore as primary authority by default once hosted Actions is available; salvage exact-tree/local receipt ideas only if independently valuable. |
| Change 180 VirtualBox disposable provider / PR #336 | merged | Optional clean-room provider. Preserve design/tests as reference; reintroduce only for real isolation/commissioning need. |
| Change 179 local Windows runner / PR #339 | merged | Direct Actions-independent primary-runner replacement. Reassess as optional fallback/local acceleration, not default landing authority after public transition. |
| Change 182 / PR #345 — detached verifier claim projection | merged | Hardening specifically for detached local verification. Reintroduce only if that verifier path survives redesign. |
| Change 183 / PR #346 — Serena exact-verification test isolation | merged | Test isolation needed by repeated exact local verifier workspaces. Port only with the dependent verifier path or if the isolation bug independently remains. |

## C — Governance/programme material to re-author rather than blindly port

| Work | State before reset | Classification |
|---|---|---|
| Change 181 / PR #344 — MCP authority/platform reliability | merged programme record; implementation not started | Valuable design/governance intent, including FastMCP 3.x → normative MCP 2025-11-25 authority. Recreate later as an explicitly approved programme on the restored codebase; do not cherry-pick stale implementation assumptions. |

## D — Dependency/update branches

- `dependabot/github_actions/astral-sh/setup-uv-9.0.0`
- `dependabot/uv/fastmcp-3.4.6`
- `dependabot/uv/pytest-9.1.1`

These should be regenerated/re-evaluated against the restored dependency graph rather than replayed mechanically.

## Recovery guarantees

- All post-boundary mainline commits remain recoverable because the restoration commit will retain current `main` as its parent while adopting the exact selected baseline tree.
- Existing remote branches/PRs are not deleted by Change 185.
- No item in this inventory is authorization to implement it under Change 185.
