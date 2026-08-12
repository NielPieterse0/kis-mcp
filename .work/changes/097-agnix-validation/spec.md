# Change Specification: Agnix Validation

- **Change ID**: `097-agnix-validation`
- **Status**: Active
- **Risk Profile**: standard

## Outcome

Expose bounded read-only agnix agent-configuration validation through KIS Work without fix, watch, init, telemetry, schema, tools, or arbitrary-command authority.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`.
- Reuse the existing workflow composition and nested Work middleware patterns.
- Keep agnix optional; unavailable native execution degrades only this workflow.
- Runtime binary is generated state at `C:\Projects\kis-mcp\.temp\tools\agnix\0.45.0`, never committed.
- Preserve exactly HR-001, HR-002, and HR-003.

## Requirements

- **REQ-001**: Add `validate_agent_configuration(project, target="generic", strict=false, max_files=1000)` with no free-form agnix arguments.
- **REQ-002**: Invoke only the pinned agnix native binary with JSON output and bounded files; never pass fix/watch/mutation flags.
- **REQ-003**: Execute via nested Work process middleware so existing HR semantics remain authoritative.
- **REQ-004**: Validate project/target/limits structurally and return bounded findings plus tool provenance.
- **REQ-005**: Report missing, blocked, wrong-version, timeout, invalid-output, or process failures as `AGNIX_*` application errors, never HR codes.
- **REQ-006**: Update the managed bootstrap path and operator/current-implementation documentation without committing runtime binaries.

## Acceptance

1. Given a valid project, when validation runs, then only the fixed agnix validation command is executed through Work middleware.
2. Given attempted unsupported target/limit input, then validation fails before process execution.
3. Given unavailable or Application-Control-blocked agnix, then the workflow reports a bounded corrective `AGNIX_*` error without bypassing OS controls.
4. Given successful JSON output, then findings are bounded, deterministic, and contain no mutation authority.
5. Focused tests, scope check, full repository verification, and independent review pass on the exact head.

## Risks and recovery

- Risk: native binary may be blocked by endpoint controls at some paths. Mitigation: readiness/smoke evidence, no bypass logic.
- Risk: agnix output schema can evolve. Mitigation: conservative parsing and pinned version 0.45.0.
- Recovery: revert the batch; old managed runtime copy is retained recoverably under KIS quarantine.

## Out of scope

- agnix `--fix`, `--fix-safe`, `--fix-unsafe`, `init`, `watch`, telemetry changes, schema generation, tool-version management, or MCP mounting.
- Govern decisions based on agnix findings.
- Changes to HR-001/HR-002/HR-003.
