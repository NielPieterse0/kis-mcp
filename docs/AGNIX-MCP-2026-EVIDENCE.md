# Agnix MCP 2026 Quality Evidence

Issue: #568

## Exemplar review provenance

The issue named three local exemplar paths: `C:\Projects\mcp-app2`, `C:\Projects\mcp-app-figma`, and `C:\Projects\mcp-app-visual-web`.
On 2026-09-03 all three paths were absent from the commissioned workstation. A GitHub repository search for `mcp-app2` under the repository owner also returned no accessible match.
No exemplar-specific finding is therefore asserted here. The missing source material is recorded as an evidence limitation rather than inferred.

The reusable implementation operates on real Agnix diagnostics returned by the existing pinned `validate_agent_configuration` workflow. It preserves each diagnostic and adds a stable MCP-quality classification, allowing later exemplar runs to populate the same evidence contract without code changes.

## KIS gap and adoption matrix

| Concern | KIS gap before #568 | Evidence class | Reuse stages | Disposition |
| --- | --- | --- | --- | --- |
| Namespaced resources | Raw diagnostics had no reusable MCP classification | `resource_namespaces` | discovery, scaffold, review | Implemented |
| MCP Tasks | Task findings were not distinguishable from app findings | `mcp_tasks` | scaffold, task execution, completion | Implemented |
| Required instructions | No normalized instruction-conformance evidence | `required_instructions` | scaffold, task execution, review | Implemented |
| Elicitation safety | Safety findings were present only as raw diagnostics | `elicitation_safety` | scaffold, task execution, review | Implemented |
| Sampling/retry | Retry/sampling quality was not promoted as reusable evidence | `sampling_retry` | task execution, review | Implemented |
| Tool result/schema consistency | Schema diagnostics lacked lifecycle reuse metadata | `tool_result_schema` | scaffold, task execution, completion | Implemented |
| Files spec migration | Files-related findings had no canonical migration category | `files_spec` | discovery, scaffold, review | Implemented |

## Evidence contract

`validate_agent_configuration` remains the single Agnix execution path. Its existing response is additive: `quality_evidence` is derived from the bounded diagnostic set. Each item contains:

- `category`: one of the seven MCP baseline categories above, otherwise `app_specific`;
- `scope`: `mcp_baseline` or `app_specific`;
- `reuse_stages`: lifecycle stages where the evidence should be consumed;
- `diagnostic`: the original Agnix diagnostic without lossy rewriting.
