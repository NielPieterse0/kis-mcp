# Change Specification: NVIDIA NIM Model Profiles

- **Change ID**: `091-nvidia-nim-model-profiles`
- **Status**: Closed implementation scope; final exact-head runtime signoff is post-branch generated-state evidence
- **Development Level**: Complex
- **Risk Profile**: rigorous

## Outcome

Configure and commission NVIDIA-hosted Nemotron 3 Nano, Super, and Ultra profiles for the existing advisory review workflow, migrate the operator-supplied NVIDIA API key from plaintext bootstrap material into the KIS encrypted secret vault, provide explicit user guidance for choosing each model, and preserve the current Codex path for a separate follow-up slice that makes Codex an independent code-review and safety-review backend.

## Authority and scope

- Authoritative repository sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- External model authority: current NVIDIA Build/NIM model cards and hosted API examples for the exact three model IDs below.
- Owned paths: the paths declared in `scope.json`; no policy file is owned.
- Shared paths: none.
- Excluded paths: `policy/**` and unrelated providers/workflows.
- Dependencies: existing application secret vault, selected-instance launcher, NVIDIA provider, advisory code-review workflow, and `kis-dev` commissioning path.
- Integration owner: this change.

## Approved architecture

1. The plaintext bootstrap folder is not a runtime credential store. The operator-supplied `.env` folder is moved outside the repository, `.env/` is ignored, and the key is imported once into the existing application-managed encrypted vault.
2. Canonical NVIDIA configuration stores a non-secret vault reference plus the process environment variable name. Startup resolves only that reference and injects the value into the selected KIS server process as `NVIDIA_API_KEY`; the key is never placed in repository JSON, command arguments, MCP requests, provider status, or logs.
3. NVIDIA remains one provider/backend (`nvidia-nim`) with three named model profiles: `nano`, `super`, and `ultra`. The configured default is `super`.
4. `review_change_with_agent` accepts an optional NVIDIA model profile selector. Omitting it uses the configured default. A model selector supplied with a non-NVIDIA backend is rejected as an invalid request rather than silently ignored.
5. The hosted API client remains non-streaming inside KIS for this slice. This avoids adding an SSE parser to an advisory workflow that returns one bounded final result. The request still carries each model's NVIDIA-documented sampling and reasoning controls.
6. Model guidance is advisory metadata. It helps the operator choose a profile but does not authorize, block, or otherwise change HR-001 / HR-002 / HR-003 decisions.

## Model profiles and user guidance

### `nano`

- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Request defaults: `temperature=0.6`, `top_p=0.95`, `max_tokens=65536`, `reasoning_budget=16384`, thinking enabled, non-streaming in KIS.
- NVIDIA capability: approximately 33B parameters, 262K hosted context, multimodal understanding plus reasoning/tool-use capability.
- KIS guidance: use for fast first-pass review, focused diffs, routine regression/error-handling checks, triage, and repeated iterative review where responsiveness matters.
- Boundary: the current KIS review evidence path is text-only; Nano's image/audio/video capability is not exposed by this slice and must not be represented as available through `review_change_with_agent`.

### `super` — default

- Model: `nvidia/nemotron-3-super-120b-a12b`
- Request defaults: `temperature=1.0`, `top_p=0.95`, `max_tokens=16384`, `reasoning_budget=16384`, thinking enabled, non-streaming in KIS.
- NVIDIA capability: 120B total / 12B active model, up to 1M context, optimized for agentic workflows, coding, planning, tool use, RAG, long-context reasoning, and high-volume workloads.
- KIS guidance: default for normal substantive code reviews, multi-file changes, correctness and regression analysis, implementation-plan checks, and broad repository-context review. Choose it when Nano may be too shallow but Ultra is unnecessary.

### `ultra`

- Model: `nvidia/nemotron-3-ultra-550b-a55b`
- Request defaults: `temperature=1.0`, `top_p=0.95`, `max_tokens=16384`, `reasoning_budget=16384`, thinking enabled, non-streaming in KIS.
- NVIDIA capability: 550B total / 55B active frontier-scale reasoning model with up to 1M context, optimized for complex agentic workflows, coding, planning, tool use, long-context analysis, and high-stakes analytical workloads.
- KIS guidance: use when depth matters more than throughput: architecture changes, subtle cross-component regressions, complex concurrency/state reasoning, security-sensitive or safety-sensitive reviews, difficult failure analysis, and final high-confidence review of high-impact changes.

## Requirements

