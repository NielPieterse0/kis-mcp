# Change Specification: Register Workspace Projects

- **Change ID**: `107-register-workspace-projects`
- **Status**: Active
- **Risk Profile**: lean
- **Development level**: Medium — one bounded declarative outcome spans the registry and existing exact-catalogue tests; no runtime code, provider authority, persistent application data, or policy changes.

## Outcome

Register the eight requested local project roots in the KIS central project registry, binding only GitHub repositories that were verified from current local or GitHub evidence.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, `settings/projects.settings.json`.
- Owned paths: `settings/projects.settings.json`, four existing project/repository registry tests, and this change record.
- Shared paths: none.
- Excluded paths: `policy/**`.
- Dependencies: none; active change `106-reviewable-pr-coordinator` owns disjoint paths.
- Integration owner: none.

## Requirements

- **REQ-001**: Register `chatgpt-skill`, `import-isolate`, `doc-solution`, `app-builder`, `app-dev-core`, `mi-fi`, `prose2llm`, and `signal` with their exact requested local roots.
- **REQ-002**: Bind current verified GitHub repositories for `chatgpt-skill`, `doc-solution`, `app-dev-core`, `mi-fi`, `prose2llm`, and `signal`.
- **REQ-003**: Register `import-isolate` and `app-builder` as local-only because neither has a matching accessible GitHub repository and neither local root is a Git repository.
- **REQ-004**: Preserve all existing registrations, `kis-mcp` as the default project, existing GitHub Project routing, and existing Supabase routing.
- **REQ-005**: Do not modify the requested projects, their Git remotes, provider settings, policy, or runtime code.

## Acceptance

1. The checked-in registry validates and loads with all twelve projects.
2. Every requested absolute local root resolves to its stable project ID.
3. The GitHub repository catalogue contains exactly the ten registered repository bindings and excludes the two local-only projects.
4. Existing `college`, `commodity`, `gpt-os`, and `kis-mcp` bindings remain unchanged.
5. Focused registry tests, scope validation, diff checks, and canonical repository verification pass.

## Risks and recovery

- Risk: a wrong repository coordinate could authorize KIS connector operations against the wrong repository.
- Recovery: revert the bounded registry/test commit; no target project content is changed.
- Known source drift: `C:\Projects\ChatGPT-skill` still has an old local remote/AGENTS repository name, while the current accessible GitHub identity is `NielPieterse0/chatgpt-skill`; KIS binds the current GitHub identity only.

## Out of scope

- Creating missing GitHub repositories for `import-isolate` or `app-builder`.
- Repairing target-project Git metadata, including the stale `ChatGPT-skill` remote or the absent `.git` metadata under `signal`.
- Adding GitHub Project or Supabase bindings not explicitly requested.
