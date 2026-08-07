# Change 061 tasks

- [x] T1 — Implement empty-process preflight hardening and PowerShell terminating-error test semantics; Windows focused verification passed.
- [x] T2 — Implement provider startup state and runtime tool snapshot on one persistent client lifespan; focused provider verification passed.
- [x] T3 — Implement pre-lifespan GitHub discovery suppression plus current runtime capability/readiness refresh while preserving non-GitHub provider discovery; focused capability/platform verification passed.
- [x] T4 — Implement separate supervised OAuth/tunnel timing and live retained server stderr. The endpoint-owner false negative caused by the Windows `uv` launcher/child process model was repaired with a RED/GREEN ancestry regression; repeat supervised commissioning then reached `health=ready` and `tunnel_state=ready`.
- [x] T5 — Static governance, focused tests, canonical verification, supervised `kis-op` OAuth/startup/tunnel commissioning, authenticated GitHub reuse, and commissioning-status reporting are verified. The final governed metadata head requires the exact-head Windows gate before landing.
