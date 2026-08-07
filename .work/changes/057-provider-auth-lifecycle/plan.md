# Plan

1. Add failing tests for a provider-neutral persistent client proxy lifecycle.
2. Implement the lifecycle component with one outer FastMCP client context and injectable startup bootstrap.
3. Add strict repository settings contracts and repository-context source.
4. Replace GitHub provider-level repository/project settings with repository-local routing settings.
5. Replace `StatefulProxyClient` with one shared FastMCP `Client`, persistent provider lifespan, and one `get_me` bootstrap.
6. Update GitHub health/readiness and routing tests.
7. Reconcile schemas, sample settings, README, SPEC, platform concept, and operations guidance.
8. Run focused tests, architecture checks, change-workflow check, and canonical verification.
9. Review the complete diff, push the exact head, open a PR, verify CI, merge, reconcile closeout, and clean the isolated worktree and branch through the governed workflow.

## Reversal

The change is reversible by restoring the prior GitHub provider settings schema and server construction. No credential migration or persisted token transformation is introduced.
