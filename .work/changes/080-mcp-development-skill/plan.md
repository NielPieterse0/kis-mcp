# MCP Development and kis-mcp Skills Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Create two ChatGPT-optimized skills: one portable MCP-development skill and one project-neutral kis-mcp operational skill with progressive disclosure and operator support.

**Architecture:** Keep stable decision flows in compact `SKILL.md` entrypoints and move conditional depth into focused one-level references. The kis-mcp skill teaches discovery/schema/effect patterns instead of copying the full catalogue, resolves project/provider targets explicitly, and treats concurrent/recent 063/077/078/079 behavior according to current remote/live status rather than freezing one development snapshot. Keep evaluation definitions outside runtime packages.

**Tech Stack:** Markdown Agent Skill package, JSON evaluation definitions, repository change-governance workflow, existing Python Skills tests.

## Global constraints

- Stay inside `scope.json`.
- Do not alter `policy/**`.
- Do not modify `settings/capabilities.settings.json` while change `078-project-registry-routing` owns it.
- Do not present draft/RC MCP behavior as stable protocol behavior.
- Do not publish an incomplete shared skill package through the runtime single-file `create_skill` operation.
- Keep the three reviewed source skills intact until the next requested skill is completed and combined review occurs.

---

### Task 1: Establish the source and activation boundary

**Files:**
- Create: `.agents/skills/mcp-development/SKILL.md`
- Test: `tests/skills/mcp-development/trigger-cases.json`

**Interfaces:**
- Consumes: repository authority, `create-skill` authoring guidance, three reviewed MCP source skills, official MCP specification evidence.
- Produces: `mcp-development` skill identity, activation boundary, and core development workflow.

- [x] Define the reusable outcome and near-miss boundary.
- [x] Verify the latest stable MCP revision against the official specification repository.
- [x] Write valid frontmatter and a compact core workflow.
- [x] Add positive, near-miss, conflict, and prompt-injection trigger cases.

### Task 2: Preserve conditional protocol and host depth

**Files:**
- Create: `.agents/skills/mcp-development/references/protocol-baseline.md`
- Create: `.agents/skills/mcp-development/references/apps.md`
- Create: `.agents/skills/mcp-development/references/local-packaging.md`

**Interfaces:**
- Consumes: core skill load conditions.
- Produces: one-level progressive-disclosure references for version-sensitive MCP, MCP Apps/ChatGPT, and local packaging.

- [x] Record the dated stable/RC protocol baseline and version-negotiation rules.
- [x] Separate MCP Apps extension semantics from ChatGPT-specific host APIs.
- [x] Reframe MCPB as optional host-specific packaging rather than core MCP.
- [x] Keep security enforcement at the actual server/host/runtime boundary.

### Task 3: Define output and abuse evaluation

**Files:**
- Create: `tests/skills/mcp-development/output-evals.json`
- Create: `tests/skills/mcp-development/abuse-cases.json`

**Interfaces:**
- Consumes: skill requirements and source-risk findings.
- Produces: three representative output cases and critical abuse checks.

- [x] Add a large remote MCP server design case.
- [x] Add a portable MCP App/ChatGPT case.
- [x] Add a malformed MCPB/ChatGPT premise case.
- [x] Add critical cases for embedded instructions, annotation-as-enforcement, draft compatibility, secret exposure, and packaging-as-sandbox errors.

### Task 4: Validate this first sub-slice

**Files:**
- Modify: `.work/changes/080-mcp-development-skill/{scope.json,spec.md,plan.md,tasks.md,closeout.md}`

**Interfaces:**
- Consumes: complete skill package and eval definitions.
- Produces: fresh structural, scope, regression, and repository verification evidence.

- [x] Validate name, description length, `SKILL.md` size, references, and JSON parsing.
- [x] Run `git diff --check`.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run `python -m pytest -q tests/skills` with the locked project interpreter.
- [x] Run full `pwsh -NoProfile -File scripts/verify.ps1` after the first-skill change-artifact updates.
- [x] Commit the first sub-slice without raising a PR (`cd5cc48`, verification follow-up `bea7d75`).

### Task 5: Add the project-neutral kis-mcp operational skill

**Files:**
- Create: `.agents/skills/kis-mcp/SKILL.md`
- Create: `.agents/skills/kis-mcp/references/{tool-selection-and-schemas,projects-and-context,providers-and-workflows,skills-module,concepts-and-errors,operator-support}.md`
- Test: `tests/skills/kis-mcp/{trigger-cases,output-evals,abuse-cases}.json`

**Interfaces:**
- Consumes: current kis-mcp authority, direct/runtime tool contracts, capability catalogue semantics, active 063/077/078/079 specs, and create-skill authoring rules.
- Produces: reusable project-neutral tool-operation guidance that loads detailed references only when the task requires them.

- [x] Expand the governed 080 claim before editing the second skill paths.
- [x] Deep-dive current tool schemas, capability discovery/dispatch, Skills, providers, Discover, Work, policy, and operator scripts.
- [x] Inspect concurrent/recent 063/077/078/079 changes, re-check remote status before PR creation, and separate landed behavior from still-transitional target state.
- [x] Create the compact `kis-mcp` entrypoint and six conditional references.
- [x] Add positive, near-miss, conflict, prompt-injection, output, and abuse evaluation definitions.
- [x] Run structural package/JSON validation.

### Task 6: Combined verification and PR preparation

- [ ] Run `git diff --check` and `scripts/change-workflow.ps1 check`.
- [ ] Run the locked-interpreter Skills regression suite.
- [ ] Run full `scripts/verify.ps1` after final change-artifact updates.
- [ ] Review the final diff for scope, stale implementation claims, hard-coded project bindings, and missing references.
- [ ] Commit the second skill and final verification record.
- [ ] Raise the deferred PR for the complete 080 branch; do not merge without normal PR review/exact-head evidence.
