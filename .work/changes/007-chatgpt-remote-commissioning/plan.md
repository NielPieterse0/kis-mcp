# ChatGPT Remote Commissioning Implementation Plan

> **For agentic workers:** execute task-by-task with test-first changes and review checkpoints.

**Goal:** Add a settings-driven, dual-instance ChatGPT remote MCP commissioning path while retaining the existing stdio runtime.

**Architecture:** Reuse `build_server()` for policy/provider behavior. A separate `remote_runtime.py` entry point serves loopback streamable HTTP. PowerShell scripts read canonical JSON, create and validate tunnel profiles, supervise the HTTP and tunnel processes, and run local behavioral commissioning.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, PowerShell 7, OpenAI tunnel-client, pytest.

## Global Constraints

- Write only beneath `C:\Projects`.
- Do not change the three-rule policy.
- Do not commit credentials, real operator IDs, or generated tunnel profiles.
- Keep `scripts/start.ps1` as the local stdio entry point.
- Use `C:\Tools\openai-tunnel-client\tunnel-client.exe` from settings.
- Support exactly `operation` and `development`; switching is explicit.
- Expose the full mixed-purpose tool surface; omit only necessarily network-only provider functions.

### Task 1: Isolate and baseline

- [x] Create and register the isolated worktree.
- [x] Read repository authorities and harvest the minimal SDK Tool tunnel pattern.
- [x] Run the baseline repository verification: 149 passed, 1 skipped.

### Task 2: Settings and HTTP runtime

- [x] Write failing tests for dual instances, loopback/path validation, instance selection, and HTTP run arguments.
- [x] Add strict `remote_mcp` validation and immutable instance configuration.
- [x] Add separate `operation` and `development` settings with blank external IDs and `configured: false`.
- [x] Add `kis_mcp.remote_runtime` using the same `build_server()` gateway as stdio.
- [x] Verify the cycle: 153 passed, 1 skipped.

### Task 3: Tunnel lifecycle scripts

- [x] Write failing tests for canonical settings sourcing, profile protection, instance switching, readiness, and paired cleanup.
- [x] Add `tunnel-state.ps1`, `setup-tunnel.ps1`, and `start-chatgpt.ps1`.
- [x] Add tunnel-client doctor validation after profile creation.
- [x] Keep credentials as environment references and generated state outside the repository.

### Task 4: Behavioral smoke test

- [x] Write failing tests for full representative tool exposure and smoke recovery.
- [x] Add local streamable HTTP initialize, tools/list, and tools/call checks.
- [x] Verify 29 tools on both instances, including filesystem/edit/process tools.
- [x] Verify the network-only feedback tool remains absent.
- [x] Execute `kis_health`, real `write_file`, `read_file`, and recoverable `kis_quarantine_path` calls.
- [x] Add best-effort failure-path quarantine before stopping the server.

### Task 5: Documentation and evidence

- [x] Update `SPEC.md` with the remote architecture, full-tool rule, and honest implementation boundary.
- [x] Update `docs/OPERATIONS.md` with configuration, setup, launch, switch, smoke, and troubleshooting steps.
- [x] Record exact local evidence and the external tunnel limitation.

### Task 6: Final review and delivery

- [x] Run authoritative verification: 158 passed, 1 skipped.
- [x] Run both-instance behavioral smoke with write/read/quarantine success.
- [x] Run the current-change scope check.
- [x] Review the final diff, secret exposure, and policy drift.
- [x] Commit and push the branch.
- [x] Open a draft PR and leave it unmerged.
