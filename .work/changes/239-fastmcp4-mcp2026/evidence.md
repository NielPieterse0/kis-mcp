# Change 239 Evidence

## MCP 2026-07-28 source resolution

Authority root: `C:\Projects\References\mcp-specification\mcp-docs-2026-07-28-direct-md-clean\markdown\000-index.md`.
Schema authority: `055-specification-schema-reference.md`.

| Page | Requirement resolved | Disposition |
|---|---|---|
| `029-specification-overview.md` | Stateless requests; request `_meta`; required modern `resultType`; default JSON Schema 2020-12 | FastMCP 4 owns protocol parsing/serialization; KIS request telemetry is correlation-only; wire/schema tests added. |
| `030-specification-versioning-and-compatibility.md` | Modern `server/discover`; no modern initialize handshake; per-request protocol/capabilities; dual-era compatibility permitted | FastMCP 4 owns negotiation. KIS observes `server/discover`; `initialize` remains only for legacy dual-era observability. |
| `032-specification-multi-round-trip-requests.md` | Follow-up interactions are independent requests with explicit state | Evaluated. Current selected KIS long operations require no mid-flight input; future trigger captured in Work #505. |
| `033-specification-subscriptions.md` | Subscription state is not connection-reconnect authority; reconnect requires re-subscription | Evaluated. KIS Tasks use normative polling today; optional push path captured in Work #499. |
| `034-specification-cancellation.md` | Cancellation is cooperative; transport cancellation must not imply durable cancelled authority; max execution deadline remains | FastMCP owns task/request cancellation signal; KIS verification propagates cancellation to its owned child PID and preserves execution deadline. |
| `035-specification-progress.md` | Progress is monotonic, bounded to active request/task, with useful messages | KIS verification reports monotonic activity progress through FastMCP `Context.report_progress`. |
| `036-specification-overview.md` / `037-specification-stdio.md` / `038-specification-streamable-http.md` | Transport is a binding; request body metadata is authoritative; modern HTTP is stateless per POST and does not use protocol sessions | FastMCP 4 owns transport mechanics. KIS retains stdio plus configured stateless loopback HTTP and does not use transport/session state as Work authority. |
| `047-specification-discovery.md` | Modern capability discovery is explicit and request-scoped | FastMCP 4 owns `server/discover`; KIS boundary observability records only bounded method/correlation metadata. |
| `050-specification-tools.md` | Tool schemas default to JSON Schema 2020-12; `ResourceLink` is valid content; modern results use discriminators | KIS tests validate generated schemas under Draft 2020-12 and exercise `ResourceLink` through a real FastMCP tool result. |
| `051-specification-caching.md` | Cache TTL describes freshness, not work/task lifetime | Evaluated. KIS does not use caching as execution durability or timeout authority. |
| `055-specification-schema-reference.md` | Modern `Result.resultType`, task/complete discrimination, wire camelCase contracts | KIS tests prove snake_case FastMCP/Python objects serialize to correct MCP wire aliases and task creation/terminal retrieval expose the expected discriminators. |
| `056-extensions-extensions-overview.md` / `057-extensions-extension-support-matrix.md` | Extensions are explicit opt-in and client support varies | Tasks are optional; non-Tasks clients retain synchronous tool behavior. |
| `063-extensions-tasks.md` | Per-request Tasks capability; durable task handle across client reconnect; polling/status/result; cooperative cancellation; optional notifications; mid-flight input | FastMCP `TasksExtension` + optional `TaskConfig` implement the protocol. KIS preserves its existing Work/execution/receipt authority and owns process/deadline/stall semantics. |

## FastMCP-owned versus KIS-owned behavior

FastMCP 4 owns modern discovery/version/capability parsing, Tasks protocol methods and task result models, per-request extension negotiation, tool wire aliases, request cancellation delivery, and the process-local Docket task store.

KIS owns selection of which tools may become Tasks, durable Work/execution/receipt/fencing authority, execution deadlines, verification stall detection, bounded progress messages, child-process termination where KIS owns the PID, provider composition, Supabase invisibility, and regression/commissioning evidence.

