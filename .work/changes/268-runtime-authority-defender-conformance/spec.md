# Change Specification: Runtime Authority Defender Conformance

- **Change ID**: `268-runtime-authority-defender-conformance`
- **Status**: Active
- **Complexity**: medium
- **Risk triggers**: `security`, `persistent_state`

## Outcome

Make the kis-mcp Python environment and Serena installation derive from an explicitly verified shared-system CPython, prohibit uv-managed Python fallback, classify Node separately from native helpers, and prove the resulting runtime model without weakening Defender/SAC.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/OPERATIONS.md`, provider/runtime settings and tests.
- Work source: `NielPieterse0/kis-mcp#541` / `WORK-541`.
- Owned paths are exactly those declared by `scope.json`.
- Commodity `.venv` remediation is excluded; commodity evidence is input only.
- No Defender/SAC exclusions, trust-folder assumptions, broad `C:\Projects` migration, or relocation-as-trust remediation.

## Requirements

- **REQ-001**: Resolve CPython through a declared system-runtime selector and require the configured Authenticode publisher/version before environment construction.
- **REQ-002**: Disable uv-managed Python fallback and bind `uv` environment construction to the verified interpreter.
- **REQ-003**: Preserve an incompatible generated KIS environment through canonical quarantine before rebuilding it.
- **REQ-004**: Build Serena acquisition/candidates from the same verified host and persist host provenance in manifests.
- **REQ-005**: Treat signed Node as host evidence only; inventory `.node` helpers independently.
- **REQ-006**: Validate real candidate imports/tests and correlate fresh Code Integrity 3033/3077 evidence.

## Acceptance

1. The configured system Python resolves to Python 3.11 with a valid Python Software Foundation Authenticode signature.
2. A clean candidate KIS environment is constructed with `--no-managed-python` and reports the configured shared-system Python as `sys.base_prefix`.
3. Focused startup/provider/runtime tests pass from that candidate environment.
4. Native Python and Node helper inventory is captured separately from host-runtime signatures.
5. No attributable Code Integrity 3033/3077 event occurs during the candidate workload window, or any event is explicitly classified and remediated.
6. Serena and runtime operator documentation reflects the implemented authority model.

## Risks and recovery

- Rebuilding the live KIS venv can disrupt a running gateway; validate a separate candidate first and perform live replacement only through the supervised bootstrap/restart sequence.
- A package may be unsigned yet execute under current Windows policy; signature status alone is not a PASS/FAIL verdict. Code Integrity plus canonical execution is the acceptance signal.
- Recovery preserves the prior generated environment beneath the KIS quarantine root.

## Out of scope

- Commodity, College, ChatGPT-skill, and import-isolate repository-local remediation.
- Changing Defender or Smart App Control policy.
- Migrating Node, Python, or `uv` solely to place them under `C:\Projects`.
