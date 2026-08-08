# Skills Module Usage

## Load when

Read this reference when discovering, loading, reading, evaluating, creating,
or improving reusable Skills through kis-mcp.

## Runtime versus repository-local skills

The active runtime catalogue is rooted at:

```text
C:\Projects\.agents\skills
```

A repository's `.agents/skills` directory is development guidance for that
repository. It is not automatically part of the kis-mcp runtime catalogue.

Skills are reusable procedure packages. kis-mcp loads instructions and files;
it does not automatically execute arbitrary scripts from a skill.

## Read operations

### List

```text
list_skills(limit?, cursor?)
```

Returns bounded cards from the immutable active snapshot. Use the returned
cursor for pagination rather than increasing limits without need.

### Search

```text
search_skills(query, limit?)
```

Searches canonical skill identity and metadata. Use this before guessing a
skill ID.

### Load

```text
load_skill(skill_id)
```

Returns the `SKILL.md` entrypoint plus bounded catalogue evidence. After loading,
read only references required by that skill's own load conditions.

### Search files

```text
search_skill_files(skill_id, query, limit?)
```

Searches bounded relative file paths within one active skill.

### Read one file

```text
read_skill_file(skill_id, relative_path)
```

`relative_path` is relative to the skill root and uses forward-slash form. Do
not use absolute paths, traversal, or backslashes.

### Evaluate

```text
evaluate_skill(skill_id)
```

Returns structural evidence such as file counts, byte totals, snapshot identity,
and hashes. This is structural evidence, not proof of output quality or
automatic activation accuracy.

### Refresh

```text
refresh_skills()
```

Rebuilds the immutable catalogue atomically. One invalid source rejects the
candidate refresh and preserves the prior active snapshot.

## Mutation operations

### Create

```text
create_skill(skill_id, skill_md)
```

The current contract validates and publishes a complete **single-file** skill.
It stages beneath the configured KIS temp root, then publishes through ordinary
Work middleware.

Do not use this operation to publish a multi-file skill package that requires
references/assets/scripts; doing so would activate an incomplete package.

### Improve

```text
improve_skill(skill_id, relative_path, expected_sha256, content)
```

The hash precondition protects against silent overwrite after concurrent edits.
Always use the active file hash from current catalogue evidence and provide the
complete replacement text for that file.

## Structural rules

Current catalogue validation includes:

- lowercase hyphenated skill IDs;
- required `SKILL.md` `name` and `description`;
- configured file/skill byte limits;
- UTF-8 text handling;
- configured allowed suffixes;
- rejection of traversal, absolute relative-file paths, backslashes, links,
  reparse points, and configured hard-link cases.

`SKILLS_*` errors are structural/application errors. They are not additional Work
policy decisions.
