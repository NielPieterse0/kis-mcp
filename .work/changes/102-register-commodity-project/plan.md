# Register Commodity Project Implementation Plan

**Goal:** Register `commodity` in the strict central project registry without expanding runtime authority.

**Architecture:** Make one declarative registry addition and update the existing checked-in registry contract test. No runtime code, provider settings, policy, or commodity project content changes are required.

**Tech Stack:** JSON, Python/pytest, PowerShell repository verification.

## Global constraints

- Stay inside `scope.json`.
- Preserve existing project registrations and `kis-mcp` as the default project.
- Add no unrequested GitHub Project or Supabase routing.
- Do not alter policy or runtime authority.

### Task 1: Register the project

- Modify `settings/projects.settings.json` with project ID `commodity`, local root `C:\Projects\commodity`, and repository `NielPieterse0/commodity`.
- Update the existing project/repository registry contract tests to include `commodity` in the bound project and GitHub repository catalogue while preserving prior bindings.

### Task 2: Verify and close out

- Run the focused project-registry test.
- Run `scripts/change-workflow.ps1 check`.
- Run `scripts/verify.ps1`.
- Review the diff, commit, publish a PR, merge, and clean the worktree.
