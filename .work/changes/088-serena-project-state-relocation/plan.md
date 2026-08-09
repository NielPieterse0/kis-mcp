# Serena Project State Relocation Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Relocate Serena project state outside repository worktrees and prevent local state recreation.

**Architecture:** Keep Serena 1.6.1 unchanged. Add one canonical `project_data_root` to provider JSON, derive the Serena central `$projectFolderName/.serena` template from it, reconcile Serena's external global config before launch, pre-create the selected central path, and protect same-name roots with a JSON identity marker. Route HR3-07 memory artifact resolution through the same central path.

**Tech Stack:** Python 3.13 KIS runtime/tests; pinned Serena 1.6.1 Python 3.11 venv; FastMCP stdio; PowerShell verification; KIS recoverable quarantine.

## Global constraints

- Stay inside `scope.json`; do not edit `policy/**`.
- Add tests before behavior changes.
- Keep all generated provider state under `C:\Projects` and production Serena project state under `C:\Projects\.kis-mcp`.
- Preserve `UV_OFFLINE=1`, hidden Serena mutation tools, and HR3-07 quarantine semantics.
- Do not hide repo-local state with `.gitignore`; prevent its creation.

---

### Task 1: Prove and model the defect

- [x] Quarantine the accidental primary `.serena` directory with recovery evidence.
- [x] Confirm pinned Serena 1.6.1 supports `project_serena_folder_location` and prefers the configured path when it exists.
- [x] Add RED tests for central state mapping and memory relocation.

### Task 2: Implement bounded relocation

- [x] Add JSON-governed `project_data_root` and strict settings validation.
- [x] Reconcile Serena global config before launch and pre-create central project state.
- [x] Add same-folder-name identity collision protection.
- [x] Route semantic activation and HR3-07 memory resolution through the centralized path.

### Task 3: Verify and close

- [x] Re-run focused Serena relocation/memory tests.
- [x] Run the bounded live Context7/Serena smoke and verify source projects remain free of `.serena`.
- [x] Run governed scope validation and canonical `scripts\verify.ps1`.
- [ ] Commit, integrate to `main`, restart `kis-dev`, exercise Serena on primary `main`, and prove `git status` remains clean.
- [ ] Publish the exact verified final `main` SHA through the 087 registered-GitHub operation and clean the 088 worktree/branch without force.
