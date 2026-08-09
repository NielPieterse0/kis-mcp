# Change Specification: Registered GitHub Exact Operations

- **Change ID**: `087-registered-commit-publication`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Make `kis-op` the primary control surface for three exact GitHub operations needed by registered repositories when ordinary Work correctly blocks networked `git push`: publish an existing immutable local commit without recreating it, merge an explicitly approved pull request only at its approved head SHA, and delete an explicitly approved remote branch only at its expected head SHA.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Provider constraint: the configured official GitHub MCP `all` toolset has no raw Git-object publication or branch-ref deletion operation; do not fake either through file APIs.
- Owned paths: the exact GitHub service, capability/workflow registration, canonical runtime configuration and its validation, authoritative configuration documentation, focused tests, and this change record.
- Excluded paths: `policy/**` only. The earlier parallel 084-086 exclusions are no longer needed because those changes are closed and this is the sole remaining implementation lane.
- No dependency on the shared skill catalogue or `mcp-tool-1` runtime. GitHub CLI authentication state is referenced only by a non-secret, JSON-governed `GH_CONFIG_DIR` path beneath `C:\\Projects`.

## Requirements

- **REQ-001 — Registered target only:** Every operation accepts a `project_id`, resolves local root and GitHub repository from `settings/projects.settings.json`, and rejects unknown projects or projects without a GitHub binding.
- **REQ-002 — Exact immutable publication:** `kis_github_publish_registered_commit` resolves a local commit object, requires explicit `approved=true`, binds the remote update to an expected remote branch state, requires an existing remote head to be an ancestor of the published commit, performs no history rewrite, and verifies the remote branch resolves to the exact local commit SHA after publication.
- **REQ-003 — No persistent credential mutation:** Git publication/deletion may use `gh auth git-credential` only through per-process Git configuration. The GitHub CLI configuration directory is a non-secret path declared in canonical JSON, must resolve beneath `C:\\Projects` and outside the repository, and is passed only as `GH_CONFIG_DIR`. KIS must not run `gh auth setup-git`, write tokens, print tokens, or alter user/global Git configuration.
- **REQ-004 — Exact approval-gated merge:** `kis_github_merge_registered_pull_request` requires `approved=true`, a non-empty expected head SHA, and an explicit merge method. It invokes GitHub CLI with `--match-head-commit`, never `--admin`, and verifies the resulting PR state is merged at the authorized head.
- **REQ-005 — Exact approval-gated remote branch deletion:** `kis_github_delete_registered_branch` requires `approved=true`, verifies the branch exists at exactly `expected_head`, refuses the repository default branch, deletes only that ref with an exact lease, and verifies the ref is absent afterward. It returns the deleted head SHA as recovery evidence.
- **REQ-006 — Correct KIS surface:** The three KIS-owned `kis_github_*` operations are discoverable virtual operations in the existing capability-control contribution and execute through the already-direct `execute_external_action` entry point. They do not alter the read-only `projects` contribution, do not expand the bounded 24-operation direct profile, do not appear as extra local FastMCP tools, and remain independent of official GitHub-MCP namespace/readiness attribution.
- **REQ-007 — Fail closed:** Missing `git`/`gh`, missing authentication, stale expected SHA, invalid branch/ref, non-ancestor publication, command failure, or unverifiable post-state returns a corrective tool error without claiming success.
- **REQ-008 — Scope discipline:** Implementation remains within change 087 claims; `policy/**` is excluded and no unrelated cleanup is folded into this delivery.

## Acceptance

1. Given a registered project and immutable local commit, when publication is approved and the remote branch matches the declared base/absence, then KIS publishes the exact commit object SHA and verifies the remote ref.
2. Given a stale or non-ancestor base, when publication is attempted, then KIS blocks before any push.
3. Given an approved PR head SHA, when merge is requested, then the command contains `--match-head-commit <sha>`, contains no `--admin`, and success is reported only after merged-state verification.
4. Given a branch whose remote SHA differs from `expected_head`, when deletion is requested, then KIS performs no deletion.
5. Given the repository default branch, branch deletion is always rejected.
6. Focused tests, change-scope check, and canonical repository verification pass on the exact 087 head.

## Risks and recovery

- **Credential boundary:** `gh` owns authentication. KIS never reads or persists the token. Failure to authenticate is a corrective connector failure.
- **Concurrent remote mutation:** expected-SHA checks plus Git ref leases prevent stale publication/deletion from silently changing an unexpected ref.
- **Deletion recovery:** branch deletion returns `recovery_sha`; an operator can recreate the branch at that SHA while the object remains available. No automatic recovery mutation is performed.
- **Rollback:** remove the three workflow tools/descriptors; no schema or persistent-data migration is introduced.

## Out of scope

- Replacing the official GitHub MCP provider.
- Force-pushing or rewriting published history.
- Admin/protection bypass.
- General unrestricted `gh api` or arbitrary network command execution.
- Changing HR-001, HR-002, or HR-003.
