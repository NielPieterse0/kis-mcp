# Change Specification: MCP Development and kis-mcp Skills

- **Change ID**: `080-mcp-development-skill`
- **Status**: Active
- **Risk Profile**: standard

## Outcome

Create two ChatGPT-optimized Skills in one bounded slice: `mcp-development`, which consolidates the reviewed MCP server/app/MCPB guidance against official protocol sources, and `kis-mcp`, which progressively discloses project-neutral operating guidance, schemas, workflows, providers, Skills, policy semantics, and operator support for the local kis-mcp tool.

## Authority and scope

- Authoritative repository sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- External protocol source: official `modelcontextprotocol/modelcontextprotocol` specification repository; stable baseline verified as `2025-11-25` on 2026-08-08.
- External UI extension source: official `modelcontextprotocol/ext-apps` repository; stable Apps specification verified as `2026-01-26` on 2026-08-08.
- ChatGPT host source: current OpenAI developer guidance and the installed `build-chatgpt-app` skill, treated as host-specific evidence rather than core MCP authority.
- Skill-authoring source: `C:\Projects\.agents\skills\create-skill` plus the local evaluation guidance requested by the operator.
- Owned paths: `.agents/skills/mcp-development/**`, `.agents/skills/kis-mcp/**`, `tests/skills/mcp-development/**`, `tests/skills/kis-mcp/**`, `.work/changes/080-mcp-development-skill/**`.
- Shared paths: none.
- Excluded paths: `policy/**`.
- Dependencies: none.
- Integration owner: none.

## Requirements

- **REQ-001**: Create one `mcp-development` skill with valid Agent Skill frontmatter and an intent-based activation description.
- **REQ-002**: Keep the default workflow in `SKILL.md` below 500 lines and move conditional depth into one-level references.
- **REQ-003**: Separate core MCP protocol, MCP Apps extension behavior, ChatGPT-specific host behavior, and host-specific local packaging.
- **REQ-004**: Treat the latest stable MCP specification as normative and label RC/draft behavior as non-stable unless explicitly targeted.
- **REQ-005**: Preserve useful server, UI, and local-packaging guidance from the three reviewed source skills while removing Claude-only defaults from the core workflow.
- **REQ-006**: Include trigger, output, and abuse evaluation definitions outside the runtime package.
- **REQ-007**: Do not activate or publish an incomplete shared runtime skill merely to exercise the runtime `create_skill` operation, because that operation accepts only `SKILL.md` and cannot publish the required reference files.
- **REQ-008**: Do not remove the three source MCP skills in this slice; retain them until the consolidated replacement and downstream catalogue metadata are reviewed separately.
- **REQ-009**: Create one `kis-mcp` operational skill that activates for use of `kis-op`, `kis-dev`, or another kis-mcp connection and teaches tool selection, schema use, status semantics, workflows, Skills, policy, and operator support.
- **REQ-010**: Keep `kis-mcp/SKILL.md` compact and progressively disclose detailed guidance through focused one-level references for tool/schema use, project context, providers/workflows, Skills, concepts/errors, and operator support.
- **REQ-011**: Make all kis-mcp usage guidance project-neutral: resolve explicit local paths, stable project IDs, repositories, GitHub Projects, and Supabase targets from live/user/configuration evidence rather than encoding kis-mcp-specific bindings as defaults.
- **REQ-012**: Treat concurrent/recent changes 063, 077, 078, and 079 as transitional evidence. Re-check remote/current status before PR creation, describe unmerged behavior only conditionally, and prefer live/runtime or checked-in evidence when a slice has already landed.
- **REQ-013**: Preserve the exact HR-001/HR-002/HR-003 Work semantics and distinguish structural `DISCOVER_*`, `SKILLS_*`, readiness, schema, and dispatcher errors from policy decisions.
- **REQ-014**: Add trigger, output, and abuse evaluation definitions for `kis-mcp` outside the runtime package, including project-neutral, schema-discipline, provider-status, startup, and policy-bypass cases.
- **REQ-015**: Do not modify `settings/capabilities.settings.json` while active change 078 owns it. Each new skill must carry the minimum intrinsic `category` and `capabilities` frontmatter required for runtime composition; centralized activation/effect/workflow-role enrichment remains an integration item after that claim is released.

## Acceptance

1. **Given** the new skill package, **When** its frontmatter and references are structurally validated, **Then** the name matches the directory, description remains within the portable limit, `SKILL.md` remains below 500 lines, and all referenced files exist.
2. **Given** a version-sensitive MCP task, **When** the skill is followed, **Then** the workflow distinguishes the stable specification from drafts/RCs and requires capability/version checks.
3. **Given** an MCP App task, **When** the app reference is loaded, **Then** MCP Apps and ChatGPT-specific APIs remain separate compatibility layers.
4. **Given** an MCPB request, **When** the packaging reference is loaded, **Then** MCPB is treated as host-specific packaging rather than core MCP or a ChatGPT distribution requirement.
5. **Given** a kis-mcp operation whose schema is not already exposed, **When** the skill is followed, **Then** it searches/describes the live capability and uses the exact original argument schema instead of guessing parameters.
6. **Given** a task for any registered project beneath `C:\Projects`, **When** the skill resolves context, **Then** it does not silently default to the kis-mcp repository and keeps project identity separate from provider authentication.
7. **Given** provider or workflow status, **When** the skill interprets it, **Then** registration, readiness, mount, authentication, commissioning, eligibility, and recommendation remain distinct evidence layers.
8. **Given** operator startup/support work, **When** the corresponding reference is loaded, **Then** it covers startup, tunnel credential/profile, smoke, provider onboarding, Control Center, verification, worktree governance, and troubleshooting without embedding credentials.
9. **Given** concurrent/recent 063/077/078/079 work, **When** the new skill mentions affected behavior, **Then** it re-checks current status, treats still-unmerged target state conditionally, and remains compatible with older instances.
10. **Given** both new skill packages and their evaluations, **When** structural checks, Skills tests, change-scope validation, `git diff --check`, and canonical repository verification run, **Then** they pass without policy or unrelated path changes.

## Risks and recovery

- Risk: external specifications evolve after this skill is written.
  - Recovery: require fresh primary-source checks for version-sensitive decisions and keep a dated baseline reference rather than hard-coding a permanent latest claim.
- Risk: consolidation removes useful specialized depth.
  - Recovery: retain the original source skills during this sub-slice and keep focused Apps/local-packaging references in the new package.
- Risk: ChatGPT-specific helpers become mistaken for normative MCP APIs.
  - Recovery: explicitly isolate host-specific APIs and require current OpenAI documentation before implementation.
- Risk: the kis-mcp usage skill freezes project/provider/startup behavior while active slices are still landing.
  - Recovery: keep stable concepts in the entrypoint, put mutable detail in conditional references, and require live capability/status evidence for 063/077/078/079 target behavior.
- Risk: the operational skill becomes a duplicate API manual with high context cost.
  - Recovery: document selection/schema patterns and representative shapes while treating exact live schemas as authoritative.

## Out of scope

- Modifying kis-mcp runtime Skills implementation.
- Changing `settings/capabilities.settings.json` while change `078-project-registry-routing` owns it.
- Publishing or removing shared runtime skills in `C:\Projects\.agents\skills` in this branch; catalogue promotion/metadata follows after the conflicting settings claim is released.
- Implementing the future Skills-over-MCP working-group extension.
- Changing project/provider/startup/workflow implementation owned by active changes 063, 077, 078, or 079.
- Merging this branch without normal PR review and exact-head verification.
