# Closeout: Stale Selected-Instance Recovery

## Implemented scope

- Added selected-runtime identity matching independent of Python executable provenance.
- Preflight now reclaims exact selected-instance runtime processes even when stale/noncanonical.
- Newly launched runtime ownership still requires canonical Python provenance.
- Unrelated port owners remain fail-closed.

## Delivery

- Issue: #604.
- Parent acceptance: #600.
- Pending focused verification, exact-head CI, merge, live recovery acceptance, and cleanup.