# Projects and Context

## Load when

Read this reference when the task targets a project/repository other than the
current checkout, uses GitHub/Supabase/database/Docker Hub/work-management
routing, or requires a stable project identifier.

## Project-neutral rule

kis-mcp is intended to operate across projects beneath `C:\Projects`. Do not
hard-code `kis-mcp` as the target merely because that repository hosts the
server implementation.

Local Work and Discover operations should receive the actual absolute project
path. Provider operations should receive the explicit provider identifiers
required by their schemas.

## Project registry

The project-neutral architecture uses a KIS-owned central registry rather than
placing KIS configuration files inside each target repository.

Prefer:

```text
kis_list_projects()
kis_project_status(project_id)
```

The first returns configured project identities and non-secret routing bindings.
The second resolves one stable `project_id` to its current local/provider
coordinates.

A running instance may lag the checked-out repository. If either operation is
missing from the host surface, use capability discovery before assuming the
registry itself is unavailable.

## Stable identity versus mutable runtime state

Keep these concepts separate:

- `project_id`: KIS-stable identifier for one configured project.
- `local_root`: absolute path beneath `C:\Projects`.
- GitHub repository coordinate: explicit remote repository identity.
- GitHub Project binding: non-secret Project owner/type/number associated with a
  KIS project.
- Supabase project identifier/ref: explicit upstream project target.
- Database binding: stable binding ID plus engine/boundary and either a local project-relative SQLite path or an external canonical vault reference; credential values are not project identity.
- Docker Hub namespace binding: optional non-secret registry namespace associated with one KIS project; public/PAT authentication remains provider runtime state.
- Provider authentication: runtime/provider-owned session state, not project
  identity.

There is no universal mutable `active_project` authorization boundary. A
working directory may help resolve local relative behavior inside a process,
but it does not authorize a provider target.

## GitHub routing

Use explicit repository arguments required by the discovered GitHub operation.
A provider can remain authenticated across multiple project operations while
routing each call to a different registered repository.

Do not infer that authentication to GitHub authorizes every repository or
GitHub Project. Registered project bindings and provider-specific routing still
apply.

## Supabase routing

Supabase uses account-scoped OAuth while KIS keeps project routing explicit and
project-neutral. Project-targeted operations carry a registered upstream
`project_id`; bounded account discovery may be targetless, while targetless
mutations are rejected.

If an older running instance reports a different onboarding state through
`kis_provider_status`, follow that live contract rather than forcing the newer
checkout's assumptions into the call.

## Work-management routing

Work-management behavior remains separately configured and may be disabled even
when GitHub is ready. When enabled, prefer the stable KIS `project_id`; resolve
GitHub Project coordinates from current registry/settings evidence rather than
embedding a Project number in a prompt.

Reconciliation is preview-first. Apply behavior requires the operation's
explicit idempotency/revision controls and does not become safe merely because a
workflow recommends it.

## Target-resolution procedure

1. Use an explicit user-supplied path/project ID when unambiguous.
2. Otherwise query the project catalogue when those operations are available.
3. Confirm the resolved local/provider target before mutation or external calls.
4. Use that target consistently through Discover, Work, provider, and
   verification steps.
5. If the target cannot be resolved uniquely, return the concrete candidates or
   missing binding rather than silently defaulting to the kis-mcp repository.

## Do not persist mutable examples

Skill examples should use placeholders such as:

```text
<project-id>
C:\Projects\<project>
<owner>/<repository>
<provider-project-id>
```

Do not encode real repository bindings, project numbers, upstream refs, OAuth
state, or secrets as reusable defaults.
