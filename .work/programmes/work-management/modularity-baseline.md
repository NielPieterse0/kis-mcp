# Seam evidence (Gate 1)

Repository: tracked Git root (absolute path omitted)
Window: `90 days ago` | Relevant commits: 95 | Granularity: dir/3
Sampling: all enumerated units

| Unit | LOC | Commits | Distinct subjects | Fan-in | Fan-out | Top co-change peer |
|---|---:|---:|---:|---:|---:|---|
| `src/kis_mcp/capabilities` | 1848 (M) | 4 (M) | 4 (M) | 22 (M) | 1 (M) | tests/capabilities (1.0/0.042) (M) |
| `src/kis_mcp/discover` | 11948 (M) | 22 (M) | 21 (M) | 15 (M) | 2 (M) | tests/discover (0.818/0.189) (M) |
| `src/kis_mcp/providers` | 4530 (M) | 27 (M) | 26 (M) | 10 (M) | 9 (M) | tests/providers (0.481/0.137) (M) |
| `src/kis_mcp/tools` | 1682 (M) | 7 (M) | 6 (M) | 3 (M) | 5 (M) | src/kis_mcp/providers (0.857/0.063) (M) |
| `src/kis_mcp/workflows` | 719 (M) | 4 (M) | 4 (M) | 1 (M) | 4 (M) | src/kis_mcp/providers (1.0/0.042) (M) |

## Limits

- Distinct subjects are not RFC kinds; cluster them before scoring.
- Fan-in and fan-out are M only for Python and JavaScript/TypeScript-only inputs.
- Read-set/edit-set, hidden coupling, and test isolation remain U until measured separately.
