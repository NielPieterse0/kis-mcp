# Registered GitHub Default-Branch Refresh

KIS refreshes a registered repository's local remote-tracking default-branch ref after an exact pull-request merge so local Git status does not rely on stale `origin/<default>` state.

## Authority

- GitHub MCP supplies the exact expected default-branch SHA to KIS.
- The central KIS project registry supplies the local root and registered GitHub repository identity.
- The local `origin` URL must resolve to that registered repository before any network or ref mutation.
- KIS re-verifies the exact SHA against the registered GitHub remote before and after materializing the commit object.

## Mutation boundary

`kis_github_refresh_registered_default_branch` may update only:

`refs/remotes/origin/<default-branch>`

The update uses Git compare-and-swap semantics with the previously observed tracking SHA. The operation does not update `refs/heads/<default-branch>`, checkout files, reset history, run generic `git fetch`, or use `gh repo sync`.

## Lifecycle sequence

For registered GitHub repositories, KIS requires refresh immediately before creating a governed worktree. Every composed workflow that merges through `kis_github_merge_registered_pull_request` also receives refresh immediately after merge; safe closeout then deletes the verified review branch and cleans the merged worktree.

The result reports local default branch, tracking ref, GitHub default branch, and one relation: `same_commit`, `tree_equivalent`, or `content_divergent`.
