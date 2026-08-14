# Workspace Agent Trigger Probe Implementation Plan

**Goal:** Prove the smallest safe external trigger path into ChatGPT Workspace Agents and identify which ingress mechanisms are usable from current KIS/GitHub infrastructure.

**Architecture:** Keep the OpenAI call in GitHub-hosted execution. Normalize `workflow_dispatch` and `repository_dispatch` into one envelope, then call the documented Workspace Agents trigger endpoint only in explicit live mode. KIS/Workbench uses the existing GitHub Actions trigger provider rather than local HTTP.

**Tech stack:** Python 3 stdlib, pytest, GitHub Actions, official GitHub MCP provider.

## Constraints

- Stay inside `scope.json`.
- No unrestricted local Work network call to OpenAI.
- No credentials in repository content or logs.
- Treat HTTP `202` as trigger acceptance; do not require beta run tracking.
- Workflow-hosted commissioning requires the workflow file on GitHub's default branch.
- The current user-owned GitHub Project is not treated as supporting `projects_v2_item` webhooks.

## Task 1 — Contract-first trigger helper

- Write failing tests for event normalization, endpoint, headers, payload, 202 handling, failure redaction, and validate mode.
- Implement the smallest stdlib helper that satisfies the OpenAI contract.
- Keep local tests network-free through a mocked opener.

## Task 2 — GitHub-hosted ingress

- Add one workflow supporting `workflow_dispatch` and `repository_dispatch`.
- Store the Workspace Agent trigger ID in repository variable state and access token in GitHub secret state.
- Use one normalized helper path for both events.
- Prove KIS exposes `github_actions_run_trigger` for Workbench/KIS -> `workflow_dispatch`.

## Task 3 — Verification and commissioning

- Run focused tests, syntax checks, diff checks, and change-governance validation.
- Run risk-scaled architecture, security, API-contract, and code-quality review.
- Publish through the registered KIS GitHub path and require exact-head GitHub verification.
- After the workflow is on `main`, invoke validate mode through KIS/GitHub Actions.
- If Workspace Agent configuration is present, run a harmless live trigger; otherwise record the exact missing prerequisite without treating it as a pass.

## Task 4 — Recommendation

- Record the viable ingress matrix: KIS `workflow_dispatch`, generic external `repository_dispatch`, future organization Project webhook, and scheduled reconciliation.
- Recommend slice 2 only if the trigger path is technically validated.
