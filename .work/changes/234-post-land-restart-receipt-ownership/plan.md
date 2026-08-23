# Plan

1. Add red worker regressions for stale receipt generations.
2. Serialize canonical receipt updates with a bounded exclusive lock.
3. Require worker-state ownership by landed SHA and worker PID; let `scheduled` acquire ownership.
4. Run focused restart tests and governed scope checks.
5. Review, publish, exact-head verify, merge, then live-bootstrap and verify 8011 plus canonical receipt ownership.
