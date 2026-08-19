# Change Specification: Repository Scoped Work Management Projection

- **Change ID**: `177-repository-scoped-work-management-projection`
- **Status**: Reviewable candidate
- **Risk Profile**: medium / public contract

## Outcome

Repair the repository-scoped Work Management projection and mutation binding proven defective by #318 while preserving the shared GitHub Project as the single Work Management authority.

## Authority and scope

- Authoritative Work Management state remains the configured shared GitHub Project.
- `ProjectBinding.repository` is a projection/query and routing boundary only; it does not create another source of truth.
- Owned production paths are the GitHub Project inventory and reconciliation adapters only.
- `work_management/service.py`, execution/verification, coordinator, and housekeeping paths are explicitly excluded.
- #318 verification is the prerequisite evidence establishing that #317 is required.

## Requirements

- Repository-bound inventory returns only items whose source repository matches the binding, case-insensitively.
- Repository filtering must happen before the public `item_limit` is counted.
- Foreign records must not cause a scoped inventory to report false truncation.
- Explicit unbound Project bindings retain cross-repository Project visibility.
- Reconciliation with an explicit source repository that conflicts with the selected repository binding must fail before provider I/O.
- Existing reconciliation idempotency and revision/CAS semantics must remain unchanged.
## Acceptance

1. Given a shared Project page containing foreign and local records, scoped inventory emits only the bound repository records and continues paging until the scoped limit or provider exhaustion.
2. Given exactly `item_limit` local records followed only by foreign records, scoped inventory is not falsely marked truncated.
3. Given a binding with `repository=None`, inventory may expose cross-repository Project records explicitly.
4. Given CREATE or UPDATE reconciliation with a foreign explicit `source_repository`, the adapter fails closed before any GitHub Project provider call.
5. Existing exact-target source matching, duplicate detection, idempotent replay, and stale-revision conflicts continue to pass.

## Risks and recovery

- Risk: filtering after a bounded shared Project read could hide local records or misreport truncation.
- Mitigation: scan provider pages while counting only matching repository records; retain bounded `max_pages` behavior and fail conservatively on page-bound exhaustion.
- Recovery: revert this isolated adapter commit; no schema migration or duplicated Work Management state is introduced.

## Out of scope

- #324/change 174 execution, verification, and VM work.
- #241/change 150 coordinator work.
- #251/#252/#253 and unrelated Work Management backlog.
- Agent B housekeeping-runner work.
- `work_management/service.py`, currently owned by active change 173.
- Merge or waiver of exact-head GitHub Actions evidence.