# Change: Register Import Isolate Routing

- **Change ID**: `129-register-import-isolate-routing`
- **Risk Profile**: lean

## Outcome

Register import-isolate GitHub repository routing in the central KIS project registry while preserving the shared Project #1 resource binding as a single kis-mcp-owned coordinate.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- `import-isolate` resolves to registered repository `nielpieterse0/import-isolate`.
- The shared GitHub Project #1 resource remains registered once through `kis-mcp`; `import-isolate` does not duplicate that provider resource coordinate.
- Registry-backed repository settings include `nielpieterse0/import-isolate` as an approved repository target.

## Implementation and verification

- Implementation notes: replaced the local-only `github: null` binding with the exact repository coordinate and retained an empty per-project `projects` tuple.
- Focused checks: `change-workflow.ps1 check` passed; `pytest -q tests/projects/test_project_registry.py tests/projects/test_project_registry_settings.py tests/repositories/test_project_registry_settings.py` passed (8 tests); `git diff --check` passed.
- Review findings: manual API-contract review found no material issue; NVIDIA review failed with upstream 502 and explicit Codex review failed with `AGENT_BACKEND_FAILED:CodexCliError`, so neither automated backend is counted as review evidence.
- CI correction: first exact-head run `31777047178` on published head `2192cea512f4493e4bd58af2c912d01a39467a94` correctly failed because the aggregate `registry.github_repositories` assertion omitted `import-isolate`; the assertion and change scope were corrected before republishing.
- Residual risk: the running pre-change KIS process cannot live-authorize the new target until the merged configuration is loaded by a fresh runtime.
- Closeout state: implementation and focused verification complete; corrected publication, exact-head CI, landing, and fresh-runtime routing proof remain.
