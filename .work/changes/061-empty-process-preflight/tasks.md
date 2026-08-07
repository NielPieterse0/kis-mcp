# Change 061 tasks

- [x] T1 — Implement empty-process preflight hardening and PowerShell terminating-error test semantics; Windows focused verification passed.
- [x] T2 — Implement provider startup state and runtime tool snapshot on one persistent client lifespan; focused provider verification passed.
- [x] T3 — Implement pre-lifespan GitHub discovery suppression plus current runtime capability/readiness refresh while preserving non-GitHub provider discovery; focused capability/platform verification passed.
- [x] T4 — Implement separate supervised OAuth/tunnel timing and live retained server stderr. First live run completed OAuth and HTTP startup but exposed an endpoint-owner false negative caused by the Windows `uv` launcher/child process model; repaired with a RED/GREEN ancestry regression. Repeat live commissioning remains pending.
- [ ] T5 — Static governance, focused tests, and canonical verification are green; exact-head Windows CI, repeat supervised commissioning, final ready/closeout, and landing decision remain.
