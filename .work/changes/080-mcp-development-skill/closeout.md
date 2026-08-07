# Closeout: MCP Development and kis-mcp Skills

## Implemented scope

- Added `.agents/skills/mcp-development/SKILL.md` as the consolidated MCP-development entry skill.
- Added focused references for the protocol baseline, MCP Apps/ChatGPT UI, and local packaging.
- Added external trigger, output, and abuse evaluation definitions under `tests/skills/mcp-development/`.
- Left the three source MCP skills intact for comparison and deferred replacement/removal.
- Added `.agents/skills/kis-mcp/SKILL.md` as the operational entry skill for kis-op/kis-dev usage.
- Added six kis-mcp references covering tool/schema selection, project context, providers/workflows, Skills, concepts/errors, and operator support.
- Added external trigger, output, and abuse evaluation definitions under `tests/skills/kis-mcp/`.
- Kept project/provider identifiers generic and re-checked concurrent/recent 063/077/078/079 status before PR publication; still-unmerged behavior remains conditional on checked-in/live runtime evidence.
- Did not publish either multi-file package to the shared runtime catalogue because the current runtime `create_skill` mutation accepts only `SKILL.md` and cannot publish required references as one complete package.
- Did not edit `settings/capabilities.settings.json` because active change 078 owns that integration path.

## Validation evidence

- First `mcp-development` sub-slice: structural validation, `git diff --check`, scope check, `32 passed` Skills regression tests, and full `scripts/verify.ps1` all passed before commits `cd5cc48` / `bea7d75`.
- Source-skill structural comparison: current active `build-mcp-server`, `build-mcp-app`, and `build-mcpb` snapshots were evaluated through the kis-dev Skills surface.
- `kis-mcp` package structural validation: passed with `SKILL.md` at 187 lines, 507-character description, six referenced files present, and all trigger/output/abuse JSON parsing successfully.
- Combined post-second-skill validation: `git diff --check` passed; `scripts/change-workflow.ps1 check` passed; locked-interpreter `tests/skills` passed; full `scripts/verify.ps1` passed with configuration, interpreter, dependency, Python syntax, change-governance, and complete pytest checks reporting `ok: true` / exit code 0.

## Review

- Finding: the reviewed source skills contain Claude-oriented defaults and host-specific claims that should not be inherited as core MCP requirements.
  - Resolution: the consolidated skill is spec-first and isolates MCP Apps, ChatGPT behavior, and local packaging.
- Finding: the official repository exposes a `2026-07-28` RC/draft while `2025-11-25` remains the latest stable core release at the verification date.
  - Resolution: the skill uses stable-first guidance and requires fresh version checks.
- Finding: runtime `create_skill` cannot publish a multi-file skill package.
  - Resolution: keep complete packages repository-local in this branch and do not create partial active runtime entries.
- Finding: current main still contains repository-specific routing while active change 078 replaces it with a central project registry.
  - Resolution: the operational skill is project-neutral and only names `kis_list_projects` / `kis_project_status` conditionally when advertised by the live runtime.
- Finding: concurrent/recent 063/077/078/079 work changes capability schemas, startup semantics, project routing, and workflow operations adjacent to this skill; remote status changed during the slice and 079 landed before PR creation while 077 remained open.
  - Resolution: document stable selection/effect/status concepts, re-check current status before publication, and defer still-mutable behavior to live capability/status evidence or the current checked-in operator script.
- Finding: copying the complete tool/provider catalogue would quickly become stale and increase activation cost.
  - Resolution: the skill teaches direct-versus-discoverable selection, exact schema inspection, and effect-separated dispatch instead of duplicating the catalogue.

## Git and merge

- Branch: `change/080-mcp-development-skill`
- Worktree: `.work/worktrees/080-mcp-development-skill`
- First sub-slice commits: `cd5cc48` (`docs: add consolidated MCP development skill`) and `bea7d75` (`docs: record MCP skill slice verification`).
- Second-skill local commits: `4ec617f` (`docs: add kis-mcp operational skill`) and `df9d56a` (`docs: align skills with concurrent runtime changes`).
- Remote publication: branch `change/080-mcp-development-skill` was created from current remote `main` and published through the authenticated GitHub provider because local Work correctly prohibits network push.
- Remote published head before this handoff update: `0a31ca18dda40e55a02715597b5af7329ddb296f`.
- Pull request: #91 — `Add MCP development and kis-mcp operational skills`; opened and intentionally not merged.
- Cleanup: not applicable while PR #91 remains open and the branch/worktree remain active.

## Residual items

- Integrate runtime capability metadata for the new skills after active change 078 releases `settings/capabilities.settings.json`.
- Promote complete multi-file packages to the shared runtime catalogue only through a mechanism that preserves all references; do not use single-file `create_skill` for these packages.
- Evaluate future Skills-over-MCP compatibility separately after the working-group extension stabilizes.
