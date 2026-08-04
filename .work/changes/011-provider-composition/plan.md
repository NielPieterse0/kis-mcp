# Plan: 011 Provider Composition

1. Register the emergency-path change metadata before implementation edits.
2. Add failing tests for Desktop Commander descriptor/readiness and three-provider composition.
3. Implement the Desktop Commander adapter using existing Work builder and offline readiness.
4. Implement explicit platform registry/service factories using the merged GitHub and Supabase registration APIs.
5. Keep composition imports explicit through the new modules; do not edit the shared package export surface.
6. Add bounded implementation documentation.
7. Run focused tests, complete verification, change scope check, and whitespace validation.
8. Commit, push, open a reviewable PR, and merge only after exact-head verification.
