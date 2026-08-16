# kis-mcp

`kis-mcp` is a private, directly supervised repository platform for local development, repository intelligence, provider/tool composition, governed workflows, and recoverable operations.

Current implemented product truth belongs to [`SPEC.md`](SPEC.md). The approved target architecture belongs to [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md). Operator procedures belong to [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

The Work path has exactly three prohibited outcomes. Their semantics are owned by [`docs/TRUST-MODEL.md`](docs/TRUST-MODEL.md): writes outside `C:\Projects`, unrestricted external-network effects through Work, and permanent deletion instead of recoverable quarantine.

## Documentation and authority

This README is the human landing page and navigation index. It does not independently define product behavior, implementation status, policy doctrine, configuration values, or operator procedure.

Repository-wide documentation ownership and conflict routing are defined in [`AGENTS.md`](AGENTS.md). Load the smallest canonical owner needed for the task:

| Need | Canonical entry |
|---|---|
| Repository workflow and documentation routing | [`AGENTS.md`](AGENTS.md) |
| Current architecture, interfaces, and implementation state | [`SPEC.md`](SPEC.md) |
| Trust model and HR-001 / HR-002 / HR-003 semantics | [`docs/TRUST-MODEL.md`](docs/TRUST-MODEL.md) |
| Approved target architecture | [`docs/PLATFORM-CONCEPT.md`](docs/PLATFORM-CONCEPT.md) |
| Installation, startup, commissioning, verification, and recovery | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) |
| Durable module contracts | `docs/*-MODULE-PRODUCT-SPEC.md` |

Historical `.work/changes/**` and `docs/development/**` records preserve evidence from their original work. They are not current product or operator authority.

## Repository layout

```text
AGENTS.md                              repository instructions and documentation routing
SPEC.md                                current product and implementation boundary
docs/TRUST-MODEL.md                    trust assumptions and three hard rules
docs/PLATFORM-CONCEPT.md               approved target architecture
docs/OPERATIONS.md                     canonical operator entry and task index
docs/operations/**                     scoped operator runbooks
docs/*-MODULE-PRODUCT-SPEC.md          durable scoped module contracts
settings/                              canonical JSON settings
policy/kis-mcp.policy.json             machine-readable three-rule declaration
contracts/                             versioned schemas and contracts
src/kis_mcp/                           platform implementation
tests/                                 verification and regression coverage
scripts/                               bootstrap, startup, workflow, smoke, and verification entry points
.work/changes/<change-id>/             active change record; historical after merge
```

## Getting started

Use [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the current bootstrap, startup, provider, ChatGPT-facing runtime, commissioning, verification, and recovery procedures. The root Operations page is a task index; load only the linked runbook needed for the operation.

## Development changes

Use the governed change workflow in [`AGENTS.md`](AGENTS.md). Active repository changes live under `.work/changes/<change-id>/` with isolated worktrees. After merge, those records become historical evidence; durable consequences belong in their canonical product, trust, policy, operations, or machine-readable owner.

## Verification

The canonical repository verification entry point is:

```powershell
pwsh -File .\scripts\verify.ps1
```

During normal development, prefer focused affected checks. Pull requests to `main` own the canonical full verification on the exact GitHub head; see [`AGENTS.md`](AGENTS.md) and [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the governing workflow.