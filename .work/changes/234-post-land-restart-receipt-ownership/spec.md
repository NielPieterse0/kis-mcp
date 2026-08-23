# Specification

## Problem

A post-land restart worker remains blocked while its `kis-dev` launcher is alive. When a later landing restarts `kis-dev`, the older worker resumes, observes launcher exit, and writes its older terminal receipt over `post-land-restart/latest.json`. Live verification then sees stale failure evidence even though the newer runtime is healthy.

## Required behavior

- `scheduled` receipt creation acquires canonical latest-receipt ownership for one `(landed_sha, worker_pid)` generation.
- Worker states may update `latest.json` only while the same generation still owns it.
- A stale worker with a different landed SHA or worker PID must not overwrite newer canonical evidence.
- If a worker has lost receipt ownership before synchronization or launch, it exits successfully before Git or runtime lifecycle side effects.
- Receipt update serialization must remain bounded and compatible with Windows PowerShell 5.1 and `pwsh.exe`.
- Preserve atomic replacement, `kis-dev`-only targeting, and no `kis-op` lifecycle management.

## Acceptance criteria

1. Regression tests prove stale different-SHA and stale same-SHA/different-worker generations cannot overwrite a newer receipt.
2. Existing post-land restart tests remain green.
3. The landed runtime restarts on 8011; after bootstrapping past the pre-fix worker, canonical receipt evidence remains owned by the healthy current generation.