An MCP task ID is never a substitute for a KIS Work record, execution identity, mutation receipt, source revision, or coordinator fence.
## Deferred high-value MCP work

- **#498 — Persist MCP Task handles across KIS server restarts.** Trigger: a supported deployment requires pre-restart task IDs to survive a KIS process restart, or KIS becomes multi-worker/multi-instance. Current #475 scope proves client disconnect/reconnect while the same service remains running; FastMCP's default task store is process-local.
- **#499 — Adopt MCP Task status push notifications when they provide value.** Trigger: FastMCP plus the deployed client support `subscriptions/listen` / task notifications and measured polling overhead or status latency justifies the subscription path. MCP 2026 explicitly defines polling as the default.
- **#505 — Support MCP Task `input_required` for mid-flight operator interaction.** Trigger: a selected long workflow actually requires input after execution starts and the deployed FastMCP/client combination supports Tasks input/update. Current selected operations receive required input at invocation time.

All three issues were reconciled into KIS Work Management as Inbox items. None is required for #475 acceptance under the current runtime/client behavior.

## Compatibility boundary

Literal MCP wire keys such as `inputSchema`, `outputSchema`, `readOnlyHint`, and `resultType` remain correct when serializing or parsing protocol data. KIS-owned Python-object access uses the FastMCP/MCP SDK v2 snake_case surfaces. `initialize` remains in boundary telemetry only to observe legacy dual-era clients; modern behavior uses `server/discover` and does not infer authority from a handshake or session.

## Commit-bound review fallback

All six required automated specialist review routes on pre-publication commit `b7ae98797e7e7ccf40095790d4899b955faa6f5c` stopped before reviewer invocation because the exact change exceeded the bounded evidence projector. Each correctly returned `manual_fallback.required=true`; none was treated as a pass.

The exact-diff fallback found and fixed two blocking issues:

1. `settings/kis-mcp.settings.json` still declared FastMCP `3.4.4` while `pyproject.toml`, the lock, and the environment used `4.0.0b3`. The setting is now `4.0.0b3`, the governed scope owns that file, `load_runtime_config()` reports the same version, and `tests/test_config.py` passes.
2. Verification stall time was measured from before `start_process`, so slow process launch could consume stall budget despite fresh launch/output evidence. Initial process/output evidence now resets only the stall clock; the independent maximum execution deadline is unchanged. Regression coverage proves both properties.

Post-fix focused evidence: changed-test set `152 passed`; provider lifecycle/gateway/Tasks/wire set `50 passed`; verification execution/tool set `16 passed`; configuration set `11 passed`; `git diff --check` and `scripts/change-workflow.ps1 check` pass. All six specialist routes were rerun on post-fix immutable head `19f4ad9174bd0c66af88999e1375f47401b93f40`; each again stopped at the bounded evidence projector with `manual_fallback.required=true`, so the completed exact-diff fallback remains the review authority. No new finding was introduced by the post-fix diff.

## Exact-head CI follow-up

GitHub canonical verification run `32914802517` failed at exact PR head `bbbaeefd38b915e1f98dcfba8de33671d309c893` on three regressions: two stale tests expected parked Supabase in provider status, and FastMCP 4 path screening intercepted the Skills traversal case before KIS could preserve `SKILLS_PATH_UNSAFE`. CI triage also confirmed that Supabase was filtered only after composition, so its builder could still run.

The follow-up disables Supabase in an effective copy of provider runtime settings before `compose_provider_runtime`, while retaining its checked-in parked configuration and filtering its disabled result from user-visible status. The Skills supporting-resource template exempts only its `path` parameter from FastMCP's generic path screening; `SkillCatalogue.read_skill_resource_bytes` remains the stricter path authority and preserves `SKILLS_PATH_UNSAFE`.

Follow-up evidence: the exact three-failure set passes; full `tests/providers` plus `tests/skills` passes; changed-file Ruff passes; `git diff --check` passes; and `scripts/change-workflow.ps1 check` passes. Architecture re-review found no blocking issue. API-contract review raised product uncertainty about disabling Supabase and the path exemption, but both are resolved by approved REQ-012 plus the existing direct and FastMCP traversal regression tests; no implementation blocker remains.
