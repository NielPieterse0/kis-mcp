# Closeout: Serena Project State Relocation

## Implemented scope

- Added canonical `project_data_root=C:\Projects\.kis-mcp\serena\projects` to Serena provider JSON.
- KIS now reconciles Serena 1.6.1 `project_serena_folder_location` to the central `$projectFolderName/.serena` template before activation and pre-creates the selected central path.
- Added exclusive JSON `project-root.json` identity binding so different same-name project roots cannot race into shared Serena state.
- Routed semantic activation and HR3-07 memory artifact resolution through the same centralized state path; repo-local `.serena` is no longer required or expected.
- The accidental primary repo-local `.serena` found during closeout was moved to recoverable quarantine as operation `ed6c0f27859b41b99f7854f621fe9a2d`, SHA-256 `be4caecd616d26805f70a24aeb6d475f2c2fa55cf2056c1f66f1f78c748ce336`.

## Validation evidence

- RED proof: initial focused run failed exactly on missing central state model/path APIs.
- Focused relocation/memory suite passed 8/8; hardened provider integration suite passed 41/41.
- Live Context7/Serena smoke passed twice after relocation and once after final hardening; retained evidence is `C:\Projects\.kis-mcp\commissioning\088-provider-live-smoke.json`.
- Final live evidence: Serena 1.6.1 offline semantic reads passed; exact memory quarantine/restore passed; restart catalogue/content passed; `repo_local_state_absent=true`; centralized artifact path was beneath `C:\Projects\.kis-mcp\serena\projects`.
- Canonical `scripts\verify.ps1` passed twice during 088; the final hardened run completed with pytest exit 0, two expected skips, 246 Python files, 79 governance claims, and passing configuration/interpreter/dependency/syntax/line-ending checks.
- `scripts/change-workflow.ps1 check` passed with only declared 088 paths.

## Review

- Direct diff review found two hardening risks before landing: project-data root drift outside Serena's external state root, and a simultaneous marker-creation race. Both were fixed before the final focused/full/live gates.
- The advisory code-review backend was attempted and returned `AGENT_BACKEND_UNAVAILABLE`; it produced no findings and is not counted as review evidence.
## Git and merge

- Branch: `change/088-serena-project-state-relocation`
- Worktree: `.work/worktrees/088-serena-project-state-relocation`
- Implementation commit: `a9626a98bb8fcd5be8766cc0b7bf077225aead22`.
- Integration: the implementation commit was fast-forwarded into local `main`.
- Post-integration runtime proof: fresh `kis-dev` reached `ready`; Serena created `C:\Projects\.kis-mcp\serena\projects\kis-mcp\.serena\project.yml`; `C:\Projects\kis-mcp\.serena` remained absent; primary Git status remained clean apart from the expected unpublished-main ahead count.
- This closeout record is the final metadata-only branch change before exact-head verification/publication.

## Post-closeout procedure

- Fast-forward this closeout record into `main`, run canonical `scripts\verify.ps1` on that exact head, and publish only that verified SHA through the registered-GitHub exact operation.
- Reconcile local `origin/main` to the independently verified remote SHA, then run governed `change-workflow.ps1 cleanup 088-serena-project-state-relocation`; do not force-delete the branch or worktree.
- Preserve local `recovery/080-local-divergent`, remote `automation/047-publish-temp`, and remote `change/007-chatgpt-remote-commissioning`: each still contains unique patches relative to `main` and is not a safe cleanup candidate without separate reconciliation.