- **REQ-001 — Plaintext secret containment**: `.env/` must be ignored by Git. The existing operator bootstrap folder must remain outside the repository after migration and must never be staged or committed.
- **REQ-002 — Vaulted NVIDIA credential**: Store the API key at one canonical non-secret reference, `secret://provider/nvidia-nim/api-key`, using the existing KIS secret vault. Repository configuration stores only that reference and `NVIDIA_API_KEY` as the environment-variable name.
- **REQ-003 — Selected-instance secret injection**: `scripts/start-chatgpt.ps1` must resolve the NVIDIA secret only for the server child environment, clear transient plaintext references after process creation, and leave the peer KIS instance untouched.
- **REQ-004 — No secret disclosure**: No MCP tool, status result, error, startup state, command line, Git diff, or retained log may contain the NVIDIA API key.
- **REQ-005 — Strict three-profile settings**: NVIDIA settings must contain exactly `nano`, `super`, and `ultra`, each with an exact model ID and bounded sampling/reasoning fields. Unknown profiles or fields fail configuration loading.
- **REQ-006 — Default profile**: `super` is the configured default profile.
- **REQ-007 — Request correctness**: The NIM request must include the selected model ID, messages, temperature, top-p, max tokens, reasoning budget, thinking configuration where documented, and `stream=false`.
- **REQ-008 — Output budget support**: NVIDIA settings validation must permit Nano's configured `max_tokens=65536` without weakening other numeric validation.
- **REQ-009 — Explicit model selection**: The public advisory review operation accepts `model=null|nano|super|ultra`. Invalid aliases are structural invalid requests. `model` with `backend=codex-cli` is invalid rather than ignored.
- **REQ-010 — Selection provenance**: Successful NVIDIA review results identify the selected profile and exact model ID without exposing credentials or reasoning traces.
- **REQ-011 — Guidance visibility**: Provider/status or review metadata and the review tool description must make the practical Nano/Super/Ultra selection guidance discoverable to the operator.
- **REQ-012 — Existing fallback containment**: Existing NVIDIA/Codex preferred/fallback behavior must not regress in this slice. No Codex executable installation, authentication, or safety-review implementation is claimed here.
- **REQ-013 — Codex follow-up boundary**: The next Codex slice will make local Codex independently selectable for code review and safety/security review. This NVIDIA slice must not couple model selection to a design that prevents those independent Codex review modes.
- **REQ-014 — Policy invariance**: The change must not alter the three-rule policy or create a model/backend choice as a fourth Work rule.
- **REQ-015 — Live commissioning**: `kis-dev` must be started from the candidate change without stopping or modifying the running `kis-op`; each of Nano, Super, and Ultra must complete a bounded live NVIDIA review/inference path, then final integrated-head `kis-dev` commissioning must re-prove readiness and the default review path.

## Acceptance

1. **Given** the primary checkout, **when** Git status is inspected, **then** no `.env` material is tracked or untracked in the repository and `.env/` is ignored.
2. **Given** the NVIDIA secret reference, **when** secret metadata is listed, **then** the reference exists while no plaintext is returned.
3. **Given** `kis-dev` startup, **when** provider status is read, **then** `nvidia-nim` is `ready` and reports only non-secret model/profile metadata.
4. **Given** each profile alias, **when** the request builder is exercised, **then** the exact NVIDIA model ID and configured request fields are present and `stream` is false.
5. **Given** `model=nano|super|ultra`, **when** a bounded live review is run through `kis-dev`, **then** the selected profile succeeds and the returned provenance identifies that profile/model without credential disclosure.
6. **Given** no model argument, **when** NVIDIA review is requested, **then** `super` is selected.
7. **Given** an invalid model alias or a model argument with `backend=codex-cli`, **when** review is requested, **then** the result is an explicit invalid request and no provider call occurs.
8. **Given** provider/tool guidance, **when** the operator inspects the surface, **then** Nano is described for fast/focused review, Super as the normal default, and Ultra for deepest/high-impact analysis; Nano multimodality is explicitly identified as outside the current text-only KIS review path.
9. **Given** the full repository verifier on the current change head, **when** it completes, **then** configuration, tests, policy invariants, change governance, and repository checks pass.
10. **Given** the final integrated head, **when** `kis-dev` is restarted and commissioned, **then** health is ready, NVIDIA is ready, the default Super path succeeds, and the existing `kis-op` instance remains independently available.

## Verification strategy

- Test-first focused NVIDIA settings/client tests for profile parsing, exact payloads, numeric bounds, redaction, and response handling.
- Test-first advisory workflow tests for model selection, defaulting, invalid combinations, provenance, fallback preservation, and user guidance.
- Launcher/secret tests proving canonical vault reference resolution, selected-server environment injection, clearing behavior, and no log/state disclosure.
- Change-scope validation followed by canonical `scripts/verify.ps1` on the exact change head.
- Live candidate `kis-dev` commissioning of all three hosted profiles.
- Final integrated-head `kis-dev` restart and default-path commissioning.

## Risks and recovery

- **Secret exposure**: highest risk. Mitigate by vault import without echoing plaintext, process-scoped injection, redaction tests, and quarantining/bootstrap cleanup only after successful vault resolution.
- **Hosted API parameter drift**: exact profile tests and live per-model commissioning catch mismatches. Recovery is a JSON/profile correction without policy changes.
- **Long output or latency**: retain configured timeout/output budgets and non-streaming KIS behavior; callers can choose Nano for responsiveness or Ultra only when deeper analysis is warranted.
- **Launcher regression**: selected-instance tests must prove `kis-dev` secret injection does not alter or terminate `kis-op`. Recovery is to stop only the candidate `kis-dev` and revert the change branch.
- **Configuration incompatibility**: settings loading remains strict. Reverting the branch restores the prior single-model configuration.

## Out of scope

- Installing or authenticating Codex CLI.
- Implementing Codex independent code-review or safety-review modes; that is the next separately commissioned slice.
- Multimodal evidence ingestion for Nano.
- General-purpose NVIDIA passthrough tools.
- Streaming/SSE exposure through KIS.
- Changes to HR-001, HR-002, or HR-003.
