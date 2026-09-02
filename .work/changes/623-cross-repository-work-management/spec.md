# Change Specification: Cross Repository Work Management

- **Change ID**: `623-cross-repository-work-management`
- **Status**: Active

## Outcome

Restore cross-repository Work Management inventory and claim visibility for shared GitHub Projects while preserving repository-scoped creation safety.

## Authority and scope

- Authority: `AGENTS.md`, current Work Management contracts, issue #651, and live GitHub Project evidence.
- Inventory is scoped to the configured Project, not implicitly to the binding repository.
- Existing observed Project items may originate from any repository represented in that shared Project.
- New item creation remains restricted by the configured repository binding.
- Change 619 / issue #625 owns the separate live-record/reconcile input-contract defect.

## Requirements

- Inventory must not inject `repo:<binding.repository>` unless the caller explicitly requests it.
- Existing foreign-repository Project items must remain updateable by observed item identity.
- Same-repository behavior, pagination, field recovery, and explicit queries must remain intact.

## Acceptance

1. Shared Project inventory returns items from multiple repositories.
2. Work Management claim resolution accepts a Ready foreign-repository item.
3. Existing-item reconciliation updates may cross repository origins; create remains repository-bound.
4. Focused regressions and change-governance checks pass.

## Risks and recovery

- Broader inventory can increase result volume; existing bounded pagination remains authoritative.
- Recovery is a bounded revert; no persistent migration is introduced.

## Out of scope

- Canonical live-record/reconcile schema alignment owned by Change 619 / issue #625.
