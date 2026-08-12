# Govern Change Workflow Exposure Implementation Plan

**Goal:** Make the existing bounded change-execution operation a complete Govern-recommendable workflow without changing its execution authority.

**Architecture:** Add one `WorkflowDescriptor` in the existing platform catalogue. Reuse `operation.execute_change_workflow` and set `executable_steps=("execute_change_workflow",)` so the existing capability resolver can validate and recommend it.

**Tech Stack:** Python 3.11+, existing capability/workflow contracts, pytest.

## Constraints

- Stay inside `scope.json`.
- Add the descriptor test first.
- Do not change policy, capability settings, direct-profile limits, or the Slice-5 tool.

## Tasks

- [ ] Add a failing descriptor contract test.
- [ ] Add the smallest workflow descriptor to `workflow_descriptors()`.
- [ ] Run focused capability/workflow tests.
- [ ] Run scope/diff checks and canonical verification.
- [ ] Close lifecycle record, publish exact head, merge PR, and clean the worktree.
