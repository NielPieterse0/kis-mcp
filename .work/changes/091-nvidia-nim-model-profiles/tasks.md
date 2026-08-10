# Tasks: 091 NVIDIA NIM Model Profiles

- [x] T1 — Strict `nano` / `super` / `ultra` configuration and exact canonical model IDs.
- [x] T2 — Profile-aware NIM payload construction and non-secret readiness guidance.
- [x] T3 — Public advisory model selection, default Super behavior, invalid-combination handling, and provenance.
- [x] T4 — `.env/` containment, vault migration, and selected-`kis-dev` child environment injection.
- [x] T5 — Documentation and operator guidance for when to use Nano, Super, and Ultra; preserve Codex independent code/safety-review follow-up boundary.
- [x] T6 — Focused test suite, scope validation, full repository verification, and complete diff/static review.
- [x] T7 — Candidate `kis-dev` live commissioning of all three NVIDIA profiles without touching `kis-op`.
- [x] T8 — Integrate the verified candidate into `main`, verify the merged head, and publish it through the exact registered-GitHub path.

Post-branch operational signoff is intentionally performed only after this closed scope is merged and cleaned: restart `kis-dev` from the stable final `main`, verify the default Super path, verify `kis-op` remains ready, and write the exact-head PASS record to `C:\Projects\.kis-mcp\commissioning\091-nvidia-nim-model-profiles-final.json`. That generated-state record is the authoritative final commissioning evidence so recording the PASS does not create another Git head.
