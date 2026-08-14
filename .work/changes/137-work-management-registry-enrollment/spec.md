# Change Specification: Work Management Registry Enrollment

- **Change ID**: `137-work-management-registry-enrollment`
- **Status**: Approved
- **Complexity**: `medium`
- **Risk Triggers**: `architecture_boundary`, `public_contract`

## Outcome

Make every centrally registered KIS project inherit the shared Work Management backend deterministically, preserving repository-neutral local projects and single Project-coordinate ownership, so defect #164 and the residual #177 portfolio dependency can close.

## Authority and scope

- `settings/projects.settings.json` remains the central project-enrolment authority.
- Work Management backend configuration remains authoritative for backend coordinates and explicit per-project overrides.
- The shared GitHub Project coordinate remains registered once; non-owner projects must not duplicate it.
- This change modifies only Work Management registry bridging, its public contract/schema, focused tests, and the canonical workflow rule in `AGENTS.md`.

## Requirements

- **REQ-001:** Every centrally registered project is represented in the effective Work Management project set.
- **REQ-002:** Explicit managed-project overrides remain valid but must reference a registered project and may not contradict its local root or GitHub repository identity.
- **REQ-003:** A single configured Work Management backend may be inherited automatically; multiple backends without an explicit mapping must fail with an actionable ambiguity error.
- **REQ-004:** Registered projects without a GitHub repository remain valid repository-neutral Work Management identities with `repository = null`.
- **REQ-005:** Backend Project coordinates remain deduplicated and conflict-checked across registered projects.

## Acceptance

1. Given the current central registry, effective Work Management enrolment contains the same project IDs.
2. Given a repository-neutral registered project, Work Management loads it without inventing a GitHub repository binding.
3. Given a non-owner GitHub-bound project, inventory and shared-schema status can use the shared backend without duplicating the Project coordinate.
4. Given more than one backend and a project without an explicit mapping, configuration fails closed with an actionable ambiguity message.
5. Existing explicit project/backend mappings continue to behave identically.

## Risks and recovery

- Risk: automatic enrolment could silently choose the wrong backend in a future multi-backend portfolio.
- Mitigation: automatic enrolment is permitted only when exactly one backend exists.
- Recovery: restore the prior five-file implementation; no external state migration is required.

## Out of scope

- Provisioning missing GitHub Project custom fields/options/views.
- Duplicating Project #1 coordinates into every repository binding.
- Unrestricted GraphQL/REST access.
