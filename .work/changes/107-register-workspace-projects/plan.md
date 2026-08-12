# Register Workspace Projects Implementation Plan

**Goal:** Extend the strict central project registry with the eight requested local roots and only their verified GitHub repository coordinates.

**Architecture:** One declarative registry update plus reconciliation of the existing exact registry/catalogue tests. No source-code, provider, policy, or target-project mutation is required.

**Tech Stack:** JSON, Python/pytest, PowerShell repository workflow and verification.

## Global constraints

- Stay inside `scope.json` and preserve active change `106` paths.
- Preserve `kis-mcp` as the default project and all existing bindings.
- Use `github: null` for roots with no verified matching repository.
- Add no GitHub Project or Supabase routing beyond existing registrations.
- Do not alter policy, runtime authority, provider configuration, or target repositories.

### Task 1: Establish current project identities

- Use local `AGENTS.md` and Git metadata where present.
- Use the authenticated GitHub connector to confirm current repository identities and absence of matching repositories where needed.
- Record source drift rather than modifying target repositories.

### Task 2: Update the registry and contract tests

- Add all eight project definitions to `settings/projects.settings.json`.
- Update the existing project ID and GitHub repository catalogue expectations.
- Add checked-in binding assertions for the new local roots and optional GitHub coordinates.

### Task 3: Verify and integrate

- Run the focused project/repository registry tests through the locked interpreter.
- Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- Run `git diff --check` and inspect the complete branch diff.
- Run `pwsh -NoProfile -File scripts/verify.ps1`.
- Record closeout evidence, commit the bounded change, merge it to local `main`, and run governed cleanup when safe.
