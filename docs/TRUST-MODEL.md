# Trust Model and Hard Rules

## Operating assumption

`kis-mcp` is a private, single-operator, directly supervised local development system.

The operator, ChatGPT session, FastMCP gateway, Desktop Commander process, and repositories beneath `C:\Projects` form one closed working environment. The system is not intended for unattended or unsupervised implementation. The operator remains responsible for starting, stopping, upgrading, and supervising the gateway.

The trust assumption permits ordinary development tools to remain ordinary. It does not permit the three prohibited outcomes below.

## Enforcement boundary

FastMCP is the policy boundary in front of Desktop Commander.

Desktop Commander supplies normal file inspection, editing, searching, process, testing, and local development functions. The gateway does not fork or recreate those functions. It resolves the effects of each invocation and either forwards the call unchanged, rejects it for HR-001 or HR-002, or replaces delete intent with HR-003 quarantine behavior.

```text
operator-supervised ChatGPT
          |
          v
kis-mcp FastMCP boundary
          |
          v
Desktop Commander
          |
          v
C:\Projects
```

## Narrow invocation-effect enforcement

FastMCP MUST enforce the three hard rules at the narrowest reliable point: the complete concrete invocation and its proven resultant effects.

The gateway evaluates the selected tool, arguments, modes, working directory, explicit targets, composed command segments, and other resolved invocation facts together. It may block or transform only when those combined facts positively establish a prohibited HR-001, HR-002, or HR-003 outcome.

No individual prompt phrase, word, URL string, tool name, executable name, command name, argument flag, capability category, or possibility of misuse is independently sufficient to block an invocation.

Uncertainty is not proof. If the resolver cannot specifically establish the prohibited effect, the invocation MUST NOT be blocked under a hard rule. A future exact resolver and conformance test may be added when a concrete bypass combination is discovered.

A structural input error may reject an invocation that cannot be executed meaningfully, but it MUST remain distinct from an HR-001, HR-002, or HR-003 policy decision and MUST NOT be used as a substitute for proving a prohibited effect.

Network-only provider capabilities MAY be omitted from the exposed Work surface when every supported invocation necessarily produces HR-002 external-network access. Once such a capability is unexposed, redundant argument or URL-content blocks for that unavailable capability are unnecessary. General terminal and process tools remain available; only concrete invocations with a proven external-network effect may be blocked.

Provider-native restriction fields must not create a second policy boundary beneath FastMCP. For the pinned Desktop Commander provider, `blockedCommands` and `allowedDirectories` remain empty, are verified at startup, and are not modifiable through the exposed provider configuration contract. These are gateway integrity invariants, not additional reasons to deny an ordinary Work invocation.

## Approved project boundary

The approved write boundary is:

```text
C:\Projects
```

A path is inside the boundary only when it is the boundary itself or a true descendant after normalization. Similar prefixes such as `C:\Projects-old` are outside.

Reads outside the boundary are not prohibited by HR-001. A provider or operating system may still make a read unavailable for ordinary technical reasons.

## HR-001 — No writes outside `C:\Projects`

Block any invocation whose resolved effect creates, changes, moves, removes, generates, caches, logs, or otherwise writes data outside `C:\Projects`.

The rule applies to direct tools and indirect effects from commands, scripts, child processes, document generation, package managers, Git, temporary files, and provider configuration.

Moving a path modifies both the source and destination. A move from outside `C:\Projects` therefore violates HR-001 even when the destination is inside.

## HR-002 — No unrestricted external network through Work

The local Work surface must not expose provider capabilities whose every supported invocation is external-network-only or allow an exposed invocation whose resolved operation consumes an external target.

Concrete evidence may include an external target in a known network-client position, an explicit external package source or registry endpoint, a locally resolved external Git remote, or a provider configuration value that enables verified telemetry. A URL string, package-manager name, package operation, unresolved remote alias, unknown executable, or general ability to open a socket is not independently sufficient.

Provider-only network tools and modes are removed from the exposed contract and rejected as unsupported if manually supplied. They are not redundantly classified again by the policy resolver. Automatic provider activity is contained at startup only where the pinned provider source proves the external effect before ordinary invocation interception.

Explicit operator bootstrap and approved ChatGPT connectors operate through separate supervised boundaries. They are not ordinary Work tool calls.

## HR-003 — No permanent deletion

Delete-like intent must become a recoverable move to:

```text
C:\Projects\.kis-mcp\quarantine\<operation-id>\
```

Each operation stores the target intact and writes bounded restoration metadata. Restoration must not overwrite an existing original path.

If the target is outside the approved boundary, cannot be moved intact, or cannot be recorded safely, reject the operation. Permanent disposal of quarantine contents is an operator action outside normal Work.

## Non-rules

The following are not independent policy reasons:

- a tool or executable name;
- shell or process usage;
- broad capability;
- destructive-looking metadata;
- absence from an allowlist;
- lack of a custom wrapper;
- provider overlap;
- an approval or capability tier.

These may be evidence when resolving one of the three outcomes, but they do not create another rule.

## Supervision requirement

The operator must supervise:

- initial installation and upgrades that require network access;
- changes to the active project boundary or quarantine root;
- changes to the three rules;
- changes that alter how command intent is mapped to HR-001, HR-002, or HR-003;
- restoration or disposal of quarantined content;
- provider version changes and renewed conformance verification.

Repository configuration may be edited as project content, but active enforcement changes do not take effect safely until the gateway is restarted and verification is rerun.

## Availability rule

Normal Desktop Commander tools, including terminal and process tools, remain available by default.

The gateway evaluates the concrete invocation. It blocks or transforms only when the invocation resolves to HR-001, HR-002, or HR-003. Unknown tool names, broad schemas, incomplete static prediction, or lack of a specialized resolver do not create another restriction.

Conformance tests improve evidence that the three rules are correctly detected and enforced; they do not authorize otherwise permitted tools.

